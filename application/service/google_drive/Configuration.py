"""Environment and path helpers for the Google Drive service."""
# Simple: Set up folder paths, OAuth redirect, and token cache for Google Drive

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from ..RuntimeConfig import PROJECT_ROOT, load_project_environment
from .Models import GoogleDrivePaths


load_project_environment()
logger = logging.getLogger(__name__)


DEFAULT_REDIRECT_URI = "http://localhost:8501/"


def _resolve_redirect_uri(credentials_file: Path) -> str:
    env_value = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
    if env_value:
        return env_value
    try:
        raw = json.loads(credentials_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_REDIRECT_URI
    for client_type in ("web", "installed"):
        block = raw.get(client_type)
        if not isinstance(block, dict):
            continue
        uris = block.get("redirect_uris") or []
        for uri in uris:
            # Skip OOB / native placeholders that aren't valid for a Streamlit redirect.
            if not isinstance(uri, str):
                continue
            if uri.startswith("http://") or uri.startswith("https://"):
                if client_type == "installed":
                    logger.warning(
                        "Using redirect URI from 'installed' OAuth client; "
                        "convert the OAuth client to a 'web' application in Google Cloud Console."
                    )
                return uri
    return DEFAULT_REDIRECT_URI


def build_google_drive_paths() -> GoogleDrivePaths:
    credentials_override = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE")
    credentials_file = (
        Path(credentials_override).expanduser()
        if credentials_override
        else PROJECT_ROOT / "config" / "google-oauth-credentials.json"
    )
    token_override = os.getenv("GOOGLE_OAUTH_TOKEN_FILE")
    token_file = (
        Path(token_override).expanduser()
        if token_override
        else PROJECT_ROOT / "config" / "google-drive-token.json"
    )
    collections_root = PROJECT_ROOT / "data" / "collections"
    redirect_uri = _resolve_redirect_uri(credentials_file)
    return GoogleDrivePaths(
        credentials_file=credentials_file,
        collections_root=collections_root,
        token_file=token_file,
        redirect_uri=redirect_uri,
    )
