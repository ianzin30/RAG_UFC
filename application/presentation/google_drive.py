import streamlit as st

from presentation.collection_selection import add_collection_selection
from service.google_drive import GoogleDriveService


def render_connect_button(
    button_label: str = "Conectar",
    help_text: str | None = None,
    key: str = "google_drive_connect",
) -> bool:
    service = GoogleDriveService()

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
