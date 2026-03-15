"""
routers/health.py — Health check a readiness endpointy.

Určené pro load balancery, orchestrátory (k8s, Docker Swarm) a monitoring.

Endpointy:
  GET /health  — liveness probe  → 200 vždy (pokud proces běží)
  GET /ready   — readiness probe → 200 pokud je DB dostupná, 503 jinak
  GET /info    — instance info   → verze, uptime, instance ID, DB type
"""
import time
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from middleware.instance_id import INSTANCE_ID

router = APIRouter(tags=["health"])

_START_TIME = time.time()
APP_VERSION = "0.7.0"


@router.get("/health")
async def health():
    """
    Liveness probe — vrátí 200 pokud proces žije.
    Load balancer by měl restartovat instanci pokud tento endpoint nereaguje.
    """
    return {"status": "ok", "instance_id": INSTANCE_ID}


@router.get("/ready")
async def ready():
    """
    Readiness probe — ověří dostupnost DB.
    Load balancer by měl vyřadit instanci z rotace pokud vrátí non-2xx.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok", "instance_id": INSTANCE_ID}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status":      "not_ready",
                "db":          "error",
                "error":       str(e),
                "instance_id": INSTANCE_ID,
            },
        )


@router.get("/info")
async def info():
    """
    Instance info — verze, uptime, konfigurace.
    Užitečné pro debugging multi-instance deploymentů.
    """
    from database import DATABASE_URL
    uptime_s = int(time.time() - _START_TIME)
    h, rem   = divmod(uptime_s, 3600)
    m, s     = divmod(rem, 60)

    # Skryj credentials z DATABASE_URL pro bezpečnost
    db_type = DATABASE_URL.split("+")[0] if DATABASE_URL else "unknown"

    return {
        "instance_id":   INSTANCE_ID,
        "version":       APP_VERSION,
        "uptime":        f"{h}h {m}m {s}s",
        "uptime_seconds": uptime_s,
        "db_type":       db_type,
        "scaling_notes": {
            "rate_limiter":  "in-memory (single-instance); set REDIS_URL for multi-instance",
            "ws_chat":       "in-memory (single-instance); Redis pub/sub needed for multi-instance",
            "cron_jobs":     "DB-backed distributed lock (multi-instance safe)",
            "disabled_quests": "DB-backed with 10s cache (multi-instance safe)",
            "sessions":      "stateless JWT (multi-instance safe)",
        },
    }
