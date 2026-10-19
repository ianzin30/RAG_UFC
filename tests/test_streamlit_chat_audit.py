"""Regression acceptance from the original audit; historical reproductions remain in audit_code.zip."""
import copy
import importlib
import json
from pathlib import Path
import sys

import pytest
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'docs/analises'))
from streamlit_audit_support import Harness


@pytest.fixture
def audit(tmp_path,monkeypatch):
    # AppTest is in-process. Any accidental SDK, requests or retriever access fails.
    monkeypatch.setattr('socket.socket.connect',lambda *a,**kw:pytest.fail('Network forbidden in audit tests'))
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**kw:pytest.fail('DNS forbidden in audit tests'))
    with_fixture=Harness(tmp_path).install()
    yield with_fixture
    with_fixture.close()


def app():
    at=AppTest.from_string('from streamlit_audit_support import render\nrender()',default_timeout=10).run()
    assert not at.exception
    return at


def submit(at,text='Quem financia Atlas?'):
    at.chat_input[0].set_value(text).run()
    return at


def test_normal_send_and_rerun_execute_flow_once(audit):
    at=submit(app());assert not at.exception
    assert len(audit.calls)==1 and audit.calls[0]['history']==[]
    assert len(at.session_state.messages)==2
    at.run();assert not at.exception and len(audit.calls)==1
    assert len(at.session_state.messages)==2
    assert audit.instances[0].callback is None


def test_composer_follows_new_responses_and_progress_is_transient(audit):
    at = app()
    for expected_calls in (1, 2):
        submit(at)
        assert not at.exception
        assert len(audit.calls) == expected_calls
        assert not any(s.label == 'Resposta concluída.' for s in at.status)
        assert not any(s.label == 'Gerando resposta...' for s in at.status)
        # Tree order matches Streamlit's DOM order, including freshly emitted messages.
        elements = list(at)
        composer = next(i for i, e in enumerate(elements) if e.type == 'chat_input')
        messages = [i for i, e in enumerate(elements) if e.type == 'chat_message']
        assert len(messages) == expected_calls * 2
        assert max(messages) < composer
        at.run()
        assert not at.exception and len(audit.calls) == expected_calls
        elements = list(at)
        composer = next(i for i, e in enumerate(elements) if e.type == 'chat_input')
        assert all(i < composer for i, e in enumerate(elements) if e.type == 'chat_message')


@pytest.mark.parametrize('mode',['error','timeout'])
def test_error_is_not_retried_and_excluded_from_semantic_history(audit,mode):
    at=app();audit.mode=mode;submit(at)
    assert not at.exception and len(audit.calls)==1
    assert at.session_state.messages[-1]['role']=='user'
    assert at.session_state.chat_sessions[0]['turns'][-1]['state']==('unknown' if mode=='timeout' else 'failed')
    at.run();assert len(audit.calls)==1
    audit.mode='success';submit(at,'E agora?')
    assert audit.calls[-1]['history']==[]


def test_identical_text_is_a_second_explicit_submission(audit):
    at=submit(app());submit(at)
    assert len(audit.calls)==2


def test_empty_answer_is_rejected(audit):
    audit.mode='empty';at=submit(app());assert not at.exception
    assert at.session_state.messages[-1]['role']=='user'
    assert at.session_state.chat_sessions[0]['turns'][-1]['state']=='failed'
    assert not any(s.label=='Resposta concluída.' and s.state=='complete' for s in at.status)


@pytest.mark.parametrize('mode',['abstain','clarification','empty_sources'])
def test_empty_citations_remain_empty_despite_legacy_sources(audit,mode):
    audit.mode=mode;at=submit(app());assert not at.exception
    assert at.session_state.messages[-1]['cited_sources']==[]
    at.run();assert not at.exception
    assert not any('Fonte citada' in m.value for m in at.markdown)


def test_profile_change_requires_restart(audit):
    at=submit(app());audit.config['llm']['num_ctx']=16384
    submit(at,'Outra pergunta')
    assert len(audit.instances)==1
    assert len(audit.calls)==1 and any('Reinicie' in e.value for e in at.error)


def test_model_switch_rebuilds_one_service(audit):
    at=submit(app());at.selectbox[0].select('audit-B').run()
    submit(at,'Outra pergunta')
    assert audit.models==[]
    assert audit.calls[-1]['model']=='audit-B' and len(audit.instances)==2


def test_collection_change_rebuilds_service(audit):
    at=submit(app())
    # initialize_chat_sessions restores the active chat, so change the chat owner.
    from presentation.chat_sessions import Storage
    Storage.mutate(lambda state:state['chat_sessions'][0].update(collection=['audit-other']))
    submit(at,'Outra pergunta')
    assert audit.calls[-1]['collection']==['audit-other']
    assert len(audit.instances)==2


def test_switch_during_execution_is_blocked(audit):
    at=app()
    def change_chat(st):
        from presentation import chat_sessions
        chat_sessions.create_new_chat(default_collection=['audit'],default_model='audit-A')
    audit.during_call=change_chat;submit(at)
    sessions=at.session_state.chat_sessions
    original=next(x for x in sessions if x['id']==audit.calls[0]['chat_id'])
    current=next(x for x in sessions if x['id']==at.session_state.active_chat_id)
    assert original['messages'][-1]['role']=='assistant'
    assert current['id']==original['id']  # switching via normal operations is blocked during execution


@pytest.mark.parametrize('field,value',[('model_name','audit-B'),('collection',['other'])])
def test_result_is_bound_to_original_profile(audit,field,value):
    at=app()
    def change(st):st.session_state[field]=value
    audit.during_call=change;submit(at)
    assert not at.exception
    message=at.session_state.messages[-1]
    assert message['role']=='assistant' and message['turn_id']
    assert message['profile']['llm']['model']=='audit-A' and message['collection']==['audit']


def test_persistence_failure_blocks_generation(audit):
    at=app();old=audit.storage.read_text();audit.fail_storage=True;submit(at)
    assert not at.exception and not audit.calls
    assert audit.storage.read_text()==old
    assert at.error


def test_two_sessions_preserve_newer_messages(audit):
    one=submit(app(),'Primeira pergunta');two=app()
    submit(one,'Pergunta nova da aba um')
    assert 'Pergunta nova da aba um' in audit.storage.read_text()
    two.run();assert not two.exception
    assert 'Pergunta nova da aba um' in audit.storage.read_text()
    assert any(m['content']=='Pergunta nova da aba um' for m in two.session_state.messages)


def test_source_fields_survive_reload(audit):
    one=submit(app());two=app();assert not two.exception
    source=two.session_state.messages[-1]['cited_sources'][0]
    assert source['evidence_id']=='E1' and source['focus_spans'][0]['quote']=='Aurora'


def test_unknown_source_id_is_omitted(audit):
    audit.mode='wrong_source';at=submit(app());assert not at.exception
    assert not any('E999.' in m.value and 'Fonte citada' in m.value for m in at.markdown)
    assert at.warning


def test_duplicate_source_is_deduplicated(audit):
    audit.mode='duplicate_distinct';at=submit(app());assert not at.exception
    assert sum('Fonte citada' in m.value for m in at.markdown)==1


def test_shared_duplicate_source_object_is_safe(audit):
    audit.mode='duplicate_sources';at=submit(app())
    assert not at.exception
    assert sum('Fonte citada' in m.value for m in at.markdown)==1


def test_malformed_source_does_not_crash(audit):
    audit.mode='invalid_source';at=submit(app())
    assert not at.exception and at.warning
    assert not any(s.label=='Resposta concluída.' for s in at.status)
    assert at.session_state.messages[-1]['role']=='assistant'


def test_missing_file_falls_back_to_visible_preview_error(audit):
    audit.mode='missing_file';at=submit(app());assert not at.exception
    assert any('Nao foi possivel abrir o Markdown' in m.value for m in at.markdown)


def test_mismatched_focus_quote_is_not_highlighted(audit):
    audit.mode='invalid_focus';at=submit(app());assert not at.exception
    assert not any('<mark class="source-focus-highlight">Atlas</mark>' in m.value for m in at.markdown)
    assert at.warning


def test_source_checkbox_survives_rerun(audit):
    at=submit(app());keep_reference=at.session_state.messages[-1]['cited_sources'][0]
    key=at.checkbox[0].key
    at.checkbox[0].check().run();assert not at.exception
    assert at.checkbox[0].key==key
    assert at.checkbox[0].value
    assert keep_reference['evidence_id']=='E1'


def test_invalid_provider_rejected_at_settings_load(audit):
    from service.rag.v2.Config import load_settings
    audit.config['llm']['provider']='not-a-provider'
    with pytest.raises(ValueError,match='Unknown provider'):load_settings()


def test_runtime_config_cache_does_not_reload_toml_automatically(audit):
    from service.RuntimeConfig import get_runtime_config
    assert get_runtime_config().llm_model=='audit-A'
    audit.config['llm']['model']='audit-B'
    assert get_runtime_config().llm_model=='audit-A'


def test_environment_authority_is_stable_after_bootstrap(audit,tmp_path,monkeypatch):
    from service import RuntimeConfig
    from llm_client import LLMSettings
    env=tmp_path/'synthetic.env'
    env.write_text('LLM_MODEL=file-model\nLLM_API_KEY=synthetic-test-key\n')
    monkeypatch.setenv('LLM_MODEL','process-model')
    monkeypatch.setenv('LLM_API_KEY','synthetic-test-key')
    monkeypatch.setattr(RuntimeConfig,'ENV_FILE',env)
    monkeypatch.setattr(RuntimeConfig,'_ENV_LOADED',False)
    assert LLMSettings.from_env(env).model=='process-model'
    RuntimeConfig.load_project_environment()
    assert LLMSettings.from_env(env).model=='process-model'


def test_pending_answer_retries_only_storage(audit):
    at=app()
    audit.during_call=lambda st:setattr(audit,'fail_storage',True)
    submit(at)
    assert not at.exception and len(audit.calls)==1
    assert any('não salva' in e.value for e in at.error)
    assert at.selectbox[0].disabled
    audit.fail_storage=False
    next(b for b in at.button if b.label=='Tentar salvar novamente').click().run()
    assert not at.exception and len(audit.calls)==1
    assert at.session_state.messages[-1]['role']=='assistant'
    at.run();assert len(audit.calls)==1


def test_legacy_answer_is_identified_without_inventing_model_metadata(audit):
    audit.storage.write_text(json.dumps({'chat_sessions':[{'id':'old','title':'Old','collection':['audit'],'model_name':'audit-A',
        'messages':[{'role':'assistant','content':'Old answer','route':'retrieval','sources':[{'document_name':'Atlas','excerpt':'Old quote','relative_path':'atlas.md'}]}]}],'next_chat_session_id':1}))
    at=app();assert not at.exception
    assert any('Resposta legada' in c.value for c in at.caption)
    assert any('Fonte histórica' in m.value for m in at.markdown)
    assert 'profile' not in at.session_state.messages[0]
    assert not audit.calls
