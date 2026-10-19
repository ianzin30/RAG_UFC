"""Explicit mutations against the current shared repository, never UI snapshots."""
import re
import streamlit as st
from service.RuntimeConfig import get_chat_config
from .Normalization import truncate_title, build_timestamp_now
from .State import create_session, get_active_chat, adopt, change_chat
from .Storage import mutate, find_chat, check_available, Conflict


def _local_busy():
    return bool(st.session_state.get('turn_in_progress') or st.session_state.get('pending_turn_result'))


def create_new_chat(default_collection=None, default_model=None):
    if _local_busy(): return False, 'Aguarde a conclusão da pergunta.'
    created = []
    def operation(state):
        if len(state['chat_sessions']) >= get_chat_config().max_sessions:
            raise Conflict(f'Você pode manter até {get_chat_config().max_sessions} chats ao mesmo tempo.')
        chat = create_session(default_collection, default_model)
        state['chat_sessions'].insert(0, chat)
        created.append(chat['id'])
    result = mutate(operation)
    if result.ok:
        st.session_state.active_chat_id = created[0]
        adopt(result.state)
    return result.ok, result.error


def rename_chat(chat_id, new_title):
    normalized = re.sub(r'\s+', ' ', (new_title or '').strip())
    if not normalized: return False, 'Digite um nome para o chat.'
    if _local_busy(): return False, 'Aguarde a conclusão da pergunta.'
    result = change_chat(lambda c: c.update(title=truncate_title(normalized)), chat_id)
    return result.ok, result.error


def delete_chat(chat_id, default_collection=None, default_model=None):
    if _local_busy(): return False, 'Aguarde a conclusão da pergunta.'
    def operation(state):
        target = find_chat(state, chat_id)
        check_available(target)
        state['chat_sessions'].remove(target)
        if not state['chat_sessions']:
            state['chat_sessions'].append(create_session(default_collection, default_model))
    result = mutate(operation)
    if result.ok: adopt(result.state)
    return result.ok, result.error


def activate_chat(chat_id):
    if _local_busy(): return
    def operation(state):
        chat = find_chat(state, chat_id)
        chat['updated_at'] = build_timestamp_now()
        state['chat_sessions'].remove(chat)
        state['chat_sessions'].insert(0, chat)
    result = mutate(operation)
    if result.ok:
        st.session_state.active_chat_id = chat_id
        adopt(result.state)
    else: st.session_state.chat_feedback = result.error


def update_active_chat_collection(collection):
    if _local_busy(): return
    return change_chat(lambda c: c.update(collection=collection))


def update_active_chat_model(model_name):
    if _local_busy(): return
    return change_chat(lambda c: c.update(model_name=model_name))


def update_active_chat_messages(messages):
    from .State import save_active_chat
    return save_active_chat(messages=messages)


def maybe_title_active_chat(prompt):
    chat = get_active_chat()
    if chat and str(chat.get('title', '')).startswith(get_chat_config().default_title):
        return change_chat(lambda c: c.update(title=truncate_title(prompt)))
