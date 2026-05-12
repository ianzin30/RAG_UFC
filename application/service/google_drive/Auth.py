"""Authentication helpers for the Google Drive service.

Implements the OAuth 2.0 web-server flow so the auth callback returns to the
running Streamlit instance via ``?code=...&state=...`` query params, rather
than spinning up a separate local HTTP server on a random port.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from .Constants import SCOPES


class GoogleDriveWebOAuthSetupError(RuntimeError):
    """Raised when Streamlit web OAuth is configured with a non-web client."""


@dataclass(frozen=True)
class GoogleDriveAuthorizationRequest:
    authorization_url: str
    state: str
    code_verifier: str


def _load_client_config(credentials_file: Path) -> dict:
    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: '{credentials_file}'."
        )
    return json.loads(credentials_file.read_text(encoding="utf-8"))


def _require_web_client_config(config: dict, credentials_file: Path) -> None:
    if "web" in config:
        return
    if "installed" in config:
        raise GoogleDriveWebOAuthSetupError(
            "Google Drive web OAuth is using a desktop/installed OAuth client. "
            "Create a Google Cloud OAuth client of type 'Web application', save it "
            "as config/google-oauth-web-credentials.json, and point "
            "GOOGLE_OAUTH_WEB_CREDENTIALS_FILE to that file."
        )
    raise GoogleDriveWebOAuthSetupError(
        f"Google OAuth credentials file '{credentials_file}' must contain a 'web' client."
    )


def build_auth_flow(
    credentials_file: Path,
    redirect_uri: str,
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    """Create a web OAuth flow bound to the redirect URI and optional PKCE verifier."""
    config = _load_client_config(credentials_file)
    _require_web_client_config(config, credentials_file)
    return Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=code_verifier is None,
    )


def build_authorization_request(flow: Flow) -> GoogleDriveAuthorizationRequest:
    """Return the authorization URL plus the PKCE verifier needed for callback exchange."""
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent select_account",
    )
    if not flow.code_verifier:
        raise GoogleDriveWebOAuthSetupError("Google OAuth did not generate a PKCE code verifier.")
    return GoogleDriveAuthorizationRequest(
        authorization_url=authorization_url,
        state=state,
        code_verifier=flow.code_verifier,
    )


def build_authorization_url(flow: Flow) -> tuple[str, str]:
    """Return ``(auth_url, state)`` for legacy callers of the helper."""
    request = build_authorization_request(flow)
    return request.authorization_url, request.state


def build_google_drive_authorization_request(
    credentials_file: Path,
    redirect_uri: str,
    state: str | None = None,
) -> GoogleDriveAuthorizationRequest:
    flow = build_auth_flow(credentials_file, redirect_uri, state=state)
    return build_authorization_request(flow)


def build_google_drive_authorization_url(
    credentials_file: Path,
    redirect_uri: str,
    state: str | None = None,
) -> str:
    return build_google_drive_authorization_request(
        credentials_file,
        redirect_uri,
        state,
    ).authorization_url


def exchange_code_for_credentials(flow: Flow, code: str) -> Credentials:
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_from_google_drive_callback(
    credentials_file: Path,
    redirect_uri: str,
    code: str,
    code_verifier: str,
    state: str | None = None,
) -> Credentials:
    flow = build_auth_flow(
        credentials_file,
        redirect_uri,
        state=state,
        code_verifier=code_verifier,
    )
    return exchange_code_for_credentials(flow, code)


def credentials_to_json(credentials: Credentials) -> str:
    return credentials.to_json()


def credentials_from_json(raw_json: str) -> Credentials:
    info = json.loads(raw_json)
    try:
        return Credentials.from_authorized_user_info(info, SCOPES)
    except ValueError as exc:
        if "refresh_token" not in str(exc):
            raise

    expiry = info.get("expiry")
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00")).replace(tzinfo=None)
    elif not isinstance(expiry, datetime):
        expiry = None

    return Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri=info.get("token_uri"),
        client_id=info.get("client_id"),
        client_secret=info.get("client_secret"),
        scopes=info.get("scopes") or SCOPES,
        expiry=expiry,
    )


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
        prompt="consent select_account",
        access_type="offline",
        include_granted_scopes="false",
    )
