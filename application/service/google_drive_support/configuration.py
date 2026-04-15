"""Environment and path helpers for the Google Drive service."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from ..runtime_config import PROJECT_ROOT, load_project_environment
except ImportError:
    from runtime_config import PROJECT_ROOT, load_project_environment

from .models import GoogleDrivePaths


load_project_environment()


def build_google_drive_paths() -> GoogleDrivePaths:
    credentials_override = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE")
    credentials_file = (
        Path(credentials_override).expanduser()
        if credentials_override
        else PROJECT_ROOT / "config" / "google-oauth-credentials.json"
    )
    collections_root = PROJECT_ROOT / "data" / "collections"
    return GoogleDrivePaths(credentials_file=credentials_file, collections_root=collections_root)
