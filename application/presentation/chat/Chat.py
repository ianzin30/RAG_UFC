"""
Chat interface for the RAG application.

This module handles:
- Model selection toolbar
- Message display and chat input
- Chat state management (loading, empty, locked states)
- Answer retrieval from the RAG service
- Source document rendering
"""

from html import escape
import logging

import streamlit as st

from presentation import chat_sessions
from presentation.shared.CollectionSelection import clone_collection_selection, normalize_collection_selection
from presentation.shared.MarkdownPreview import render_markdown_preview_link
from service.ModelOptions import coerce_llm_model_name, get_llm_model_labels, get_llm_model_names
from service.rag.RagService import RAGService


logger = logging.getLogger(__name__)
MODEL_SELECTOR_KEY = "chat_model_selector"
MODEL_SELECTOR_CHAT_KEY = "chat_model_selector_active_chat_id"
DEFAULT_RESPONSE_STATUS_MESSAGE = "Analisando sua pergunta..."

COLLECTION_PROGRESS_LABELS = {
    "collection_load_started": "Preparando coleção...",
    "collection_fingerprint_ready": "Verificando cache do índice...",
    "collection_cache_restore_started": "Restaurando índice do cache (rápido)...",
    "collection_cache_restored": "Índice pronto!",
    "collection_index_build_started": "Construindo índice do zero (pode demorar)...",
    "collection_documents_loaded": "Documentos lidos. Gerando embeddings...",
    "collection_cache_write_started": "Salvando índice em cache...",
    "collection_cache_written": "Pronto!",
}

COLLECTION_PROGRESS_LABELS.update(
    {
        "collection_load_started": "Preparando a base de arquivos...",
        "collection_fingerprint_ready": "Conferindo se os arquivos mudaram desde o ultimo indice...",
        "collection_cache_restore_started": "Cache encontrado. Restaurando o indice salvo...",
        "collection_cache_restored": "Indice restaurado do cache.",
        "collection_index_build_started": "Arquivos mudaram. Construindo um novo indice de busca...",
        "collection_documents_loaded": "Markdown carregado. Organizando documentos para busca...",
        "index_chunking_started": "Separando documentos em trechos pesquisaveis...",
        "index_chunking_progress": "Separando documentos em trechos pesquisaveis...",
        "index_embedding_started": "Gerando embeddings dos trechos...",
        "index_embedding_progress": "Gerando embeddings dos trechos...",
        "index_faiss_build_started": "Montando indice vetorial para consultas rapidas...",
        "index_faiss_build_completed": "Indice vetorial montado.",
        "collection_cache_write_started": "Salvando indice local para acelerar as proximas perguntas...",
        "collection_cache_written": "Pronto!",
    }
)


def _progress_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_collection_progress_label(payload) -> str:
    if not isinstance(payload, dict):
        return "Atualizando a base de arquivos..."

    event = str(payload.get("event") or "").strip()
    base_label = COLLECTION_PROGRESS_LABELS.get(event, "Atualizando a base de arquivos...")
    completed = _progress_int(payload.get("completed"))
    total = _progress_int(payload.get("total"))
    file_count = _progress_int(payload.get("file_count"))
    document_count = _progress_int(payload.get("document_count"))
    chunk_count = _progress_int(payload.get("chunk_count"))
    document_name = str(payload.get("document_name") or "").strip()

    if event == "collection_fingerprint_ready" and file_count:
        return f"{base_label} {file_count} arquivo(s) verificado(s)."
    if event == "collection_index_build_started" and file_count:
        return f"{base_label} {file_count} arquivo(s) serao indexados."
    if event == "collection_documents_loaded" and document_count:
        return f"{base_label} {document_count} documento(s) lido(s)."
    if event == "index_chunking_started" and total:
        return f"{base_label} 0/{total} documento(s) preparados."
    if event == "index_chunking_progress":
        detail = f" Agora: {document_name}." if document_name else ""
        if total:
            return f"{base_label} {completed}/{total} documento(s), {chunk_count} trecho(s).{detail}"
        return f"{base_label} {chunk_count} trecho(s).{detail}"
    if event == "index_embedding_started" and total:
        return f"{base_label} 0/{total} trecho(s) vetorizado(s)."
    if event == "index_embedding_progress" and total:
        return f"{base_label} {completed}/{total} trecho(s) vetorizado(s)."
    if event == "index_faiss_build_started" and chunk_count:
        return f"{base_label} {chunk_count} trecho(s) entrando no indice."
    return base_label


def normalize_response_status_payload(payload=None, *, state: str = "loading") -> dict[str, str | None]:
    if isinstance(payload, dict):
        message = str(payload.get("message") or "").strip()
        stage = str(payload.get("stage") or "").strip()
        mode = str(payload.get("mode") or "").strip() or None
        agent = str(payload.get("agent") or "").strip() or None
    else:
        message = str(payload or "").strip()
        stage = ""
        mode = None
        agent = None

    return {
        "stage": stage or "processing",
        "message": message or DEFAULT_RESPONSE_STATUS_MESSAGE,
        "mode": mode,
        "agent": agent,
        "state": str(state or "loading").strip() or "loading",
    }


def render_response_status_indicator(payload=None, *, state: str = "loading") -> None:
    status = normalize_response_status_payload(payload, state=state)
    state_name = status["state"] or "loading"
    message = escape(status["message"] or DEFAULT_RESPONSE_STATUS_MESSAGE)
    marker_html = (
        '<div class="chat-response-status-error-mark">!</div>'
        if state_name == "error"
        else '<div class="loading-spinner"></div>'
    )
    st.markdown(
        f"""
        <div class="chat-response-status chat-response-status-{escape(state_name)}">
            {marker_html}
            <div class="chat-response-status-message">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_model_toolbar() -> str:
    model_options = list(get_llm_model_names())
    model_labels = get_llm_model_labels()
    current_model = coerce_llm_model_name(st.session_state.get("model_name"))
    if st.session_state.get("model_name") != current_model:
        chat_sessions.update_active_chat_model(current_model)

    active_chat_id = str(st.session_state.get("active_chat_id") or "default")
    if st.session_state.get(MODEL_SELECTOR_CHAT_KEY) != active_chat_id:
        st.session_state[MODEL_SELECTOR_KEY] = current_model
        st.session_state[MODEL_SELECTOR_CHAT_KEY] = active_chat_id
    elif MODEL_SELECTOR_KEY not in st.session_state:
        st.session_state[MODEL_SELECTOR_KEY] = current_model
    else:
        st.session_state[MODEL_SELECTOR_KEY] = coerce_llm_model_name(
            st.session_state.get(MODEL_SELECTOR_KEY)
        )

    toolbar_col, _ = st.columns([0.24, 0.76], vertical_alignment="center")
    with toolbar_col:
        st.markdown('<div class="model-toolbar">', unsafe_allow_html=True)
        selected_model = st.selectbox(
            "Modelo",
            options=model_options,
            index=model_options.index(current_model),
            format_func=lambda model: model_labels.get(model, model),
            key=MODEL_SELECTOR_KEY,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    return coerce_llm_model_name(selected_model)


def render_notice(message: str) -> None:
    st.markdown(
        f'<div class="app-note">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_sources(sources) -> None:
    valid_sources = [source for source in list(sources or []) if isinstance(source, dict)]
    if not valid_sources:
        return

    st.markdown('<div class="source-preview-title">Fontes:</div>', unsafe_allow_html=True)
    for index, source in enumerate(valid_sources[:4], start=1):
        document_name = str(source.get("document_name", "documento")).strip() or "documento"
        chunk_kind = str(source.get("chunk_kind", "text")).strip() or "text"
        excerpt = str(source.get("excerpt", "")).strip()
        source_link = render_markdown_preview_link(
            label=document_name,
            document=source,
            prefix=f"source-{index}-{id(source)}-{document_name}",
            class_name="markdown-preview-link source-preview-link",
        )
        excerpt_html = (
            f'<span class="source-preview-excerpt"> - {escape(excerpt)}</span>'
            if excerpt
            else ""
        )
        source_row = (
            '<div class="source-preview-row">'
            f'<span class="source-preview-index">{index}.</span>'
            f"{source_link}"
            f'<span class="source-preview-kind">({escape(chunk_kind)})</span>'
            f"{excerpt_html}"
            "</div>"
        )
        st.markdown(source_row, unsafe_allow_html=True)


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
            <div class="chat-empty-cta">
                <strong>Nenhum documento carregado.</strong><br/>
                Arraste arquivos na lateral para liberar o chat.
            </div>
            """,
            unsafe_allow_html=True,
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
    """Display the main chat interface with messages and input."""
    with st.container(key="main_chat_shell"):
        # Create layout containers for messages and input
        messages_shell = st.container(key="main_chat_messages_shell")
        input_shell = st.container(key="main_chat_input_shell")

        # Update model if it changed in the toolbar
        current_model = coerce_llm_model_name(st.session_state.get("model_name"))
        if st.session_state.get("model_name") != current_model:
            chat_sessions.update_active_chat_model(current_model)
        if selected_model != current_model:
            logger.info("User selected LLM model: %s", selected_model)
            chat_sessions.update_active_chat_model(selected_model)
            current_model = selected_model
            if st.session_state.get("rag_service") is not None:
                st.session_state.rag_service.set_model(current_model)

        # Check if collections are selected
        selected_collections = normalize_collection_selection(st.session_state.get("collection"))
        if not selected_collections:
            with messages_shell:
                _show_locked_chat_state()
            return

        # Display feedback from integrations (e.g., Google Drive connection)
        feedback = st.session_state.pop("drive_feedback", None)
        if feedback:
            with messages_shell:
                render_notice(feedback)

        # Check if RAG service needs to be reloaded (collection or model changed)
        current_collection = normalize_collection_selection(st.session_state.get("current_collection"))
        collection_changed = current_collection != selected_collections
        model_changed = (
            "rag_service" in st.session_state
            and st.session_state.rag_service is not None
            and st.session_state.rag_service.model_name != current_model
        )
        # Reload RAG service if collections changed or service not initialized
        if "rag_service" not in st.session_state or st.session_state.rag_service is None or collection_changed:
            with messages_shell:
                with st.status("Preparando assistente...", expanded=True) as status:
                    def on_collection_progress(payload):
                        label = format_collection_progress_label(payload)
                        status.update(label=label, state="running")

                    rag_service = RAGService(model_name=current_model)
                    rag_service.set_collection_progress_callback(on_collection_progress)
                    try:
                        rag_service.load_collection(selected_collections)
                        status.update(label="Pronto!", state="complete", expanded=False)
                    except Exception:
                        status.update(label="Erro ao carregar a coleção.", state="error")
                        raise
                    finally:
                        rag_service.set_collection_progress_callback(None)

                    st.session_state.rag_service = rag_service
                    st.session_state.current_collection = clone_collection_selection(selected_collections)
        elif model_changed:
            with messages_shell:
                with st.status("Trocando modelo...", expanded=False) as status:
                    st.session_state.rag_service.set_model(current_model)
                    status.update(label="Modelo atualizado.", state="complete")

        # Display chat history
        with messages_shell:
            if not st.session_state.messages:
                render_empty_state()

            # Render each message with sources if it's a retrieval-based answer
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    if message.get("role") == "assistant":
                        st.empty()
                    st.write(message["content"])
                    if message.get("role") == "assistant" and message.get("route") == "retrieval":
                        render_sources(message.get("sources"))

        # Input area for user questions
        with input_shell:
            prompt = st.chat_input("Faca uma pergunta sobre os documentos carregados...")

        # Process user input and get answer from RAG service
        if prompt:
            recent_history = st.session_state.messages[-6:]
            with messages_shell:
                st.chat_message("user").write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            chat_sessions.maybe_title_active_chat(prompt)
            chat_sessions.update_active_chat_messages(st.session_state.messages)

            with messages_shell:
                with st.chat_message("assistant"):
                    rag_service = st.session_state.rag_service
                    answer_text = None
                    route = "retrieval"
                    sources = []
                    matched_documents = []
                    needs_document_refinement = False
                    resolved_question = prompt
                    response_succeeded = False

                    with st.status(DEFAULT_RESPONSE_STATUS_MESSAGE, expanded=True) as status:
                        def update_response_status(status_payload) -> None:
                            message = ""
                            if isinstance(status_payload, dict):
                                message = str(status_payload.get("message") or "").strip()
                            else:
                                message = str(status_payload or "").strip()
                            status.update(
                                label=message or DEFAULT_RESPONSE_STATUS_MESSAGE,
                                state="running",
                            )

                        if hasattr(rag_service, "set_response_status_callback"):
                            rag_service.set_response_status_callback(update_response_status)

                        try:
                            answer_trace = rag_service.ask_question_with_trace(prompt, recent_history)
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
                            status.update(label="Resposta pronta.", state="complete", expanded=False)
                            response_succeeded = True
                        except Exception:
                            logger.exception("Failed to generate chat response.")
                            answer_text = "Nao consegui gerar a resposta agora. Tente novamente em instantes."
                            status.update(label=answer_text, state="error")
                        finally:
                            if hasattr(rag_service, "set_response_status_callback"):
                                rag_service.set_response_status_callback(None)

                    if response_succeeded:
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
                    elif answer_text:
                        st.session_state.messages.append({"role": "assistant", "content": answer_text})
                        chat_sessions.update_active_chat_messages(st.session_state.messages)
