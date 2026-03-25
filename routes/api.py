"""REST API endpoints — called via AJAX from the dashboard."""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from database.models import db, Post, Config, ApiKey, Prompt, Platform, AIModel
from datetime import datetime
import json

api_bp = Blueprint('api', __name__, url_prefix='/api')


# ── Posts ─────────────────────────────────────────────────────────────────────

@api_bp.route('/posts', methods=['GET'])
@login_required
def get_posts():
    status = request.args.get('status', 'ALL')
    q = request.args.get('q', '')
    query = Post.query
    if status != 'ALL':
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Post.idea.ilike(f'%{q}%'))
    posts = query.order_by(Post.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts])


@api_bp.route('/posts', methods=['POST'])
@login_required
def create_post():
    data = request.json
    post = Post(
        idea=data.get('idea', ''),
        keywords=data.get('keywords', ''),
        tone=data.get('tone', ''),
        writing_style=data.get('writing_style', ''),
        opening_type=data.get('opening_type', ''),
        status='NEW',
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'ok': True, 'id': post.id})


@api_bp.route('/posts/<int:post_id>', methods=['PATCH'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.json
    for field in ['status', 'idea', 'keywords', 'tone', 'writing_style', 'opening_type',
                  'engagement_score', 'likes', 'comments', 'shares']:
        if field in data:
            setattr(post, field, data[field])
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'ok': True})


# ── Config ────────────────────────────────────────────────────────────────────

@api_bp.route('/config', methods=['GET'])
@login_required
def get_config():
    return jsonify({row.key: row.value for row in Config.query.all()})


@api_bp.route('/config', methods=['POST'])
@login_required
def save_config():
    data = request.json
    for key, value in data.items():
        Config.set(key, str(value))
    return jsonify({'ok': True})


# ── API Keys ──────────────────────────────────────────────────────────────────

@api_bp.route('/api-keys', methods=['POST'])
@login_required
def add_api_key():
    data = request.json
    key = ApiKey(
        platform=data['platform'],
        label=data.get('label', ''),
        key_value=data.get('key_value', ''),
        is_active=False,
    )
    db.session.add(key)
    db.session.commit()
    return jsonify({'ok': True, 'id': key.id})


@api_bp.route('/api-keys/<int:key_id>/activate', methods=['POST'])
@login_required
def activate_api_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    ApiKey.query.filter_by(platform=key.platform).update({'is_active': False})
    key.is_active = True
    # Sync to config
    config_map = {
        'facebook': 'fb_access_token',
        'twitter': 'x_oauth1_cred_id',
        'threads': 'threads_access_token',
        'linkedin': 'li_access_token',
    }
    if key.platform in config_map:
        Config.set(config_map[key.platform], key.key_value)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/api-keys/<int:key_id>', methods=['PATCH'])
@login_required
def update_api_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    data = request.json
    if 'key_value' in data:
        key.key_value = data['key_value']
    db.session.commit()
    return jsonify({'ok': True})


# ── Models ────────────────────────────────────────────────────────────────────

@api_bp.route('/models', methods=['POST'])
@login_required
def save_models():
    data = request.json  # [{stage, provider, model_id}]
    for item in data:
        row = db.session.get(AIModel, item['stage'])
        if row:
            row.provider = item['provider']
            row.model_id = item['model_id']
            from database.models import Prompt
            p = db.session.get(Prompt, item['stage'])
            if p:
                p.model = item['model_id']
    db.session.commit()
    return jsonify({'ok': True})


# ── Prompts ───────────────────────────────────────────────────────────────────

@api_bp.route('/prompts', methods=['POST'])
@login_required
def save_prompts():
    data = request.json  # [{stage, system_prompt, user_prompt, temperature, max_tokens}]
    for item in data:
        row = db.session.get(Prompt, item['stage'])
        if row:
            row.system_prompt = item.get('system_prompt', row.system_prompt)
            row.user_prompt = item.get('user_prompt', row.user_prompt)
            row.temperature = float(item.get('temperature', row.temperature))
            row.max_tokens = int(item.get('max_tokens', row.max_tokens))
    db.session.commit()
    return jsonify({'ok': True})


# ── Platforms ─────────────────────────────────────────────────────────────────

@api_bp.route('/platforms', methods=['POST'])
@login_required
def save_platforms():
    data = request.json  # [{name, enabled, settings}]
    for item in data:
        row = db.session.get(Platform, item['name'])
        if row:
            row.enabled = item.get('enabled', row.enabled)
            row.settings = json.dumps(item.get('settings', {}))
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/platforms/<name>/toggle', methods=['POST'])
@login_required
def toggle_platform(name):
    row = Platform.query.get_or_404(name)
    row.enabled = not row.enabled
    db.session.commit()
    return jsonify({'ok': True, 'enabled': row.enabled})


# ── Analytics ─────────────────────────────────────────────────────────────────

@api_bp.route('/engagement', methods=['POST'])
@login_required
def save_engagement():
    data = request.json
    post = Post.query.get_or_404(data['post_id'])
    post.engagement_score = int(data.get('score', 0))
    post.likes = int(data.get('likes', 0))
    post.comments = int(data.get('comments', 0))
    post.shares = int(data.get('shares', 0))
    db.session.commit()
    return jsonify({'ok': True})


# ── AI Provider Keys ──────────────────────────────────────────────────────────

@api_bp.route('/ai-keys', methods=['GET'])
@login_required
def get_ai_keys():
    from database.models import AIProviderKey
    provider = request.args.get('provider')
    q = AIProviderKey.query
    if provider:
        q = q.filter_by(provider=provider)
    keys = q.order_by(AIProviderKey.provider, AIProviderKey.priority).all()
    return jsonify([k.to_dict() for k in keys])


@api_bp.route('/ai-keys', methods=['POST'])
@login_required
def add_ai_key():
    from database.models import AIProviderKey
    data = request.json
    key = AIProviderKey(
        provider=data['provider'],
        label=data.get('label', ''),
        key_value=data['key_value'],
        priority=int(data.get('priority', 0)),
        is_active=True,
    )
    db.session.add(key)
    db.session.commit()
    return jsonify({'ok': True, 'id': key.id})


@api_bp.route('/ai-keys/<int:key_id>', methods=['PATCH'])
@login_required
def update_ai_key(key_id):
    from database.models import AIProviderKey
    key = AIProviderKey.query.get_or_404(key_id)
    data = request.json
    for field in ['label', 'key_value', 'priority', 'is_active']:
        if field in data:
            setattr(key, field, data[field])
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/ai-keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_ai_key(key_id):
    from database.models import AIProviderKey
    key = AIProviderKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/ai-keys/<int:key_id>/reset', methods=['POST'])
@login_required
def reset_ai_key(key_id):
    from services.key_rotator import reset_key
    reset_key(key_id)
    return jsonify({'ok': True})


@api_bp.route('/ai-keys/reset-all', methods=['POST'])
@login_required
def reset_all_ai_keys():
    from services.key_rotator import reset_all_keys
    provider = request.json.get('provider')
    if provider:
        reset_all_keys(provider)
    return jsonify({'ok': True})


@api_bp.route('/ai-keys/status', methods=['GET'])
@login_required
def ai_keys_status():
    from services.key_rotator import get_provider_status
    providers = ['cohere', 'gemini', 'groq', 'openrouter', 'openai']
    return jsonify({p: get_provider_status(p) for p in providers})




# ── Platform connection test ──────────────────────────────────────────────────

@api_bp.route('/platforms/test/<name>', methods=['POST'])
@login_required
def test_platform(name):
    from services.social_service import (
        test_facebook, test_instagram, test_twitter, test_threads, test_linkedin
    )
    cfg = {row.key: row.value for row in Config.query.all()}
    try:
        if name == 'facebook':
            result = test_facebook(cfg.get('fb_page_id',''), cfg.get('fb_access_token',''))
        elif name == 'instagram':
            result = test_instagram(cfg.get('ig_user_id',''), cfg.get('ig_access_token',''))
        elif name == 'twitter':
            result = test_twitter(
                cfg.get('twitter_api_key',''), cfg.get('twitter_api_secret',''),
                cfg.get('twitter_access_token',''), cfg.get('twitter_access_token_secret','')
            )
        elif name == 'threads':
            result = test_threads(cfg.get('threads_user_id',''), cfg.get('threads_access_token',''))
        elif name == 'linkedin':
            result = test_linkedin(cfg.get('li_access_token',''))
        else:
            return jsonify({'ok': False, 'error': 'Unknown platform'}), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


# ── Telegram config ───────────────────────────────────────────────────────────

@api_bp.route('/telegram/config', methods=['POST'])
@login_required
def save_telegram_config():
    data = request.json
    if 'bot_token' in data:
        Config.set('telegram_bot_token', data['bot_token'])
    if 'admin_chat_id' in data:
        Config.set('telegram_admin_chat_id', data['admin_chat_id'])
    return jsonify({'ok': True})


@api_bp.route('/telegram/test', methods=['POST'])
@login_required
def test_telegram():
    try:
        from services.telegram_bot import notify
        notify("✅ <b>اختبار الاتصال:</b> البوت يعمل بشكل صحيح!")
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]})


@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    total = Post.query.count()
    posted = Post.query.filter_by(status='POSTED').count()
    pending = Post.query.filter_by(status='NEW').count()
    today = Post.query.filter(
        Post.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    return jsonify({'total': total, 'posted': posted, 'pending': pending, 'today': today})


# ── DB Query ──────────────────────────────────────────────────────────────────

@api_bp.route('/db/query', methods=['POST'])
@login_required
def run_query():
    sql = request.json.get('sql', '').strip()
    if not sql:
        return jsonify({'error': 'No SQL provided'}), 400
    try:
        result = db.session.execute(db.text(sql))
        if sql.lower().startswith('select'):
            rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
            return jsonify({'rows': rows, 'count': len(rows)})
        else:
            db.session.commit()
            return jsonify({'ok': True, 'message': 'Query executed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
