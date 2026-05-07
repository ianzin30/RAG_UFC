"""Resolves all per-user on-disk paths and enforces path containment."""
from __future__ import annotations

import re
from pathlib import Path


# Only allow Firebase UIDs (alphanumeric, dash, underscore) so user-controlled
# UIDs cannot escape the user directory via path traversal.
_UID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")


def _validate_uid(uid: str) -> str:
    if not uid or not _UID_RE.match(uid):
        raise ValueError(f"Invalid Firebase UID format: {uid!r}")
    return uid


def _users_base() -> Path:
    from ..RuntimeConfig import get_runtime_config, PROJECT_ROOT
    base = get_runtime_config().user_storage.base_dir
    p = Path(base)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def user_root(uid: str) -> Path:
    """Return data/users/{uid}/ — the root of all storage for this user."""
    return _users_base() / _validate_uid(uid)


def collections_root_for(uid: str) -> Path:
    """Return data/users/{uid}/collections/ — user-scoped FAISS collection source."""
    return user_root(uid) / "collections"


def uploads_root_for(uid: str) -> Path:
    """Return data/users/{uid}/uploads/ — raw uploaded byte storage."""
    return user_root(uid) / "uploads"


def vector_cache_root_for(uid: str) -> Path:
    """Return data/users/{uid}/vector/ — FAISS persistent cache directory."""
    return user_root(uid) / "vector"


def assert_safe_path(path: Path, uid: str) -> Path:
    """Raise if *path* is not strictly under the user's root (prevents directory traversal)."""
    root = user_root(uid).resolve()
    resolved = path.resolve()
    if not str(resolved).startswith(str(root)):
        raise ValueError(f"Path {resolved} escapes user root {root}")
    return resolved
