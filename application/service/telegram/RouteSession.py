"""Session state helpers for collection-routing replies."""
# Simple: Track loaded documents for each user

def ensure_collection_session(session: dict) -> dict:
    session.setdefault("loaded_files", [])
    session.setdefault("loaded_folder_name", None)
    session.setdefault("last_collection_intent", None)
    return session


def clear_collection_session(session: dict) -> None:
    session["loaded_files"] = []
    session["loaded_folder_name"] = None
    session["last_collection_intent"] = None


def update_collection_session(session: dict, result: dict) -> None:
    session["loaded_files"] = list(result.get("files") or [])
    session["loaded_folder_name"] = result.get("folder_name")
    session["last_collection_intent"] = None
