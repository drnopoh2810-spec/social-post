"""
Redis Config Store — Upstash Redis via REST API
=================================================
يستخدم Upstash REST API (HTTPS port 443) بدل TCP port 6379.
هذا يحل مشكلة PythonAnywhere الذي يحجب port 6379.

الاستخدام:
  REDIS_URL=rediss://default:TOKEN@host:6379  (يُحوَّل تلقائياً لـ REST)
  أو مباشرةً:
  UPSTASH_REDIS_REST_URL=https://host.upstash.io
  UPSTASH_REDIS_REST_TOKEN=TOKEN
"""

import os
import logging
import requests as _requests

logger = logging.getLogger(__name__)

_rest_url   = None   # https://current-fox-81218.upstash.io
_rest_token = None   # Bearer token
_connected  = False
_failed     = False


def reset_redis_client():
    """Force reconnect on next call."""
    global _rest_url, _rest_token, _connected, _failed
    _rest_url   = None
    _rest_token = None
    _connected  = False
    _failed     = False


def _parse_redis_url(url: str):
    """
    Extract REST URL and token from various Upstash URL formats.

    Supported formats:
      rediss://default:TOKEN@host:6379
      redis://default:TOKEN@host:6379
      https://host.upstash.io  (with separate token)
    """
    url = url.strip()
    if url.startswith("https://"):
        # Already REST URL — token must come from env
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        return url.rstrip("/"), token

    # Parse redis(s)://default:TOKEN@host:PORT
    try:
        # Remove scheme
        rest = url.split("://", 1)[1] if "://" in url else url
        # Split user:pass@host:port
        at_idx = rest.rfind("@")
        if at_idx == -1:
            return None, None
        userinfo = rest[:at_idx]          # default:TOKEN
        hostport = rest[at_idx + 1:]      # host:6379
        host     = hostport.split(":")[0] # host only
        token    = userinfo.split(":", 1)[1] if ":" in userinfo else userinfo
        rest_url = f"https://{host}"
        return rest_url, token
    except Exception as e:
        logger.warning(f"Could not parse Redis URL: {e}")
        return None, None


def _init_client():
    """Initialize REST client from env or DB."""
    global _rest_url, _rest_token, _connected, _failed

    if _connected:
        return True
    if _failed:
        return False

    # 1. Try UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN directly
    rest_url   = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    rest_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

    # 2. Try REDIS_URL (parse it)
    if not rest_url:
        redis_url = os.environ.get("REDIS_URL", "").strip()
        if redis_url:
            rest_url, rest_token = _parse_redis_url(redis_url)

    # 3. Try DB
    if not rest_url:
        try:
            from database.models import db as _db, Config as _Cfg
            row = _db.session.get(_Cfg, 'redis_url')
            if row and row.value:
                rest_url, rest_token = _parse_redis_url(row.value)
        except Exception:
            pass

    if not rest_url or not rest_token:
        return False

    # Test connection with a PING
    try:
        r = _requests.post(
            f"{rest_url}/ping",
            headers={"Authorization": f"Bearer {rest_token}"},
            timeout=8,
        )
        if r.ok and "PONG" in r.text.upper():
            _rest_url   = rest_url
            _rest_token = rest_token
            _connected  = True
            logger.info(f"Redis REST connected: {rest_url}")
            return True
        else:
            logger.warning(f"Redis REST ping failed: {r.status_code} {r.text[:100]}")
            _failed = True
            return False
    except Exception as e:
        logger.warning(f"Redis REST connection failed: {e}")
        _failed = True
        return False


def get_redis():
    """Returns True if connected, None otherwise (for backward compat)."""
    if _init_client():
        return True
    return None


def _exec(command: list):
    """Execute a Redis command via REST API."""
    if not _init_client():
        return None
    try:
        r = _requests.post(
            f"{_rest_url}/{'/'.join(str(c) for c in command)}",
            headers={"Authorization": f"Bearer {_rest_token}"},
            timeout=8,
        )
        if r.ok:
            return r.json().get("result")
        logger.warning(f"Redis REST error: {r.status_code} {r.text[:100]}")
        return None
    except Exception as e:
        logger.warning(f"Redis REST exec failed: {e}")
        return None


def redis_get(key: str, default: str = '') -> str:
    """Get a config value from Redis."""
    val = _exec(["GET", f"config:{key}"])
    return val if val is not None else default


def redis_set(key: str, value: str):
    """Set a config value in Redis."""
    _exec(["SET", f"config:{key}", str(value)])


def redis_get_all() -> dict:
    """Get all config values from Redis."""
    if not _init_client():
        return {}
    try:
        # KEYS config:*
        keys_result = _exec(["KEYS", "config:*"])
        if not keys_result:
            return {}
        result = {}
        for k in keys_result:
            val = _exec(["GET", k])
            if val is not None:
                result[k.replace("config:", "")] = val
        return result
    except Exception as e:
        logger.warning(f"redis_get_all failed: {e}")
        return {}


def redis_set_many(data: dict):
    """Set multiple config values in Redis at once using pipeline."""
    if not _init_client():
        return
    try:
        # Use Upstash pipeline endpoint for batch operations
        pipeline = [[f"SET", f"config:{k}", str(v)] for k, v in data.items() if v]
        r = _requests.post(
            f"{_rest_url}/pipeline",
            headers={"Authorization": f"Bearer {_rest_token}",
                     "Content-Type": "application/json"},
            json=pipeline,
            timeout=15,
        )
        if r.ok:
            logger.info(f"Redis pipeline: saved {len(pipeline)} values")
        else:
            logger.warning(f"Redis pipeline failed: {r.text[:100]}")
    except Exception as e:
        logger.warning(f"redis_set_many failed: {e}")


def sync_db_to_redis():
    """Sync all Config rows from DB → Redis."""
    if not _init_client():
        return
    try:
        from database.models import Config
        rows = Config.query.all()
        if not rows:
            return
        data = {row.key: row.value for row in rows if row.value}
        redis_set_many(data)
        logger.info(f"Synced {len(data)} config rows → Redis")
    except Exception as e:
        logger.warning(f"sync_db_to_redis failed: {e}")


def sync_redis_to_db():
    """Sync all Redis config values → DB."""
    if not _init_client():
        return 0
    try:
        from database.models import db, Config
        redis_data = redis_get_all()
        if not redis_data:
            return 0
        synced = 0
        for key, value in redis_data.items():
            if not value:
                continue
            existing = db.session.get(Config, key)
            if not existing:
                db.session.add(Config(key=key, value=value))
                synced += 1
            elif existing.value != value:
                existing.value = value
                synced += 1
        if synced:
            db.session.commit()
            logger.info(f"Synced {synced} Redis values → DB")
        return synced
    except Exception as e:
        logger.warning(f"sync_redis_to_db failed: {e}")
        return 0
