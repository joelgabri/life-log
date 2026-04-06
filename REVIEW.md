# Code Review: life-log

Overall this is a clean, well-structured codebase. The architecture is sound, the auth model is correct, and using real PostgreSQL in tests is the right call. There are a handful of genuine bugs and some design blindspots worth knowing about.

---

## Bugs

### 1. Batch writes are not atomic — `entries.py:54`

```python
return [_upsert_entry(db, entry) for entry in entries]
```

`_upsert_entry` calls `db.commit()` for each entry individually. If entry N fails (e.g., a DB error), entries 0..N-1 are already committed with no rollback. The batch endpoint isn't actually atomic. The fix is to collect all the ORM objects, then do a single `db.commit()` at the end — and move `db.refresh` calls after that.

---

### 2. Upsert silently drops `source` updates — `entries.py:25-27`

```python
existing.data = entry.data
existing.timestamp = entry.timestamp
existing.updated_at = datetime.now(timezone.utc)
```

`source` is not updated. If you re-sync an entry with a corrected `source`, it's silently ignored. Probably not intentional — the intent seems to be "make the entry match the submitted payload". Either add `existing.source = entry.source`, or document that source is immutable after first write.

---

### 3. No lower bound on `limit` or `offset` — `entries.py:63-64`

```python
limit: int = Query(default=100, le=1000),
offset: int = 0,
```

- `limit=0` is legal and returns nothing (confusing but harmless)
- `limit=-1` passes to PostgreSQL which will raise an error
- `offset=-1` also causes a DB error

Should be `limit: int = Query(default=100, ge=1, le=1000)` and `offset: int = Query(default=0, ge=0)`.

---

### 4. Race condition in upsert — `entries.py:15-36`

The upsert is a SELECT-then-INSERT/UPDATE. Two concurrent requests with the same `(type, external_id)` could both pass the `existing is None` check and both attempt an INSERT, which would hit the partial unique constraint and raise an unhandled `IntegrityError` (500 to the client). For a single-user personal app with rare concurrent writes this is low-risk, but the correct fix is a real SQL `INSERT ... ON CONFLICT DO UPDATE` instead of the Python-level check-and-write pattern.

---

## Design Issues / Blind Spots

### 5. `type` query param shadows Python's built-in — `entries.py:59`

```python
type: Optional[str] = None,
```

Works fine, but it's easy to accidentally call `type(something)` in the function body and get the string value instead. Naming it `entry_type` and mapping it via an alias would be cleaner: `entry_type: Optional[str] = Query(None, alias="type")`.

---

### 6. Batch endpoint returns 201 for pure updates

`POST /entries/batch` returns `201 Created` even when every entry in the batch already existed and was just updated. HTTP 201 is semantically wrong in that case. `200` would be correct (or `207 Multi-Status` if you wanted to distinguish per-item). Minor, but it makes clients that key on status codes behave incorrectly.

---

### 7. Health check doesn't probe the DB — `main.py:11-13`

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

If the DB goes down, the health check still returns 200. Docker won't restart the container. Adding a `SELECT 1` probe here would make it actually useful as a liveness indicator.

---

### 8. `manage.py` parser setup at module level — `manage.py:63-81`

Argument parser setup runs at import time, not inside `if __name__ == "__main__"`. This is a minor anti-pattern — it won't cause a problem since nobody imports this, but it's not idiomatic.

---

### 9. `data` field restricted to `dict[str, Any]` — `schemas.py:13`

```python
data: dict[str, Any]
```

The underlying JSONB column can store any JSON value, but the schema forces a JSON object. You can't store `data: [1, 2, 3]` or `data: 42`. This may be intentional, but it's worth knowing it's a schema-level constraint.

---

### 10. `source` filter is untested

`GET /entries?source=...` is implemented (`entries.py:71-72`) but there's no test for it. All other filters have test coverage.

---

## What's Good

- **SHA256 key hashing**: raw key never touches the DB. The `ll_` prefix is a nice touch — easy to grep for in logs.
- **Partial unique index**: `uq_entries_type_external_id` (only when `external_id IS NOT NULL`) is the right way to model optional idempotency. Elegant.
- **Real PostgreSQL in tests**: `testcontainers` instead of SQLite means the partial unique index, JSONB, and `ARRAY` types all actually work in tests.
- **`last_used_at` tracking**: free audit trail.
- **`docker-compose` health-check dependency**: the `api` service correctly waits for `db` to be ready before starting.
- **Clean separation of concerns**: auth, models, schemas, routers, database are all properly separated.

---

## Summary

| Issue | Severity | File |
|---|---|---|
| Batch writes not atomic | Medium | `entries.py:54` |
| Upsert drops `source` updates | Medium | `entries.py:25` |
| No lower bound on `limit`/`offset` | Low | `entries.py:63` |
| Race condition in upsert | Low (personal app) | `entries.py:15` |
| 201 on batch update | Low | `entries.py:48` |
| `type` param shadows builtin | Cosmetic | `entries.py:59` |
| Health check ignores DB | Low | `main.py:11` |
| `source` filter untested | Coverage gap | `tests/test_entries.py` |

The two to fix first: **batch atomicity** and **`source` not being updated on upsert**. Both are correctness bugs that could silently produce wrong data.
