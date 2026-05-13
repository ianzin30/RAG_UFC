"""Sidebar rendering for collection file selection."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re

import streamlit as st

from presentation import chat_sessions
from presentation.shared.Config import PROJECT_ROOT
from presentation.shared.MarkdownPreview import render_markdown_preview_link

from .Collections import format_collection_label, group_documents_by_collection
from .Uploads import render_upload_dropzone


ICON_ONLY_BUTTON_LABEL = "\u200b"


def _render_files_header() -> None:
    st.markdown(
        """
        <div class="nav-panel-header">
            <div class="nav-panel-title">Arquivos</div>
            <div class="nav-panel-subtitle">Envie arquivos locais, arreste ou escolha</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_document_action_key(prefix: str, document: dict[str, str]) -> str:
    document_key = document.get("relative_path") or document.get("file_name") or ""
    raw_key = f"{prefix}_{document['collection']}::{document_key}"
    return re.sub(r"[^a-zA-Z0-9_:-]+", "_", raw_key)


def _active_collections_root() -> Path:
    return PROJECT_ROOT / "data" / "collections"


def _resolve_document_path(document: dict[str, str], collections_root: Path | None = None) -> Path:
    collections_root = (collections_root or _active_collections_root()).resolve()
    relative_path = Path(str(document.get("relative_path") or document.get("file_name") or ""))
    if not relative_path.name:
        raise RuntimeError("Arquivo nao identificado para exclusao.")

    resolved_path = (collections_root / relative_path).resolve()
    if not resolved_path.is_relative_to(collections_root):
        raise RuntimeError("Caminho de arquivo invalido para exclusao.")
    if resolved_path.suffix.lower() != ".md":
        raise RuntimeError("Apenas arquivos extraidos em Markdown podem ser excluidos pela interface.")
    return resolved_path


def _has_markdown_files(collections_root: Path | None = None) -> bool:
    collections_root = collections_root or _active_collections_root()
    return collections_root.exists() and any(path.is_file() for path in collections_root.rglob("*.md"))


def _delete_document(document: dict[str, str]) -> None:
    collections_root = _active_collections_root()
    document_path = _resolve_document_path(document, collections_root)
    if not document_path.exists():
        raise RuntimeError("Arquivo nao encontrado. Talvez ele ja tenha sido removido.")

    document_path.unlink()

    try:
        if (
            document_path.parent != collections_root
            and document_path.parent.exists()
            and not any(document_path.parent.iterdir())
        ):
            document_path.parent.rmdir()
    except OSError:
        pass

    st.session_state.current_collection = None
    st.session_state.rag_service = None
    if not _has_markdown_files(collections_root):
        chat_sessions.update_active_chat_collection(None)


@st.dialog("Excluir arquivo?")
def _render_delete_document_dialog(document: dict[str, str]) -> None:
    label = str(document.get("label") or document.get("file_name") or "arquivo").strip()
    st.write(f"Tem certeza que deseja excluir `{label}`?")
    st.caption("O arquivo sera removido da colecao local e so voltara se for enviado ou importado novamente.")

    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button(
            "Cancelar",
            key=_build_document_action_key("cancel_delete", document),
            use_container_width=True,
        ):
            st.rerun()
    with delete_col:
        if st.button(
            "Excluir",
            key=_build_document_action_key("confirm_delete", document),
            type="primary",
            icon=":material/delete:",
            use_container_width=True,
        ):
            try:
                _delete_document(document)
            except Exception as exc:
                st.session_state.upload_feedback = f"Nao foi possivel excluir o arquivo: {exc}"
                st.session_state.upload_feedback_kind = "error"
            else:
                st.toast(f"Arquivo '{label}' excluído.", icon=":material/delete:")
            st.rerun()


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
                badge_col, button_col, delete_col = st.columns([0.18, 0.66, 0.16], vertical_alignment="center")
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
                    st.markdown(
                        render_markdown_preview_link(
                            label=str(document.get("label") or document.get("file_name") or "arquivo"),
                            document=document,
                            prefix=_build_document_action_key("file", document),
                            class_name="markdown-preview-link file-row-preview-link",
                            close_href="#sidebar-files-panel",
                        ),
                        unsafe_allow_html=True,
                    )
                with delete_col:
                    if st.button(
                        ICON_ONLY_BUTTON_LABEL,
                        key=_build_document_action_key("delete", document),
                        help=f"Excluir {document['label']}",
                        icon=":material/delete:",
                        use_container_width=True,
                    ):
                        _render_delete_document_dialog(document)


def render_files_panel(available_documents: list[dict[str, str]]) -> None:
    with st.container(key="sidebar_files_shell"):
        _render_files_header()
        with st.container(key="sidebar_upload_shell"):
            render_upload_dropzone()
        st.divider()
        _render_file_library(available_documents)
