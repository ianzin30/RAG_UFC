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
from hashlib import sha256
import logging
import re

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
        message = {"planning": "Preparando a busca...", "retrieval": "Buscando evidências...", "reasoning": "Analisando as evidências...", "answer": "Redigindo a resposta...", "verification": "Conferindo a resposta...", "source_focus": "Organizando as fontes..."}.get(message, message)
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


def _chat_config():
    from service.RuntimeConfig import get_chat_config
    return get_chat_config()


def render_model_toolbar() -> str:
    model_options = list(get_llm_model_names())
    labels = get_llm_model_labels()
    current_model = st.session_state.get('model_name') or model_options[0]
    if current_model not in model_options:
        model_options.append(current_model)
        labels[current_model] = current_model + ' (perfil anterior; selecione um modelo disponível)'
    active = str(st.session_state.get('active_chat_id') or 'default')
    if st.session_state.pop('_model_backend_changed', False) or st.session_state.get(MODEL_SELECTOR_CHAT_KEY) != active or st.session_state.get(MODEL_SELECTOR_KEY) not in model_options:
        st.session_state[MODEL_SELECTOR_KEY] = current_model
        st.session_state[MODEL_SELECTOR_CHAT_KEY] = active
    selected = st.selectbox('Modelo', model_options, format_func=lambda name: labels.get(name, name),
        key=MODEL_SELECTOR_KEY, disabled=bool(st.session_state.get('turn_in_progress') or st.session_state.get('pending_turn_result')))
    return selected


def render_notice(message: str) -> None:
    st.markdown(
        f'<div class="app-note">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _valid_focus_spans(source: dict, excerpt: str) -> list[dict]:
    spans = []
    for span in list(source.get("focus_spans") or []):
        if not isinstance(span, dict):
            continue
        try:
            start, end = int(span.get("start")), int(span.get("end"))
        except (TypeError, ValueError):
            continue
        if 0 <= start < end <= len(excerpt) and span.get("quote") == excerpt[start:end]:
            spans.append({**span, "start": start, "end": end})
    return sorted(spans, key=lambda item: (item["start"], item["end"]))


def _sentence_context(text: str, start: int, end: int) -> tuple[str, int, int]:
    before = text[:start]
    after = text[end:]
    previous = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
    next_match = re.search(r"[.!?](?:\s|$)", after)
    context_start = previous + 1 if previous >= 0 else 0
    context_end = end + next_match.end() if next_match else len(text)
    context_end = min(len(text), context_end)
    raw_context = text[context_start:context_end]
    left_trim = len(raw_context) - len(raw_context.lstrip())
    right_trim = len(raw_context) - len(raw_context.rstrip())
    return (
        raw_context.strip(),
        context_start + left_trim,
        context_end - right_trim,
    )


def _highlight(text: str, start: int, end: int) -> str:
    return (
        escape(text[:start])
        + '<mark class="source-focus-highlight">'
        + escape(text[start:end])
        + "</mark>"
        + escape(text[end:])
    )


def render_sources(sources, *, turn_key="legacy", citation_label="Fonte citada") -> None:
    from service.rag.v2.Sources import normalize_presentation
    valid_sources = normalize_presentation({"sources": sources})["sources"]
    if not valid_sources:
        return

    st.markdown('<div class="source-preview-title">Fontes:</div>', unsafe_allow_html=True)
    for index, source in enumerate(valid_sources, start=1):
        document_name = str(source.get("document_name", "documento")).strip() or "documento"
        chunk_kind = str(source.get("chunk_kind", "text")).strip() or "text"
        excerpt = str(source.get("excerpt", ""))
        section = str(source.get("section_title") or "").strip()
        if section:
            chunk_kind = f"{chunk_kind} · {section}"
        pages = sorted({str(item.get("page_no")) for item in source.get("provenance", []) if item.get("page_no") is not None})
        if pages:
            chunk_kind += " · p. " + ", ".join(pages)
        source_link = render_markdown_preview_link(
            label=document_name,
            document=source,
            prefix=f"source-{turn_key}-{source.get('source_id', index)}",
            class_name="markdown-preview-link source-preview-link",
        )
        evidence_id = str(source.get("evidence_id") or index)
        spans = _valid_focus_spans(source, excerpt)
        if spans:
            focused = spans[0]
            maximum = _chat_config().excerpt_chars
            start = max(0, focused['start'] - maximum // 3)
            end = min(len(excerpt), start + maximum)
            preview = _highlight(excerpt[start:end], focused['start'] - start, focused['end'] - start) if focused['end'] <= end else escape(excerpt[start:end])
            preview_html = ('… ' if start else '') + preview + (' …' if end < len(excerpt) else '')
            if len(spans) > 1:
                preview_html += f' <span class="source-focus-more">+{len(spans) - 1}</span>'
        else:
            preview_html = escape(excerpt[:_chat_config().excerpt_chars]) + (" …" if len(excerpt) > _chat_config().excerpt_chars else "")
        source_key = sha256(
            f"{turn_key}|{source.get('source_id')}".encode()
        ).hexdigest()[:12]
        source_row = (
            '<div class="source-preview-row source-preview-header">'
            f'<span class="source-preview-index">{escape(evidence_id)}.</span>'
            f"{source_link}"
            f'<span class="source-preview-kind">{escape(citation_label)}</span>'
            "</div>"
        )
        st.markdown(source_row, unsafe_allow_html=True)
        if excerpt:
            st.markdown(
                f'<div class="source-preview-compact">{preview_html}</div>',
                unsafe_allow_html=True,
            )
        with st.expander("Expandir fonte", expanded=False):
            st.markdown(
                f'<div class="source-preview-metadata">{escape(chunk_kind)}</div>',
                unsafe_allow_html=True,
            )
            if spans:
                for span in spans:
                    context, context_start, _ = _sentence_context(
                        excerpt, span["start"], span["end"]
                    )
                    start = span["start"] - context_start
                    end = span["end"] - context_start
                    claim_ids = ", ".join(str(value) for value in span.get("claim_ids", []))
                    if claim_ids:
                        st.caption(f"Sustenta: {claim_ids}")
                    st.markdown(
                        f'<div class="source-focus-context">{_highlight(context, start, end)}</div>',
                        unsafe_allow_html=True,
                    )
            elif excerpt:
                st.markdown(
                    f'<div class="source-focus-context">{escape(excerpt[:_chat_config().excerpt_chars])}</div>',
                    unsafe_allow_html=True,
                )
            if excerpt and st.checkbox("Ver excerto completo", key=f"source-full-{source_key}"):
                st.text(excerpt)


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


def _render_message(message, key):
    from service.rag.v2.Sources import normalize_presentation, displayed_sources
    message = normalize_presentation(message)
    with st.chat_message(message.get('role', 'assistant')):
        st.write(message.get('content', ''))
        legacy = message.get('role') == 'assistant' and not message.get('turn_id')
        if legacy:
            st.caption('Resposta legada — modelo e execução não registrados.')
        for warning in message.get('source_warnings', []): st.warning(warning)
        if message.get('role') == 'assistant' and message.get('route') == 'retrieval':
            render_sources(displayed_sources(message), turn_key=message.get('turn_id') or key, citation_label='Fonte histórica' if legacy else 'Fonte citada')
        if message.get('role') == 'assistant' and message.get('execution'):
            with st.expander('Detalhes da execução'):
                st.json({'turn_id': message.get('turn_id'), 'model': message.get('profile', {}).get('llm', {}).get('model'),
                    'collection': message.get('collection'), **message['execution']})


def _ui_progress_callback(callback):
    """Bind only the synchronous callback to the originating Streamlit session."""
    import threading
    from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
    from streamlit.runtime.scriptrunner_utils.script_run_context import SCRIPT_RUN_CONTEXT_ATTR_NAME
    context = get_script_run_ctx(suppress_warning=True)
    def deliver(payload):
        thread = threading.current_thread()
        previous = get_script_run_ctx(suppress_warning=True)
        if context is None:
            return
        if previous is not context:
            add_script_run_ctx(thread, context)
        try:
            callback(payload)
        finally:
            if previous is not context:
                setattr(thread, SCRIPT_RUN_CONTEXT_ATTR_NAME, previous)
    return deliver


def show(selected_model: str) -> None:
    from copy import deepcopy
    from service.RuntimeConfig import application_profile
    from presentation.chat_sessions import State, Storage
    from . import Turns

    st.caption('RAG V2 — integração para testes')
    if st.session_state.get('storage_error'):
        st.error(st.session_state.storage_error)
        return
    active = chat_sessions.get_active_chat()
    if active is None:
        st.error('Conversa indisponível. Atualize o histórico.')
        return
    if selected_model != active.get('model_name'):
        result = chat_sessions.update_active_chat_model(selected_model)
        if result and not result.ok:
            st.error(result.error)
        active = chat_sessions.get_active_chat()
    model = active.get('model_name')
    selected_collections = normalize_collection_selection(active.get('collection'))
    turns = {t.get('turn_id'): t for t in active.get('turns', [])}
    for index, message in enumerate(st.session_state.get('messages', [])):
        _render_message(message, f"{active['id']}-{index}")
        turn = turns.get(message.get('turn_id'), {})
        if message.get('role') == 'user' and turn.get('state') in {'failed', 'unknown'}:
            st.warning(turn.get('error') or 'Esta pergunta não foi concluída. Nenhuma repetição automática foi feita.')
            with st.expander('Detalhes da falha'):
                st.json({'turn_id': turn.get('turn_id'), **dict(turn.get('execution') or {})})

    pending = st.session_state.get('pending_turn_result')
    if pending:
        context, result = pending
        if result.message: _render_message(result.message, context.turn_id)
        elif result.error: st.warning(result.error)
        st.error('Resposta não salva. Mantenha esta aba aberta e tente salvar novamente.')
        if st.button('Tentar salvar novamente', key='retry_save_turn'):
            saved = Turns.finish(context, result)
            if saved.ok:
                st.session_state.pop('pending_turn_result', None)
                State.adopt(saved.state)
                st.rerun()
            else: st.error(saved.error)
        return

    busy = any(t.get('state') == 'running' for t in active.get('turns', []))
    if busy:
        st.info('Esta conversa tem uma pergunta em execução. Aguarde; atualizar não repete a chamada.')
        if st.button('Atualizar histórico', key='refresh_chat'): st.rerun()
        st.chat_input('Aguarde a conclusão da pergunta.', disabled=True)
        return
    if not selected_collections:
        _show_locked_chat_state()
        return
    if model not in get_llm_model_names():
        st.warning('Esta conversa usa um modelo anterior. Selecione um modelo disponível para continuar; as respostas antigas serão preservadas.')
        return
    try:
        profile = application_profile()
        profile['llm']['model'] = model
        fingerprint = profile['fingerprint']
        old = st.session_state.get('app_profile_fingerprint')
        if old and old != fingerprint:
            st.error('A configuração ou o código mudou. Reinicie o Streamlit antes de enviar outra pergunta.')
            return
        st.session_state.app_profile_fingerprint = fingerprint
        st.caption(f"Modelo: {model} · Coleção: {', '.join(selected_collections)} · Contexto documental: {profile['retrieval']['context_tokens']} tokens")
        identity = (fingerprint, model, tuple(selected_collections))
        if st.session_state.get('rag_identity') != identity or st.session_state.get('rag_service') is None:
            with st.status('Preparando assistente...', expanded=True) as status:
                service = RAGService(model_name=model)
                service.set_collection_progress_callback(lambda payload: status.update(label=format_collection_progress_label(payload)))
                try:
                    if hasattr(service, "check_model_ready"): service.check_model_ready()
                    service.load_collection(selected_collections)
                    if hasattr(service, 'check_ready'): service.check_ready()
                finally:
                    service.set_collection_progress_callback(None)
                status.update(label='Modelo e recuperação disponíveis.', state='complete', expanded=False)
            st.session_state.rag_service = service
            st.session_state.index_identity = deepcopy(getattr(getattr(service, '_v2', None), 'load_diagnostics', {}))
            st.session_state.rag_identity = identity
            st.session_state.current_collection = clone_collection_selection(selected_collections)
    except Exception as exc:
        from llm_client import LLMError
        from service.RuntimeConfig import RuntimeConfigurationError
        from service.rag.v2.Providers import ProviderError
        safe = str(exc) if isinstance(exc, (LLMError, ProviderError, RuntimeConfigurationError)) else 'Não foi possível preparar o modelo ou a coleção. Confira o índice, o serviço de embeddings e a configuração.'
        st.error(safe)
        st.session_state.rag_service = None
        st.chat_input('Assistente indisponível.', disabled=True)
        return

    if not st.session_state.messages: render_empty_state()
    # Reserve the new turn above the composer before accepting a submission.
    turn_output = st.container()
    prompt = st.chat_input('Faça uma pergunta sobre os documentos carregados...')
    if prompt:
        with turn_output:
            profile['index'] = deepcopy(st.session_state.get('index_identity', {}))
            context, saved = Turns.begin(active['id'], prompt, selected_collections, profile, expected_revision=active.get('revision', 0))
            if context is None:
                st.error(saved.error)
                return
            State.adopt(saved.state)
            st.session_state.turn_in_progress = context.turn_id
            service = st.session_state.rag_service
            with st.chat_message('user'): st.write(prompt)
            result = None
            try:
                progress = st.empty()
                with progress.container(), st.status('Gerando resposta...', expanded=True) as status:
                    if hasattr(service, 'set_response_status_callback'):
                        service.set_response_status_callback(_ui_progress_callback(lambda payload: status.update(label=normalize_response_status_payload(payload)['message'])))
                    result = Turns.run(service, context)
                progress.empty()
                # Persist before rendering sources: a bad widget cannot lose a completed answer.
                saved = Turns.finish(context, result)
                if saved.ok:
                    State.adopt(saved.state)
                    if result.message:
                        if st.session_state.get('active_chat_id') == context.chat_id:
                            _render_message(result.message, context.turn_id)
                        else:
                            st.info('Resposta salva na conversa de origem.')
                        st.caption('Resposta salva.')
                    else: st.warning(result.error)
                else:
                    st.session_state.pending_turn_result = (context, result)
                    if result.message: _render_message(result.message, context.turn_id)
                    st.error('Resposta não salva. Use “Tentar salvar novamente”; a geração não será repetida.')
                    st.rerun()
            finally:
                progress.empty()
                if hasattr(service, 'set_response_status_callback'): service.set_response_status_callback(None)
                st.session_state.pop('turn_in_progress', None)
                if result is None:
                    interrupted = Turns.TurnResult('unknown', error='Execução interrompida; resultado desconhecido. Nenhuma chamada será repetida automaticamente.')
                    persisted = Turns.finish(context, interrupted)
                    if not persisted.ok: Storage._ACTIVE_TURNS.discard(context.turn_id)
