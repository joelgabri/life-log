import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class EntryCreate(BaseModel):
    type: str
    source: Optional[str] = None
    external_id: Optional[str] = None
    timestamp: datetime
    data: dict[str, Any]


class EntryResponse(BaseModel):
    id: uuid.UUID
    type: str
    source: Optional[str]
    external_id: Optional[str]
    timestamp: datetime
    data: dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str]


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    scopes: list[str]
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyResponse):
    key: str  # raw key — only returned at creation time
