import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SCOPE_WRITE_ENTRIES = "write:entries"
SCOPE_READ_ENTRIES = "read:entries"
SCOPE_ADMIN = "admin"

_api_key_header = APIKeyHeader(name="X-Api-Key")


def generate_api_key() -> str:
    return "ll_" + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_api_key(
    raw_key: str = Security(_api_key_header),
    db: Session = Depends(get_db),
) -> models.ApiKey:
    key_hash = hash_key(raw_key)
    record = db.query(models.ApiKey).filter(models.ApiKey.key_hash == key_hash).first()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")
    record.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return record


def require_scope(scope: str):
    def checker(key: models.ApiKey = Depends(get_api_key)) -> models.ApiKey:
        if SCOPE_ADMIN not in key.scopes and scope not in key.scopes:
            raise HTTPException(status_code=403, detail=f"Missing required scope: {scope}")
        return key

    return checker
