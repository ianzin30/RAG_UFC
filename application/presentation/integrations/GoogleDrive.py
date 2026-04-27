"""
Google Drive integration - allows users to import documents from Google Drive.

Provides UI for connecting to Google Drive and ingesting files into a collection.
"""

import streamlit as st

from presentation.shared.CollectionSelection import add_collection_selection
from service.GoogleDrive import GoogleDriveService


def render_connect_button(
    button_label: str = "Conectar",
    help_text: str | None = None,
    key: str = "google_drive_connect",
) -> bool:
    """
    Render a button to connect to Google Drive and import documents.

    When clicked, authenticates with Google Drive, imports files from the 'rag' folder,
    adds them to the collection, and resets the chat to start fresh.
    """
    service = GoogleDriveService()

    # Render and handle the connection button
    if st.button(button_label, key=key, use_container_width=True, help=help_text):
        with st.spinner("Conectando ao Google Drive e preparando o chat..."):
            try:
                credentials = service.login()
                result = service.ingest_folder_to_collection(
                    folder_name="rag",
                    collection_name="google_drive_rag",
                    credentials=credentials,
                )
            except Exception as exc:
                st.error(str(exc))
                return False

        st.session_state.collection = add_collection_selection(
            st.session_state.get("collection"),
            result["collection_name"],
        )
        st.session_state.current_collection = None
        st.session_state.messages = []
        st.session_state.rag_service = None
        st.session_state.drive_feedback = (
            f"{len(result['files'])} arquivos importados do Google Drive para a colecao '{result['collection_name']}'."
        )
        st.rerun()

    return False
