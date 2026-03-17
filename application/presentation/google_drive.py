import streamlit as st

from service.google_drive import GoogleDriveService


def show():
    st.subheader("Google Drive")
    service = GoogleDriveService()

    if st.button("Connect", key="google_drive_connect"):
        with st.spinner("Connecting to Google Drive and preparing chat..."):
            try:
                credentials = service.login()
                result = service.ingest_folder_to_collection(
                    folder_name="rag",
                    collection_name="google_drive_rag",
                    credentials=credentials,
                )
            except Exception as exc:
                st.error(str(exc))
                return

        st.session_state.collection = result["collection_name"]
        st.session_state.current_collection = None
        st.session_state.messages = []
        st.session_state.rag_service = None
        st.session_state.pending_mode = "Chat"
        st.rerun()

    st.caption("Connect to Google Drive and the PDFs from the folder named 'rag' will be sent directly to chat.")
