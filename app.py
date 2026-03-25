import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import config
from database.models import db, User, Config, Prompt, Platform, AIModel, AIProviderKey

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

login_manager = LoginManager()
csrf = CSRFProtect()
scheduler = BackgroundScheduler(timezone="Africa/Cairo")


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'يرجى تسجيل الدخول أولاً'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.api import api_bp
    from routes.workflow import workflow_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(workflow_bp)

    # ── Health check endpoint (no auth, no CSRF) ──────────────────────────────
    @app.route('/health')
    def health():
        try:
            # Quick DB ping
            db.session.execute(db.text('SELECT 1'))
            db_ok = True
        except Exception:
            db_ok = False
        status = 'ok' if db_ok else 'degraded'
        code = 200 if db_ok else 503
        return jsonify({
            'status': status,
            'db': db_ok,
            'scheduler': scheduler.running,
            'time': datetime.utcnow().isoformat(),
        }), code

    # Context processor — inject pending_count to all templates
    @app.context_processor
    def inject_globals():
        try:
            from database.models import Post
            pending = Post.query.filter_by(status='NEW').count()
        except Exception:
            pending = 0
        return {'pending_count': pending}

    # Init DB and seed data
    with app.app_context():
        db.create_all()
        _seed_admin(app)
        _seed_defaults()
        _seed_from_env()   # sync env vars → DB for dashboard display

    # Scheduler
    _setup_scheduler(app)

    # Telegram Bot (non-blocking background thread)
    from services.telegram_bot import start_bot
    start_bot(app)

    return app


def _seed_from_env():
    """
    عند بدء التشغيل: اقرأ المتغيرات من os.environ واكتبها في DB.
    هذا يجعل لوحة التحكم تعرض القيم الصحيحة حتى لو جاءت من HF Secrets.
    لا يُكتب فوق قيمة موجودة في DB إلا لو الـ env أحدث (أطول).
    """
    from database.models import Config as Cfg
    env_map = Cfg._ENV_MAP
    synced = 0
    for db_key, env_name in env_map.items():
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
    """Create admin user if not exists."""
    if not User.query.filter_by(username=app.config['ADMIN_USERNAME']).first():
        user = User(username=app.config['ADMIN_USERNAME'])
        user.set_password(app.config['ADMIN_PASSWORD'])
        db.session.add(user)
        db.session.commit()
        logger.info(f"Admin user '{app.config['ADMIN_USERNAME']}' created")


def _seed_defaults():
    """Seed default config, prompts, platforms, models if DB is empty."""
    # Config defaults
    defaults = {
        'niche': 'تربية خاصة → Special Education 📚\nالإعاقة العقلية → Intellectual Disability 🧠\nاضطرابات التواصل → Communication Disorders 💬\nاضطراب التعلم المحدد → Specific Learning Disorder ✏️\nApplied Behavior Analysis',
        'image_ratio_percent': '90',
        'image_model': 'flux',
        'image_width': '1080',
        'image_height': '1350',
        'delay_min_seconds': '60',
        'delay_max_seconds': '420',
        'idea_factory_time': '08:00',
        'sched_1': '09:00', 'sched_2': '13:00', 'sched_3': '17:00', 'sched_4': '21:00',
        'frame_opacity': '100',
    }
    for k, v in defaults.items():
        if not db.session.get(Config, k):
            db.session.add(Config(key=k, value=v))

    # Platforms
    for name in ['facebook', 'instagram', 'twitter', 'threads', 'linkedin']:
        if not db.session.get(Platform, name):
            db.session.add(Platform(name=name, enabled=True, settings='{}'))

    # AI Models
    model_defs = [
        ('idea_factory', 'cohere', 'command-r7b-arabic-02-2025'),
        ('post_writer', 'cohere', 'command-r7b-arabic-02-2025'),
        ('image_prompt', 'cohere', 'command-r-08-2024'),
        ('ig_caption', 'cohere', 'command-r7b-arabic-02-2025'),
        ('x_caption', 'cohere', 'command-r7b-arabic-02-2025'),
        ('threads_caption', 'cohere', 'command-r7b-arabic-02-2025'),
        ('linkedin_caption', 'cohere', 'command-r-plus-08-2024'),
    ]
    for stage, provider, model_id in model_defs:
        if not db.session.get(AIModel, stage):
            db.session.add(AIModel(stage=stage, provider=provider, model_id=model_id))

    # Prompts
    _seed_prompts()

    db.session.commit()


def _seed_prompts():
    prompts_data = [
        {
            'stage': 'idea_factory',
            'model': 'command-r7b-arabic-02-2025',
            'temperature': 0.9, 'max_tokens': 4096,
            'system_prompt': 'You are a world-class Arabic content strategist specializing in educational psychology. Generate diverse, non-repetitive content ideas. Output ONLY a valid JSON array, nothing else.',
            'user_prompt': '''NICHE: {niche}

CONTEXT:
- Total ideas: {total_ideas}
- Published: {total_posted} | Pending: {total_pending}

PERFORMANCE DATA:
- Average engagement score: {avg_engagement_score}
- TOP PERFORMING: {top5_performing}
- WORST PERFORMING: {bottom5_performing}

SATURATED TOPICS (avoid): {saturated_topics}
IDEAS LAST 7 DAYS: {recent_ideas_text}
FULL ARCHIVE: {all_ideas_text}
RECENT STYLES USED: {recent_styles}
RECENT OPENINGS USED: {recent_openings}

MISSION: Generate exactly 10 content ideas. Each 100% original.

DISTRIBUTION (2 each):
1. Myth Correction + Evidence
2. Real Case Story + Lesson
3. Research/Statistic + Analysis
4. Step-by-Step + Tool
5. Discussion Question + Comparison

STYLES: مراقب ميداني | محلل علمي | محاور هادئ | ناقد لطيف | راوي تجربة | مقارن دقيق
OPENINGS: مشهد ميداني | سؤال صامت | ملاحظة مضادة للحدس | إحصاء مفاجئ | ذاكرة مهنية | مقارنة مباشرة

OUTPUT: Raw JSON array ONLY. No markdown. Start with [ end with ].
[{"idea":"...","keywords":["#tag1"],"tone":"...","writing_style":"...","opening_type":"..."}]'''
        },
        {
            'stage': 'post_writer',
            'model': 'command-r7b-arabic-02-2025',
            'temperature': 0.85, 'max_tokens': 4096,
            'system_prompt': 'You are a world-class Arabic content writer specializing in educational psychology. Write in pure Egyptian Arabic colloquial dialect.',
            'user_prompt': '''You are a senior Egyptian field specialist in: {niche}

ASSIGNED WRITING STYLE: {writing_style}
ASSIGNED OPENING TYPE: {opening_type}
IDEA: {idea}
KEYWORDS: {keywords}
EMOTIONAL TONE: {tone}

WRITE A FACEBOOK POST with FOUR LAYERS:
LAYER 1 — QUIET OBSERVATION: Open with field moment. No hooks.
LAYER 2 — SCIENTIFIC WHY: Explain neurological/psychological mechanism.
LAYER 3 — MYTH CORRECTION: Address common Egyptian misunderstanding gently.
LAYER 4 — PERSPECTIVE SHIFT: Reframe how reader sees the child.

LANGUAGE: Pure Egyptian Arabic colloquial only. Never Fusha.
LENGTH: 600-1000 words.
EMOJIS: Maximum 20.
HASHTAGS: 3-5 niche-specific at end.
FORMAT: Plain flowing text only. No markdown.'''
        },
        {
            'stage': 'image_prompt',
            'model': 'command-r-08-2024',
            'temperature': 0.8, 'max_tokens': 2048,
            'system_prompt': 'You are a world-class visual prompt engineer for Flux 2. Generate precise, structured image prompts.',
            'user_prompt': '''NICHE: {niche}
CONCEPT: {idea}
KEYWORDS: {keywords}
TONE: {tone}
CANVAS: {image_width}x{image_height} pixels

Generate ONE Flux 2 image prompt. English only. 350-550 words.
Start directly with subject. No markdown. Kodak Portra 400 palette. Negative space upper third for text.'''
        },
        {
            'stage': 'ig_caption',
            'model': 'command-r7b-arabic-02-2025',
            'temperature': 0.7, 'max_tokens': 1024,
            'system_prompt': 'You are a social media specialist. Output only the Instagram caption text.',
            'user_prompt': 'Rewrite this post for Instagram. Max 1300 words. Keep core message. Add 5-10 Arabic hashtags. Use 8 emojis naturally. Plain text only.\n\nOriginal:\n{post_content}'
        },
        {
            'stage': 'x_caption',
            'model': 'command-r7b-arabic-02-2025',
            'temperature': 0.7, 'max_tokens': 512,
            'system_prompt': 'You are a social media specialist. Output only the tweet text.',
            'user_prompt': 'Rewrite for X (Twitter). Max 270 characters. One punchy insight. 1-2 hashtags. No emojis unless space-saving.\n\nOriginal:\n{post_content}'
        },
        {
            'stage': 'threads_caption',
            'model': 'command-r7b-arabic-02-2025',
            'temperature': 0.7, 'max_tokens': 512,
            'system_prompt': 'You are a social media specialist. Output only the Threads post text.',
            'user_prompt': 'Rewrite for Threads. Max 450 characters. Conversational tone. One clear idea. 1-2 emojis max. No hashtags.\n\nOriginal:\n{post_content}'
        },
        {
            'stage': 'linkedin_caption',
            'model': 'command-r-plus-08-2024',
            'temperature': 0.7, 'max_tokens': 2048,
            'system_prompt': 'You are a bilingual content specialist with deep expertise in special education.',
            'user_prompt': 'Translate and adapt for LinkedIn in American English. Max 2800 characters. Professional yet warm. 3-5 English hashtags. Max 2 emojis. Plain text only.\n\nOriginal Arabic:\n{post_content}'
        },
    ]
    for p in prompts_data:
        if not db.session.get(Prompt, p['stage']):
            db.session.add(Prompt(**p))


def _setup_scheduler(app):
    """
    Configure APScheduler.
    - Uses SQLAlchemyJobStore so jobs survive restarts.
    - Runs in 1 gunicorn worker (gthread) — no duplicate jobs.
    - Adds a keep-alive self-ping every 25 minutes to prevent
      HuggingFace Spaces / Render free-tier sleep.
    """
    if scheduler.running:
        logger.info("Scheduler already running — skipping setup")
        return

    # ── Persistent job store ──────────────────────────────────────────────────
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///social_post.db')
    scheduler.configure(jobstores={
        'default': SQLAlchemyJobStore(url=db_url)
    })

    # ── Job functions ─────────────────────────────────────────────────────────
    def idea_job():
        from services.workflow_service import run_idea_factory
        run_idea_factory(app)

    def post_job():
        from services.workflow_service import run_post_engine
        run_post_engine(app)

    def keep_alive_ping():
        """Self-ping to prevent free-tier sleep (HuggingFace / Render)."""
        try:
            import requests as req
            port = os.environ.get('PORT', '5000')
            req.get(f'http://localhost:{port}/health', timeout=8)
            logger.debug("Keep-alive ping sent")
        except Exception as e:
            logger.debug(f"Keep-alive ping failed (normal on startup): {e}")

    # ── Load schedule from DB ─────────────────────────────────────────────────
    with app.app_context():
        idea_time  = Config.get('idea_factory_time', '08:00')
        post_times = [
            Config.get('sched_1', '09:00'),
            Config.get('sched_2', '13:00'),
            Config.get('sched_3', '17:00'),
            Config.get('sched_4', '21:00'),
        ]

    ih, im = idea_time.split(':')
    scheduler.add_job(
        idea_job, CronTrigger(hour=int(ih), minute=int(im)),
        id='idea_factory', replace_existing=True, misfire_grace_time=600
    )

    for i, t in enumerate(post_times):
        h, m = t.split(':')
        scheduler.add_job(
            post_job, CronTrigger(hour=int(h), minute=int(m)),
            id=f'post_{i}', replace_existing=True, misfire_grace_time=600
        )

    # Keep-alive every 25 minutes
    scheduler.add_job(
        keep_alive_ping, IntervalTrigger(minutes=25),
        id='keep_alive', replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with SQLAlchemy job store")
