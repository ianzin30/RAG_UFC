"""Upload helpers for the app sidebar."""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from service.LocalUploads import LocalUploadService

from presentation.shared.Config import UPLOAD_COLLECTION_NAME, UPLOAD_FILE_TYPES
from .Selection import set_selected_collections


def build_upload_signature(uploaded_files) -> str:
    parts = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        parts.append(f"{uploaded_file.name}:{len(content)}")
    return "|".join(parts)


def _progress_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_file_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.1f} MB"


def summarize_upload_selection(uploaded_files) -> str:
    uploaded_files = list(uploaded_files or [])
    total_bytes = sum(len(uploaded_file.getvalue()) for uploaded_file in uploaded_files)
    file_count = len(uploaded_files)
    if file_count == 1:
        return f"1 arquivo selecionado, {_format_file_size(total_bytes)}."
    return f"{file_count} arquivos selecionados, {_format_file_size(total_bytes)} no total."


def _format_upload_progress(progress: dict[str, object] | None) -> tuple[str, str]:
    if not progress:
        return ("Preparando arquivos", "Aguardando a selecao dos arquivos.")

    status = str(progress.get("status") or "").strip()
    processed = _progress_int(progress.get("processed"))
    total = _progress_int(progress.get("total"))
    saved = _progress_int(progress.get("saved"))
    skipped = _progress_int(progress.get("skipped"))
    file_name = Path(str(progress.get("file_name") or "")).name
    reason = str(progress.get("reason") or "").strip()

    if status == "queued":
        return (
            "Arquivos recebidos",
            f"Preparando {total} arquivo(s) para extracao e conversao em Markdown.",
        )
    if status == "extracting":
        return (
            f"Extraindo texto de {file_name}",
            f"{processed}/{total} arquivos processados. {saved} salvo(s), {skipped} ignorado(s).",
        )
    if status == "saved":
        return (
            f"{file_name} pronto",
            f"{processed}/{total} arquivos processados. {saved} salvo(s), {skipped} ignorado(s).",
        )
    if status == "skipped":
        detail = f" Motivo: {reason}." if reason else ""
        return (
            f"{file_name} ignorado",
            f"{processed}/{total} arquivos processados. {saved} salvo(s), {skipped} ignorado(s).{detail}",
        )
    if status == "completed":
        return (
            "Upload concluido",
            f"{processed}/{total} arquivos processados. {saved} salvo(s), {skipped} ignorado(s).",
        )
    if status == "error":
        detail = f" {reason}" if reason else ""
        return ("Falha ao processar arquivos", f"{processed}/{total} arquivos verificados.{detail}")
    return ("Processando arquivos", f"{processed}/{total} arquivos processados.")


def _upload_progress_percent(progress: dict[str, object] | None) -> int:
    if not progress:
        return 0
    total = _progress_int(progress.get("total"))
    if total <= 0:
        return 0
    status = str(progress.get("status") or "").strip()
    if status == "completed":
        return 100
    processed = min(_progress_int(progress.get("processed")), total)
    return min(99, int((processed / total) * 100))


def _render_upload_progress(progress_slot, progress: dict[str, object] | None) -> None:
    title, subtitle = _format_upload_progress(progress)
    with progress_slot.container():
        st.markdown(
            f"""
            <div class="upload-processing-shell">
                <div class="upload-processing-spinner"></div>
                <div class="upload-processing-copy">
                    <div class="upload-processing-title">{escape(title)}</div>
                    <div class="upload-processing-subtitle">{escape(subtitle)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(_upload_progress_percent(progress))


def ingest_sidebar_uploads(uploaded_files, progress_callback=None) -> None:
    upload_service = LocalUploadService()
    result = upload_service.ingest_uploaded_files(
        uploaded_files,
        collection_name=UPLOAD_COLLECTION_NAME,
        progress_callback=progress_callback,
    )
    saved_count = len(result["files"])
    skipped_count = len(result["skipped_files"])
    feedback = f"{saved_count} arquivo(s) convertido(s) e pronto(s) para o chat."
    if skipped_count:
        feedback += f" {skipped_count} arquivo(s) ignorado(s)."

    st.toast(feedback, icon=":material/check_circle:")
    set_selected_collections([result["collection_name"]])


def render_notice(message: str, kind: str = "neutral") -> None:
    st.markdown(
        f'<div class="app-note {escape(kind)}">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_upload_dropzone() -> None:
    upload_slot = st.empty()
    with upload_slot.container():
        st.markdown('<div class="section-label">Arraste arquivos</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="upload-meta">PDF, DOCX, PPTX, XLSX, CSV, MD, TXT e imagens. Ate 200MB por arquivo.</div>',
            unsafe_allow_html=True,
        )
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
    progress_state = {
        "status": "queued",
        "processed": 0,
        "total": len(uploaded_files),
        "saved": 0,
        "skipped": 0,
    }
    with upload_slot.container():
        st.markdown('<div class="section-label">Processamento</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="upload-meta">{escape(summarize_upload_selection(uploaded_files))}</div>',
            unsafe_allow_html=True,
        )
        progress_slot = st.empty()
        _render_upload_progress(progress_slot, progress_state)

    def handle_progress(progress: dict[str, object]) -> None:
        progress_state.update(progress)
        _render_upload_progress(progress_slot, progress_state)

    try:
        ingest_sidebar_uploads(uploaded_files, progress_callback=handle_progress)
    except Exception as exc:
        st.session_state.upload_feedback = str(exc)
        st.session_state.upload_feedback_kind = "error"
    finally:
        st.session_state.last_upload_signature = None
        st.session_state.upload_widget_version += 1
        st.rerun()
