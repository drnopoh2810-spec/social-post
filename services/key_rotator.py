"""
AI Provider Key Rotator — Multi-Provider Failover
===================================================
نظام rotation متكامل على مستويين:

المستوى 1 — Key Rotation (داخل نفس الـ provider):
  • يجرب كل مفاتيح الـ provider بالترتيب (priority)
  • لو مفتاح وصل rate-limit/quota → يعلّمه exhausted ويجرب التالي
  • بعد RESET_AFTER_HOURS ساعة → يعيد تفعيل المفتاح تلقائياً

المستوى 2 — Provider Failover (بين الـ providers):
  • لو كل مفاتيح provider X انتهت → يجرب provider Y تلقائياً
  • ترتيب الـ fallback محدد في PROVIDER_FALLBACK_CHAIN
  • يحوّل الـ model تلقائياً للنموذج المكافئ في الـ provider الجديد

Model Mapping:
  • لكل stage عنده model mapping بين الـ providers
  • لو مفيش mapping → يستخدم default model للـ provider الجديد
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_FAILS         = 3   # consecutive failures before marking exhausted
RESET_AFTER_HOURS = 24  # auto-reset exhausted keys after N hours

# ── Provider fallback chain ───────────────────────────────────────────────────
# لو provider X فشل → يجرب الـ providers دي بالترتيب
PROVIDER_FALLBACK_CHAIN = [
    "gemini",
    "groq",
    "cohere",
    "openrouter",
    "airforce",   # مجاني — deepseek-v3, gemini-2.5-flash, gemma3 (free)
    "openai",
]

# ── Model equivalents across providers ───────────────────────────────────────
PROVIDER_DEFAULT_MODELS = {
    "gemini":     "gemini-2.0-flash",
    "groq":       "llama-3.3-70b-versatile",
    "cohere":     "command-r7b-arabic-02-2025",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    "airforce":   "deepseek-v3-0324",   # operational + يدعم العربية جيداً
    "openai":     "gpt-4o-mini",
}

# HTTP status codes / error substrings that mean "quota/rate-limit"
QUOTA_STATUS_CODES  = {429, 402, 403}
QUOTA_ERROR_STRINGS = [
    "rate limit", "quota", "exceeded", "too many requests",
    "insufficient_quota", "billing", "limit reached",
    "resource_exhausted", "ratelimitexceeded", "daily limit",
    "tokens per", "requests per",
]


class KeysExhaustedError(Exception):
    """Raised when all keys for ALL providers are exhausted."""
    pass


class ProviderExhaustedError(Exception):
    """Raised when all keys for a single provider are exhausted (triggers failover)."""
    pass


def _is_quota_error(exc) -> bool:
    msg = str(exc).lower()
    if any(s in msg for s in QUOTA_ERROR_STRINGS):
        return True
    if hasattr(exc, 'response') and exc.response is not None:
        if exc.response.status_code in QUOTA_STATUS_CODES:
            return True
    return False


def _is_transient_error(exc) -> bool:
    """Network/timeout errors — don't exhaust the key, just retry."""
    msg = str(exc).lower()
    return any(s in msg for s in ["timeout", "connection", "network", "read timed out", "ssl"])


def _auto_reset_if_due(key):
    if key.is_exhausted and key.exhausted_at:
        if datetime.utcnow() - key.exhausted_at > timedelta(hours=RESET_AFTER_HOURS):
            key.is_exhausted = False
            key.fail_count   = 0
            key.last_error   = None
            key.exhausted_at = None
            logger.info(f"Auto-reset key #{key.id} ({key.provider}/{key.label})")
            return True
    return False


def get_available_keys(provider: str):
    """Return active non-exhausted keys for a provider, sorted by priority."""
    from database.models import db, AIProviderKey
    keys = AIProviderKey.query.filter_by(
        provider=provider, is_active=True
    ).order_by(AIProviderKey.priority.asc(), AIProviderKey.id.asc()).all()

    reset_any = False
    for k in keys:
        if _auto_reset_if_due(k):
            reset_any = True
    if reset_any:
        db.session.commit()

    return [k for k in keys if not k.is_exhausted]


def _try_provider(provider: str, call_fn):
    """
    Try all keys for a single provider.
    Returns result on success.
    Raises ProviderExhaustedError if all keys fail.
    """
    from database.models import db, AIProviderKey, Config, WorkflowLog

    keys = get_available_keys(provider)

    # Fallback: no AIProviderKey rows → use Config single key
    if not keys:
        fallback = Config.get(f"{provider}_api_key", "")
        if not fallback:
            raise ProviderExhaustedError(f"No keys configured for '{provider}'")
        logger.debug(f"Using config fallback key for {provider}")
        try:
            return call_fn(fallback)
        except Exception as exc:
            raise ProviderExhaustedError(f"Config key for '{provider}' failed: {exc}") from exc

    last_exc = None
    for key in keys:
        try:
            result = call_fn(key.key_value)
            # Success
            key.last_used_at = datetime.utcnow()
            key.fail_count   = 0
            key.last_error   = None
            db.session.commit()
            logger.debug(f"✅ Key #{key.id} ({key.label}) succeeded for {provider}")
            return result

        except Exception as exc:
            last_exc = exc
            is_quota    = _is_quota_error(exc)
            is_transient = _is_transient_error(exc)

            if is_transient:
                # Network error — don't exhaust, just skip this attempt
                logger.warning(f"⚠️ Key #{key.id} ({provider}/{key.label}) transient error: {exc}")
                key.fail_count = (key.fail_count or 0) + 1
                key.last_error = str(exc)[:300]
                db.session.commit()
                continue

            key.fail_count = (key.fail_count or 0) + 1
            key.last_error = str(exc)[:500]

            if is_quota or key.fail_count >= MAX_FAILS:
                key.is_exhausted = True
                key.exhausted_at = datetime.utcnow()
                reason = "quota/rate-limit" if is_quota else f"fail×{key.fail_count}"
                logger.warning(f"🔴 Key #{key.id} ({provider}/{key.label}) exhausted — {reason}")
                db.session.add(WorkflowLog(
                    event="key_rotation",
                    message=f"Key #{key.id} '{key.label}' ({provider}) exhausted [{reason}]: {str(exc)[:200]}",
                    level="warning"
                ))
            else:
                logger.warning(f"⚠️ Key #{key.id} ({provider}/{key.label}) failed ({key.fail_count}/{MAX_FAILS}): {exc}")

            db.session.commit()

    # All keys for this provider exhausted
    raise ProviderExhaustedError(
        f"All keys for '{provider}' exhausted. Last: {last_exc}"
    ) from last_exc


def call_with_rotation(provider: str, call_fn, *args, **kwargs):
    """
    Execute call_fn(api_key) with full multi-provider failover.

    Level 1: rotates through all keys of `provider`
    Level 2: if all keys exhausted → tries next provider in PROVIDER_FALLBACK_CHAIN
             and wraps call_fn to use the new provider's API

    Returns result on success.
    Raises KeysExhaustedError if ALL providers fail.
    """
    from database.models import db, WorkflowLog

    # Build provider chain: requested provider first, then fallbacks
    chain = [provider] + [p for p in PROVIDER_FALLBACK_CHAIN if p != provider]

    tried = []
    for current_provider in chain:
        # Check if this provider has any keys at all
        available = get_available_keys(current_provider)
        has_config_key = bool(__import__('os').environ.get(f"{current_provider.upper()}_API_KEY") or
                              _get_config_key(current_provider))

        if not available and not has_config_key:
            logger.debug(f"Skipping {current_provider} — no keys configured")
            continue

        # Wrap call_fn for the current provider if it's a fallback
        if current_provider != provider:
            wrapped_fn = _make_provider_wrapper(current_provider, call_fn, provider)
            if wrapped_fn is None:
                logger.debug(f"Skipping {current_provider} — no wrapper available")
                continue
        else:
            wrapped_fn = call_fn

        try:
            result = _try_provider(current_provider, wrapped_fn)

            if current_provider != provider:
                logger.info(f"✅ Failover succeeded: {provider} → {current_provider}")
                db.session.add(WorkflowLog(
                    event="provider_failover",
                    message=f"Failover: {provider} → {current_provider} (tried: {tried})",
                    level="info"
                ))
                db.session.commit()

            return result

        except ProviderExhaustedError as e:
            tried.append(current_provider)
            logger.warning(f"🔴 Provider '{current_provider}' exhausted — trying next...")
            db.session.add(WorkflowLog(
                event="provider_failover",
                message=f"Provider '{current_provider}' exhausted, trying next. Error: {str(e)[:150]}",
                level="warning"
            ))
            db.session.commit()
            continue

    # All providers failed
    db.session.add(WorkflowLog(
        event="provider_failover",
        message=f"ALL providers exhausted! Tried: {tried}",
        level="error"
    ))
    db.session.commit()

    raise KeysExhaustedError(
        f"All providers exhausted. Tried: {tried}"
    )


def _get_config_key(provider: str) -> str:
    """Get single API key from Config DB."""
    try:
        from database.models import Config
        return Config.get(f"{provider}_api_key", "")
    except Exception:
        return ""


def _make_provider_wrapper(new_provider: str, original_call_fn, original_provider: str):
    """
    Create a wrapper that calls the new provider's API instead of the original.
    Extracts closure variables safely from the original call_fn.
    """
    from services.ai_service import _call_gemini, _call_openai_compat, _call_cohere, PROVIDER_BASE_URLS

    # Extract closure variables safely
    closure_vars = {}
    try:
        if hasattr(original_call_fn, '__closure__') and original_call_fn.__closure__:
            code = original_call_fn.__code__
            freevars = code.co_freevars
            cells = original_call_fn.__closure__
            closure_vars = {
                name: cell.cell_contents
                for name, cell in zip(freevars, cells)
                if hasattr(cell, 'cell_contents')
            }
    except Exception as e:
        logger.debug(f"Could not extract closure vars: {e}")

    # Get default model for new provider
    default_model = PROVIDER_DEFAULT_MODELS.get(new_provider, "")
    if not default_model:
        return None

    # Read params from closure (set in ai_service.call_ai._do_call)
    model_id      = closure_vars.get('model_id',      closure_vars.get('_model_id',      default_model))
    system_prompt = closure_vars.get('system_prompt', closure_vars.get('_system_prompt', ''))
    user_prompt   = closure_vars.get('user_prompt',   closure_vars.get('_user_prompt',   ''))
    temperature   = closure_vars.get('temperature',   closure_vars.get('_temperature',   0.8))
    max_tokens    = closure_vars.get('max_tokens',    closure_vars.get('_max_tokens',    2048))

    def wrapper(api_key: str):
        if new_provider == "gemini":
            return _call_gemini(api_key, default_model, system_prompt, user_prompt, temperature, max_tokens)
        elif new_provider == "cohere":
            return _call_cohere(api_key, default_model, system_prompt, user_prompt, temperature, max_tokens)
        else:
            base_url = PROVIDER_BASE_URLS.get(new_provider, PROVIDER_BASE_URLS["openai"])
            return _call_openai_compat(api_key, default_model, system_prompt, user_prompt,
                                       temperature, max_tokens, base_url)

    return wrapper


# ── Admin helpers ─────────────────────────────────────────────────────────────

def reset_key(key_id: int):
    from database.models import db, AIProviderKey
    key = db.session.get(AIProviderKey, key_id)
    if key:
        key.is_exhausted = False
        key.fail_count   = 0
        key.last_error   = None
        key.exhausted_at = None
        db.session.commit()
        logger.info(f"Key #{key_id} manually reset")


def reset_all_keys(provider: str):
    from database.models import db, AIProviderKey
    AIProviderKey.query.filter_by(provider=provider, is_exhausted=True).update({
        'is_exhausted': False, 'fail_count': 0,
        'last_error': None, 'exhausted_at': None,
    })
    db.session.commit()
    logger.info(f"All keys reset for provider '{provider}'")


def get_provider_status(provider: str) -> dict:
    from database.models import AIProviderKey
    all_keys  = AIProviderKey.query.filter_by(provider=provider).all()
    active    = [k for k in all_keys if k.is_active and not k.is_exhausted]
    exhausted = [k for k in all_keys if k.is_exhausted]
    disabled  = [k for k in all_keys if not k.is_active]
    return {
        'total':     len(all_keys),
        'available': len(active),
        'exhausted': len(exhausted),
        'disabled':  len(disabled),
        'healthy':   len(active) > 0,
    }


def get_all_providers_status() -> dict:
    """Summary of all providers health."""
    result = {}
    for p in PROVIDER_FALLBACK_CHAIN:
        status = get_provider_status(p)
        config_key = _get_config_key(p)
        status['has_config_key'] = bool(config_key)
        status['usable'] = status['healthy'] or status['has_config_key']
        result[p] = status
    return result
