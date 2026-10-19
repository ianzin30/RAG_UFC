"""Browser selection is local; conversation mutations belong to the repository."""
from copy import deepcopy
import streamlit as st
from presentation.shared.CollectionSelection import clone_collection_selection
from .Normalization import build_default_title, build_timestamp_now, clone_messages
from .Storage import load_persisted_chat_state, mutate, find_chat, check_available, StorageError


def create_session(collection=None, model_name=None):
    import uuid
    timestamp = build_timestamp_now()
    return {'id': 'chat_' + uuid.uuid4().hex, 'title': build_default_title(),
            'collection': clone_collection_selection(collection), 'model_name': model_name,
            'messages': [], 'turns': [], 'revision': 0, 'created_at': timestamp, 'updated_at': timestamp}


def get_chat_sessions():
    return st.session_state.setdefault('chat_sessions', [])


def get_active_chat():
    return next((c for c in get_chat_sessions() if c['id'] == st.session_state.get('active_chat_id')), None)


def adopt(state):
    st.session_state.chat_sessions = deepcopy(state['chat_sessions'])
    st.session_state.next_chat_session_id = state['next_chat_session_id']
    st.session_state['_storage_revision'] = state['revision']
    if not get_active_chat():
        st.session_state.active_chat_id = state['chat_sessions'][0]['id'] if state['chat_sessions'] else None
    sync_active_chat_to_state()


def sync_active_chat_to_state():
    chat = get_active_chat()
    previous = (st.session_state.get('collection'), st.session_state.get('model_name'))
    st.session_state.messages = clone_messages(chat.get('messages', []) if chat else [])
    st.session_state.collection = clone_collection_selection(chat.get('collection')) if chat else None
    st.session_state.model_name = chat.get('model_name') if chat else None
    if previous != (st.session_state.collection, st.session_state.model_name):
        st.session_state.current_collection = None
        st.session_state.rag_service = None
        if previous[1] != st.session_state.model_name:
            st.session_state["_model_backend_changed"] = True


def change_chat(operation, chat_id=None, *, expected_revision=None):
    target = chat_id or st.session_state.get('active_chat_id')
    def apply(state):
        chat = find_chat(state, target)
        check_available(chat)
        if expected_revision is not None and chat.get('revision', 0) != expected_revision:
            from .Storage import Conflict
            raise Conflict('A conversa mudou em outra aba. Atualize antes de alterar as mensagens.')
        operation(chat)
        chat['revision'] = chat.get('revision', 0) + 1
        chat['updated_at'] = build_timestamp_now()
    result = mutate(apply)
    if result.ok:
        adopt(result.state)
    else:
        st.session_state.chat_feedback = result.error
    return result


def save_active_chat(messages=None, collection=None, title=None, model_name=None, *, touch_recency=True):
    # Compatibility for explicit updates only. Never copy all UI fields implicitly.
    def update(chat):
        if messages is not None: chat['messages'] = clone_messages(messages)
        if collection is not None: chat['collection'] = clone_collection_selection(collection)
        if title is not None: chat['title'] = title
        if model_name is not None: chat['model_name'] = model_name
    if all(v is None for v in (messages, collection, title, model_name)):
        return None
    current = get_active_chat()
    return change_chat(update, expected_revision=current.get('revision', 0) if messages is not None and current else None)


def initialize_chat_sessions(user_id=None, default_collection=None, default_model=None):
    _ = user_id
    try:
        state = load_persisted_chat_state()
        if not state['chat_sessions']:
            def create(current):
                if not current['chat_sessions']:
                    chat = create_session(default_collection, default_model)
                    current['chat_sessions'].append(chat)
            result = mutate(create)
            if not result.ok:
                raise StorageError(result.error)
            state = result.state
        st.session_state.pop('storage_error', None)
        adopt(state)
    except StorageError as exc:
        st.session_state.storage_error = str(exc)
        st.session_state.setdefault('chat_sessions', [])
        st.session_state.setdefault('messages', [])
