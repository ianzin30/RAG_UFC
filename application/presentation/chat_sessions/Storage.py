"""Transactional shared JSON store. Render never writes a session snapshot."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid

import streamlit as st
from .Constants import CHAT_STORAGE_PATH

_CHAT_STORAGE_LOCK = threading.RLock()
PROCESS_TOKEN = uuid.uuid4().hex
_ACTIVE_TURNS: set[str] = set()


class StorageError(RuntimeError):
    pass


class Conflict(StorageError):
    pass


@dataclass
class PersistenceResult:
    status: str
    state: dict | None = None
    error: str | None = None

    @property
    def ok(self):
        return self.status == 'saved'


def _path():
    from .Constants import PROJECT_ROOT
    default = PROJECT_ROOT / 'data/local_chat_sessions.json'
    if CHAT_STORAGE_PATH != default:
        return Path(CHAT_STORAGE_PATH)
    from service.RuntimeConfig import get_chat_config
    return Path(PROJECT_ROOT / get_chat_config().history_path)


def _empty_state():
    return {'schema_version': 2, 'revision': 0, 'chat_sessions': [], 'next_chat_session_id': 1}


def _owner_alive(turn):
    if turn.get('owner_pid') == os.getpid():
        return turn.get('owner_token') == PROCESS_TOKEN and turn.get('turn_id') in _ACTIVE_TURNS
    try:
        pid = int(turn.get('owner_pid', 0))
        if pid <= 0: return False
        os.kill(pid, 0)
        return True
    except (ValueError, TypeError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def _read(path):
    if not path.exists():
        return _empty_state()
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict) or not isinstance(state.get('chat_sessions'), list):
            raise ValueError()
        if state.get('schema_version', 1) not in (1, 2):
            raise ValueError()
        for chat in state['chat_sessions']:
            if not isinstance(chat, dict) or not isinstance(chat.get('id'), str) or not isinstance(chat.get('messages', []), list):
                raise ValueError()
            chat.setdefault('revision', 0)
            chat.setdefault('turns', [])
            if not isinstance(chat['turns'], list):
                raise ValueError()
            for turn in chat['turns']:
                if not isinstance(turn, dict) or not isinstance(turn.get('turn_id'), str) or turn.get('state') not in {'running', 'answered', 'partial', 'casual', 'abstained', 'clarification_required', 'unknown', 'failed'}:
                    raise ValueError()
                if turn.get('state') == 'running' and not _owner_alive(turn):
                    turn.update(state='unknown', error='Resultado desconhecido após interrupção. Nenhuma chamada foi repetida.')
        state.setdefault('revision', 0)
        state.setdefault('next_chat_session_id', 1)
        if not isinstance(state['revision'], int) or not isinstance(state['next_chat_session_id'], int):
            raise ValueError()
        return state
    except (OSError, ValueError, TypeError, KeyError):
        raise StorageError('Não foi possível ler o histórico. Preserve o arquivo e restaure um backup antes de continuar; nenhum dado foi substituído.') from None


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _CHAT_STORAGE_LOCK:
        with path.with_name(path.name + '.lock').open('a') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _write(path, state):
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        if old.get('schema_version', 1) == 1:
            backup = path.with_name(path.name + '.v1.bak')
            if not backup.exists():
                with backup.open('x', encoding='utf-8') as f:
                    f.write(path.read_text(encoding='utf-8'))
                    f.flush()
                    os.fsync(f.fileno())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as f:
            temporary = f.name
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_persisted_chat_state(user_id=None):
    _ = user_id
    path = _path()
    if not path.exists():
        return _empty_state()
    try:
        with _locked(path):
            return _read(path)
    except StorageError:
        raise
    except OSError:
        raise StorageError('Não foi possível acessar o histórico. Confira as permissões; nenhum dado foi substituído.') from None


def mutate(operation):
    """Read, validate and mutate the latest state under one interprocess lock."""
    try:
        path = _path()
        with _locked(path):
            state = _read(path)
            updated = deepcopy(state)
            operation(updated)
            updated['schema_version'] = 2
            updated['revision'] = state['revision'] + 1
            _write(path, updated)
        return PersistenceResult('saved', updated)
    except Conflict as exc:
        return PersistenceResult('conflict', error=str(exc))
    except StorageError as exc:
        return PersistenceResult('failed', error=str(exc))
    except Exception:
        return PersistenceResult('failed', error='Não foi possível salvar o histórico. Confira espaço e permissão de escrita.')


def find_chat(state, chat_id):
    for chat in state['chat_sessions']:
        if chat['id'] == chat_id:
            return chat
    raise Conflict('A conversa não existe mais. Atualize o histórico.')


def check_available(chat):
    if any(t.get('state') == 'running' for t in chat.get('turns', [])):
        raise Conflict('Esta conversa já tem uma pergunta em execução em outra aba.')


def persist_chat_state(get_chat_sessions, user_id=None):
    """Compatibility only: compare-and-swap prevents old callers overwriting newer data."""
    _ = user_id
    expected = st.session_state.get('_storage_revision', 0)
    def operation(state):
        if state['revision'] != expected:
            raise Conflict('O histórico mudou em outra aba. Atualize antes de salvar.')
        state['chat_sessions'] = deepcopy(get_chat_sessions())
        state['next_chat_session_id'] = int(st.session_state.get('next_chat_session_id', 1))
    result = mutate(operation)
    if result.ok:
        st.session_state['_storage_revision'] = result.state['revision']
    return result
