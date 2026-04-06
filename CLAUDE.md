# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (including dev)
uv sync

# Run tests, lint, and format (use this to verify work)
./check

# Run a single test
uv run pytest tests/test_keys.py
uv run pytest tests/test_keys.py::test_create_key_returns_raw_key

# Run the API locally (requires a running Postgres)
uv run uvicorn app.main:app --reload

# Docker Compose (starts Postgres + API)
docker compose up

# Database management CLI (against the configured DATABASE_URL)
python manage.py init-db
python manage.py create-key --name <name> --scopes admin,write:entries,read:entries
python manage.py list-keys
python manage.py delete-key <uuid>
```

## Development workflow

**CRITICAL — non-negotiable:**
1. **Red/green TDD.** Write a failing test first, run it to confirm it fails, then implement. Never write implementation code before a failing test exists.
2. **Always run `./check` before marking work done.** It runs format, lint, and the full test suite. Work is not complete until `./check` passes cleanly.

## Architecture

FastAPI app (`app/`) backed by PostgreSQL via SQLAlchemy (sync ORM, not async).

**Request flow:** `app/main.py` mounts two routers under `/api/v1`:
- `routers/entries.py` — write/read life-log entries (`write:entries`, `read:entries` scopes)
- `routers/keys.py` — CRUD for API keys (`admin` scope only)

**Auth:** Every protected endpoint depends on `auth.require_scope(scope)`, which reads `X-Api-Key` from the request header, SHA-256 hashes it, looks it up in `api_keys`, and checks scopes. Raw keys are never stored. `admin` scope bypasses all other scope checks.

**Entries upsert:** `_upsert_entry` in `routers/entries.py` deduplicates on `(type, external_id)` when `external_id` is provided — enforced by a partial unique index in the DB. This is the core ingestion pattern; collectors set `external_id` to avoid duplicates on re-import.

**Config:** `app/config.py` uses `pydantic-settings`; the only setting is `DATABASE_URL` (defaults to the Docker Compose value). Override via `.env` or environment variable.

**Tests:** Use `testcontainers` to spin up a real Postgres instance per session (`scope="session"`). Each test gets a fresh schema via `Base.metadata.create_all` / `drop_all`. The `client`, `admin_key`, `write_key`, `read_key` fixtures in `conftest.py` are the standard building blocks for new tests.

**Deployment:** `Dockerfile` + `docker-compose.yml`. On startup the container runs `python manage.py init-db` before launching uvicorn. Configurable via `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `API_PORT` env vars.
