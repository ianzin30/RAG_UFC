"""Cached pymongo client and database handle with index bootstrapping."""
from __future__ import annotations

import logging
from functools import lru_cache

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database

logger = logging.getLogger("ragufc.storage")


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    from ..RuntimeConfig import get_runtime_config
    cfg = get_runtime_config().mongodb
    client: MongoClient = MongoClient(cfg.uri, serverSelectionTimeoutMS=5000)
    # Ping to catch misconfig early
    client.admin.command("ping")
    logger.info("MongoDB connected — uri=%s db=%s", cfg.uri, cfg.database)
    return client


def get_db() -> Database:
    from ..RuntimeConfig import get_runtime_config
    client = get_mongo_client()
    db_name = get_runtime_config().mongodb.database
    return client[db_name]


def ensure_indexes(db: Database) -> None:
    """Create all application indexes idempotently."""
    db["users"].create_index([("user_id", ASCENDING)], unique=True, background=True)

    db["chat_sessions"].create_index(
        [("user_id", ASCENDING), ("updated_at", DESCENDING)], background=True
    )

    db["chat_messages"].create_index(
        [("user_id", ASCENDING), ("chat_id", ASCENDING), ("created_at", ASCENDING)],
        background=True,
    )

    db["user_files"].create_index(
        [("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        background=True,
    )
    # Partial unique: no two active files with same (user_id, collection_name, filename)
    db["user_files"].create_index(
        [("user_id", ASCENDING), ("collection_name", ASCENDING), ("filename", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": {"$in": ["uploaded", "indexed", "processing", "failed"]}},
        background=True,
    )
    logger.info("MongoDB indexes ensured")
