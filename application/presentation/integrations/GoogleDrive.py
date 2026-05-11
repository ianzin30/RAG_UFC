"""
Google Drive integration - allows users to import documents from Google Drive.

Implements the OAuth web-flow state machine on top of Streamlit:
- Connect button -> authorize link (Google in the same tab)
- Google redirects back to the running app with ?code=&state=
- App detects the callback, exchanges the code, persists the token,
  and imports the configured Drive folder, surfacing progress in-page.
"""

from __future__ import annotations

import logging

import streamlit as st

from presentation.shared.CollectionSelection import add_collection_selection
from service.GoogleDrive import GoogleDriveService


logger = logging.getLogger(__name__)


_DRIVE_FOLDER_NAME = "rag"
_COLLECTION_NAME = "google_drive_rag"


def _reset_state(*, keep_error: bool = False) -> None:
    st.session_state.gdrive_status = "idle"
    st.session_state.gdrive_oauth_state = None
    st.session_state.gdrive_auth_url = None
    if not keep_error:
        st.session_state.gdrive_error = None


def _bootstrap_from_persisted(service: GoogleDriveService) -> None:
    """If a token file exists, hydrate session as already-connected."""
    if st.session_state.gdrive_status != "idle":
        return
    if st.session_state.gdrive_credentials_json:
        return
    credentials = service.load_persisted_credentials()
    if credentials is None:
        return
    st.session_state.gdrive_credentials_json = credentials.to_json()
    st.session_state.gdrive_status = "connected"


def _handle_oauth_callback(service: GoogleDriveService) -> bool:
    """Detect ``?code=&state=`` in the URL and complete the exchange.

    Returns ``True`` when a callback was consumed (and a rerun should follow).
    """
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    if not code or not state:
        return False

    expected_state = st.session_state.gdrive_oauth_state
    if not expected_state or state != expected_state:
        # Stale or unrelated query params — clear and ignore so we don't loop.
        st.query_params.clear()
        return False

    st.session_state.gdrive_status = "exchanging"
    try:
        credentials = service.complete_login(state=state, code=code)
    except Exception as exc:
        logger.warning("Google Drive auth exchange failed: %s", exc)
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao conectar ao Google Drive: {exc}"
        st.session_state.gdrive_oauth_state = None
        st.session_state.gdrive_auth_url = None
        st.query_params.clear()
        return True

    st.session_state.gdrive_credentials_json = credentials.to_json()
    st.session_state.gdrive_oauth_state = None
    st.session_state.gdrive_auth_url = None
    st.session_state.gdrive_status = "importing"
    st.query_params.clear()
    return True


def _run_import(service: GoogleDriveService) -> None:
    raw = st.session_state.gdrive_credentials_json
    if not raw:
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = "Credenciais do Google Drive nao encontradas."
        return
    try:
        credentials = service.credentials_from_json(raw)
        result = service.ingest_folder_to_collection(
            folder_name=_DRIVE_FOLDER_NAME,
            collection_name=_COLLECTION_NAME,
            credentials=credentials,
        )
    except Exception as exc:
        logger.warning("Google Drive import failed: %s", exc)
        st.session_state.gdrive_status = "error"
        st.session_state.gdrive_error = f"Falha ao importar arquivos: {exc}"
        return

    st.session_state.collection = add_collection_selection(
        st.session_state.get("collection"),
        result["collection_name"],
    )
    st.session_state.current_collection = None
    st.session_state.messages = []
    st.session_state.rag_service = None
    file_count = len(result["files"])
    st.session_state.gdrive_import_result = {
        "collection_name": result["collection_name"],
        "file_count": file_count,
    }
    st.session_state.drive_feedback = (
        f"{file_count} arquivos importados do Google Drive para a colecao '{result['collection_name']}'."
    )
    st.session_state.gdrive_status = "connected"


def render_connect_button(
    button_label: str = "Conectar ao Google Drive",
    help_text: str | None = None,
    key: str = "google_drive_connect",
) -> bool:
    """Render the Google Drive connection UI as a status-aware state machine."""
    service = GoogleDriveService()

    _bootstrap_from_persisted(service)

    if _handle_oauth_callback(service):
        # Either we transitioned to "importing"/"error" — rerun so the UI updates,
        # and the actual import runs on the next pass.
        st.rerun()

    if st.session_state.gdrive_status == "importing":
        with st.spinner("Importando arquivos da pasta RAG..."):
            _run_import(service)
        st.rerun()

    status = st.session_state.gdrive_status

    if status == "idle":
        if st.button(button_label, key=key, use_container_width=True, help=help_text):
            try:
                auth_url, state = service.start_login()
            except FileNotFoundError as exc:
                st.session_state.gdrive_status = "error"
                st.session_state.gdrive_error = str(exc)
                st.rerun()
            except Exception as exc:
                logger.warning("Failed to start Google Drive auth flow: %s", exc)
                st.session_state.gdrive_status = "error"
                st.session_state.gdrive_error = f"Falha ao iniciar autenticacao: {exc}"
                st.rerun()
            else:
                st.session_state.gdrive_oauth_state = state
                st.session_state.gdrive_auth_url = auth_url
                st.session_state.gdrive_status = "awaiting_authorize"
                st.rerun()
        return False

    if status == "awaiting_authorize":
        st.info("Conectando ao Google Drive...")
        auth_url = st.session_state.gdrive_auth_url
        if auth_url:
            st.link_button(
                "Autorizar no Google",
                auth_url,
                use_container_width=True,
                type="primary",
            )
        if st.button(
            "Cancelar",
            key=f"{key}_cancel",
            use_container_width=True,
        ):
            _reset_state()
            st.rerun()
        return False

    if status == "exchanging":
        st.info("Conectando ao Google Drive...")
        st.button(button_label, key=f"{key}_disabled_exchange", disabled=True, use_container_width=True)
        return False

    if status == "connected":
        result = st.session_state.gdrive_import_result
        if result:
            st.success(
                f"Google Drive conectado. {result['file_count']} arquivos importados "
                f"para a colecao '{result['collection_name']}'."
            )
        else:
            st.success("Google Drive conectado.")
        reimport_col, disconnect_col = st.columns(2)
        with reimport_col:
            if st.button(
                "Reimportar pasta RAG",
                key=f"{key}_reimport",
                use_container_width=True,
            ):
                st.session_state.gdrive_status = "importing"
                st.session_state.gdrive_error = None
                st.rerun()
        with disconnect_col:
            if st.button(
                "Desconectar",
                key=f"{key}_disconnect",
                use_container_width=True,
            ):
                service.forget_persisted_credentials()
                st.session_state.gdrive_credentials_json = None
                st.session_state.gdrive_import_result = None
                _reset_state()
                st.rerun()
        return False

    if status == "error":
        message = st.session_state.gdrive_error or "Falha ao conectar ao Google Drive."
        st.error(message)
        if st.button(
            "Tentar novamente",
            key=f"{key}_retry",
            use_container_width=True,
        ):
            _reset_state()
            st.rerun()
        return False

    return False
