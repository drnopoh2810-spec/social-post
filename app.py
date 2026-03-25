import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
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


def _auto_update_runner():
    """Check GitHub for updates every 30 minutes."""
    if _app_instance:
        from services.auto_updater import check_and_update
        check_and_update(_app_instance)


def _keep_alive_runner():
    """Self-ping to prevent free-tier sleep."""
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

    # Fix for reverse proxy (HuggingFace Spaces, Nginx, etc.)
    # Tells Flask to trust X-Forwarded-For and X-Forwarded-Proto headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
        # Restore config from Redis if DB was wiped (restart)
        try:
            from services.redis_config import sync_redis_to_db, sync_db_to_redis
            restored = sync_redis_to_db()
            if restored:
                logger.info(f"Restored {restored} config values from Redis")
            else:
                sync_db_to_redis()  # First run — push DB → Redis
        except Exception as e:
            logger.warning(f"Redis sync skipped: {e}")

        # Restore posts from Google Sheets if DB is empty
        try:
            from services.sheets_sync import is_configured, restore_from_sheets
            from database.models import Post
            if is_configured():
                post_count = Post.query.count()
                if post_count == 0:
                    restored = restore_from_sheets()
                    if restored:
                        logger.info(f"Restored {restored} posts from Google Sheets")
                else:
                    # Sync any newer engagement data from Sheets
                    restored = restore_from_sheets()
                    if restored:
                        logger.info(f"Updated {restored} posts from Google Sheets")
        except Exception as e:
            logger.warning(f"Google Sheets restore skipped: {e}")

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
    """
    Sync HuggingFace Secrets / env vars → DB on every startup.
    Handles both Config keys and AIProviderKey entries.
    """
    from database.models import Config as Cfg, AIProviderKey
    synced = 0

    # ── 1. Config key-value pairs ─────────────────────────────────────────────
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

    # ── 2. AI Provider Keys (COHERE_KEY_1, COHERE_KEY_2, GEMINI_KEY_1 ...) ───
    # Format: {PROVIDER}_KEY_{N} e.g. COHERE_KEY_1=sk-xxx
    #         {PROVIDER}_KEY_{N}_LABEL=حساب شخصي  (optional label)
    providers = ['COHERE', 'GEMINI', 'GROQ', 'OPENROUTER', 'OPENAI']
    for provider_upper in providers:
        provider = provider_upper.lower()
        for n in range(1, 6):  # support up to 5 keys per provider
            env_key = f'{provider_upper}_KEY_{n}'
            key_val = os.environ.get(env_key, '').strip()
            if not key_val:
                continue
            label = os.environ.get(f'{env_key}_LABEL', f'Key {n}').strip()
            # Check if already exists (match by provider + key_value)
            exists = AIProviderKey.query.filter_by(
                provider=provider, key_value=key_val
            ).first()
            if not exists:
                db.session.add(AIProviderKey(
                    provider=provider,
                    label=label,
                    key_value=key_val,
                    priority=n - 1,
                    is_active=True,
                ))
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
        # ══════════════════════════════════════════════════════════════════════
        # 1. IDEA FACTORY — مصنع الأفكار
        # ══════════════════════════════════════════════════════════════════════
        ('idea_factory', 'command-r7b-arabic-02-2025', 0.9, 4096,

         # SYSTEM PROMPT
         '''أنت خبير استراتيجي في إنتاج محتوى تعليمي وتوعوي على السوشال ميديا.
مهمتك: توليد أفكار محتوى أصيلة ومتنوعة في المجال المحدد.

قواعد صارمة — لا تخرج عنها أبداً:
❌ ممنوع: أي إعلان أو ترويج لمنتج أو خدمة
❌ ممنوع: دعوة لندوة أو ورشة أو كورس أو حجز
❌ ممنوع: ذكر أسعار أو عروض أو خصومات
❌ ممنوع: الإعلان عن وظائف أو فرص عمل
❌ ممنوع: المناسبات والأعياد والتهاني
❌ ممنوع: الدعاية السياسية أو الدينية
❌ ممنوع: أي محتوى تسويقي بأي شكل

✅ مسموح فقط:
• توعية وتثقيف في المجال
• معلومات علمية عميقة وموثوقة
• شرح مفاهيم ومصطلحات
• تصحيح مفاهيم خاطئة شائعة
• قصص حالات حقيقية ودروس مستفادة
• إحصائيات وأبحاث علمية محكّمة
• نصائح عملية قابلة للتطبيق
• مقارنات توضيحية
• محتوى كوميدي/ترفيهي في المجال
• أسئلة للنقاش والتفكير

الناتج: JSON array فقط — لا نص قبله ولا بعده.''',

         # USER PROMPT
         '''المجال: {niche}

السياق الحالي:
- إجمالي الأفكار: {total_ideas} | منشور: {total_posted} | انتظار: {total_pending}
- متوسط الـ engagement: {avg_engagement_score}

أفضل المنشورات أداءً (كرر أنماطها):
{top5_performing}

أضعف المنشورات (تجنب أنماطها):
{bottom5_performing}

المواضيع المشبعة (تجنبها تماماً):
{saturated_topics}

أفكار آخر 7 أيام (لا تكرر):
{recent_ideas_text}

الأرشيف الكامل (صفر تكرار):
{all_ideas_text}

الأساليب المستخدمة مؤخراً (نوّع):
{recent_styles}

الافتتاحيات المستخدمة مؤخراً (نوّع):
{recent_openings}

══════════════════════════════════════════
المهمة: ولّد 10 أفكار محتوى أصيلة 100%

التوزيع المطلوب (فكرتان لكل نوع):
1. تصحيح خرافة شائعة + دليل علمي مبسط
2. قصة حالة حقيقية + درس مستفاد
3. إحصائية أو بحث حديث + تحليل تطبيقي
4. شرح خطوة بخطوة + أداة أو استراتيجية عملية
5. سؤال للنقاش + مقارنة توضيحية

أساليب الكتابة المتاحة:
مراقب ميداني | محلل علمي | محاور هادئ | ناقد لطيف | راوي تجربة | مقارن دقيق | كوميدي ساخر | مبسّط للعلوم

أنواع الافتتاحيات المتاحة:
مشهد ميداني | سؤال صامت | ملاحظة مضادة للحدس | إحصاء مفاجئ | ذاكرة مهنية | مقارنة مباشرة | موقف كوميدي | حقيقة غريبة

تعليمات الجودة:
- كل فكرة لازم تكون محددة وعميقة (مش عامة)
- الفكرة لازم تحتوي على: الموضوع + الزاوية + الجمهور المستهدف + التحول المتوقع
- تجنب أي فكرة فيها رائحة تسويق أو إعلان
- ركّز على القيمة التعليمية والترفيهية

الناتج: JSON array فقط. لا markdown. ابدأ بـ [ وانتهِ بـ ]
[{"idea":"وصف تفصيلي للفكرة بالعربية (60+ كلمة)","keywords":["#tag1","#tag2","#tag3"],"tone":"نوع المحتوى","writing_style":"أسلوب الكتابة","opening_type":"نوع الافتتاحية"}]'''),

        # ══════════════════════════════════════════════════════════════════════
        # 2. POST WRITER — كاتب المنشورات
        # ══════════════════════════════════════════════════════════════════════
        ('post_writer', 'command-r7b-arabic-02-2025', 0.85, 4096,

         # SYSTEM PROMPT
         '''أنت كاتب محتوى مصري متخصص في التعليم والتوعية.
أسلوبك: عامية مصرية خالصة — دافئة، ذكية، قريبة من القارئ.

قواعد الكتابة الصارمة:
❌ ممنوع: أي إعلان أو ترويج أو دعوة لشراء
❌ ممنوع: ذكر أسعار أو عروض أو خصومات
❌ ممنوع: دعوة لندوة أو كورس أو حجز
❌ ممنوع: الفصحى أو اللغة الرسمية الجافة
❌ ممنوع: الـ clickbait أو العناوين المثيرة الفارغة
❌ ممنوع: الـ markdown أو الـ bold أو القوائم المرقمة
❌ ممنوع: عبارات "هل تعلم" أو "لن تصدق" أو "سر"

✅ المطلوب:
• عامية مصرية طبيعية وسلسة
• محتوى تعليمي/توعوي/ترفيهي حقيقي
• نص متدفق بدون تقسيمات مصطنعة
• قيمة حقيقية في كل سطر''',

         # USER PROMPT
         '''متخصص في: {niche}

أسلوب الكتابة المطلوب: {writing_style}
نوع الافتتاحية: {opening_type}
الفكرة: {idea}
الكلمات المفتاحية: {keywords}
النبرة العاطفية: {tone}

══════════════════════════════════════════
اكتب منشور فيسبوك بالطبقات الأربعة دي:

الطبقة 1 — الافتتاحية الهادئة:
افتح بالأسلوب المحدد ({opening_type}) بدون hooks أو صدمة مصطنعة.
مشهد حقيقي أو ملاحظة دقيقة أو سؤال صامت يخلي القارئ يفكر.

الطبقة 2 — العمق العلمي:
اشرح الآلية العلمية أو النفسية أو السلوكية وراء الموضوع.
استخدم أمثلة مصرية مألوفة. اخلي المعقد بسيط.

الطبقة 3 — تصحيح المفهوم الخاطئ:
حدد الفهم الشائع الغلط في مصر وصحّحه بلطف وبدون إدانة.
"الناس بتفتكر... بس الحقيقة..."

الطبقة 4 — إعادة التأطير:
جملة أو اتنين بتخلي القارئ يشوف الموضوع بعين تانية.
مش call to action — مجرد منظور جديد.

قواعد الكتابة:
• عامية مصرية خالصة — مفيش فصحى خالص
• الطول: 600-1000 كلمة
• الإيموجي: 15-20 بحد أقصى، وظيفية مش زينة
• الهاشتاق: 3-5 في الآخر فقط
• نص متدفق — مفيش headers أو قوائم أو bold
• مفيش أي إشارة لمنتج أو خدمة أو سعر'''),

        # ══════════════════════════════════════════════════════════════════════
        # 3. IMAGE PROMPT — برومبت الصور
        # ══════════════════════════════════════════════════════════════════════
        ('image_prompt', 'command-r-08-2024', 0.8, 2048,

         'You are a world-class visual prompt engineer for Flux 2 image generation.',

         '''NICHE: {niche}
CONCEPT: {idea}
KEYWORDS: {keywords}
EMOTIONAL TONE: {tone}
CANVAS: {image_width}x{image_height} pixels (portrait format)

Generate ONE precise Flux 2 image prompt. English only. 350-500 words.

REQUIRED ELEMENTS (include all):
1. Subject + camera setup (focal length, aperture, angle)
2. Lighting (direction, quality, color temperature, shadow behavior)
3. Three depth planes (foreground/midground/background with focus behavior)
4. Color palette (2-3 specific tone names, Kodak Portra 400 style)
5. Symbolic props (readable at thumbnail size)
6. Negative space (upper third — clean area for text overlay)
7. Style anchors (editorial photography, Magnum Photos aesthetic)
8. Human presence (partial only: hands, figure from behind, shoulder)

RULES:
- Start directly with subject and camera framing
- No markdown, no headers, no lists, no preamble
- Avoid: stunning, breathtaking, photorealistic, ultra-detailed, amazing
- Use: Kodak Portra 400 palette, Hasselblad color science, ISO 400 grain
- One dominant focal point readable in 0.3 seconds on mobile
- Clean negative space in upper third for Arabic text overlay
- Warm, human, documentary feel — not commercial or stock photo'''),

        # ══════════════════════════════════════════════════════════════════════
        # 4-7. PLATFORM CAPTIONS
        # ══════════════════════════════════════════════════════════════════════
        ('ig_caption', 'command-r7b-arabic-02-2025', 0.7, 1024,
         'أنت متخصص في السوشال ميديا. اكتب كابشن Instagram فقط — بدون أي نص تاني.',
         '''حوّل المنشور ده لكابشن Instagram.

القواعد:
• بحد أقصى 2200 حرف
• احتفظ بالرسالة الأساسية
• 5-10 هاشتاق عربي في الآخر
• 8 إيموجي طبيعية في النص
• نص عادي فقط — مفيش markdown
• مفيش أي إعلان أو ترويج

المنشور الأصلي:
{post_content}'''),

        ('x_caption', 'command-r7b-arabic-02-2025', 0.7, 512,
         'أنت متخصص في السوشال ميديا. اكتب تغريدة فقط — بدون أي نص تاني.',
         '''حوّل المنشور ده لتغريدة X (Twitter).

القواعد:
• بحد أقصى 270 حرف
• فكرة واحدة قوية ومركّزة
• 1-2 هاشتاق بس
• مفيش إيموجي إلا لو بتوفر مساحة
• مفيش أي إعلان أو ترويج

المنشور الأصلي:
{post_content}'''),

        ('threads_caption', 'command-r7b-arabic-02-2025', 0.7, 512,
         'أنت متخصص في السوشال ميديا. اكتب بوست Threads فقط — بدون أي نص تاني.',
         '''حوّل المنشور ده لبوست Threads.

القواعد:
• بحد أقصى 450 حرف
• نبرة محادثة وشخصية
• فكرة واحدة واضحة
• 1-2 إيموجي بحد أقصى
• مفيش هاشتاق
• مفيش أي إعلان أو ترويج

المنشور الأصلي:
{post_content}'''),

        ('linkedin_caption', 'command-r-plus-08-2024', 0.7, 2048,
         '''You are a bilingual content specialist with deep expertise in the given field.
Your job: translate Arabic posts into compelling American English LinkedIn content.
Never translate word-for-word — always adapt for natural American English flow.
Output only the final LinkedIn post text, nothing else.''',

         '''Translate and adapt this post for LinkedIn in American English.

RULES:
- Fluent, natural American English (NOT a literal translation)
- Adapt Egyptian cultural references for a global professional audience
- Max 2800 characters
- Structure: Hook (1-2 punchy sentences) → Core Insight → Practical Takeaway → Closing Question
- Professional yet warm and human tone
- Add 3-5 English professional hashtags at the end
- Max 2 emojis, placed naturally
- Plain text only — no markdown, no bold, no bullet lists
- Preserve scientific accuracy and emotional depth
- NO marketing, NO promotional content, NO calls to buy anything

Original Arabic post:
{post_content}'''),
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

    # Auto-update from GitHub every 30 minutes
    scheduler.add_job(_auto_update_runner, IntervalTrigger(minutes=30),
                      id='auto_update', replace_existing=True)

    scheduler.start()
    logger.info("Scheduler started")
