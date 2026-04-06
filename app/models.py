import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from .database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    scopes = Column(ARRAY(String), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)


class Entry(Base):
    __tablename__ = "entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    source = Column(String, nullable=True)
    external_id = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_entries_type", "type"),
        Index("idx_entries_timestamp", "timestamp"),
        Index("idx_entries_type_timestamp", "type", "timestamp"),
        # partial unique index: (type, external_id) only when external_id is not null
        Index(
            "uq_entries_type_external_id",
            "type",
            "external_id",
            unique=True,
            postgresql_where=Column("external_id").isnot(None),
        ),
    )
