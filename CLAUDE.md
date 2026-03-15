# Dungeon Chronicles — CLAUDE.md

Browser-based async RPG. Backend: FastAPI + SQLAlchemy. Frontend: Vanilla JS SPA.

## Architecture
- `models/` — ORM only | `routers/` — API layer | `game/` — pure logic (no HTTP)
- Never duplicate logic between routers and game layer
- All DB access uses async session pattern

## Auth
- JWT (7-day expiry), issued at `/auth/login`, validated via `get_current_user` dependency
- Admin routes require header `X-Admin-Key` matching env `ADMIN_KEY`

## Database
- Dev: SQLite | Prod: PostgreSQL — switched via `DATABASE_URL` env var
- Migrations: Alembic, always idempotent (`inspect()` guard), run `alembic upgrade head` on startup

## Dev commands
```
uvicorn main:app --reload --port 8000   # from /backend
pytest backend/tests/                   # all tests
pytest backend/tests/test_X.py::name -v
```

## Env vars
`SECRET_KEY` `ADMIN_KEY` `DATABASE_URL` `ALLOWED_ORIGINS`

## Token rules
- Skip generic FastAPI/SQLAlchemy/JWT explanations — project-specific only
- Read files selectively; don't echo content user already sees
- Response length proportional to task complexity
