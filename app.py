import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from config import config
from database.models import db, User, Config, Prompt, Platform, AIModel, AIProviderKey

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

login_manager = LoginManager()
csrf = CSRFProtect()
scheduler = BackgroundScheduler(
    timezone="Africa/Cairo",
    jobstores={'default': MemoryJobStore()}
)

# Global app reference — set in create_app, used by scheduler jobs
_app_instance = None


# ── Scheduler job functions (must be module-level for APScheduler) ────────────

def _idea_job_runner():
    if _app_instance:
        from services.workflow_service import run_idea_factory
        run_idea_factory(_app_instance)


def _post_job_runner():
    if _app_instance:
        from services.workflow_service import run_post_engine
        run_post_engine(_app_instance)


def _keep_alive_runner():
    try:
        import requests as req
        port = os.environ.get('PORT', '7860')
        req.get(f'http://localhost:{port}/health', timeout=8)
    except Exception:
        pass


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(config_name=None):
    global _app_instance

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'يرجى تسجيل الدخول أولاً'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.api import api_bp
    from routes.workflow import workflow_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(workflow_bp)

    @app.route('/health')
    def health():
        try:
            db.session.execute(db.text('SELECT 1'))
            db_ok = True
        except Exception:
            db_ok = False
        return jsonify({
            'status': 'ok' if db_ok else 'degraded',
            'db': db_ok,
            'scheduler': scheduler.running,
            'time': datetime.utcnow().isoformat(),
        }), (200 if db_ok else 503)

    @app.context_processor
    def inject_globals():
        try:
            from database.models import Post
            pending = Post.query.filter_by(status='NEW').count()
        except Exception:
            pending = 0
        return {'pending_count': pending}

    with app.app_context():
        db.create_all()
        _seed_admin(app)
        _seed_defaults()
        _seed_from_env()

    _app_instance = app
    _setup_scheduler(app)

    from services.telegram_bot import start_bot
    start_bot(app)

    return app


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _seed_admin(app):
    if not User.query.filter_by(username=app.config['ADMIN_USERNAME']).first():
        user = User(username=app.config['ADMIN_USERNAME'])
        user.set_password(app.config['ADMIN_PASSWORD'])
        db.session.add(user)
        db.session.commit()
        logger.info(f"Admin user '{app.config['ADMIN_USERNAME']}' created")


def _seed_from_env():
    """Sync HuggingFace Secrets / env vars → DB on every startup."""
    from database.models import Config as Cfg
    synced = 0
    for db_key, env_name in Cfg._ENV_MAP.items():
        env_val = os.environ.get(env_name, '').strip()
        if not env_val:
            continue
        existing = db.session.get(Cfg, db_key)
        if not existing:
            db.session.add(Cfg(key=db_key, value=env_val))
            synced += 1
        elif existing.value != env_val:
            existing.value = env_val
            synced += 1
    if synced:
        db.session.commit()
        logger.info(f"Synced {synced} env vars → DB")


def _seed_defaults():
    defaults = {
        'niche': 'تربية خاصة → Special Education 📚\nالإعاقة العقلية → Intellectual Disability 🧠\nاضطرابات التواصل → Communication Disorders 💬\nاضطراب التعلم المحدد → Specific Learning Disorder ✏️\nApplied Behavior Analysis',
        'image_ratio_percent': '90', 'image_model': 'flux',
        'image_width': '1080', 'image_height': '1350',
        'delay_min_seconds': '60', 'delay_max_seconds': '420',
        'idea_factory_time': '08:00',
        'sched_1': '09:00', 'sched_2': '13:00', 'sched_3': '17:00', 'sched_4': '21:00',
        'frame_opacity': '100',
    }
    for k, v in defaults.items():
        if not db.session.get(Config, k):
            db.session.add(Config(key=k, value=v))

    for name in ['facebook', 'instagram', 'twitter', 'threads', 'linkedin']:
        if not db.session.get(Platform, name):
            db.session.add(Platform(name=name, enabled=True, settings='{}'))

    for stage, provider, model_id in [
        ('idea_factory',    'cohere', 'command-r7b-arabic-02-2025'),
        ('post_writer',     'cohere', 'command-r7b-arabic-02-2025'),
        ('image_prompt',    'cohere', 'command-r-08-2024'),
        ('ig_caption',      'cohere', 'command-r7b-arabic-02-2025'),
        ('x_caption',       'cohere', 'command-r7b-arabic-02-2025'),
        ('threads_caption', 'cohere', 'command-r7b-arabic-02-2025'),
        ('linkedin_caption','cohere', 'command-r-plus-08-2024'),
    ]:
        if not db.session.get(AIModel, stage):
            db.session.add(AIModel(stage=stage, provider=provider, model_id=model_id))

    _seed_prompts()
    db.session.commit()


def _seed_prompts():
    prompts = [
        ('idea_factory', 'command-r7b-arabic-02-2025', 0.9, 4096,
         'You are a world-class Arabic content strategist. Output ONLY a valid JSON array.',
         'NICHE: {niche}\nTotal: {total_ideas} | Posted: {total_posted} | Pending: {total_pending}\nSaturated: {saturated_topics}\nRecent: {recent_ideas_text}\nArchive: {all_ideas_text}\nStyles: {recent_styles}\nOpenings: {recent_openings}\n\nGenerate 10 original ideas. JSON array only:\n[{"idea":"...","keywords":["#tag"],"tone":"...","writing_style":"...","opening_type":"..."}]'),
        ('post_writer', 'command-r7b-arabic-02-2025', 0.85, 4096,
         'You are a world-class Arabic content writer. Write in pure Egyptian Arabic colloquial dialect.',
         'Specialist in: {niche}\nStyle: {writing_style} | Opening: {opening_type}\nIdea: {idea}\nKeywords: {keywords}\nTone: {tone}\n\nWrite Facebook post 600-1000 words. Egyptian Arabic only. Max 20 emojis. 3-5 hashtags. Plain text only.'),
        ('image_prompt', 'command-r-08-2024', 0.8, 2048,
         'You are a visual prompt engineer for Flux 2.',
         'NICHE: {niche}\nCONCEPT: {idea}\nKEYWORDS: {keywords}\nTONE: {tone}\nCANVAS: {image_width}x{image_height}\n\nGenerate ONE Flux 2 image prompt. English only. 350-550 words. Kodak Portra 400. Negative space upper third.'),
        ('ig_caption', 'command-r7b-arabic-02-2025', 0.7, 1024,
         'You are a social media specialist. Output only the Instagram caption.',
         'Rewrite for Instagram. Max 2200 chars. 5-10 Arabic hashtags. 8 emojis. Plain text.\n\nOriginal:\n{post_content}'),
        ('x_caption', 'command-r7b-arabic-02-2025', 0.7, 512,
         'You are a social media specialist. Output only the tweet.',
         'Rewrite for X. Max 270 chars. 1-2 hashtags.\n\nOriginal:\n{post_content}'),
        ('threads_caption', 'command-r7b-arabic-02-2025', 0.7, 512,
         'You are a social media specialist. Output only the Threads post.',
         'Rewrite for Threads. Max 450 chars. Conversational. 1-2 emojis. No hashtags.\n\nOriginal:\n{post_content}'),
        ('linkedin_caption', 'command-r-plus-08-2024', 0.7, 2048,
         'You are a bilingual content specialist in special education.',
         'Translate for LinkedIn in American English. Max 2800 chars. 3-5 English hashtags. Max 2 emojis. Plain text.\n\nOriginal Arabic:\n{post_content}'),
    ]
    for stage, model, temp, tokens, sys_p, usr_p in prompts:
        if not db.session.get(Prompt, stage):
            db.session.add(Prompt(
                stage=stage, model=model, temperature=temp, max_tokens=tokens,
                system_prompt=sys_p, user_prompt=usr_p
            ))


# ── Scheduler setup ───────────────────────────────────────────────────────────

def _setup_scheduler(app):
    if scheduler.running:
        logger.info("Scheduler already running — skipping")
        return

    with app.app_context():
        idea_time = Config.get('idea_factory_time', '08:00')
        post_times = [
            Config.get('sched_1', '09:00'),
            Config.get('sched_2', '13:00'),
            Config.get('sched_3', '17:00'),
            Config.get('sched_4', '21:00'),
        ]

    ih, im = idea_time.split(':')
    scheduler.add_job(_idea_job_runner, CronTrigger(hour=int(ih), minute=int(im)),
                      id='idea_factory', replace_existing=True, misfire_grace_time=600)

    for i, t in enumerate(post_times):
        h, m = t.split(':')
        scheduler.add_job(_post_job_runner, CronTrigger(hour=int(h), minute=int(m)),
                          id=f'post_{i}', replace_existing=True, misfire_grace_time=600)

    scheduler.add_job(_keep_alive_runner, IntervalTrigger(minutes=25),
                      id='keep_alive', replace_existing=True)

    scheduler.start()
    logger.info("Scheduler started")
