"""Authentication helpers for the Google Drive service."""

from __future__ import annotations

import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .constants import SCOPES


# Esta funcao abre o fluxo OAuth local para o usuario autorizar o Drive.
def login_with_google_drive(credentials_file: Path):
    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: '{credentials_file}'."
        )

    config = json.loads(credentials_file.read_text(encoding="utf-8"))
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    return flow.run_local_server(
        port=0,
        open_browser=True,
        prompt="select_account",
        access_type="offline",
        include_granted_scopes="false",
    )


# Este helper recompõe credenciais salvas sem refazer o login no navegador.
def credentials_from_json(raw_json: str):
    return Credentials.from_authorized_user_info(json.loads(raw_json), SCOPES)


# Esta fabrica monta o cliente da API do Drive usado pelo restante do pipeline.
def build_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)
