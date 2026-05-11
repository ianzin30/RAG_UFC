"""Authentication helpers for the Google Drive service.

Implements the OAuth 2.0 web-server flow so the auth callback returns to the
running Streamlit instance via ``?code=...&state=...`` query params, rather
than spinning up a separate local HTTP server on a random port.
"""

from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from .Constants import SCOPES


def _load_client_config(credentials_file: Path) -> dict:
    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: '{credentials_file}'."
        )
    return json.loads(credentials_file.read_text(encoding="utf-8"))


def build_auth_flow(credentials_file: Path, redirect_uri: str, state: str | None = None) -> Flow:
    """Create a Flow bound to the given redirect URI (and optionally a known state)."""
    config = _load_client_config(credentials_file)
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect_uri, state=state)


def build_authorization_url(flow: Flow) -> tuple[str, str]:
    """Return ``(auth_url, state)`` for the user to authorize the app."""
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="select_account",
    )
    return auth_url, state


def exchange_code_for_credentials(flow: Flow, code: str) -> Credentials:
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_json(credentials: Credentials) -> str:
    return credentials.to_json()


def credentials_from_json(raw_json: str) -> Credentials:
    return Credentials.from_authorized_user_info(json.loads(raw_json), SCOPES)


def refresh_if_needed(credentials: Credentials) -> Credentials:
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials


def build_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)


def login_with_google_drive(credentials_file: Path):
    """Desktop OAuth flow — used by non-web callers (e.g., Telegram bot).

    Streamlit must not call this; it spawns a local server on a random port
    and only makes sense when the operator is sitting at the same machine.
    """
    config = _load_client_config(credentials_file)
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    return flow.run_local_server(
        port=0,
        open_browser=True,
        prompt="select_account",
        access_type="offline",
        include_granted_scopes="false",
    )
