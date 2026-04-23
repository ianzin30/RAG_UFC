from html import escape
import time

import streamlit as st

from presentation import chat_sessions
from presentation.shared.CollectionSelection import clone_collection_selection, normalize_collection_selection
from presentation.integrations import GoogleDrive as google_drive
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


def render_sources(sources) -> None:
    valid_sources = [source for source in list(sources or []) if isinstance(source, dict)]
    if not valid_sources:
        return

    lines = ["**Fontes:**"]
    for index, source in enumerate(valid_sources[:4], start=1):
        document_name = str(source.get("document_name", "documento")).strip() or "documento"
        chunk_kind = str(source.get("chunk_kind", "text")).strip() or "text"
        excerpt = str(source.get("excerpt", "")).strip()
        if excerpt:
            lines.append(f"{index}. `{document_name}` ({chunk_kind}) - {excerpt}")
        else:
            lines.append(f"{index}. `{document_name}` ({chunk_kind})")

    st.markdown("\n".join(lines))


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


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="chat-empty-state-shell">
            <div class="chat-empty-state-copy">
                <div class="chat-welcome">Por onde comecamos?</div>
                <div class="chat-welcome-subtitle">Pergunte algo sobre os arquivos carregados.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_locked_chat_state() -> None:
    with st.container(key="main_chat_locked_state_shell"):
        st.markdown(
            """
            <div class="chat-empty-state-copy chat-empty-state-copy-locked">
                <div class="chat-empty-message"><strong>Assistente</strong><br/>Conecte ou envie documentos para comecarmos.</div>
                <div class="chat-empty-message"><strong>Voce</strong><br/>Quais sao os principais pontos dos arquivos carregados?</div>
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
            with st.container(key="main_drive_connect_shell"):
                google_drive.render_connect_button(
                    button_label="Conectar ao Google Drive",
                    key="google_drive_connect_main",
                )


def render_locked_chat_input_placeholder() -> None:
    st.markdown(
        """
        <div class="chat-empty-input chat-empty-input-bottom">
            Faca uma pergunta sobre os documentos carregados...
        </div>
        """,
        unsafe_allow_html=True,
    )


def show(selected_model: str) -> None:
    with st.container(key="main_chat_shell"):
        messages_shell = st.container(key="main_chat_messages_shell")
        input_shell = st.container(key="main_chat_input_shell")

        current_model = st.session_state.get("model_name") or next(iter(CHAT_MODELS))
        if selected_model != current_model:
            chat_sessions.update_active_chat_model(selected_model)
            current_model = selected_model
            if st.session_state.get("rag_service") is not None:
                st.session_state.rag_service.set_model(current_model)

        selected_collections = normalize_collection_selection(st.session_state.get("collection"))
        if not selected_collections:
            with messages_shell:
                _show_locked_chat_state()
            with input_shell:
                render_locked_chat_input_placeholder()
            return

        feedback = st.session_state.pop("drive_feedback", None)
        if feedback:
            with messages_shell:
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
            loader = messages_shell.empty()
            with loader.container():
                render_loading_state()
            time.sleep(0.05)
            st.session_state.rag_service.load_collection(selected_collections)
            st.session_state.current_collection = clone_collection_selection(selected_collections)
            loader.empty()
        elif model_changed:
            loader = messages_shell.empty()
            with loader.container():
                render_loading_state()
            time.sleep(0.05)
            st.session_state.rag_service.set_model(current_model)
            loader.empty()

        with messages_shell:
            if not st.session_state.messages:
                render_empty_state()

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    if message.get("role") == "assistant" and message.get("route") == "retrieval":
                        render_sources(message.get("sources"))

        with input_shell:
            prompt = st.chat_input("Faca uma pergunta sobre os documentos carregados...")

        if prompt:
            recent_history = st.session_state.messages[-6:]
            with messages_shell:
                st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            chat_sessions.maybe_title_active_chat(prompt)
            chat_sessions.update_active_chat_messages(st.session_state.messages)

            with messages_shell:
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        try:
                            answer_trace = st.session_state.rag_service.ask_question_with_trace(prompt, recent_history)
                            answer_text = str(answer_trace.get("answer_text", "")).strip()
                            route = str(answer_trace.get("route", "")).strip() or "retrieval"
                            resolved_question = str(answer_trace.get("resolved_question", prompt)).strip() or prompt
                            matched_documents = [
                                str(item).strip()
                                for item in list(answer_trace.get("matched_documents") or [])
                                if str(item).strip()
                            ]
                            needs_document_refinement = bool(answer_trace.get("needs_document_refinement"))
                            sources = answer_trace.get("sources") or []

                            st.write(answer_text)
                            if route == "retrieval":
                                render_sources(sources)

                            assistant_message = {
                                "role": "assistant",
                                "content": answer_text,
                                "route": route,
                                "resolved_question": resolved_question,
                            }
                            if matched_documents:
                                assistant_message["matched_documents"] = matched_documents
                            if needs_document_refinement:
                                assistant_message["needs_document_refinement"] = True
                            if sources:
                                assistant_message["sources"] = sources

                            st.session_state.messages.append(assistant_message)
                            chat_sessions.update_active_chat_messages(st.session_state.messages)
                        except Exception as exc:
                            error_msg = f"Erro ao obter resposta: {exc}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                            chat_sessions.update_active_chat_messages(st.session_state.messages)
