"""
Redis Config Store — Upstash Redis
===================================
يخزن جميع إعدادات التطبيق في Redis بحيث:
- لا تضيع عند restart (PythonAnywhere / HuggingFace)
- تُشارك بين عدة instances
- تُحمَّل تلقائياً عند بدء التشغيل

الاستخدام:
  REDIS_URL=redis://default:TOKEN@host:port  (في .env أو HF Secrets)
"""

import os
import logging

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    """Get or create Redis client. Returns None if not configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    # Try env first, then DB
    url = os.environ.get('REDIS_URL', '')
    if not url:
        try:
            from database.models import Config
            url = Config.query.get('redis_url')
            url = url.value if url else ''
        except Exception:
            pass
    if not url:
        return None

    try:
        import redis
        # Upstash requires SSL
        _redis_client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _redis_client.ping()
        logger.info("Redis connected successfully")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} — falling back to DB only")
        _redis_client = None
        return None


def redis_get(key: str, default: str = '') -> str:
    """Get a config value from Redis."""
    r = get_redis()
    if not r:
        return default
    try:
        val = r.get(f'config:{key}')
        return val if val is not None else default
    except Exception as e:
        logger.warning(f"Redis get failed for {key}: {e}")
        return default


def redis_set(key: str, value: str):
    """Set a config value in Redis."""
    r = get_redis()
    if not r:
        return
    try:
        r.set(f'config:{key}', value)
    except Exception as e:
        logger.warning(f"Redis set failed for {key}: {e}")


def redis_get_all() -> dict:
    """Get all config values from Redis."""
    r = get_redis()
    if not r:
        return {}
    try:
        keys = r.keys('config:*')
        if not keys:
            return {}
        values = r.mget(keys)
        return {
            k.replace('config:', ''): v
            for k, v in zip(keys, values)
            if v is not None
        }
    except Exception as e:
        logger.warning(f"Redis get_all failed: {e}")
        return {}


def redis_set_many(data: dict):
    """Set multiple config values in Redis at once."""
    r = get_redis()
    if not r:
        return
    try:
        pipe = r.pipeline()
        for key, value in data.items():
            if value:
                pipe.set(f'config:{key}', str(value))
        pipe.execute()
        logger.info(f"Redis: saved {len(data)} config values")
    except Exception as e:
        logger.warning(f"Redis set_many failed: {e}")


def sync_db_to_redis():
    """
    عند بدء التشغيل: اقرأ كل الـ config من DB واكتبها في Redis.
    يضمن إن Redis دايماً محدّث.
    """
    r = get_redis()
    if not r:
        return
    try:
        from database.models import Config
        rows = Config.query.all()
        if not rows:
            return
        pipe = r.pipeline()
        for row in rows:
            if row.value:
                pipe.set(f'config:{row.key}', row.value)
        pipe.execute()
        logger.info(f"Synced {len(rows)} config rows → Redis")
    except Exception as e:
        logger.warning(f"sync_db_to_redis failed: {e}")


def sync_redis_to_db():
    """
    عند بدء التشغيل: اقرأ كل الـ config من Redis واكتبها في DB.
    يضمن إن DB محدّث حتى لو اتمسحت (HuggingFace restart).
    """
    r = get_redis()
    if not r:
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
