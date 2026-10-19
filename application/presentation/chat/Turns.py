"""Turn coordination independent of rendering. One accepted submission = one flow."""
from copy import deepcopy
from dataclasses import dataclass
import logging
import os
import time
import uuid

from presentation.chat_sessions import Storage
from presentation.chat_sessions.Normalization import build_timestamp_now, truncate_title
from service.RuntimeConfig import get_chat_config
from service.rag.v2.Sources import normalize_presentation, preserve_v2_fields

logger = logging.getLogger('ragufc.turns')


@dataclass(frozen=True)
class TurnContext:
    turn_id: str
    chat_id: str
    question: str
    history: list
    collection: list
    profile: dict


@dataclass
class TurnResult:
    state: str
    message: dict | None = None
    error: str | None = None
    metadata: dict | None = None


def semantic_history(messages):
    """Only completed pairs and compatible legacy dialogue enter the prompt."""
    complete = {m.get('turn_id') for m in messages if m.get('role') == 'assistant' and m.get('turn_id') and m.get('turn_state') in {'answered', 'partial', 'casual', 'abstained', 'clarification_required'}}
    known_legacy_error = 'Nao consegui gerar a resposta agora. Tente novamente em instantes.'
    history = []
    for index, message in enumerate(messages):
        if message.get('turn_id'):
            if message['turn_id'] not in complete: continue
        elif message.get('content') == known_legacy_error:
            continue
        elif message.get('role') == 'user':
            following = messages[index + 1] if index + 1 < len(messages) else {}
            if following.get('turn_id') or following.get('role') != 'assistant' or following.get('content') == known_legacy_error or not str(following.get('content') or '').strip():
                continue
        elif message.get('role') == 'assistant':
            previous = messages[index - 1] if index else {}
            if previous.get('turn_id') or previous.get('role') != 'user': continue
        if message.get('role') in {'user', 'assistant'} and str(message.get('content') or '').strip():
            history.append({'role': message['role'], 'content': message['content']})
    limit = get_chat_config().history_messages
    return history[-limit:] if limit else []


def begin(chat_id, question, collection, profile, *, expected_revision, turn_id=None):
    identifier = turn_id or uuid.uuid4().hex
    context = None
    with Storage._CHAT_STORAGE_LOCK:
        if identifier in Storage._ACTIVE_TURNS:
            return None, Storage.PersistenceResult("conflict", error="Esta submissão já está em execução.")
        Storage._ACTIVE_TURNS.add(identifier)
    def operation(state):
        nonlocal context
        chat = Storage.find_chat(state, chat_id)
        if any(t.get('turn_id') == identifier for t in chat.get('turns', [])):
            raise Storage.Conflict('Esta submissão já foi registrada. Nenhuma nova execução foi iniciada.')
        Storage.check_available(chat)
        if chat.get('revision', 0) != expected_revision:
            raise Storage.Conflict('A conversa mudou em outra aba. Atualize e envie novamente.')
        context = TurnContext(identifier, chat_id, question, semantic_history(chat['messages']), deepcopy(collection), deepcopy(profile))
        chat.setdefault('turns', []).append({'turn_id': identifier, 'state': 'running', 'owner_pid': os.getpid(),
            'owner_token': Storage.PROCESS_TOKEN, 'profile': deepcopy(profile), 'collection': deepcopy(collection), 'created_at': build_timestamp_now()})
        chat['messages'].append({'role': 'user', 'content': question, 'turn_id': identifier, 'turn_state': 'running'})
        if str(chat.get('title', '')).startswith(get_chat_config().default_title): chat['title'] = truncate_title(question)
        chat['revision'] = chat.get('revision', 0) + 1
        chat['updated_at'] = build_timestamp_now()
    saved = Storage.mutate(operation)
    if not saved.ok:
        Storage._ACTIVE_TURNS.discard(identifier)
        return None, saved
    return context, saved


def run(service, context):
    started = time.perf_counter()
    try:
        trace = service.ask_question_with_trace(context.question, deepcopy(context.history))
        if not isinstance(trace, dict) or not isinstance(trace.get('answer_text'), str) or not trace['answer_text'].strip():
            raise ValueError('empty_response')
        state = trace.get('status', 'answered')
        if state not in {'answered', 'partial', 'casual', 'abstained', 'clarification_required', 'completed'}:
            raise ValueError('invalid_response_state')
        state = 'answered' if state == 'completed' else state
        message = {'role': 'assistant', 'content': trace['answer_text'].strip(), 'route': trace.get('route', 'retrieval'),
            'resolved_question': trace.get('resolved_question', context.question), 'turn_id': context.turn_id,
            'turn_state': state, 'profile': deepcopy(context.profile), 'collection': deepcopy(context.collection),
            'sources': trace.get('sources', [])}
        preserve_v2_fields(trace, message)
        metadata = safe_calls(trace.get('provider_calls', []))
        message['execution'] = metadata
        return TurnResult(state, normalize_presentation(message), metadata=metadata)
    except Exception as exc:
        from llm_client import LLMError, LLMConnectionError
        from service.rag.v2.Providers import ProviderError
        unknown = isinstance(exc, (TimeoutError, ConnectionError, LLMConnectionError))
        error = str(exc) if isinstance(exc, (LLMError, ProviderError)) else (
            'A resposta recebida estava vazia ou inválida.' if isinstance(exc, ValueError) else 'Não foi possível concluir a resposta. Confira os serviços e envie uma nova pergunta quando estiverem disponíveis.')
        if getattr(exc, 'code', None) == 'input_budget_exceeded':
            error = exc.public_message
        if isinstance(exc, ProviderError) and str(exc).startswith('Invalid '):
            error = 'A saída estruturada do modelo não passou na validação após o reparo permitido.'
        if unknown: error = 'Resultado remoto desconhecido. A pergunta não será repetida automaticamente. Confira a conexão antes de fazer um novo envio.'
        registry = getattr(getattr(service, '_v2', None), 'providers', None)
        import traceback
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        metadata = safe_calls(getattr(registry, 'calls', []))
        metadata['error_type'] = type(exc).__name__
        metadata['error_origin'] = [{'file': str(Path(f.filename).relative_to(root)), 'line': f.lineno, 'function': f.name}
            for f in traceback.extract_tb(exc.__traceback__) if Path(f.filename).is_relative_to(root) and '.venv' not in Path(f.filename).parts]
        return TurnResult('unknown' if unknown else 'failed', error=error, metadata=metadata)
    finally:
        logger.info('turn_finished turn_id=%s chat_id=%s seconds=%.3f', context.turn_id, context.chat_id, time.perf_counter() - started)


def safe_calls(calls):
    safe = []
    for c in calls if isinstance(calls, list) else []:
        if not isinstance(c, dict): continue
        safe.append({k: deepcopy(c[k]) for k in ('role', 'status', 'provider', 'logical_model', 'physical_model', 'endpoint', 'latency_seconds', 'structured_attempt', 'sent_parameters', 'observed', 'server_timings') if k in c})
    return {'provider_calls': safe, 'logical_calls': len(safe),
        'transport_attempts': sum((c.get('server_timings') or {}).get('transport_attempts', 1) for c in safe)}


def finish(context, result):
    def operation(state):
        chat = Storage.find_chat(state, context.chat_id)
        turn = next((t for t in chat.get('turns', []) if t['turn_id'] == context.turn_id), None)
        if turn is None: raise Storage.Conflict('Turno de origem não encontrado; resposta preservada somente nesta sessão.')
        if turn.get('state') in {'answered', 'partial', 'casual', 'abstained', 'clarification_required', 'failed'}:
            return  # Retry storage is idempotent, never append a second response.
        turn.update(state=result.state, error=result.error, execution=result.metadata, finished_at=build_timestamp_now())
        for message in chat['messages']:
            if message.get('turn_id') == context.turn_id: message['turn_state'] = result.state
        if result.message and not any(m.get('turn_id') == context.turn_id and m.get('role') == 'assistant' for m in chat['messages']):
            chat['messages'].append(deepcopy(result.message))
        chat['revision'] = chat.get('revision', 0) + 1
        chat['updated_at'] = build_timestamp_now()
    saved = Storage.mutate(operation)
    if saved.ok: Storage._ACTIVE_TURNS.discard(context.turn_id)
    return saved
