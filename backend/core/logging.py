"""
core/logging.py — Structured JSON logging

Každý log záznam obsahuje:
  timestamp  — ISO-8601 UTC
  level      — DEBUG / INFO / WARNING / ERROR
  logger     — název modulu
  request_id — UUID per HTTP request (injektován přes RequestIdMiddleware)
  event      — text zprávy
  data       — libovolný dict s extra kontextem (volitelné)

Použití:
    from core.logging import get_logger
    log = get_logger(__name__)

    log.info("Quest completed", extra={"data": {"quest_id": 42, "user_id": 7}})
    log.warning("Boss killed", extra={"data": {"boss": "skeleton_king"}})
    log.error("DB error", exc_info=True)

Žádné nové závislosti — čistý Python stdlib logging.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone


# ContextVar pro request_id — propaguje se přes async context (asyncio tasks)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _JSONFormatter(logging.Formatter):
    """Formátuje log záznamy jako JSON — jeden řádek na záznam."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "level":      record.levelname,
            "logger":     record.name,
            "request_id": request_id_var.get(),
            "event":      record.getMessage(),
        }

        # Extra kontext: logger.info("...", extra={"data": {...}})
        if hasattr(record, "data"):
            log["data"] = record.data

        # Stack trace pro chyby
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """
    Nakonfiguruje root logger pro JSON výstup na stdout.
    Volat jednou při startu aplikace (v lifespan nebo main).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Ztlum výřečné knihovní logy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Vrátí pojmenovaný logger pro daný modul."""
    return logging.getLogger(name)
