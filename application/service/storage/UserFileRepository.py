"""user_files collection — all queries filter by user_id."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pymongo.database import Database

logger = logging.getLogger("ragufc.storage")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_file(
    db: Database,
    *,
    user_id: str,
    filename: str,
    original_filename: str,
    storage_path: str,
    collection_name: str,
    status: str = "uploaded",
) -> str:
    """Insert or update a user_files document. Returns the inserted _id as str."""
    now = _now()
    result = db["user_files"].update_one(
        {"user_id": user_id, "collection_name": collection_name, "filename": filename},
        {
            "$set": {
                "original_filename": original_filename,
                "storage_path": storage_path,
                "status": status,
                "updated_at": now,
            },
            "$setOnInsert": {"user_id": user_id, "created_at": now, "deleted_at": None},
        },
        upsert=True,
    )
    inserted_id = str(result.upserted_id) if result.upserted_id else ""
    logger.info(
        "File recorded — uid=%s filename=%s collection=%s status=%s",
        user_id,
        filename,
        collection_name,
        status,
    )
    return inserted_id


def mark_collection_deleted(db: Database, user_id: str, collection_name: str) -> int:
    """Mark all active files in a collection as deleted. Returns count."""
    now = _now()
    result = db["user_files"].update_many(
        {"user_id": user_id, "collection_name": collection_name, "status": {"$ne": "deleted"}},
        {"$set": {"status": "deleted", "deleted_at": now}},
    )
    logger.info(
        "Collection marked deleted — uid=%s collection=%s count=%d",
        user_id,
        collection_name,
        result.modified_count,
    )
    return result.modified_count


def mark_file_indexed(db: Database, user_id: str, filename: str, collection_name: str) -> None:
    db["user_files"].update_one(
        {"user_id": user_id, "filename": filename, "collection_name": collection_name},
        {"$set": {"status": "indexed", "updated_at": _now()}},
    )


def list_active_files(db: Database, user_id: str) -> list[dict]:
    """Return all non-deleted files for *user_id*."""
    return list(
        db["user_files"]
        .find(
            {"user_id": user_id, "status": {"$ne": "deleted"}},
            {"_id": 0, "user_id": 0},
        )
        .sort("created_at", -1)
    )


def list_indexed_collections(db: Database, user_id: str) -> list[str]:
    """Return distinct collection names that have at least one indexed file."""
    return db["user_files"].distinct(
        "collection_name",
        {"user_id": user_id, "status": "indexed"},
    )
