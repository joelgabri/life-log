from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import SCOPE_WRITE_ENTRIES, require_scope
from ..database import get_db
from .entries import _upsert_entry

router = APIRouter(prefix="/owntracks", tags=["owntracks"])

_STRIP = {"_type", "tst", "batt", "bs", "t", "m", "conn", "SSID", "inregions", "topic", "_http"}


class OwnTracksPayload(BaseModel):
    model_config = {"extra": "allow"}

    type_: str = Field(alias="_type")
    tst: Optional[int] = None
    tid: Optional[str] = None


@router.post("/", response_model=list)
def receive_owntracks(
    payload: OwnTracksPayload,
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_WRITE_ENTRIES)),
):
    if payload.type_ != "location":
        return []

    if payload.tst is None or payload.tid is None:
        raise HTTPException(status_code=422, detail="location type requires 'tst' and 'tid'")

    raw = payload.model_dump(by_alias=True)
    entry = schemas.EntryCreate(
        type="location",
        source="owntracks",
        external_id=f"{payload.tid}:{payload.tst}",
        timestamp=datetime.fromtimestamp(payload.tst, tz=timezone.utc),
        data={k: v for k, v in raw.items() if k not in _STRIP},
    )
    _upsert_entry(db, entry)
    db.commit()
    return []
