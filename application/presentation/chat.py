from html import escape
import time

import streamlit as st

from presentation import chat_sessions
from presentation.collection_selection import clone_collection_selection, normalize_collection_selection
from presentation import google_drive
from service.rag import RAGService

CHAT_MODELS = {
    "llama3.1:8b": "Llama 3.1 8B",
    "qwen2.5:14b": "Qwen 2.5 14B",
    "phi4:latest": "Phi-4",
}


def render_model_toolbar() -> str:
    current_model = st.session_state.get("model_name") or next(iter(CHAT_MODELS))
    if current_model not in CHAT_MODELS:
        current_model = next(iter(CHAT_MODELS))

    toolbar_col, _ = st.columns([0.24, 0.76], vertical_alignment="center")
    with toolbar_col:
        st.markdown('<div class="model-toolbar">', unsafe_allow_html=True)
        selected_model = st.selectbox(
            "Modelo",
            options=list(CHAT_MODELS),
            index=list(CHAT_MODELS).index(current_model),
            format_func=lambda model: CHAT_MODELS[model],
            key=f"chat_model_selector_{st.session_state.get('active_chat_id', 'default')}",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    return selected_model


def render_notice(message: str) -> None:
    st.markdown(
        f'<div class="app-note">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_loading_state() -> None:
    st.markdown(
        """
        <div class="chat-loading-shell">
            <div class="chat-loading-overlay">
                <div class="chat-loading-title">
                    Carregando Chat
                    <span class="chat-loading-dot dot-1">.</span>
                    <span class="chat-loading-dot dot-2">.</span>
                    <span class="chat-loading-dot dot-3">.</span>
                </div>
            </div>
            <div class="chat-loading-backdrop">
                <div class="chat-loading-bubble bubble-wide"></div>
                <div class="chat-loading-bubble bubble-short"></div>
                <div class="chat-loading-bubble bubble-medium align-right"></div>
                <div class="chat-loading-bubble bubble-wide align-right"></div>
                <div class="chat-loading-input-bar"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_locked_chat_state() -> None:
    st.markdown(
        """
        <div class="chat-empty-shell">
            <div class="chat-empty-message"><strong>Assistente</strong><br/>Conecte ou envie documentos para comecarmos.</div>
            <div class="chat-empty-message"><strong>Voce</strong><br/>Quais sao os principais pontos dos arquivos carregados?</div>
            <div class="chat-empty-input">Faca uma pergunta sobre os documentos carregados...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="chat-empty-cta">
            <strong>Nenhum documento carregado.</strong><br/>
            Arraste arquivos na lateral ou conecte o Google Drive para liberar o chat.
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        google_drive.render_connect_button(
            button_label="Conectar ao Google Drive",
            key="google_drive_connect_main",
        )


def show(selected_model: str) -> None:
    current_model = st.session_state.get("model_name") or next(iter(CHAT_MODELS))
    if selected_model != current_model:
        chat_sessions.update_active_chat_model(selected_model)
        current_model = selected_model
        if st.session_state.get("rag_service") is not None:
            st.session_state.rag_service.set_model(current_model)

    selected_collections = normalize_collection_selection(st.session_state.get("collection"))
    if not selected_collections:
        _show_locked_chat_state()
        return

    feedback = st.session_state.pop("drive_feedback", None)
    if feedback:
        render_notice(feedback)

    current_collection = normalize_collection_selection(st.session_state.get("current_collection"))
    collection_changed = current_collection != selected_collections
    model_changed = (
        "rag_service" in st.session_state
        and st.session_state.rag_service is not None
        and st.session_state.rag_service.model_name != current_model
    )
    if "rag_service" not in st.session_state or st.session_state.rag_service is None or collection_changed:
        st.session_state.rag_service = RAGService(model_name=current_model)
        loader = st.empty()
        with loader.container():
            render_loading_state()
        time.sleep(0.05)
        st.session_state.rag_service.load_collection(selected_collections)
        st.session_state.current_collection = clone_collection_selection(selected_collections)
        loader.empty()
    elif model_changed:
        loader = st.empty()
        with loader.container():
            render_loading_state()
        time.sleep(0.05)
        st.session_state.rag_service.set_model(current_model)
        loader.empty()

    if not st.session_state.messages:
        st.markdown('<div class="chat-welcome">Por onde comecamos?</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="chat-welcome-subtitle">Pergunte algo sobre os arquivos carregados.</div>',
            unsafe_allow_html=True,
        )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Faca uma pergunta sobre os documentos carregados..."):
        recent_history = st.session_state.messages[-6:]
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        chat_sessions.maybe_title_active_chat(prompt)
        chat_sessions.update_active_chat_messages(st.session_state.messages)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    answer = st.session_state.rag_service.ask_question(prompt, recent_history)
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    chat_sessions.update_active_chat_messages(st.session_state.messages)
                except Exception as exc:
                    error_msg = f"Erro ao obter resposta: {exc}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    chat_sessions.update_active_chat_messages(st.session_state.messages)
