import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app import models  # noqa: F401 — registers models with Base
from app.auth import hash_key
from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()


@pytest.fixture()
def db(pg_url):
    engine = create_engine(pg_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_key(db):
    raw_key = "test_admin_key_abcdefgh"
    key = models.ApiKey(name="test-admin", key_hash=hash_key(raw_key), scopes=["admin"])
    db.add(key)
    db.commit()
    return raw_key


@pytest.fixture()
def write_key(db):
    raw_key = "test_write_key_abcdefgh"
    key = models.ApiKey(name="test-writer", key_hash=hash_key(raw_key), scopes=["write:entries"])
    db.add(key)
    db.commit()
    return raw_key


@pytest.fixture()
def read_key(db):
    raw_key = "test_read_key_abcdefgh"
    key = models.ApiKey(name="test-reader", key_hash=hash_key(raw_key), scopes=["read:entries"])
    db.add(key)
    db.commit()
    return raw_key
