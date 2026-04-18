from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import SCOPE_WRITE_ENTRIES, require_scope_basic_or_header
from ..database import get_db
from ..services.weather import fetch_weather_entry, weather_external_id
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
    _key=Depends(require_scope_basic_or_header(SCOPE_WRITE_ENTRIES)),
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

    lat = raw.get("lat")
    lon = raw.get("lon")
    if lat is not None and lon is not None:
        weather_eid = weather_external_id(lat, lon, payload.tst)
        exists = (
            db.query(models.Entry)
            .filter(
                models.Entry.type == "weather",
                models.Entry.external_id == weather_eid,
            )
            .first()
        )
        if not exists:
            weather_entry = fetch_weather_entry(lat, lon, payload.tst)
            if weather_entry is not None:
                _upsert_entry(db, weather_entry)

    db.commit()
    return []
