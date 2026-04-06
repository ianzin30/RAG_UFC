import base64
import os
import re
from html import escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from presentation import chat
from presentation import chat_sessions
from presentation.collection_selection import (
    add_collection_selection,
    is_collection_selected,
    normalize_collection_selection,
    sanitize_collection_selection,
    toggle_collection_selection,
)
from service.local_uploads import LocalUploadService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PROJECT_ROOT / "application" / "assets" / "rag_treino_icon.png"
LOGO_DATA_URI = (
    f"data:image/png;base64,{base64.b64encode(LOGO_PATH.read_bytes()).decode('ascii')}"
    if LOGO_PATH.exists()
    else ""
)
ROOT_COLLECTION_KEY = "__root__"
UPLOAD_COLLECTION_NAME = "uploaded_files"
UPLOAD_FILE_TYPES = [
    "pdf",
    "docx",
    "pptx",
    "xlsx",
    "csv",
    "md",
    "txt",
    "html",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "tiff",
    "bmp",
]

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def list_collection_documents() -> list[dict[str, str]]:
    collections_dir = PROJECT_ROOT / "data" / "collections"
    if not collections_dir.exists():
        return []

    documents: list[dict[str, str]] = []
    for file_path in sorted(collections_dir.glob("*.md"), key=lambda item: item.name.lower()):
        label = re.sub(r"^\d+[_\- ]*", "", file_path.stem).strip() or file_path.stem
        documents.append(
            {
                "collection": ROOT_COLLECTION_KEY,
                "file_name": file_path.name,
                "label": label,
            }
        )

    for folder in sorted(collections_dir.iterdir(), key=lambda item: item.name.lower()):
        if not folder.is_dir():
            continue

        markdown_files = sorted(folder.glob("*.md"), key=lambda item: item.name.lower())
        for file_path in markdown_files:
            label = re.sub(r"^\d+[_\- ]*", "", file_path.stem).strip() or file_path.stem
            documents.append(
                {
                    "collection": folder.name,
                    "file_name": file_path.name,
                    "label": label,
                }
            )

    return documents


def list_available_collections(documents: list[dict[str, str]]) -> list[str]:
    return sorted({document["collection"] for document in documents if document["collection"]})


def group_documents_by_collection(documents: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for document in documents:
        grouped.setdefault(document["collection"], []).append(document)

    return sorted(grouped.items(), key=lambda item: (item[0] != ROOT_COLLECTION_KEY, item[0].lower()))


def format_collection_label(collection_name: str) -> str:
    if not collection_name or collection_name == ROOT_COLLECTION_KEY:
        return ""
    return collection_name.replace("_", " ").strip()


def set_selected_collections(collections) -> None:
    normalized = normalize_collection_selection(collections)
    current = normalize_collection_selection(st.session_state.get("collection"))
    if current == normalized:
        return

    st.session_state.current_collection = None
    st.session_state.rag_service = None
    chat_sessions.update_active_chat_collection(normalized or None)


def toggle_collection(collection_name: str | None) -> None:
    set_selected_collections(toggle_collection_selection(st.session_state.get("collection"), collection_name))


def add_collection(collection_name: str | None) -> None:
    set_selected_collections(add_collection_selection(st.session_state.get("collection"), collection_name))


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

    st.session_state.upload_feedback = feedback
    st.session_state.upload_feedback_kind = "success"
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
    with upload_slot.container():
        st.markdown(
            """
            <div class="upload-processing-shell">
                <div class="upload-processing-spinner"></div>
                <div class="upload-processing-copy">
                    <div class="upload-processing-title">Loading files</div>
                    <div class="upload-processing-subtitle">Please wait while we prepare the data.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    try:
        ingest_sidebar_uploads(uploaded_files)
    except Exception as exc:
        st.session_state.upload_feedback = str(exc)
        st.session_state.upload_feedback_kind = "error"
    finally:
        st.session_state.last_upload_signature = None
        st.session_state.upload_widget_version += 1
        st.rerun()


if "messages" not in st.session_state:
    st.session_state.messages = []
if "collection" not in st.session_state:
    st.session_state.collection = None
if "current_collection" not in st.session_state:
    st.session_state.current_collection = None
if "rag_service" not in st.session_state:
    st.session_state.rag_service = None
if "drive_feedback" not in st.session_state:
    st.session_state.drive_feedback = None
if "upload_feedback" not in st.session_state:
    st.session_state.upload_feedback = None
if "upload_feedback_kind" not in st.session_state:
    st.session_state.upload_feedback_kind = "neutral"
if "upload_widget_version" not in st.session_state:
    st.session_state.upload_widget_version = 0
if "chat_feedback" not in st.session_state:
    st.session_state.chat_feedback = None
if "last_upload_signature" not in st.session_state:
    st.session_state.last_upload_signature = None

st.set_page_config(
    page_title="RAG Treino",
    page_icon=str(LOGO_PATH),
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #ffffff;
        color: #111111;
    }
    .block-container {
        padding-top: 0.95rem;
    }
    [data-testid="stSidebarHeader"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f5f5f2 0%, #edf4ee 100%);
        border-right: 1px solid #e2e8e1;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 0rem;
        padding-left: 0.95rem;
        padding-right: 0.95rem;
    }
    [data-testid="stSidebar"] hr {
        margin: 1.15rem 0;
        border-color: #dbe3db;
    }
    .sidebar-hero {
        display: flex;
        align-items: center;
        gap: 0.95rem;
        margin-top: 0.4rem;
        margin-bottom: 1rem;
        padding: 0.95rem 1rem;
        border: 1px solid rgba(217, 225, 216, 0.92);
        border-radius: 24px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(245, 249, 246, 0.9));
        box-shadow: 0 18px 34px rgba(84, 104, 88, 0.08);
        backdrop-filter: blur(8px);
    }
    .sidebar-hero-mark {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: #ffffff;
        border: 1px solid #dfe7de;
        flex-shrink: 0;
    }
    .sidebar-hero-mark img {
        width: 22px;
        height: 22px;
        object-fit: contain;
        display: block;
    }
    .sidebar-hero-copy {
        min-width: 0;
    }
    .sidebar-brand-title {
        font-size: 1.04rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #162018;
        line-height: 1.15;
    }
    .sidebar-brand-subtitle {
        margin-top: 0.16rem;
        font-size: 0.78rem;
        color: #6a776d;
        line-height: 1.35;
    }
    .sidebar-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 0.1rem 0 0.55rem;
    }
    .sidebar-section-title {
        display: inline-flex;
        align-items: center;
        gap: 0.22rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: #59665c;
        letter-spacing: -0.01em;
    }
    .sidebar-section-caret {
        font-size: 0.9rem;
        color: #869288;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell [data-testid="stButton"] {
        margin-bottom: 0.08rem;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell .stButton > button {
        min-height: 2.5rem;
        border-radius: 14px;
        border: 1px solid transparent;
        background: transparent;
        color: #1a251d;
        box-shadow: none;
        padding: 0.5rem 0.72rem;
        justify-content: flex-start;
        font-weight: 400;
        transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell .stButton > button:hover {
        background: rgba(224, 228, 224, 0.62);
        border-color: rgba(210, 217, 211, 0.75);
        color: #111111;
        transform: none;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell .stButton > button[kind="primary"] {
        background: #dfe2df;
        border-color: transparent;
        color: #111111;
        box-shadow: none;
        font-weight: 500;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell .stButton > button[kind="primary"]:hover {
        background: #d9ddda;
        border-color: transparent;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell [data-testid="stPopover"] button {
        min-height: 2.3rem;
        width: 2.2rem;
        justify-content: center;
        padding: 0;
        border-radius: 12px;
        color: #69766d;
        border: 1px solid transparent;
        background: transparent;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell [data-testid="stPopover"] button:hover {
        color: #111111;
        background: rgba(224, 228, 224, 0.62);
        border-color: rgba(210, 217, 211, 0.75);
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell [data-testid="stPopover"] button svg {
        display: none;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chat_shell [data-testid="stPopover"] button p {
        font-size: 1.05rem;
        line-height: 1;
        margin-top: -0.08rem;
    }
    [data-testid="stSidebar"] .st-key-sidebar_files_shell [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 24px;
        border: 1px solid #dfe7de;
        background: rgba(255, 255, 255, 0.78);
        box-shadow: 0 14px 34px rgba(64, 85, 69, 0.05);
    }
    .folder-card {
        margin-bottom: 0.75rem;
        border: 1px solid #e8e8ea;
        border-radius: 18px;
        padding: 0.85rem 0.75rem 0.35rem;
        background: #ffffff;
    }
    .folder-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.8rem;
    }
    .folder-card-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: #172119;
        letter-spacing: -0.01em;
    }
    .folder-card-count {
        font-size: 0.76rem;
        color: #758177;
    }
    .root-files-shell {
        margin-bottom: 0.6rem;
    }
    .section-label {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #748171;
        margin-bottom: 0.45rem;
        font-weight: 600;
    }
    .upload-meta {
        margin-bottom: 0.85rem;
        font-size: 0.8rem;
        color: #758177;
    }
    .app-note {
        margin-bottom: 0.8rem;
        border: 1px solid #dfe7de;
        border-radius: 16px;
        padding: 0.72rem 0.9rem;
        background: rgba(255, 255, 255, 0.76);
        font-size: 0.86rem;
        color: #111111;
        box-shadow: 0 10px 24px rgba(64, 85, 69, 0.05);
    }
    .app-note.error {
        background: #fbf6f6;
        border-color: #ead4d4;
    }
    .app-note.success {
        background: #f5fbf6;
        border-color: #d6e7d8;
    }
    .pdf-file-icon {
        position: relative;
        width: 34px;
        height: 40px;
        border-radius: 10px;
        background: #dc2626;
        box-shadow: inset 0 -10px 16px rgba(0, 0, 0, 0.08), 0 8px 18px rgba(220, 38, 38, 0.18);
        margin-top: 0.1rem;
    }
    .pdf-file-corner {
        position: absolute;
        top: 0;
        right: 0;
        width: 12px;
        height: 12px;
        background: rgba(255, 255, 255, 0.9);
        clip-path: polygon(0 0, 100% 0, 100% 100%);
        border-top-right-radius: 10px;
    }
    .pdf-file-label {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 7px;
        text-align: center;
        color: #ffffff;
        font-size: 0.54rem;
        font-weight: 700;
        letter-spacing: 0.08em;
    }
    .upload-processing-shell {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        min-height: 120px;
    }
    .upload-processing-copy {
        display: flex;
        flex-direction: column;
        gap: 0.12rem;
    }
    .upload-processing-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #111111;
    }
    .upload-processing-subtitle {
        font-size: 0.8rem;
        color: #758177;
    }
    .upload-processing-spinner,
    .loading-spinner {
        width: 18px;
        height: 18px;
        border-radius: 999px;
        border: 2px solid #d4d4d8;
        border-top-color: #111111;
        animation: app-spin 0.8s linear infinite;
        flex-shrink: 0;
    }
    .chat-loading-shell {
        position: relative;
        max-width: 860px;
        margin: 6.8rem auto 0;
        min-height: 380px;
    }
    .chat-loading-overlay {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2;
        pointer-events: none;
    }
    .chat-loading-title {
        font-size: 2.15rem;
        line-height: 1.1;
        font-weight: 600;
        letter-spacing: -0.04em;
        color: #111111;
    }
    .chat-loading-dot {
        display: inline-block;
        min-width: 0.2em;
        opacity: 0;
        animation: chat-dots 1.4s infinite;
    }
    .chat-loading-dot.dot-1 {
        animation-delay: 0s;
    }
    .chat-loading-dot.dot-2 {
        animation-delay: 0.2s;
    }
    .chat-loading-dot.dot-3 {
        animation-delay: 0.4s;
    }
    .chat-loading-backdrop {
        opacity: 0.24;
        filter: grayscale(1);
        pointer-events: none;
    }
    .chat-loading-bubble {
        height: 58px;
        border-radius: 18px;
        border: 1px solid #ececec;
        background: #ffffff;
        margin-bottom: 0.9rem;
    }
    .chat-loading-bubble.bubble-wide {
        width: 68%;
    }
    .chat-loading-bubble.bubble-medium {
        width: 52%;
    }
    .chat-loading-bubble.bubble-short {
        width: 44%;
    }
    .chat-loading-bubble.align-right {
        margin-left: auto;
    }
    .chat-loading-input-bar {
        margin-top: 6rem;
        height: 56px;
        border-radius: 22px;
        border: 1px solid #ececec;
        background: #ffffff;
    }
    .chat-empty-shell {
        border: 1px solid #ececec;
        border-radius: 24px;
        padding: 1.35rem;
        background: #fbfbfb;
        margin: 1.4rem auto 1rem;
        max-width: 760px;
    }
    .chat-empty-message {
        background: #ffffff;
        border: 1px solid #f0f0f0;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.8rem;
        color: #444444;
    }
    .chat-empty-input {
        border: 1px solid #e5e5e5;
        border-radius: 999px;
        padding: 0.9rem 1rem;
        background: #ffffff;
        color: #737373;
    }
    .chat-empty-cta {
        text-align: center;
        border: 1px dashed #d4d4d8;
        border-radius: 20px;
        padding: 1.35rem 1rem;
        background: #fafafa;
        margin: 0 auto 1rem;
        max-width: 760px;
        color: #111111;
    }
    .chat-welcome {
        margin-top: 7rem;
        text-align: center;
        font-size: 2.25rem;
        line-height: 1.1;
        letter-spacing: -0.04em;
        color: #111111;
    }
    .chat-welcome-subtitle {
        text-align: center;
        margin-top: 0.55rem;
        margin-bottom: 2.5rem;
        font-size: 0.98rem;
        color: #737373;
    }
    [data-baseweb="select"] > div {
        border-radius: 16px;
        border-color: #e5e7eb !important;
        background: #ffffff !important;
        min-height: 48px;
        box-shadow: none !important;
    }
    .model-toolbar {
        max-width: 240px;
        margin-bottom: 0.85rem;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] {
        margin-bottom: 0.28rem;
    }
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 18px;
        border: 1px solid #dfe7de;
        background: rgba(255, 255, 255, 0.84);
        color: #162018;
        min-height: 2.72rem;
        padding: 0.62rem 0.9rem;
        box-shadow: 0 12px 26px rgba(64, 85, 69, 0.05);
        justify-content: flex-start;
        font-weight: 500;
        transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #ffffff;
        border-color: #ced8cf;
        color: #111111;
        transform: translateY(-1px);
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #e8ece7;
        border-color: transparent;
        color: #111111;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #e2e7e2;
        border-color: transparent;
    }
    [data-testid="stSidebar"] .stButton > button:disabled {
        background: #eff7f0;
        border-color: #cfe3d1;
        color: #132018;
        opacity: 1;
        box-shadow: none;
    }
    .st-key-sidebar_upload_shell {
        background: transparent;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        min-height: 158px;
        border-radius: 22px;
        border: 1.5px dashed #ccd7cd;
        background: linear-gradient(180deg, rgba(245, 248, 245, 0.92), rgba(255, 255, 255, 0.95));
        padding: 1rem;
        transition: border-color 0.2s ease, background 0.2s ease;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        background: #ffffff;
        border-color: #b6c3b7;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        display: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
        text-align: center;
        width: 100%;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] div {
        font-weight: 600;
        color: #111111;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] small {
        color: #758177;
    }
    @keyframes app-spin {
        to {
            transform: rotate(360deg);
        }
    }
    @keyframes chat-dots {
        0%, 20% {
            opacity: 0;
        }
        35%, 100% {
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

available_documents = list_collection_documents()
available_collections = list_available_collections(available_documents)
default_collection = [available_collections[0]] if available_collections else None
default_model = os.getenv("UFC_MODEL_NAME")
chat_sessions.initialize_chat_sessions(default_collection=default_collection, default_model=default_model)
selected_collections = sanitize_collection_selection(st.session_state.get("collection"), available_collections)

if normalize_collection_selection(st.session_state.get("collection")) != selected_collections:
    set_selected_collections(selected_collections)
elif not selected_collections and default_collection:
    set_selected_collections(default_collection)

selected_model = chat.render_model_toolbar()

with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-hero">
            <div class="sidebar-hero-mark">
                <img src="{LOGO_DATA_URI}" alt="RAG Treino" />
            </div>
            <div class="sidebar-hero-copy">
                <div class="sidebar-brand-title">RAG Treino</div>
                <div class="sidebar-brand-subtitle">Assistente local</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    upload_feedback = st.session_state.pop("upload_feedback", None)
    if upload_feedback:
        kind = st.session_state.pop("upload_feedback_kind", "neutral")
        render_notice(upload_feedback, kind=kind)

    chat_feedback = st.session_state.pop("chat_feedback", None)
    if chat_feedback:
        render_notice(chat_feedback)

    with st.container(key="sidebar_chat_shell"):
        st.markdown(
            """
            <div class="sidebar-section-header">
                <div class="sidebar-section-title">Seus chats <span class="sidebar-section-caret">&#709;</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Novo chat", key="new_chat_button", use_container_width=True):
            created, message = chat_sessions.create_new_chat(
                default_collection=default_collection,
                default_model=st.session_state.get("model_name") or default_model,
            )
            st.session_state.chat_feedback = "Novo chat criado." if created else message
            st.rerun()

        for item in chat_sessions.get_chat_sessions():
            is_active_chat = item["id"] == st.session_state.get("active_chat_id")
            title_col, actions_col = st.columns([0.9, 0.1], vertical_alignment="center")
            with title_col:
                if st.button(
                    str(item["title"]),
                    key=f"chat_session_{item['id']}",
                    use_container_width=True,
                    type="primary" if is_active_chat else "secondary",
                ):
                    chat_sessions.activate_chat(str(item["id"]))
                    st.rerun()
            with actions_col:
                with st.popover("..."):
                    rename_key = f"rename_chat_input_{item['id']}"
                    new_title = st.text_input(
                        "Renomear chat",
                        value=str(item["title"]),
                        key=rename_key,
                    )
                    if st.button("Salvar nome", key=f"rename_chat_save_{item['id']}", use_container_width=True):
                        renamed, message = chat_sessions.rename_chat(str(item["id"]), new_title)
                        st.session_state.chat_feedback = "Chat renomeado." if renamed else message
                        st.rerun()
                    if st.button("Excluir chat", key=f"delete_chat_{item['id']}", use_container_width=True):
                        deleted, message = chat_sessions.delete_chat(
                            str(item["id"]),
                            default_collection=default_collection,
                            default_model=st.session_state.get("model_name") or default_model,
                        )
                        st.session_state.chat_feedback = "Chat excluido." if deleted else message
                        st.rerun()

    st.divider()
    with st.container(key="sidebar_upload_shell"):
        render_upload_dropzone()

    st.divider()
    with st.container(key="sidebar_files_shell"):
        st.markdown('<div class="section-label">Arquivos</div>', unsafe_allow_html=True)
        if available_documents:
            for collection_name, documents in group_documents_by_collection(available_documents):
                if collection_name:
                    group_container = st.container(border=True)
                else:
                    group_container = st.container()

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
        else:
            st.caption("Nenhum arquivo.")

chat.show(selected_model)
