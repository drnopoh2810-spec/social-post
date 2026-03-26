"""
Redis Config Store — Upstash Redis
=====================================
يستخدم upstash-redis SDK الذي يعمل عبر HTTPS على port 443.
يحل مشكلة PythonAnywhere الذي يحجب port 6379 و proxy 403.

المتغيرات المدعومة:
  REDIS_URL=rediss://default:TOKEN@host:6379   ← يُحوَّل تلقائياً
  أو
  UPSTASH_REDIS_REST_URL=https://host.upstash.io
  UPSTASH_REDIS_REST_TOKEN=TOKEN
"""

import os
import logging

logger = logging.getLogger(__name__)

_client     = None
_connected  = False
_failed     = False


def reset_redis_client():
    """Force reconnect on next call."""
    global _client, _connected, _failed
    _client    = None
    _connected = False
    _failed    = False


def _parse_upstash_url(redis_url: str):
    """
    Convert rediss://default:TOKEN@host:PORT → (https://host, TOKEN)
    """
    try:
        # Remove scheme
        rest = redis_url.split("://", 1)[1] if "://" in redis_url else redis_url
        at   = rest.rfind("@")
        if at == -1:
            return None, None
        userinfo = rest[:at]                    # default:TOKEN
        hostport = rest[at + 1:]                # host:6379
        host     = hostport.split(":")[0]
        token    = userinfo.split(":", 1)[1] if ":" in userinfo else userinfo
        return f"https://{host}", token
    except Exception:
        return None, None


def _get_credentials():
    """Return (url, token) from env or DB."""
    # 1. Direct REST env vars
    url   = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
    if url and token:
        return url, token

    # 2. REDIS_URL env var
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        return _parse_upstash_url(redis_url)

    # 3. DB
    try:
        from database.models import db as _db, Config as _Cfg
        row = _db.session.get(_Cfg, 'redis_url')
        if row and row.value:
            return _parse_upstash_url(row.value)
    except Exception:
        pass

    return None, None


def _init_client():
    """Initialize upstash_redis client."""
    global _client, _connected, _failed

    if _connected and _client:
        return True
    if _failed:
        return False

    url, token = _get_credentials()
    if not url or not token:
        return False

    try:
        from upstash_redis import Redis
        client = Redis(url=url, token=token)
        # Test connection
        result = client.ping()
        if result:
            _client    = client
            _connected = True
            logger.info(f"✅ Upstash Redis connected: {url}")
            return True
        else:
            logger.warning("Upstash Redis ping returned False")
            _failed = True
            return False
    except ImportError:
        logger.warning("upstash-redis not installed — run: pip install upstash-redis")
        _failed = True
        return False
    except Exception as e:
        logger.warning(f"Upstash Redis connection failed: {e}")
        _failed = True
        return False


def get_redis():
    """Returns client if connected, None otherwise."""
    if _init_client():
        return _client
    return None


def redis_get(key: str, default: str = '') -> str:
    """Get a config value from Redis."""
    if not _init_client():
        return default
    try:
        val = _client.get(f'config:{key}')
        return val if val is not None else default
    except Exception as e:
        logger.warning(f"Redis get failed for {key}: {e}")
        return default


def redis_set(key: str, value: str):
    """Set a config value in Redis."""
    if not _init_client():
        return
    try:
        _client.set(f'config:{key}', str(value))
    except Exception as e:
        logger.warning(f"Redis set failed for {key}: {e}")


def redis_get_all() -> dict:
    """Get all config values from Redis."""
    if not _init_client():
        return {}
    try:
        keys = _client.keys('config:*')
        if not keys:
            return {}
        result = {}
        for k in keys:
            val = _client.get(k)
            if val is not None:
                clean_key = k.replace('config:', '') if isinstance(k, str) else k.decode().replace('config:', '')
                result[clean_key] = val
        return result
    except Exception as e:
        logger.warning(f"redis_get_all failed: {e}")
        return {}


def redis_set_many(data: dict):
    """Set multiple config values in Redis using pipeline."""
    if not _init_client():
        return
    try:
        pipe = _client.pipeline()
        for key, value in data.items():
            if value:
                pipe.set(f'config:{key}', str(value))
        pipe.execute()
        logger.info(f"Redis pipeline: saved {len(data)} values")
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
