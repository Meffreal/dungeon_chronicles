"""
middleware/request_id.py — Injectuje X-Request-ID do ContextVar pro structured logging.

Každý HTTP request dostane unikátní ID:
  - Přečteme z příchozího headeru X-Request-ID (pokud klient posílá)
  - Nebo vygenerujeme nové UUID (8 znaků)
  - Uložíme do request_id_var (ContextVar) → dostupné ve všech loggerech
  - Vrátíme v response headeru X-Request-ID pro debugování
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.logging import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)
