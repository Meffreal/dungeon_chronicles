"""
middleware/instance_id.py — X-Instance-Id response header.

Každá odpověď obsahuje hlavičku X-Instance-Id identifikující instanci serveru.
Usnadňuje debugging v multi-instance prostředí (load balancer, k8s).

Konfigurace:
  - Env var INSTANCE_ID — nastav explicitně v deployment config
  - Pokud není nastaven, vygeneruje se náhodný 8-znakový hex při startu
"""
import os
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# ── Instance ID ────────────────────────────────────────────────────────────────
# Generuje se jednou při startu procesu — stabilní po celou dobu běhu instance.
INSTANCE_ID: str = os.getenv("INSTANCE_ID") or uuid.uuid4().hex[:8]


class InstanceIdMiddleware(BaseHTTPMiddleware):
    """Přidá X-Instance-Id header do každé odpovědi."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Instance-Id"] = INSTANCE_ID
        return response
