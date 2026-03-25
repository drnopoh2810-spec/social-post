"""
AI Provider Key Rotator
=======================
Manages multiple API keys per provider with automatic failover.

Logic:
  1. Pick the lowest-priority non-exhausted active key.
  2. Try the call.
  3. On success → reset fail_count, update last_used_at.
  4. On rate-limit / quota error (429, 402, specific messages) →
       mark key as exhausted, log error, try next key.
  5. On other transient error → increment fail_count.
     If fail_count >= MAX_FAILS → mark exhausted.
  6. If ALL keys exhausted → raise KeysExhaustedError.

Reset:
  Admin can manually reset exhausted keys from the dashboard,
  or they auto-reset after RESET_AFTER_HOURS hours.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_FAILS = 3          # consecutive failures before marking exhausted
RESET_AFTER_HOURS = 24  # auto-reset exhausted keys after this many hours

# HTTP status codes / error substrings that mean "quota/rate-limit"
QUOTA_STATUS_CODES = {429, 402, 403}
QUOTA_ERROR_STRINGS = [
    "rate limit", "quota", "exceeded", "too many requests",
    "insufficient_quota", "billing", "limit reached",
    "resource_exhausted", "rateLimitExceeded",
]


class KeysExhaustedError(Exception):
    """Raised when all keys for a provider are exhausted."""
    pass


def _is_quota_error(exc) -> bool:
    """Detect if an exception is a quota/rate-limit error."""
    msg = str(exc).lower()
    if any(s in msg for s in QUOTA_ERROR_STRINGS):
        return True
    # requests.HTTPError carries status code
    if hasattr(exc, 'response') and exc.response is not None:
        if exc.response.status_code in QUOTA_STATUS_CODES:
            return True
    return False


def _auto_reset_if_due(key):
    """Auto-reset a key if it's been exhausted long enough."""
    if key.is_exhausted and key.exhausted_at:
        if datetime.utcnow() - key.exhausted_at > timedelta(hours=RESET_AFTER_HOURS):
            key.is_exhausted = False
            key.fail_count = 0
            key.last_error = None
            key.exhausted_at = None
            logger.info(f"Auto-reset key #{key.id} ({key.provider} / {key.label}) after {RESET_AFTER_HOURS}h")
            return True
    return False


def get_available_keys(provider: str):
    """
    Return all active, non-exhausted keys for a provider,
    sorted by priority (ascending). Auto-resets stale exhausted keys.
    """
    from database.models import db, AIProviderKey
    keys = AIProviderKey.query.filter_by(provider=provider, is_active=True).order_by(
        AIProviderKey.priority.asc(), AIProviderKey.id.asc()
    ).all()

    reset_any = False
    for k in keys:
        if _auto_reset_if_due(k):
            reset_any = True
    if reset_any:
        db.session.commit()

    return [k for k in keys if not k.is_exhausted]


def call_with_rotation(provider: str, call_fn, *args, **kwargs):
    """
    Execute call_fn(api_key, *args, **kwargs) with automatic key rotation.

    call_fn signature: call_fn(api_key: str, ...) -> result

    Raises KeysExhaustedError if all keys fail.
    Falls back to Config single-key if no AIProviderKey rows exist.
    """
    from database.models import db, AIProviderKey, Config, WorkflowLog

    keys = get_available_keys(provider)

    # ── Fallback: no keys in DB → use Config single key ──────────────────────
    if not keys:
        fallback_key = Config.get(f"{provider}_api_key", "")
        if not fallback_key:
            raise KeysExhaustedError(f"No API keys configured for provider '{provider}'")
        logger.debug(f"Using fallback config key for {provider}")
        return call_fn(fallback_key, *args, **kwargs)

    last_exc = None
    for key in keys:
        try:
            result = call_fn(key.key_value, *args, **kwargs)
            # ── Success ──────────────────────────────────────────────────────
            key.last_used_at = datetime.utcnow()
            key.fail_count = 0
            key.last_error = None
            db.session.commit()
            logger.debug(f"Key #{key.id} ({key.label}) succeeded for {provider}")
            return result

        except Exception as exc:
            last_exc = exc
            is_quota = _is_quota_error(exc)
            key.fail_count = (key.fail_count or 0) + 1
            key.last_error = str(exc)[:500]

            if is_quota or key.fail_count >= MAX_FAILS:
                key.is_exhausted = True
                key.exhausted_at = datetime.utcnow()
                reason = "quota/rate-limit" if is_quota else f"fail_count={key.fail_count}"
                logger.warning(
                    f"Key #{key.id} ({key.provider}/{key.label}) exhausted — {reason}. "
                    f"Trying next key..."
                )
                # Log to workflow_logs
                log = WorkflowLog(
                    event="key_rotation",
                    message=f"Key #{key.id} '{key.label}' ({key.provider}) exhausted: {reason}. Error: {str(exc)[:200]}",
                    level="warning"
                )
                db.session.add(log)
            else:
                logger.warning(
                    f"Key #{key.id} ({key.provider}/{key.label}) failed "
                    f"(attempt {key.fail_count}/{MAX_FAILS}): {exc}"
                )

            db.session.commit()
            continue  # try next key

    # All keys exhausted
    log = WorkflowLog(
        event="key_rotation",
        message=f"ALL keys exhausted for provider '{provider}'. Last error: {str(last_exc)[:300]}",
        level="error"
    )
    from database.models import db as _db
    _db.session.add(log)
    _db.session.commit()

    raise KeysExhaustedError(
        f"All API keys for '{provider}' are exhausted. Last error: {last_exc}"
    )


# ── Admin helpers ─────────────────────────────────────────────────────────────

def reset_key(key_id: int):
    """Manually reset an exhausted key."""
    from database.models import db, AIProviderKey
    key = db.session.get(AIProviderKey, key_id)
    if key:
        key.is_exhausted = False
        key.fail_count = 0
        key.last_error = None
        key.exhausted_at = None
        db.session.commit()
        logger.info(f"Key #{key_id} manually reset")


def reset_all_keys(provider: str):
    """Reset all exhausted keys for a provider."""
    from database.models import db, AIProviderKey
    AIProviderKey.query.filter_by(provider=provider, is_exhausted=True).update({
        'is_exhausted': False,
        'fail_count': 0,
        'last_error': None,
        'exhausted_at': None,
    })
    db.session.commit()
    logger.info(f"All keys reset for provider '{provider}'")


def get_provider_status(provider: str) -> dict:
    """Return a summary of key health for a provider."""
    from database.models import AIProviderKey
    all_keys = AIProviderKey.query.filter_by(provider=provider).all()
    active = [k for k in all_keys if k.is_active and not k.is_exhausted]
    exhausted = [k for k in all_keys if k.is_exhausted]
    disabled = [k for k in all_keys if not k.is_active]
    return {
        'total': len(all_keys),
        'available': len(active),
        'exhausted': len(exhausted),
        'disabled': len(disabled),
        'healthy': len(active) > 0,
    }
