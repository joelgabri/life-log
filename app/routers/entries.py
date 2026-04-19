from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import SCOPE_READ_ENTRIES, SCOPE_WRITE_ENTRIES, require_scope
from ..database import get_db

router = APIRouter(prefix="/entries", tags=["entries"])


def _upsert_entry(db: Session, entry: schemas.EntryCreate) -> models.Entry:
    """Stage an entry upsert without committing. Caller must commit and refresh."""
    if entry.external_id is not None:
        existing = (
            db.query(models.Entry)
            .filter(
                models.Entry.type == entry.type,
                models.Entry.external_id == entry.external_id,
            )
            .first()
        )
        if existing is not None:
            existing.data = entry.data
            existing.source = entry.source
            existing.timestamp = entry.timestamp
            existing.updated_at = datetime.now(timezone.utc)
            return existing

    db_entry = models.Entry(**entry.model_dump())
    db.add(db_entry)
    return db_entry


@router.post("/", response_model=schemas.EntryResponse, status_code=201)
def create_entry(
    entry: schemas.EntryCreate,
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_WRITE_ENTRIES)),
):
    result = _upsert_entry(db, entry)
    db.commit()
    db.refresh(result)
    return result


@router.post("/batch", response_model=list[schemas.EntryResponse], status_code=200)
def create_entries_batch(
    entries: list[schemas.EntryCreate],
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_WRITE_ENTRIES)),
):
    seen: dict[tuple[str, str], int] = {}
    deduped: list[schemas.EntryCreate] = []
    original_to_deduped: list[int] = []
    for entry in entries:
        if entry.external_id is not None:
            key = (entry.type, entry.external_id)
            if key in seen:
                deduped[seen[key]] = entry
                original_to_deduped.append(seen[key])
            else:
                idx = len(deduped)
                seen[key] = idx
                original_to_deduped.append(idx)
                deduped.append(entry)
        else:
            idx = len(deduped)
            original_to_deduped.append(idx)
            deduped.append(entry)
    deduped_results = [_upsert_entry(db, entry) for entry in deduped]
    db.commit()
    for r in deduped_results:
        db.refresh(r)
    return [deduped_results[i] for i in original_to_deduped]


@router.get("/", response_model=list[schemas.EntryResponse])
def get_entries(
    entry_type: Optional[str] = Query(None, alias="type"),
    source: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_READ_ENTRIES)),
):
    q = db.query(models.Entry)
    if entry_type is not None:
        q = q.filter(models.Entry.type == entry_type)
    if source is not None:
        q = q.filter(models.Entry.source == source)
    if start is not None:
        q = q.filter(models.Entry.timestamp >= start)
    if end is not None:
        q = q.filter(models.Entry.timestamp <= end)
    return q.order_by(models.Entry.timestamp.desc()).offset(offset).limit(limit).all()
