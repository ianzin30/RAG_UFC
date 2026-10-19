"""Paired live budget study: transport and controller boundaries."""
import json
from types import SimpleNamespace

import httpx
import pytest

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.search import document_budget_cycle as study

bootstrap_python_path()
SOURCE=PROJECT_ROOT/'benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01'


@pytest.fixture
def model():
    return artifacts.read_json(SOURCE/'signature.json')['llm']


def transport(monkeypatch,tmp_path,model,handler):
    import llm_client
    for name in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL'):
        monkeypatch.delenv(name,raising=False)
    env=tmp_path/'.env'
    env.write_text('LLM_API_KEY=test-only-key\nLLM_BASE_URL=https://spark.test/api\nLLM_MODEL='+model['model']+'\n')
    real=llm_client.LLMClient
    monkeypatch.setattr(llm_client,'LLMClient',lambda **kw:real(env_path=env,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),**kw))


def completion(model,usage=100,content='{}'):
    return httpx.Response(200,json={'id':'test','object':'chat.completion','created':0,
        'model':model['model'],'choices':[{'index':0,'finish_reason':'stop',
        'message':{'role':'assistant','content':content}}],
        'usage':{'prompt_tokens':usage,'completion_tokens':10,'total_tokens':usage+10}})


def test_sdk_sends_exact_frozen_payload_and_no_server_schema(monkeypatch,tmp_path,model):
    bodies=[]
    def handler(req):
        assert req.headers['authorization']=='Bearer test-only-key'
        if req.method=='GET':return httpx.Response(200,json={'data':[{'id':model['model']}]})
        bodies.append(json.loads(req.content));return completion(model)
    transport(monkeypatch,tmp_path,model,handler)
    registry,client,meta=study.spark_registry(model,lambda _:512)
    try:
        assert registry.generate('planner','prompt',{'type':'object'})=='{}'
        assert bodies==[{**model['request_parameters'],'messages':[{'role':'user','content':'prompt'}]}]
        assert 'response_format' not in bodies[0]
        assert registry.calls[-1]['usage']['prompt_tokens']==100
        assert 'test-only-key' not in json.dumps([registry.calls,meta])
        with pytest.raises(AssertionError):registry.generate('answer','forbidden')
    finally:client.close()


@pytest.mark.parametrize('status',[401,403,429,500])
def test_no_retry_and_safe_error(monkeypatch,tmp_path,model,status):
    posts=[]
    def handler(req):
        if req.method=='GET':return httpx.Response(200,json={'data':[{'id':model['model']}]})
        posts.append(req);return httpx.Response(status,json={'error':'test-only-key sensitive content'})
    transport(monkeypatch,tmp_path,model,handler)
    registry,client,_=study.spark_registry(model,lambda _:512)
    try:
        with pytest.raises(Exception):registry.generate('planner','private')
        assert len(posts)==1
        assert 'test-only-key' not in json.dumps(registry.calls)
        assert 'sensitive content' not in json.dumps(registry.calls)
    finally:client.close()


def test_server_usage_violation_is_recorded(monkeypatch,tmp_path,model):
    def handler(req):
        if req.method=='GET':return httpx.Response(200,json={'data':[{'id':model['model']}]})
        return completion(model,usage=2000)
    transport(monkeypatch,tmp_path,model,handler)
    registry,client,_=study.spark_registry(model,lambda _:1000)
    try:
        with pytest.raises(Exception,match='InputBudget'):registry.generate('planner','prompt')
        assert registry.calls[-1]['status']=='error'
    finally:client.close()


def test_paired_evidence_loss_is_not_hidden_by_same_complete_count():
    def row(hit):
        score={'complete_selected_anchors':False,'selected_hits':{hit:True}}
        return {'key':'Q:collection','condition':'collection','status':'ok',
            'evaluations':{v:score for v in ('evidence_v2','literal_v1')},
            'candidate_evaluation':{v:score for v in ('evidence_v2','literal_v1')},
            'declared_sufficient':False,'plan':{'decisions':[]},'search_count':1,
            'diagnostics':{'searches':[{'text':'Q','document_ids':None}]}}
    records={a:SimpleNamespace(data={'results':[row(h)]}) for a,h in [('D3000','old'),('D6000','new')]}
    result=study.paired_summary(records,[])
    ev=result['scopes']['collection']['evaluators']['evidence_v2']
    assert not ev['question_losses']
    assert ev['evidence_lost']==[{'key':'Q:collection','evidence_id':'old'}]
    assert result['recommendation']=='incomplete'


def test_cli_preflight_dispatches(monkeypatch,tmp_path):
    from benchmark.search import run as runner
    calls=[]
    monkeypatch.setattr(study,'run',lambda *args:calls.append(args))
    monkeypatch.setattr('sys.argv',['benchmark','--study','document_budget_cycle','--source-run',str(SOURCE),
        '--output-dir',str(tmp_path),'--preflight-only'])
    runner.main()
    assert calls==[(tmp_path,SOURCE,True)]


def test_real_preflight_has_no_transport_and_checks_both_budgets(monkeypatch,tmp_path):
    monkeypatch.setattr(study,'spark_registry',lambda *args:pytest.fail('Live transport in preflight'))
    study.run(tmp_path,SOURCE,True)
    assert artifacts.read_json(tmp_path/'control_reproduction.json')=={'status':'passed','rows':140}
    audit=artifacts.read_json(tmp_path/'initial_input_audit.json')
    assert audit['status']=='passed' and audit['generation_calls']==0
    assert len(audit['requests'])==280
    assert {r['arm'] for r in audit['requests']}=={'D3000','D6000'}
    for req in audit['requests']:assert req['tokens']+4096<=16384
