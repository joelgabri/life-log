from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import SCOPE_WRITE_ENTRIES, require_scope_authorization
from ..database import get_db
from .entries import _upsert_entry

router = APIRouter(prefix="/waistline", tags=["waistline"])


class WaistlineDiaryEntry(BaseModel):
    dateTime: datetime

    @field_validator("dateTime")
    @classmethod
    def must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("dateTime must include a timezone offset")
        return v


class WaistlinePayload(BaseModel):
    entry: WaistlineDiaryEntry
    nutrition: dict[str, Any]
    entryDetails: list[Any] = []


@router.post("/sync", status_code=200)
def waistline_sync(
    payload: WaistlinePayload,
    db: Session = Depends(get_db),
    _key=Depends(require_scope_authorization(SCOPE_WRITE_ENTRIES)),
):
    date_str = payload.entry.dateTime.date().isoformat()
    entry = schemas.EntryCreate(
        type="nutrition",
        source="waistline",
        external_id=f"waistline:{date_str}",
        timestamp=payload.entry.dateTime,
        data={
            "nutrition": payload.nutrition,
            "entryDetails": payload.entryDetails,
        },
    )
    _upsert_entry(db, entry)
    db.commit()
    return {"status": 200, "message": "Data synchronized."}
