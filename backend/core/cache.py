"""
core/cache.py — Redis async cache s in-memory fallbackem.

Pokud REDIS_URL není nastaven (dev prostředí), automaticky používá
in-memory dict s TTL — žádná instalace Redis není potřeba pro vývoj.

Typické použití:
    from core.cache import cache

    data = await cache.get("arena:leaderboard")
    if data is None:
        data = await expensive_db_query()
        await cache.set("arena:leaderboard", data, ttl=60)

    # Invalidace po změně dat
    await cache.delete("arena:leaderboard")

Sorted set API (pro rate limiter):
    await cache.zadd(key, {member: score})
    count = await cache.zcard(key)
    await cache.zremrangebyscore(key, min_score, max_score)
    await cache.expire(key, ttl)
"""

import asyncio
import json
import random
import time
from typing import Any

from core.logging import get_logger

log = get_logger(__name__)


# ── In-memory fallback (single-instance, bez Redis) ──────────────────────────

class _InMemoryCache:
    """
    In-memory cache s TTL.
    Použito jako fallback když REDIS_URL není nastaven.

    Sorted set operace (pro rate limiter) jsou zde simulovány
    pomocí dict timestampů — funkční pro single-instance deployment.
    """

    def __init__(self) -> None:
        self._kv: dict[str, tuple[Any, float]] = {}          # key → (value, expires_at)
        self._zsets: dict[str, dict[str, float]] = {}        # key → {member: score}
        self._zset_ttls: dict[str, float] = {}               # key → expires_at
        self._lock = asyncio.Lock()

    # ── KV operace ─────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._kv.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._kv[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        async with self._lock:
            self._kv[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._kv.pop(key, None)

    async def delete_pattern(self, pattern: str) -> None:
        """Smaže klíče podle prefixu (pattern musí končit *)."""
        prefix = pattern.rstrip("*")
        async with self._lock:
            to_del = [k for k in self._kv if k.startswith(prefix)]
            for k in to_del:
                del self._kv[k]

    # ── Sorted set operace (pro rate limiter) ──────────────────────────────────

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        async with self._lock:
            zset = self._zsets.setdefault(key, {})
            zset.update(mapping)

    async def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list[str]:
        async with self._lock:
            zset = self._zsets.get(key, {})
            return [m for m, s in zset.items() if min_score <= s <= max_score]

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> None:
        async with self._lock:
            zset = self._zsets.get(key)
            if zset:
                to_del = [m for m, s in zset.items() if min_score <= s <= max_score]
                for m in to_del:
                    del zset[m]

    async def expire(self, key: str, ttl: int) -> None:
        # U sorted setů zaznamenáme expiraci (čistí se lazy při zcard)
        async with self._lock:
            self._zset_ttls[key] = time.monotonic() + ttl

    async def zcard(self, key: str) -> int:
        async with self._lock:
            # Lazy expiration sorted setů
            exp = self._zset_ttls.get(key)
            if exp and time.monotonic() > exp:
                self._zsets.pop(key, None)
                self._zset_ttls.pop(key, None)
                return 0
            return len(self._zsets.get(key, {}))

    @property
    def connected(self) -> bool:
        return False


# ── Redis klient ──────────────────────────────────────────────────────────────

class _RedisCache:
    """
    Redis-backed cache přes redis.asyncio.
    Hodnoty jsou serializovány jako JSON.
    """

    def __init__(self, client: Any) -> None:
        self._r = client

    # ── KV operace ─────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        raw = await self._r.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        await self._r.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        keys = await self._r.keys(pattern)
        if keys:
            await self._r.delete(*keys)

    # ── Sorted set operace (pro rate limiter) ──────────────────────────────────

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        await self._r.zadd(key, mapping)

    async def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list[str]:
        return await self._r.zrangebyscore(key, min_score, max_score)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> None:
        await self._r.zremrangebyscore(key, min_score, max_score)

    async def expire(self, key: str, ttl: int) -> None:
        await self._r.expire(key, ttl)

    async def zcard(self, key: str) -> int:
        return await self._r.zcard(key)

    @property
    def connected(self) -> bool:
        return True

    async def aclose(self) -> None:
        await self._r.aclose()


# ── Globální instance (nastavuje se při startu aplikace) ─────────────────────

cache: _InMemoryCache | _RedisCache = _InMemoryCache()


async def init_cache() -> None:
    """
    Inicializuje Redis pokud je REDIS_URL nastaven.
    Jinak používá in-memory fallback bez nutnosti instalace Redis.
    """
    global cache

    from config import settings
    redis_url = settings.REDIS_URL

    if not redis_url:
        log.info("Cache: REDIS_URL not set — using in-memory fallback (single-instance)")
        return

    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)
        await client.ping()
        cache = _RedisCache(client)
        log.info("Cache: Redis connected", extra={"data": {"url": redis_url}})
    except ImportError:
        log.warning("Cache: redis package not installed — using in-memory fallback")
    except Exception as e:
        log.warning(
            "Cache: Redis unavailable — using in-memory fallback",
            extra={"data": {"error": str(e)}},
        )


async def close_cache() -> None:
    """Zavře Redis spojení při shutdown aplikace."""
    global cache
    if isinstance(cache, _RedisCache):
        await cache.aclose()
        log.info("Cache: Redis connection closed")


def make_rl_member() -> str:
    """Unikátní člen pro sorted set rate limiteru (timestamp + random suffix)."""
    return f"{time.time():.6f}:{random.getrandbits(32)}"
