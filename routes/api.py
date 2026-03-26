"""REST API endpoints — called via AJAX from the dashboard."""
from flask import Blueprint, request, jsonify, Response
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

# Static fallback model lists (used when API discovery fails or key not set)
_STATIC_MODELS = {
    "cohere": [
        {"id": "command-r7b-arabic-02-2025", "name": "Command R7B Arabic (مجاني ⭐)", "free": True},
        {"id": "command-r-08-2024",           "name": "Command R (مجاني)",             "free": True},
        {"id": "command-r-plus-08-2024",      "name": "Command R+ (مجاني محدود)",      "free": True},
        {"id": "command-a-03-2025",           "name": "Command A (مجاني)",             "free": True},
    ],
    "gemini": [
        {"id": "gemini-2.0-flash",            "name": "Gemini 2.0 Flash (مجاني ⭐)",   "free": True},
        {"id": "gemini-2.0-flash-lite",       "name": "Gemini 2.0 Flash Lite (مجاني)","free": True},
        {"id": "gemini-1.5-flash",            "name": "Gemini 1.5 Flash (مجاني)",      "free": True},
        {"id": "gemini-1.5-flash-8b",         "name": "Gemini 1.5 Flash 8B (مجاني)",  "free": True},
        {"id": "gemini-1.5-pro",              "name": "Gemini 1.5 Pro (مدفوع)",        "free": False},
        {"id": "gemini-2.0-pro-exp",          "name": "Gemini 2.0 Pro Exp (تجريبي)",   "free": True},
    ],
    "groq": [
        {"id": "llama-3.1-8b-instant",        "name": "Llama 3.1 8B Instant (مجاني ⭐)","free": True},
        {"id": "llama-3.3-70b-versatile",     "name": "Llama 3.3 70B (مجاني)",         "free": True},
        {"id": "llama3-8b-8192",              "name": "Llama 3 8B (مجاني)",            "free": True},
        {"id": "mixtral-8x7b-32768",          "name": "Mixtral 8x7B (مجاني)",          "free": True},
        {"id": "gemma2-9b-it",                "name": "Gemma 2 9B (مجاني)",            "free": True},
    ],
    "openrouter": [
        {"id": "meta-llama/llama-3.1-8b-instruct:free",  "name": "Llama 3.1 8B (مجاني ⭐)", "free": True},
        {"id": "google/gemma-2-9b-it:free",              "name": "Gemma 2 9B (مجاني)",      "free": True},
        {"id": "mistralai/mistral-7b-instruct:free",     "name": "Mistral 7B (مجاني)",      "free": True},
        {"id": "qwen/qwen-2.5-72b-instruct:free",        "name": "Qwen 2.5 72B (مجاني)",    "free": True},
        {"id": "deepseek/deepseek-r1:free",              "name": "DeepSeek R1 (مجاني)",     "free": True},
    ],
    "airforce": [
        {"id": "deepseek-v3-0324",   "name": "DeepSeek V3 (مجاني ⭐ operational)", "free": True},
        {"id": "deepseek-r1",        "name": "DeepSeek R1 (مجاني operational)",    "free": True},
        {"id": "gemini-2.5-flash",   "name": "Gemini 2.5 Flash (مجاني operational)","free": True},
        {"id": "gemma3-270m:free",   "name": "Gemma 3 270M (مجاني تماماً)",        "free": True},
        {"id": "moirai-agent",       "name": "Moirai Agent (مجاني تماماً)",         "free": True},
        {"id": "claude-sonnet-4.6",  "name": "Claude Sonnet 4.6 (operational)",    "free": False},
        {"id": "gpt-5-nano",         "name": "GPT-5 Nano (operational)",            "free": False},
        {"id": "chatgpt-4o-latest",  "name": "ChatGPT-4o Latest (operational)",    "free": False},
    ],
    "openai": [
        {"id": "gpt-4o-mini",   "name": "GPT-4o Mini (مدفوع رخيص)", "free": False},
        {"id": "gpt-4o",        "name": "GPT-4o (مدفوع)",            "free": False},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (مدفوع)",    "free": False},
    ],
}


def _fetch_cohere_models(api_key: str) -> list:
    """Fetch available models from Cohere API."""
    import requests as req
    try:
        r = req.get(
            "https://api.cohere.com/v2/models",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=8,
        )
        if not r.ok:
            return []
        data = r.json().get("models", [])
        # Filter to chat/generate capable models only
        result = []
        for m in data:
            endpoints = m.get("endpoints", [])
            if "chat" in endpoints or "generate" in endpoints:
                mid = m.get("name", "")
                # Mark free models (no billing required)
                is_free = not m.get("finetuned", False)
                result.append({"id": mid, "name": mid, "free": is_free})
        return sorted(result, key=lambda x: (not x["free"], x["id"]))
    except Exception:
        return []


def _fetch_gemini_models(api_key: str) -> list:
    """Fetch available models from Google Gemini API."""
    import requests as req
    try:
        r = req.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=8,
        )
        if not r.ok:
            return []
        data = r.json().get("models", [])
        result = []
        for m in data:
            # Only include models that support generateContent
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            mid = m.get("name", "").replace("models/", "")
            display = m.get("displayName", mid)
            # Free models: flash variants and experimental
            is_free = any(x in mid for x in ["flash", "exp", "lite"])
            result.append({"id": mid, "name": f"{display} {'(مجاني)' if is_free else '(مدفوع)'}", "free": is_free})
        return sorted(result, key=lambda x: (not x["free"], x["id"]))
    except Exception:
        return []


def _fetch_groq_models(api_key: str) -> list:
    """Fetch available models from Groq API."""
    import requests as req
    try:
        r = req.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=8,
        )
        if not r.ok:
            return []
        data = r.json().get("data", [])
        result = []
        for m in data:
            mid = m.get("id", "")
            # Groq is free for all listed models
            result.append({"id": mid, "name": f"{mid} (مجاني)", "free": True})
        return sorted(result, key=lambda x: x["id"])
    except Exception:
        return []


def _fetch_openrouter_models(api_key: str) -> list:
    """Fetch free models from OpenRouter API."""
    import requests as req
    try:
        r = req.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if not r.ok:
            return []
        data = r.json().get("data", [])
        result = []
        for m in data:
            mid = m.get("id", "")
            pricing = m.get("pricing", {})
            # Free if prompt price is "0" or model id ends with :free
            prompt_price = str(pricing.get("prompt", "1"))
            is_free = prompt_price in ("0", "0.0") or mid.endswith(":free")
            name = m.get("name", mid)
            label = f"{name} (مجاني)" if is_free else f"{name} (مدفوع)"
            result.append({"id": mid, "name": label, "free": is_free})
        # Sort: free first
        return sorted(result, key=lambda x: (not x["free"], x["id"]))[:40]
    except Exception:
        return []


def _fetch_airforce_models(api_key: str = "") -> list:
    """Fetch operational chat models from api.airforce (live)."""
    import requests as req
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        r = req.get("https://api.airforce/v1/models", headers=headers, timeout=10)
        if not r.ok:
            return []
        result = []
        for m in r.json().get("data", []):
            if not m.get("supports_chat"):
                continue
            if m.get("status") not in ("operational", "degraded"):
                continue
            mid   = m.get("id", "")
            price = m.get("pricepermilliontokens", 999)
            owner = m.get("owned_by", "")
            is_free = price == 0
            cost_label = "(مجاني تماماً)" if is_free else f"(${price/1000:.3f}/1K tokens)"
            result.append({
                "id": mid,
                "name": f"{mid} [{owner}] {cost_label}",
                "free": is_free,
            })
        return sorted(result, key=lambda x: (not x["free"], x["id"]))
    except Exception:
        return []


@api_bp.route('/models/list', methods=['GET'])
@login_required
def list_models():
    """
    Returns available models for a given provider.
    If the provider has an API key configured, fetches live from the API.
    Falls back to static list if no key or API call fails.
    Query param: ?provider=gemini
    """
    from database.models import AIProviderKey
    provider = request.args.get('provider', '').lower()
    if not provider:
        return jsonify({'ok': False, 'error': 'provider required'}), 400

    # Get the first active key for this provider
    key_row = AIProviderKey.query.filter_by(
        provider=provider, is_active=True, is_exhausted=False
    ).order_by(AIProviderKey.priority).first()

    # Also check single-key config
    if not key_row:
        api_key = Config.get(f'{provider}_api_key', '')
    else:
        api_key = key_row.key_value

    models = []
    source = "static"

    if api_key:
        # Try live fetch
        if provider == "cohere":
            models = _fetch_cohere_models(api_key)
        elif provider == "gemini":
            models = _fetch_gemini_models(api_key)
        elif provider == "groq":
            models = _fetch_groq_models(api_key)
        elif provider == "openrouter":
            models = _fetch_openrouter_models(api_key)
        elif provider == "airforce":
            models = _fetch_airforce_models(api_key)

        if models:
            source = "live"

    # Fallback to static list
    if not models:
        models = _STATIC_MODELS.get(provider, [])
        source = "static"

    return jsonify({
        'ok': True,
        'provider': provider,
        'source': source,  # 'live' or 'static'
        'has_key': bool(api_key),
        'models': models,
    })


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
    from services.key_rotator import get_provider_status, get_all_providers_status
    providers = ['cohere', 'gemini', 'groq', 'openrouter', 'openai']
    data = get_all_providers_status()
    # Ensure all providers present
    for p in providers:
        if p not in data:
            data[p] = get_provider_status(p)
    return jsonify(data)




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


@api_bp.route('/prompts/reset', methods=['POST'])
@login_required
def reset_prompts():
    """إعادة ضبط البرومبتات للقيم الجديدة من prompts_config.py"""
    from database.models import Prompt
    try:
        Prompt.query.delete()
        db.session.commit()
        from prompts_config import PROMPTS
        for stage, model, temp, tokens, sys_p, usr_p in PROMPTS:
            db.session.add(Prompt(
                stage=stage, model=model, temperature=temp, max_tokens=tokens,
                system_prompt=sys_p, user_prompt=usr_p
            ))
        db.session.commit()
        return jsonify({'ok': True, 'message': f'تم إعادة ضبط {len(PROMPTS)} برومبت ✅'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]})
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


# ── Backup & Restore ──────────────────────────────────────────────────────────

@api_bp.route('/backup/export', methods=['GET'])
@login_required
def export_backup():
    """تصدير نسخة احتياطية كاملة بصيغة JSON."""
    from database.models import AIProviderKey, AIModel, Prompt, Platform, WorkflowLog

    # Config
    config_data = {r.key: r.value for r in Config.query.all()}

    # API Keys (social platforms)
    api_keys = [k.to_dict() for k in ApiKey.query.all()]

    # AI Provider Keys
    ai_keys = [k.to_dict() for k in AIProviderKey.query.all()]

    # AI Models
    ai_models = [m.to_dict() for m in AIModel.query.all()]

    # Prompts
    prompts = [p.to_dict() for p in Prompt.query.all()]

    # Platforms
    platforms = [p.to_dict() for p in Platform.query.all()]

    # Posts (بدون post_content لتقليل الحجم — اختياري)
    include_posts = request.args.get('include_posts', 'false') == 'true'
    posts_data = []
    if include_posts:
        posts_data = [p.to_dict() for p in Post.query.all()]

    backup = {
        'version': '1.0',
        'created_at': datetime.utcnow().isoformat(),
        'config': config_data,
        'api_keys': api_keys,
        'ai_provider_keys': ai_keys,
        'ai_models': ai_models,
        'prompts': prompts,
        'platforms': platforms,
        'posts': posts_data,
        'stats': {
            'total_posts': Post.query.count(),
            'posted': Post.query.filter_by(status='POSTED').count(),
            'pending': Post.query.filter_by(status='NEW').count(),
        }
    }

    filename = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        json.dumps(backup, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@api_bp.route('/backup/import', methods=['POST'])
@login_required
def import_backup():
    """استيراد نسخة احتياطية من ملف JSON."""
    from database.models import AIProviderKey, AIModel, Prompt, Platform

    if 'file' not in request.files:
        return jsonify({'error': 'لم يتم رفع ملف'}), 400

    f = request.files['file']
    try:
        data = json.loads(f.read().decode('utf-8'))
    except Exception as e:
        return jsonify({'error': f'ملف غير صالح: {e}'}), 400

    restored = {'config': 0, 'api_keys': 0, 'ai_keys': 0, 'prompts': 0, 'platforms': 0}

    # Config
    for key, value in data.get('config', {}).items():
        Config.set(key, value)
        restored['config'] += 1

    # API Keys
    for k in data.get('api_keys', []):
        if not ApiKey.query.filter_by(platform=k['platform'], label=k.get('label','')).first():
            db.session.add(ApiKey(
                platform=k['platform'], label=k.get('label',''),
                key_value=k.get('key_value',''), is_active=k.get('is_active', False)
            ))
            restored['api_keys'] += 1

    # AI Provider Keys
    for k in data.get('ai_provider_keys', []):
        if not AIProviderKey.query.filter_by(
            provider=k['provider'], key_value=k.get('key_value','')
        ).first():
            db.session.add(AIProviderKey(
                provider=k['provider'], label=k.get('label',''),
                key_value=k.get('key_value',''), priority=k.get('priority', 0),
                is_active=k.get('is_active', True)
            ))
            restored['ai_keys'] += 1

    # Prompts
    for p in data.get('prompts', []):
        row = db.session.get(Prompt, p['stage'])
        if row:
            row.system_prompt = p.get('system_prompt', row.system_prompt)
            row.user_prompt   = p.get('user_prompt', row.user_prompt)
            row.model         = p.get('model', row.model)
            row.temperature   = p.get('temperature', row.temperature)
            row.max_tokens    = p.get('max_tokens', row.max_tokens)
        else:
            db.session.add(Prompt(**{k: v for k, v in p.items() if k in
                ['stage','system_prompt','user_prompt','model','temperature','max_tokens']}))
        restored['prompts'] += 1

    # Platforms
    for p in data.get('platforms', []):
        row = db.session.get(Platform, p['name'])
        if row:
            row.enabled  = p.get('enabled', row.enabled)
            row.settings = json.dumps(p.get('settings', {}))
            restored['platforms'] += 1

    db.session.commit()

    # Sync to Redis if available
    try:
        from services.redis_config import sync_db_to_redis
        sync_db_to_redis()
    except Exception:
        pass

    return jsonify({'ok': True, 'restored': restored})


@api_bp.route('/backup/push-redis', methods=['POST'])
@login_required
def push_to_redis():
    """دفع كل الإعدادات الحالية إلى Redis يدوياً."""
    try:
        from services.redis_config import sync_db_to_redis, get_redis
        r = get_redis()
        if not r:
            return jsonify({'ok': False, 'error': 'REDIS_URL غير مضبوط'})
        sync_db_to_redis()
        return jsonify({'ok': True, 'message': 'تم حفظ الإعدادات في Redis ✅'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]})


@api_bp.route('/backup/push-sheets', methods=['POST'])
@login_required
def push_to_sheets():
    """دفع كل المنشورات إلى Google Sheets."""
    try:
        from services.sheets_sync import push_all_posts, is_configured
        if not is_configured():
            return jsonify({'ok': False, 'error': 'Google Sheets غير مضبوط — أضف GOOGLE_SHEETS_CREDENTIALS و GOOGLE_SHEET_ID'})
        count = push_all_posts()
        return jsonify({'ok': True, 'message': f'تم رفع {count} منشور إلى Google Sheets ✅'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


@api_bp.route('/backup/restore-sheets', methods=['POST'])
@login_required
def restore_from_sheets_api():
    """استعادة المنشورات من Google Sheets إلى DB."""
    try:
        from services.sheets_sync import restore_from_sheets, is_configured
        if not is_configured():
            return jsonify({'ok': False, 'error': 'Google Sheets غير مضبوط'})
        count = restore_from_sheets()
        return jsonify({'ok': True, 'message': f'تم استعادة {count} منشور من Google Sheets ✅'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


# ── PA Scheduled Tasks Setup ──────────────────────────────────────────────────

@api_bp.route('/pa-tasks/setup', methods=['POST'])
@login_required
def setup_pa_tasks():
    """
    يضبط PA Scheduled Tasks تلقائياً عبر PythonAnywhere API.
    يحتاج: pythonanywhere_token و pythonanywhere_username في الـ config.
    """
    import requests as req

    pa_token    = Config.get("pythonanywhere_token", "")
    pa_username = Config.get("pythonanywhere_username", "")

    if not pa_token or not pa_username:
        return jsonify({
            'ok': False,
            'error': 'أضف pythonanywhere_token و pythonanywhere_username في الإعدادات أولاً'
        })

    headers = {"Authorization": f"Token {pa_token}"}
    base    = f"https://www.pythonanywhere.com/api/v0/user/{pa_username}"
    app_dir = f"/home/{pa_username}/social-post"
    venv_py = f"{app_dir}/venv/bin/python"

    tasks_to_create = [
        {
            "description": "توليد الأفكار يومياً",
            "command": f"{venv_py} {app_dir}/pa_task_ideas.py",
            "hour": 8, "minute": 0,
        },
        {
            "description": "نشر المنشورات صباحاً",
            "command": f"{venv_py} {app_dir}/pa_task_post.py",
            "hour": 9, "minute": 0,
        },
        {
            "description": "نشر المنشورات مساءً",
            "command": f"{venv_py} {app_dir}/pa_task_post.py",
            "hour": 17, "minute": 0,
        },
    ]

    # Get existing tasks
    existing_r = req.get(f"{base}/schedule/tasks/", headers=headers, timeout=10)
    existing   = existing_r.json() if existing_r.ok else []
    existing_cmds = [t.get("command", "") for t in existing]

    created = []
    skipped = []
    errors  = []

    for task in tasks_to_create:
        cmd = task["command"]
        # Skip if already exists
        if any(cmd in ec for ec in existing_cmds):
            skipped.append(task["description"])
            continue

        # Free plan: max 2 tasks
        if len(existing) + len(created) >= 2:
            errors.append(f"حد الـ free plan (2 tasks) — تخطي: {task['description']}")
            continue

        r = req.post(f"{base}/schedule/tasks/", headers=headers, timeout=10, data={
            "command":  cmd,
            "enabled":  "true",
            "interval": "daily",
            "hour":     str(task["hour"]),
            "minute":   str(task["minute"]),
        })
        if r.ok:
            created.append(f"{task['description']} ({task['hour']:02d}:00)")
        else:
            errors.append(f"{task['description']}: {r.text[:100]}")

    return jsonify({
        'ok': True,
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'note': 'الـ free plan يسمح بـ 2 tasks فقط — استخدم 08:00 للأفكار و 09:00 للنشر',
    })


@api_bp.route('/pa-tasks/list', methods=['GET'])
@login_required
def list_pa_tasks():
    """عرض الـ PA Scheduled Tasks الحالية."""
    import requests as req

    pa_token    = Config.get("pythonanywhere_token", "")
    pa_username = Config.get("pythonanywhere_username", "")

    if not pa_token or not pa_username:
        return jsonify({'ok': False, 'tasks': [], 'error': 'PA credentials not set'})

    headers = {"Authorization": f"Token {pa_token}"}
    r = req.get(
        f"https://www.pythonanywhere.com/api/v0/user/{pa_username}/schedule/tasks/",
        headers=headers, timeout=10
    )
    if r.ok:
        return jsonify({'ok': True, 'tasks': r.json()})
    return jsonify({'ok': False, 'tasks': [], 'error': r.text[:200]})


@api_bp.route('/sheets/sync', methods=['POST'])
@login_required
def manual_sheets_sync():
    """مزامنة يدوية من Google Sheets → DB."""
    try:
        from services.sheets_sync import sync_from_sheets_to_db, is_configured
        if not is_configured():
            return jsonify({'ok': False, 'error': 'Google Sheets غير مضبوط'})
        ins, upd = sync_from_sheets_to_db()
        return jsonify({
            'ok': True,
            'message': f'✅ تمت المزامنة: {ins} جديد، {upd} محدّث'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


# ── Workflow shortcuts (used by scheduler page) ───────────────────────────────

@api_bp.route('/workflow/ideas', methods=['POST'])
@login_required
def api_run_ideas():
    from flask import current_app
    import threading
    app = current_app._get_current_object()
    threading.Thread(target=lambda: __import__('services.workflow_service', fromlist=['run_idea_factory']).run_idea_factory(app), daemon=True).start()
    return jsonify({'ok': True, 'message': '🧠 مصنع الأفكار يعمل في الخلفية — تحقق من /posts بعد دقيقة'})


@api_bp.route('/workflow/post', methods=['POST'])
@login_required
def api_run_post():
    from flask import current_app
    import threading
    app = current_app._get_current_object()
    threading.Thread(target=lambda: __import__('services.workflow_service', fromlist=['run_post_engine']).run_post_engine(app), daemon=True).start()
    return jsonify({'ok': True, 'message': '📢 محرك النشر يعمل في الخلفية'})


# ── Image test endpoint ───────────────────────────────────────────────────────

@api_bp.route('/image/test', methods=['POST'])
@login_required
def test_image_generation():
    """Test image generation through the full provider chain."""
    from database.models import Config as Cfg
    prompt = request.json.get('prompt', 'A colorful educational scene, warm light')
    cfg = {row.key: row.value for row in Cfg.query.all()}
    try:
        from services.image_service import (
            _enhance_prompt, generate_image_cloudflare,
            _try_huggingface, _try_together, _try_fal,
            generate_image_pollinations, upload_to_cloudinary,
            _try_gemini_image, _try_airforce
        )
        width      = int(cfg.get('image_width', 1080))
        height     = int(cfg.get('image_height', 1350))
        worker_url = cfg.get('worker_url', '')
        poll_key   = cfg.get('pollinations_key', '')
        cloud_name = cfg.get('cloudinary_cloud_name', '')
        api_key    = cfg.get('cloudinary_api_key', '')
        api_secret = cfg.get('cloudinary_api_secret', '')

        enhanced = _enhance_prompt(prompt)
        image_bytes = None
        used = ''

        if worker_url:
            try:
                image_bytes = generate_image_cloudflare(worker_url, enhanced, width, height)
                used = 'Cloudflare Worker'
            except Exception: pass

        if not image_bytes:
            image_bytes = _try_gemini_image(enhanced, width, height)
            if image_bytes: used = 'Google Imagen'

        if not image_bytes:
            image_bytes = _try_huggingface(enhanced, width, height)
            if image_bytes: used = 'HuggingFace'

        if not image_bytes:
            image_bytes = _try_together(enhanced, width, height)
            if image_bytes: used = 'Together AI'

        if not image_bytes:
            image_bytes = _try_fal(enhanced, width, height)
            if image_bytes: used = 'Fal.ai'

        if not image_bytes:
            image_bytes = _try_airforce(enhanced, width, height)
            if image_bytes: used = 'api.airforce'

        if not image_bytes:
            image_bytes = generate_image_pollinations(
                enhanced, width=min(width, 1080), height=min(height, 1080), api_key=poll_key
            )
            used = 'Pollinations'

        if not cloud_name:
            return jsonify({'ok': False, 'error': 'Cloudinary غير مضبوط'})

        url_result = upload_to_cloudinary(image_bytes, cloud_name, api_key, api_secret, folder='test')
        url = url_result[0] if isinstance(url_result, tuple) else url_result
        return jsonify({'ok': True, 'url': url, 'provider': used})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


@api_bp.route('/image/test-overlay', methods=['POST'])
@login_required
def test_image_overlay():
    """Test image generation + text overlay."""
    from database.models import Config as Cfg
    data         = request.json
    prompt       = data.get('prompt', 'A colorful educational scene, warm light')
    post_content = data.get('post_content', '')
    idea         = data.get('idea', '')

    cfg = {row.key: row.value for row in Cfg.query.all()}
    try:
        from services.image_service import (
            _enhance_prompt, generate_image_cloudflare,
            _try_huggingface, _try_together, _try_fal,
            generate_image_pollinations, upload_to_cloudinary,
            _try_gemini_image, _try_airforce
        )
        from services.overlay_service import process_overlay, generate_overlay_text

        width      = int(cfg.get('image_width', 1080))
        height     = int(cfg.get('image_height', 1350))
        worker_url = cfg.get('worker_url', '')
        poll_key   = cfg.get('pollinations_key', '')
        cloud_name = cfg.get('cloudinary_cloud_name', '')
        api_key    = cfg.get('cloudinary_api_key', '')
        api_secret = cfg.get('cloudinary_api_secret', '')

        enhanced = _enhance_prompt(prompt)
        image_bytes = None
        used = ''

        if worker_url:
            try:
                image_bytes = generate_image_cloudflare(worker_url, enhanced, width, height)
                used = 'Cloudflare Worker'
            except Exception: pass

        if not image_bytes:
            image_bytes = _try_gemini_image(enhanced, width, height)
            if image_bytes: used = 'Google Imagen'

        if not image_bytes:
            image_bytes = _try_airforce(enhanced, width, height)
            if image_bytes: used = 'api.airforce'

        if not image_bytes:
            image_bytes = generate_image_pollinations(
                enhanced, width=min(width, 1080), height=min(height, 1080), api_key=poll_key
            )
            used = 'Pollinations'

        if not cloud_name:
            return jsonify({'ok': False, 'error': 'Cloudinary غير مضبوط'})

        # Apply overlay
        overlay_text = ""
        overlaid = process_overlay(image_bytes, post_content, idea)
        if overlaid != image_bytes:
            # Get the generated text for display
            from services.overlay_service import _get_overlay_cfg, _extract_first_line
            ocfg = _get_overlay_cfg()
            if ocfg["text_source"] == "custom":
                overlay_text = ocfg["custom_text"]
            elif ocfg["text_source"] == "first_line":
                overlay_text = _extract_first_line(post_content)
            else:
                overlay_text = generate_overlay_text(post_content, idea)

        url_result = upload_to_cloudinary(
            overlaid, cloud_name, api_key, api_secret, folder='test_overlay'
        )
        url = url_result[0] if isinstance(url_result, tuple) else url_result
        return jsonify({'ok': True, 'url': url, 'provider': used, 'overlay_text': overlay_text})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


# ── Analytics endpoints ───────────────────────────────────────────────────────

@api_bp.route('/analytics/refresh/<int:post_id>', methods=['POST'])
@login_required
def refresh_post_metrics(post_id):
    """Fetch and update metrics for a single post from all platforms."""
    try:
        from services.analytics_service import update_post_metrics
        result = update_post_metrics(post_id)
        if result:
            return jsonify({
                'ok': True,
                'score':     result.get('score', 0),
                'totals':    result.get('totals', {}),
                'platforms': result.get('platforms', {}),
            })
        return jsonify({'ok': False, 'error': 'No metrics returned — check platform credentials'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


@api_bp.route('/analytics/refresh-all', methods=['POST'])
@login_required
def refresh_all_metrics():
    """Bulk update metrics for recent posts."""
    try:
        from flask import current_app
        from services.analytics_service import bulk_update_metrics
        limit   = int(request.json.get('limit', 20)) if request.json else 20
        updated = bulk_update_metrics(app=current_app._get_current_object(), limit=limit)
        return jsonify({'ok': True, 'updated': updated})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:300]})


@api_bp.route('/analytics/summary', methods=['GET'])
@login_required
def analytics_summary():
    """Get analytics summary for the dashboard."""
    from database.models import Post
    from datetime import datetime, timedelta

    days = int(request.args.get('days', 30))
    since = datetime.utcnow() - timedelta(days=days)

    posts = Post.query.filter(
        Post.status == 'POSTED',
        Post.posted_at >= since
    ).order_by(Post.posted_at.desc()).all()

    if not posts:
        return jsonify({'ok': True, 'posts': [], 'summary': {}})

    total_likes       = sum(p.likes or 0 for p in posts)
    total_comments    = sum(p.comments or 0 for p in posts)
    total_shares      = sum(p.shares or 0 for p in posts)
    total_impressions = sum(p.impressions or 0 for p in posts)
    avg_score         = int(sum(p.engagement_score or 0 for p in posts) / len(posts))

    # Best performing
    top_posts = sorted(posts, key=lambda p: p.engagement_score or 0, reverse=True)[:5]

    # By writing style
    style_scores = {}
    for p in posts:
        if p.writing_style:
            if p.writing_style not in style_scores:
                style_scores[p.writing_style] = []
            style_scores[p.writing_style].append(p.engagement_score or 0)
    style_avg = {k: int(sum(v)/len(v)) for k, v in style_scores.items() if v}

    # By tone
    tone_scores = {}
    for p in posts:
        if p.tone:
            if p.tone not in tone_scores:
                tone_scores[p.tone] = []
            tone_scores[p.tone].append(p.engagement_score or 0)
    tone_avg = {k: int(sum(v)/len(v)) for k, v in tone_scores.items() if v}

    # Daily trend (last 7 days)
    daily = {}
    for p in posts:
        if p.posted_at:
            day = p.posted_at.strftime('%Y-%m-%d')
            if day not in daily:
                daily[day] = {'count': 0, 'score': 0}
            daily[day]['count'] += 1
            daily[day]['score'] += p.engagement_score or 0

    return jsonify({
        'ok': True,
        'summary': {
            'total_posts':    len(posts),
            'total_likes':    total_likes,
            'total_comments': total_comments,
            'total_shares':   total_shares,
            'total_impressions': total_impressions,
            'avg_score':      avg_score,
            'best_style':     max(style_avg, key=style_avg.get) if style_avg else '—',
            'best_tone':      max(tone_avg, key=tone_avg.get) if tone_avg else '—',
        },
        'top_posts': [p.to_dict() for p in top_posts],
        'style_avg': style_avg,
        'tone_avg':  tone_avg,
        'daily':     daily,
    })


@api_bp.route('/overlay/fonts', methods=['GET'])
@login_required
def get_overlay_fonts():
    """Return available Arabic fonts with availability status."""
    from services.overlay_service import get_available_fonts
    return jsonify({'ok': True, 'fonts': get_available_fonts()})


# ── Provider chain order ──────────────────────────────────────────────────────

@api_bp.route('/provider-chain', methods=['GET'])
@login_required
def get_provider_chain():
    """Get current AI and image provider chains."""
    from services.key_rotator import get_ai_chain, get_image_chain, _DEFAULT_AI_CHAIN, _DEFAULT_IMAGE_CHAIN
    return jsonify({
        'ok': True,
        'ai_chain':    get_ai_chain(),
        'image_chain': get_image_chain(),
        'ai_default':    list(_DEFAULT_AI_CHAIN),
        'image_default': list(_DEFAULT_IMAGE_CHAIN),
    })


@api_bp.route('/provider-chain', methods=['POST'])
@login_required
def save_provider_chain():
    """Save AI and/or image provider chain order."""
    data = request.json or {}
    if 'ai_chain' in data:
        chain = [p.strip() for p in data['ai_chain'] if p.strip()]
        Config.set('ai_provider_chain', ','.join(chain))
    if 'image_chain' in data:
        chain = [p.strip() for p in data['image_chain'] if p.strip()]
        Config.set('image_provider_chain', ','.join(chain))
    return jsonify({'ok': True})


@api_bp.route('/redis/status', methods=['GET'])
@login_required
def redis_status():
    """Check Redis connection status and key count."""
    try:
        from services.redis_config import get_redis, reset_redis_client
        # Force reconnect attempt
        reset_redis_client()
        r = get_redis()
        if not r:
            return jsonify({'ok': False, 'connected': False,
                            'error': 'REDIS_URL غير مضبوط أو الاتصال فشل'})
        keys = r.keys('config:*')
        return jsonify({
            'ok': True, 'connected': True,
            'keys_count': len(keys),
            'message': f'✅ متصل — {len(keys)} مفتاح محفوظ'
        })
    except Exception as e:
        return jsonify({'ok': False, 'connected': False, 'error': str(e)[:200]})


@api_bp.route('/redis/sync', methods=['POST'])
@login_required
def redis_force_sync():
    """Force sync DB → Redis."""
    try:
        from services.redis_config import sync_db_to_redis, reset_redis_client, get_redis
        reset_redis_client()
        r = get_redis()
        if not r:
            return jsonify({'ok': False, 'error': 'Redis غير متصل'})
        sync_db_to_redis()
        keys = r.keys('config:*')
        return jsonify({'ok': True, 'message': f'✅ تم sync {len(keys)} مفتاح إلى Redis'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]})
