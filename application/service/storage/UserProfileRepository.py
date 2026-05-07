"""users collection — upsert profile on login."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pymongo.database import Database

logger = logging.getLogger("ragufc.storage")


def upsert_on_login(db: Database, user_id: str, email: str, display_name: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db["users"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "email": email,
                "display_name": display_name,
                "last_login_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    logger.info("User profile upserted — uid=%s", user_id)
