#!/usr/bin/env python
"""Management CLI for life-log."""

import argparse
import sys

from app.auth import generate_api_key, hash_key
from app.database import Base, SessionLocal, engine
from app.models import ApiKey  # noqa: F401 — ensures model is registered


def cmd_init_db(args):
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


def cmd_create_key(args):
    scopes = [s.strip() for s in args.scopes.split(",")]
    raw_key = generate_api_key()
    db = SessionLocal()
    try:
        key = ApiKey(name=args.name, key_hash=hash_key(raw_key), scopes=scopes)
        db.add(key)
        db.commit()
        db.refresh(key)
        print(f"Created API key '{args.name}'")
        print(f"  ID:     {key.id}")
        print(f"  Scopes: {scopes}")
        print(f"  Key:    {raw_key}")
        print("Store this securely — it will not be shown again.")
    finally:
        db.close()


def cmd_list_keys(args):
    db = SessionLocal()
    try:
        keys = db.query(ApiKey).order_by(ApiKey.created_at).all()
        if not keys:
            print("No API keys found.")
            return
        for key in keys:
            last_used = key.last_used_at.isoformat() if key.last_used_at else "never"
            print(f"{key.id}  {key.name:<30}  scopes={key.scopes}  last_used={last_used}")
    finally:
        db.close()


def cmd_delete_key(args):
    db = SessionLocal()
    try:
        key = db.query(ApiKey).filter(ApiKey.id == args.id).first()
        if not key:
            print(f"Key '{args.id}' not found.")
            sys.exit(1)
        db.delete(key)
        db.commit()
        print(f"Deleted key '{key.name}' ({key.id})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="manage.py", description="life-log management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create database tables").set_defaults(func=cmd_init_db)

    p_create = sub.add_parser("create-key", help="Create an API key")
    p_create.add_argument("--name", required=True, help="Human-readable label")
    p_create.add_argument(
        "--scopes",
        required=True,
        help="Comma-separated scopes: admin, write:entries, read:entries",
    )
    p_create.set_defaults(func=cmd_create_key)

    sub.add_parser("list-keys", help="List all API keys").set_defaults(func=cmd_list_keys)

    p_delete = sub.add_parser("delete-key", help="Delete an API key by ID")
    p_delete.add_argument("id", help="UUID of the key to delete")
    p_delete.set_defaults(func=cmd_delete_key)

    args = parser.parse_args()
    args.func(args)
