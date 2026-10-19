"""Application Spark transport and transactional turn guarantees (no live requests)."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'application'))
from service import RuntimeConfig
from service.rag.v2.Config import LLMConfig, ModelSelection
from service.rag.v2.Spark import SparkProvider
from service.rag.v2.Providers import ProviderError
from presentation.chat_sessions import Storage
from presentation.chat import Turns


class Tokenizer:
    def __init__(self, size=10): self.size=size
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs['enable_thinking'] is False
        return list(range(self.size))
    def encode(self, text, **kwargs): return [1]


class Client:
    def __init__(self): self.requests=[]
    def list_models(self): return ['qwen']
    def chat_with_metadata(self, messages, **params):
        self.requests.append((messages, params))
        return {'text':'ok','model':'qwen','finish_reason':'stop','usage':{'prompt_tokens':10,'completion_tokens':1},'transport_attempts':1}


def test_spark_public_transport_parameters_and_metadata():
    client=Client()
    config=LLMConfig(provider='spark',model='qwen',max_output_tokens=100, providers={'spark':{'options':{'seed':42,'top_k':20}}})
    provider=SparkProvider(ModelSelection(provider='spark',model='qwen'),config,client=client,tokenizer=Tokenizer())
    result=provider.generate_result('hello',{'type':'object'})
    assert 'response_format' not in client.requests[0][1]
    assert provider.capabilities.structured_output is False
    assert result.text=='ok' and result.finish_reason=='stop' and result.usage['prompt_tokens']==10
    params=client.requests[0][1]
    assert params['seed']==42 and params['max_tokens']==100 and params['temperature']==0
    assert params['extra_body']=={'top_k':20,'chat_template_kwargs':{'enable_thinking':False}}
    assert result.identity['provider']=='spark' and result.server_timings['transport_attempts']==1


def test_token_guard_refuses_before_completion():
    client=Client();config=LLMConfig(provider='spark',model='qwen',num_ctx=1024,max_output_tokens=100)
    provider=SparkProvider(ModelSelection(provider='spark',model='qwen'),config,client=client,tokenizer=Tokenizer(1000))
    with pytest.raises(ProviderError,match='Esta chamada'):provider.generate('long')
    assert not client.requests


def test_unavailable_model_never_falls_back():
    provider=SparkProvider(ModelSelection(provider='spark',model='absent'),LLMConfig(),client=Client(),tokenizer=Tokenizer())
    with pytest.raises(ProviderError,match='não está disponível'):provider.resolve()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    path=tmp_path/'history.json';monkeypatch.setattr(Storage,'CHAT_STORAGE_PATH',path)
    monkeypatch.setattr(RuntimeConfig,'_read_config_document',lambda:{'streamlit':{}})
    RuntimeConfig.reset_runtime_config_cache()
    chat={'id':'one','title':'Nova conversa','messages':[],'collection':['docs'],'model_name':'qwen','turns':[],'revision':0}
    assert Storage.mutate(lambda s:s['chat_sessions'].append(chat)).ok
    yield path
    Storage._ACTIVE_TURNS.clear()
    RuntimeConfig.reset_runtime_config_cache()


def start():
    chat=Storage.load_persisted_chat_state()['chat_sessions'][0]
    return Turns.begin('one','Question',['docs'],{'llm':{'model':'qwen'}},expected_revision=chat['revision'])


def test_two_submissions_same_chat_are_serialized(repo):
    context,first=start();assert first.ok
    second,result=start()
    assert second is None and result.status=='conflict'
    assert len(Storage.load_persisted_chat_state()['chat_sessions'][0]['messages'])==1
    assert Turns.finish(context,Turns.TurnResult('failed',error='test')).ok
    assert start()[0] is not None


def test_duplicate_submission_id_never_runs_twice(repo):
    context,saved=start()
    duplicate,result=Turns.begin('one','Question',['docs'],{},expected_revision=1,turn_id=context.turn_id)
    assert duplicate is None and not result.ok
    assert Storage.load_persisted_chat_state()['chat_sessions'][0]['turns'][0]['state']=='running'


def test_context_history_includes_only_completed_pairs(repo):
    context,_=start()
    result=Turns.TurnResult('answered',{'role':'assistant','content':'Answer','turn_id':context.turn_id,'turn_state':'answered'})
    assert Turns.finish(context,result).ok
    later,_=start()
    assert later.history==[{'role':'user','content':'Question'},{'role':'assistant','content':'Answer'}]


def test_finish_idempotent_and_bound_to_origin(repo):
    context,_=start()
    assert Storage.mutate(lambda s:s['chat_sessions'].append({'id':'other','messages':[],'revision':0})).ok
    result=Turns.TurnResult('answered',{'role':'assistant','content':'Answer','turn_id':context.turn_id,'turn_state':'answered'})
    assert Turns.finish(context,result).ok and Turns.finish(context,result).ok
    state=Storage.load_persisted_chat_state()
    assert len(state['chat_sessions'][0]['messages'])==2 and not state['chat_sessions'][1]['messages']


def test_save_retry_does_not_repeat_generation(repo, monkeypatch):
    context,_=start()
    class Service:
        count=0
        def ask_question_with_trace(self,*args):
            self.count+=1
            return {'answer_text':'Answer','cited_sources':[],'status':'answered'}
    service=Service();result=Turns.run(service,context)
    write=Storage._write
    monkeypatch.setattr(Storage,'_write',lambda *a:(_ for _ in ()).throw(OSError()))
    assert not Turns.finish(context,result).ok
    monkeypatch.setattr(Storage,'_write',write)
    assert Turns.finish(context,result).ok and service.count==1


def test_orphan_turn_becomes_unknown_without_write(repo):
    context,_=start();before=repo.read_bytes()
    Storage._ACTIVE_TURNS.clear()
    chat=Storage.load_persisted_chat_state()['chat_sessions'][0]
    assert chat['turns'][0]['state']=='unknown'
    assert repo.read_bytes()==before
    next_context,_=start();assert next_context and next_context.history==[]


def test_corrupt_storage_not_replaced(repo):
    repo.write_text('{broken')
    with pytest.raises(Storage.StorageError):Storage.load_persisted_chat_state()
    assert not Storage.mutate(lambda s:None).ok
    assert repo.read_text()=='{broken'


def test_legacy_migration_backed_up_without_changing_messages(repo):
    legacy={'chat_sessions':[{'id':'legacy','messages':[{'role':'assistant','content':'Historical','sources':[{'document_name':'Doc','excerpt':'quote'}]}]}],'next_chat_session_id':2}
    raw=json.dumps(legacy).encode();repo.write_bytes(raw)
    assert not repo.with_name(repo.name+'.v1.bak').exists()
    state=Storage.load_persisted_chat_state()
    assert repo.read_bytes()==raw
    assert Storage.mutate(lambda s:s.update(marker=True)).ok
    assert repo.with_name(repo.name+'.v1.bak').read_bytes()==raw
    assert Storage.load_persisted_chat_state()['chat_sessions'][0]['messages']==legacy['chat_sessions'][0]['messages']


def _increment(path, count):
    Storage.CHAT_STORAGE_PATH=Path(path)
    for _ in range(count):
        result=Storage.mutate(lambda s:s.update(counter=s.get('counter',0)+1))
        if not result.ok:raise RuntimeError(result.error)


def test_interprocess_lock_serializes_transactions(repo):
    # Fresh interpreters avoid inheriting Streamlit's temporary __main__ module.
    import subprocess
    code = """
import sys
from pathlib import Path
sys.path.insert(0, 'application')
from presentation.chat_sessions import Storage
Storage.CHAT_STORAGE_PATH=Path(sys.argv[1])
for _ in range(8):
    result=Storage.mutate(lambda state:state.update(counter=state.get('counter',0)+1))
    assert result.ok,result.error
"""
    processes=[subprocess.Popen([sys.executable,'-c',code,str(repo)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    try:
        for process in processes:
            stdout,stderr=process.communicate(timeout=15)
            assert process.returncode==0,stderr.decode()
    finally:
        for process in processes:
            if process.poll() is None:process.kill();process.wait()
    assert Storage.load_persisted_chat_state()['counter']==16


def test_legacy_dotenv_conflict_and_process_override(tmp_path,monkeypatch):
    file=tmp_path/'env';file.write_text('LLM_MODEL=old\nLLM_BASE_URL=https://old.invalid/api\n')
    monkeypatch.setattr(RuntimeConfig,'ENV_FILE',file)
    monkeypatch.delenv('LLM_MODEL',raising=False);monkeypatch.delenv('LLM_BASE_URL',raising=False)
    raw={'provider':'spark','model':'qwen','providers':{'spark':{'base_url':'https://new.invalid/api'}}}
    with pytest.raises(ValueError,match='diverge'):RuntimeConfig.resolve_application_llm(raw)
    monkeypatch.setenv('LLM_MODEL','process');monkeypatch.setenv('LLM_BASE_URL','https://process.invalid/api')
    resolved=RuntimeConfig.resolve_application_llm(raw)
    assert resolved['model']=='process' and resolved['providers']['spark']['base_url']=='https://process.invalid/api'
    assert raw['model']=='qwen'


def test_missing_key_has_safe_error(tmp_path,monkeypatch):
    file=tmp_path/'env';file.write_text('')
    monkeypatch.setattr(RuntimeConfig,'ENV_FILE',file);monkeypatch.delenv('LLM_API_KEY',raising=False)
    with pytest.raises(ProviderError,match='Preencha LLM_API_KEY'):SparkProvider(ModelSelection(),LLMConfig())


def test_launcher_translates_native_only():
    from run_streamlit import build_command
    command=build_command(['--server.port=8999'])
    assert '--server.port=8501' in command and command[-1]=='--server.port=8999'
    assert not any('history_messages' in arg or 'LLM_API_KEY' in arg for arg in command)


def test_unanswered_legacy_user_not_in_history(repo):
    assert Turns.semantic_history([{'role':'user','content':'unfinished'}])==[]
    assert Turns.semantic_history([{'role':'user','content':'Q'},{'role':'assistant','content':'A'}])==[{'role':'user','content':'Q'},{'role':'assistant','content':'A'}]


def test_initial_queries_bind_to_controller_requirements():
    from types import SimpleNamespace
    from service.rag.v2.Planning import DocumentResolver
    from service.rag.v2.Models import QueryPlan, RetrievalQuery
    resolver=DocumentResolver([],[])
    contract=SimpleNamespace(requirements=[SimpleNamespace(requirement_id='R1'),SimpleNamespace(requirement_id='R2')],mandatory_document_ids=[],scope_is_exclusive=False)
    plan=QueryPlan(resolved_question='A general question',queries=[RetrievalQuery(text='a',requirement_ids=['not-created-yet']),RetrievalQuery(text='b',requirement_ids=['R2'])])
    searches=resolver.searches(plan,contract)
    assert searches[0].requirement_ids==['R1','R2'] and searches[1].requirement_ids==['R2']


def test_partial_and_casual_are_completed_results(repo):
    for status in ('partial','casual'):
        context,_=start()
        class Service:
            def ask_question_with_trace(self,*args):return {'answer_text':'Valid explicit status','status':status,'cited_sources':[]}
        result=Turns.run(Service(),context)
        assert result.state==status and result.message
        assert Turns.finish(context,result).ok


def test_crewai_failure_does_not_print_payload_or_error(capfd):
    from pydantic import BaseModel
    from service.rag.v2.Agents import AgentTeam
    from types import SimpleNamespace
    import time
    class Schema(BaseModel):
        value:str
    class Registry:
        config=SimpleNamespace(model='synthetic',temperature=0)
        def structured(self,*args):raise ProviderError('sensitive-error-sentinel')
    with pytest.raises(ProviderError):
        AgentTeam(Registry()).run('planner','Synthetic instruction',{'question':'sensitive-question-sentinel'},Schema)
    time.sleep(.1)
    output=capfd.readouterr()
    assert 'sensitive-error-sentinel' not in output.out+output.err
    assert 'sensitive-question-sentinel' not in output.out+output.err


def test_frozen_reference_rejects_application_budget_change():
    from benchmark.search.runtime import load_reference
    # The guard must run before creating an encoder or calling any model.
    with pytest.raises(ValueError,match='Retrieval settings changed from frozen reference'):
        load_reference()
