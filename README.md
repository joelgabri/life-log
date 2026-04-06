# life-log

A self-hosted API for logging and querying personal time-series data ("quantified self"). Designed for a single user running their own infrastructure.

## Concepts

- **Entries** — the core data unit. Each entry has a `type` (e.g. `health_connect.steps`), a `timestamp`, and a free-form `data` payload (JSON).
- **Collectors** — apps that write data (e.g. an Android app syncing Health Connect data).
- **Consumers** — apps that read data (e.g. a dashboard).
- **API keys** — each collector/consumer gets a scoped key.

## Quick start

```bash
# 1. Start the stack
docker compose up --build

# 2. Create your first admin key
docker compose exec api python manage.py create-key --name admin --scopes admin

# 3. Verify
curl -H "X-Api-Key: <your-key>" http://localhost:8000/health
```

## API

All data endpoints are under `/api/v1/`. Authenticate with the `X-Api-Key` header.

### Entries

```
POST   /api/v1/entries          Write a single entry
POST   /api/v1/entries/batch    Write multiple entries (primary path for sync)
GET    /api/v1/entries          Query entries
```

**Query parameters for GET:**

| Param    | Description                        |
|----------|------------------------------------|
| `type`   | Filter by entry type               |
| `source` | Filter by source                   |
| `start`  | ISO 8601 datetime (inclusive)      |
| `end`    | ISO 8601 datetime (inclusive)      |
| `limit`  | Max results (default 100, max 1000)|
| `offset` | Pagination offset                  |

**Entry payload:**

```json
{
  "type": "health_connect.steps",
  "source": "android_pixel_8",
  "external_id": "hc_3f2a1b4c-...",
  "timestamp": "2026-04-05T08:00:00Z",
  "data": { "count": 8432 }
}
```

`external_id` is optional but recommended for sources that have stable record IDs (e.g. Health Connect `metadata.id`). When provided, re-submitting the same `(type, external_id)` will update the existing record rather than create a duplicate — making syncs safe to re-run.

### Key management

```
POST   /api/v1/keys             Create an API key  (admin)
GET    /api/v1/keys             List all keys       (admin)
DELETE /api/v1/keys/{id}        Delete a key        (admin)
```

The raw key is only returned at creation time. Store it securely.

### Scopes

| Scope           | Grants                       |
|-----------------|------------------------------|
| `write:entries` | POST entries                 |
| `read:entries`  | GET entries                  |
| `admin`         | All of the above + key management |

## Key management CLI

Run inside the container (`docker compose exec api`) or locally with `uv run`:

```bash
python manage.py init-db
python manage.py create-key --name "health-connect" --scopes write:entries
python manage.py create-key --name "dashboard" --scopes read:entries
python manage.py create-key --name "admin" --scopes admin
python manage.py list-keys
python manage.py delete-key <uuid>
```

## Development

```bash
uv sync                        # install all deps including dev
uv run pytest                  # run tests (spins up a postgres container automatically)
uv run pytest -x -v            # stop on first failure, verbose
uv run ruff format .           # format
uv run ruff check --fix .      # lint + auto-fix
```

Tests use [testcontainers](https://testcontainers-python.readthedocs.io/) to run against a real PostgreSQL instance — no mocks.

## Adding new data types

No schema changes needed. Just POST entries with a new `type` string and whatever shape `data` makes sense:

```json
{ "type": "location.visit", "timestamp": "...", "data": { "lat": 51.5, "lng": -0.1, "place": "home" } }
```
