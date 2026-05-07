"""Firebase authentication — app bootstrap and ID token verification."""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from .UserContext import UserContext

logger = logging.getLogger("ragufc.auth")


@lru_cache(maxsize=1)
def _init_firebase_app():
    """Initialize the firebase-admin app once per process."""
    import firebase_admin
    from firebase_admin import credentials

    from ..RuntimeConfig import get_runtime_config

    cfg = get_runtime_config().firebase
    if not cfg.enabled:
        return None

    cred_path = Path(cfg.credentials_path)
    if not cred_path.is_absolute():
        from ..RuntimeConfig import PROJECT_ROOT
        cred_path = PROJECT_ROOT / cfg.credentials_path

    if not cred_path.exists():
        raise RuntimeError(
            f"Firebase service account not found at {cred_path}. "
            "Download it from the Firebase Console → Project Settings → Service Accounts "
            "and place it at that path (never commit it)."
        )

    if not firebase_admin._apps:
        app = firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
    else:
        app = firebase_admin.get_app()

    logger.info("Firebase app initialized (project: %s)", getattr(app, "project_id", "?"))
    return app


def verify_id_token(id_token: str) -> UserContext:
    """Verify a Firebase ID token and return a UserContext.

    Raises firebase_admin.auth.InvalidIdTokenError / ExpiredIdTokenError on failure.
    """
    from firebase_admin import auth

    _init_firebase_app()
    decoded = auth.verify_id_token(id_token)
    user_id: str = decoded["uid"]
    email: str = decoded.get("email", "")
    display_name: str | None = decoded.get("name") or decoded.get("display_name")
    logger.info("Token verified — uid=%s email=%s", user_id, email)
    return UserContext(user_id=user_id, email=email, display_name=display_name)


def is_firebase_enabled() -> bool:
    from ..RuntimeConfig import get_runtime_config
    try:
        return get_runtime_config().firebase.enabled
    except Exception:
        return False
