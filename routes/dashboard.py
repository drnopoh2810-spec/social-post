from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from database.models import db, Post, Config, ApiKey, Prompt, Platform, AIModel, WorkflowLog
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)


def get_stats():
    total = Post.query.count()
    posted = Post.query.filter_by(status='POSTED').count()
    pending = Post.query.filter_by(status='NEW').count()
    today = Post.query.filter(
        Post.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    return {'total': total, 'posted': posted, 'pending': pending, 'today': today}


# ── Main pages ────────────────────────────────────────────────────────────────

@dashboard_bp.route('/')
@login_required
def index():
    stats = get_stats()
    recent = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    platforms = Platform.query.all()
    logs = WorkflowLog.query.order_by(WorkflowLog.created_at.desc()).limit(10).all()
    return render_template('pages/dashboard.html', stats=stats, recent=recent,
                           platforms=platforms, logs=logs)


@dashboard_bp.route('/posts')
@login_required
def posts():
    status = request.args.get('status', 'ALL')
    q = request.args.get('q', '')

    # Auto-sync from Google Sheets on every page load (fast, non-blocking)
    try:
        from services.sheets_sync import sync_from_sheets_to_db, is_configured
        if is_configured():
            ins, upd = sync_from_sheets_to_db()
            if ins or upd:
                import logging
                logging.getLogger(__name__).info(f"Posts page: synced {ins} new, {upd} updated from Sheets")
    except Exception:
        pass

    query = Post.query
    if status != 'ALL':
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Post.idea.ilike(f'%{q}%'))
    posts_list = query.order_by(Post.created_at.desc()).all()
    stats = get_stats()
    return render_template('pages/posts.html', posts=posts_list, stats=stats,
                           current_status=status, q=q)


@dashboard_bp.route('/analytics')
@login_required
def analytics():
    posted = Post.query.filter_by(status='POSTED').order_by(Post.engagement_score.desc()).all()
    avg = int(sum(p.engagement_score or 0 for p in posted) / len(posted)) if posted else 0
    top5 = posted[:5]
    bottom5 = sorted(posted, key=lambda x: x.engagement_score or 0)[:5]
    best_tone = _best_by(posted, 'tone')
    best_style = _best_by(posted, 'writing_style')
    all_posted = Post.query.filter_by(status='POSTED').all()
    return render_template('pages/analytics.html', avg=avg, top5=top5, bottom5=bottom5,
                           best_tone=best_tone, best_style=best_style, all_posted=all_posted)


def _best_by(posts, attr):
    scores = {}
    for p in posts:
        v = getattr(p, attr, None)
        if v:
            scores[v] = scores.get(v, 0) + (p.engagement_score or 0)
    if not scores:
        return '—'
    return max(scores, key=scores.get)


@dashboard_bp.route('/config')
@login_required
def config_page():
    cfg = {row.key: row.value for row in Config.query.all()}
    return render_template('pages/config.html', cfg=cfg)


@dashboard_bp.route('/api-manager')
@login_required
def api_manager():
    fb_keys = ApiKey.query.filter_by(platform='facebook').all()
    x_keys = ApiKey.query.filter_by(platform='twitter').all()
    th_keys = ApiKey.query.filter_by(platform='threads').all()
    li_keys = ApiKey.query.filter_by(platform='linkedin').all()
    cfg = {row.key: row.value for row in Config.query.all()}
    return render_template('pages/api_manager.html', fb_keys=fb_keys, x_keys=x_keys,
                           th_keys=th_keys, li_keys=li_keys, cfg=cfg)


@dashboard_bp.route('/models')
@login_required
def models_page():
    models = AIModel.query.all()
    return render_template('pages/models.html', models=models)


@dashboard_bp.route('/prompts')
@login_required
def prompts_page():
    prompts = Prompt.query.all()
    return render_template('pages/prompts.html', prompts=prompts)


@dashboard_bp.route('/platforms')
@login_required
def platforms_page():
    import json
    platforms_raw = Platform.query.all()
    platforms = []
    for p in platforms_raw:
        p._settings_dict = json.loads(p.settings or '{}')
        platforms.append(p)
    return render_template('pages/platforms.html', platforms=platforms)


@dashboard_bp.route('/image-config')
@login_required
def image_config():
    from database.models import AIProviderKey
    from services.key_rotator import get_image_chain
    cfg = {row.key: row.value for row in Config.query.all()}
    img_providers = ['huggingface', 'together', 'fal', 'gemini_image', 'ideogram', 
                     'openai_image', 'stability']
    keys_by_provider = {
        p: AIProviderKey.query.filter_by(provider=p).order_by(AIProviderKey.priority).all()
        for p in img_providers
    }
    # Get current provider order
    current_order = get_image_chain()
    return render_template('pages/image_config.html', cfg=cfg, keys_by_provider=keys_by_provider,
                          current_order=current_order)


@dashboard_bp.route('/scheduler')
@login_required
def scheduler_page():
    cfg = {row.key: row.value for row in Config.query.all()}
    return render_template('pages/scheduler.html', cfg=cfg)


@dashboard_bp.route('/telegram')
@login_required
def telegram_page():
    cfg = {row.key: row.value for row in Config.query.all()}
    return render_template('pages/telegram.html', cfg=cfg)


@dashboard_bp.route('/ai-keys')
@login_required
def ai_keys_page():
    from database.models import AIProviderKey
    # AI text providers
    ai_providers = ['cohere', 'gemini', 'groq', 'openrouter', 'airforce', 'openai']
    # Image providers
    img_providers = ['gemini_image', 'huggingface', 'together', 'fal',
                     'pollinations', 'ideogram', 'openai_image', 'stability']
    all_providers = ai_providers + img_providers
    keys_by_provider = {}
    for p in all_providers:
        keys_by_provider[p] = AIProviderKey.query.filter_by(provider=p).order_by(
            AIProviderKey.priority.asc(), AIProviderKey.id.asc()
        ).all()
    from services.image_service import IMAGE_PROVIDERS_INFO
    return render_template('pages/ai_keys.html',
                           keys_by_provider=keys_by_provider,
                           providers=ai_providers,
                           img_providers=img_providers,
                           img_providers_info=IMAGE_PROVIDERS_INFO)


@dashboard_bp.route('/db')
@login_required
def db_page():
    return render_template('pages/db.html')


@dashboard_bp.route('/backup')
@login_required
def backup_page():
    return render_template('pages/backup.html')
