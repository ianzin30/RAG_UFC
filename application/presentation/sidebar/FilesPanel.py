"""Sidebar rendering for collection file selection."""

from html import escape

import streamlit as st

from presentation.shared.CollectionSelection import is_collection_selected
from presentation.integrations.GoogleDrive import render_connect_button

from .Collections import format_collection_label, group_documents_by_collection
from .Selection import toggle_collection
from .Uploads import render_upload_dropzone


def _render_files_header() -> None:
    st.markdown(
        """
        <div class="nav-panel-header">
            <div class="nav-panel-title">Arquivos</div>
            <div class="nav-panel-subtitle">Conecte o Drive, envie novos arquivos e escolha a colecao ativa.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_drive_connect_button() -> None:
    with st.container(key="sidebar_drive_connect_shell"):
        render_connect_button(
            button_label="Conectar ao Google Drive",
            help_text="Importa a pasta rag do Google Drive para a colecao local.",
            key="google_drive_connect_sidebar",
        )


def _render_file_library(available_documents: list[dict[str, str]]) -> None:
    st.markdown('<div class="section-label">Arquivos</div>', unsafe_allow_html=True)
    if not available_documents:
        st.caption("Nenhum arquivo.")
        return

    for collection_name, documents in group_documents_by_collection(available_documents):
        group_container = st.container(border=bool(collection_name))
        with group_container:
            if collection_name:
                st.markdown(
                    f"""
                    <div class="folder-card-header">
                        <div class="folder-card-title">{escape(format_collection_label(collection_name))}</div>
                        <div class="folder-card-count">{len(documents)} arquivo(s)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            for document in documents:
                is_active = is_collection_selected(st.session_state.get("collection"), document["collection"])
                badge_col, button_col = st.columns([0.22, 0.78], vertical_alignment="center")
                with badge_col:
                    st.markdown(
                        """
                        <div class="pdf-file-icon">
                            <div class="pdf-file-corner"></div>
                            <div class="pdf-file-label">PDF</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with button_col:
                    if st.button(
                        document["label"],
                        key=f"use_{document['collection']}::{document['file_name']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        toggle_collection(document["collection"])
                        st.rerun()


def render_files_panel(available_documents: list[dict[str, str]]) -> None:
    with st.container(key="sidebar_files_shell"):
        _render_files_header()
        _render_drive_connect_button()
        st.divider()
        with st.container(key="sidebar_upload_shell"):
            render_upload_dropzone()
        st.divider()
        _render_file_library(available_documents)
