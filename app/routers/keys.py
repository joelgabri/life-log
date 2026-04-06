import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import SCOPE_ADMIN, generate_api_key, hash_key, require_scope
from ..database import get_db

router = APIRouter(prefix="/keys", tags=["api-keys"])


@router.post("/", response_model=schemas.ApiKeyCreated, status_code=201)
def create_key(
    key_data: schemas.ApiKeyCreate,
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_ADMIN)),
):
    raw_key = generate_api_key()
    db_key = models.ApiKey(
        name=key_data.name,
        key_hash=hash_key(raw_key),
        scopes=key_data.scopes,
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return schemas.ApiKeyCreated.model_validate({**db_key.__dict__, "key": raw_key})


@router.get("/", response_model=list[schemas.ApiKeyResponse])
def list_keys(
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_ADMIN)),
):
    return db.query(models.ApiKey).all()


@router.delete("/{key_id}", status_code=204)
def delete_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    _key=Depends(require_scope(SCOPE_ADMIN)),
):
    record = db.query(models.ApiKey).filter(models.ApiKey.id == key_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(record)
    db.commit()
