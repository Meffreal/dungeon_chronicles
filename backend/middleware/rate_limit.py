"""
middleware/rate_limit.py — Sliding window rate limiter

Limity (per IP, per minuta):
  auth    : 10  — /auth/register, /auth/login  (ochrana před brute-force)
  combat  : 30  — /arena/attack, /boss/attack, /dungeon/*
  general : 120 — vše ostatní

Implementace:
  • Pokud je Redis dostupný (REDIS_URL nastaven): Redis sorted set sliding window
    — cross-instance bezpečné, vhodné pro horizontální škálování
  • Fallback: in-memory deque sliding window (single-instance)

Redis klíče: rl:{category}:{ip} — sorted set timestampů, TTL 70s
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# ── Kategorie a limity (požadavků / 60 s) ────────────────────────────────────

_LIMITS: dict[str, int] = {
    "auth":    10,
    "combat":  30,
    "general": 120,
}

_AUTH_PATHS = {"/auth/register", "/auth/login"}
_COMBAT_PREFIXES = ("/arena/attack", "/boss/attack", "/dungeon/")


def _category(path: str) -> str:
    if path in _AUTH_PATHS:
        return "auth"
    if any(path.startswith(p) for p in _COMBAT_PREFIXES):
        return "combat"
    return "general"


# ── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.

    Automaticky přepíná mezi Redis a in-memory implementací podle dostupnosti
    Redis klienta. In-memory je použit jako fallback při každém requestu,
    pokud cache není connected.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        # In-memory fallback storage
        self._windows: dict[str, dict[str, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )

    async def dispatch(self, request: Request, call_next):
        # Rate limiting dočasně vypnuto
        return await call_next(request)

    # ── Redis sliding window ──────────────────────────────────────────────────

    async def _redis_check(self, request: Request, call_next, ip: str, category: str, limit: int):
        from core.cache import cache, make_rl_member

        now = time.time()
        cutoff = now - 60.0
        key = f"rl:{category}:{ip}"
        member = make_rl_member()

        # Přidej aktuální timestamp, odstraň staré, nastav TTL
        await cache.zadd(key, {member: now})
        await cache.zremrangebyscore(key, 0, cutoff)
        await cache.expire(key, 70)

        count = await cache.zcard(key)

        if count > limit:
            oldest_members = await cache.zrangebyscore(key, cutoff, "+inf")
            if oldest_members:
                retry_after = int(60 - (now - float(oldest_members[0].split(":")[0]))) + 1
                retry_after = max(1, min(retry_after, 60))
            else:
                retry_after = 60
            return _rate_limit_response(category, limit, retry_after)

        return await call_next(request)

    # ── In-memory sliding window (fallback) ───────────────────────────────────

    async def _memory_check(self, request: Request, call_next, ip: str, category: str, limit: int):
        now = time.monotonic()
        window = self._windows[category][ip]

        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= limit:
            retry_after = int(60 - (now - window[0])) + 1
            return _rate_limit_response(category, limit, retry_after)

        window.append(now)
        return await call_next(request)


def _rate_limit_response(category: str, limit: int, retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                f"Příliš mnoho požadavků ({category}). "
                f"Limit: {limit}/min. Zkus za {retry_after} s."
            )
        },
        headers={"Retry-After": str(retry_after)},
    )
