"""Upload helpers for the app sidebar."""

from html import escape

import streamlit as st

from service.LocalUploads import LocalUploadService

from presentation.shared.Config import UPLOAD_COLLECTION_NAME, UPLOAD_FILE_TYPES
from .Selection import add_collection


def build_upload_signature(uploaded_files) -> str:
    parts = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        parts.append(f"{uploaded_file.name}:{len(content)}")
    return "|".join(parts)


def ingest_sidebar_uploads(uploaded_files) -> None:
    upload_service = LocalUploadService()
    result = upload_service.ingest_uploaded_files(
        uploaded_files,
        collection_name=UPLOAD_COLLECTION_NAME,
    )
    saved_count = len(result["files"])
    skipped_count = len(result["skipped_files"])
    feedback = f"{saved_count} arquivo(s) pronto(s)."
    if skipped_count:
        feedback += f" {skipped_count} arquivo(s) ignorado(s)."

    st.toast(feedback, icon=":material/check_circle:")
    add_collection(result["collection_name"])


def render_notice(message: str, kind: str = "neutral") -> None:
    st.markdown(
        f'<div class="app-note {escape(kind)}">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_upload_dropzone() -> None:
    upload_slot = st.empty()
    with upload_slot.container():
        st.markdown('<div class="section-label">Arraste arquivos</div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-meta">PDF, DOCX, PPTX, XLSX, CSV, MD</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Arraste arquivos para o chat",
            type=UPLOAD_FILE_TYPES,
            accept_multiple_files=True,
            label_visibility="collapsed",
            key=f"sidebar_upload_files_{st.session_state.upload_widget_version}",
        )

    if not uploaded_files:
        st.session_state.last_upload_signature = None
        return

    signature = build_upload_signature(uploaded_files)
    if signature == st.session_state.get("last_upload_signature"):
        return

    st.session_state.last_upload_signature = signature
    file_count = len(uploaded_files)
    with upload_slot.container():
        with st.status(
            f"Processando {file_count} arquivo(s)...",
            expanded=True,
        ) as status:
            try:
                status.update(label=f"Salvando {file_count} arquivo(s)...", state="running")
                ingest_sidebar_uploads(uploaded_files)
                status.update(label="Arquivos prontos!", state="complete", expanded=False)
            except Exception as exc:
                st.session_state.upload_feedback = str(exc)
                st.session_state.upload_feedback_kind = "error"
                status.update(label="Erro no upload.", state="error")
            finally:
                st.session_state.last_upload_signature = None
                st.session_state.upload_widget_version += 1
                st.rerun()
