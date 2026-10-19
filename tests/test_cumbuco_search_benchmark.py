from types import SimpleNamespace
import copy
import pytest

from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
from benchmark.core.config import load_benchmark_llm
from benchmark.search.run import get_plan, is_transport_error
from benchmark.search.report import compare
from service.rag.v2.SemanticRetrieval import SemanticPlanner, SemanticPlan
from service.rag.v2.Config import load_settings


class Registry:
    def __init__(self, plan):
        self.value = plan
        self.calls = []
    def structured(self, role, prompt, model, references=None, max_attempts=1):
        assert role == 'planner' and max_attempts == 1
        assert 'expected_answer' not in prompt and 'evidence_ids' not in prompt
        self.calls.append({'latency_seconds': 0})
        return model.model_validate(self.value)


def planner(plan, budget=100):
    chunks = [SimpleNamespace(document_id='doc-a', chunk_id='a', text='Eva criou o sensor Prisma.'),
              SimpleNamespace(document_id='doc-b', chunk_id='b', text='Orçamento do ensaio: 500.')]
    registry = Registry(plan)
    instance = SemanticPlanner(registry, [{'document_id':'doc-a','document_name':'Relatório Prisma'},
        {'document_id':'doc-b','document_name':'Registro Delta'}], chunks, lambda _:budget,
        window=2048, max_searches=4, output_tokens=512)
    return instance, registry


def query(text='formação acadêmica de Eva', document_ids=None, source='', quote=''):
    return {'text':text,'need':'formação da inventora','document_ids':document_ids or [],
            'scope_source':source,'scope_quote':quote}


def test_config_is_centralized_and_does_not_change_application_model():
    from service.RuntimeConfig import _read_config_document
    configured = _read_config_document()['benchmark']['llm']
    app, _ = load_settings()
    cfg, tokenizer = load_benchmark_llm()
    assert cfg.provider == configured['provider'] and cfg.model == configured['model']
    assert cfg.roles == {} and cfg.role_max_output_tokens['planner'] == configured['max_output_tokens']
    assert cfg.timeout_seconds == configured['timeout_seconds']
    assert cfg.num_ctx == configured['num_ctx'] and cfg.temperature == configured['temperature']
    assert app.model_dump() == load_settings()[0].model_dump()
    if cfg.provider == 'vllm':
        assert cfg.providers['vllm']['base_url'] == configured['providers']['vllm']['base_url']
        assert app.providers['vllm']['base_url'] == 'http://127.0.0.1:8000/v1'
    assert tokenizer == configured['tokenizer']


def test_freeform_planning_indirect_reference_and_duplicate_queries():
    value = {'needs':['inventora','formação'], 'queries':[query(),query()]}
    p, registry = planner(value)
    searches, diag = p.plan('Onde se formou quem criou Prisma?', 'original', [], [{'position':0}])
    assert len(searches)==2 and len(registry.calls)==1
    assert searches[1].document_ids is None
    assert diag['issues'][0]['reason']=='duplicate_query'
    assert diag['output_reserved_tokens']==512


def test_unsupported_scope_opens_collection_and_unknown_id_fails():
    p, _ = planner({'needs':['formação'], 'queries':[query(document_ids=['doc-b'],source='a',quote='Eva')]})
    searches, diag = p.plan('Formação da inventora?', 'original', [], [{'position':0}])
    assert searches[1].document_ids is None and diag['issues'][0]['reason']=='unproved_scope_opened'
    p, _ = planner({'needs':['formação'], 'queries':[query(document_ids=['invented-id'])]})
    with pytest.raises(ValueError,match='Unknown'):p.plan('Formação?', 'original', [], [])


def test_empty_scope_and_token_budget_never_generate():
    p, registry = planner({'needs':['prazo'], 'queries':[]},budget=2000)
    searches, diag = p.plan('Prazo?', 'original', [], [],scope=[])
    assert len(searches)==1 and diag['calls']==0 and not registry.calls
    with pytest.raises(ValueError,match='exceed'):p.plan('Prazo?', 'original', [], [])
    assert not registry.calls


def test_four_search_limit_and_no_additional_queries():
    p, _ = planner({'needs':['orçamento'], 'queries':[]})
    searches, _ = p.plan('Orçamento?', 'original', [], [])
    assert len(searches)==1
    p, _ = planner({'needs':['orçamento','prazo','beneficiário'], 'queries':[query('orçamento'),query('prazo'),query('beneficiário')]})
    searches, _ = p.plan('Orçamento, prazo e beneficiário?', 'original', [], [])
    assert len(searches)==4


def test_started_and_failed_plans_never_repeat():
    calls=[]; cache={}; saves=[]
    def callback():calls.append(1);return {'status':'ok','events':[{}]}
    value=get_plan(cache,'same',callback,lambda:saves.append(1))
    assert get_plan(cache,'same',callback,lambda:None)==value and len(calls)==1
    cache['interrupted']={'status':'started'}
    value=get_plan(cache,'interrupted',callback,lambda:None)
    assert value['status']=='error' and value['planning_calls_unknown'] and len(calls)==1
    def broken():calls.append(1);raise ValueError('malformed JSON')
    assert get_plan(cache,'bad',broken,lambda:None)['status']=='error'
    get_plan(cache,'bad',broken,lambda:None)
    assert len(calls)==2


def test_alternation_comparison_rejects_any_plan_candidate_or_score_change():
    from tests.test_evidence_selection_benchmark import row, with_scopes
    before=with_scopes([row(1,'multi-hop',False)])
    after=with_scopes([row(1,'multi-hop',True)])
    for r in before+after:
        r.update(planner_digest='plan',shared_queries_digest='queries',source_candidate_digest='scores')
    a={'signature':{'identity':'frozen'},'results':before}
    b={'signature':{'identity':'frozen'},'results':after}
    assert compare(a,b,True)['collection']['complete_gains']==['1']
    for field in ('planner_digest','shared_queries_digest','source_candidate_digest'):
        modified=copy.deepcopy(b); modified['results'][0][field]='changed'
        with pytest.raises(ValueError,match='Alternation changed'):compare(a,modified,True)
    changed=copy.deepcopy(b); changed['results'][0]['source_candidate_digest']='new-search'
    assert compare(a,changed,False)['collection']['complete_gains']==['1']


def test_transport_stop_classification_does_not_hide_malformed_output():
    assert is_transport_error({'message':'Timeout while waiting for the UFC LLM response.'})
    assert not is_transport_error({'message':'JSON invalid'})


def test_empty_conditions_are_reported_as_unexecuted_not_zero_accuracy(tmp_path):
    import json
    from benchmark.search.report import report
    from benchmark.search.run import CONDITIONS
    from benchmark.core.artifacts import save_json
    from tests.test_evidence_selection_benchmark import row, with_scopes
    data = with_scopes([row(1, 'multi-hop', True)])
    for r in data:
        r.update(latency_seconds=1., search_count=1, reranker_pairs_logical=2,
                 planning_calls=0, planning_prompt_tokens=0, planning_completion_tokens=0,
                 candidate_evaluation=r['evaluations'])
    save_json(tmp_path / 'signature.json', {'identity':'frozen'})
    save_json(tmp_path / 'A_baseline' / 'retrieval.json', {'results': data})
    save_json(tmp_path / 'execution_status.json', {'status':'incomplete','stop_reason':'preflight_failure'})
    result = report(tmp_path)
    assert result['comparisons'] == {}
    assert result['metrics']['B_single_shot']['evidence_v2']['collection']['total'] == 0
    assert result['metrics']['B_single_shot']['evidence_v2']['collection']['partial'] is None
    assert 'NaN' not in (tmp_path / 'comparison.json').read_text()


def test_vllm_runtime_respects_served_window_and_keeps_local_json_validation(monkeypatch):
    from service.rag.v2.Config import LLMConfig
    from benchmark.search import runtime
    cfg = LLMConfig(provider='vllm', model='test-model', num_ctx=12288,
                    providers={'vllm': {'base_url': 'http://test/v1'}})
    descriptor = {'id': 'test-model', 'max_model_len': 12288}
    class Session:
        headers = {}
        def get(self, url, timeout):
            assert url == 'http://test/v1/models'
            return SimpleNamespace(raise_for_status=lambda: None,
                                   json=lambda: {'data': [descriptor]})
    tokenizer = SimpleNamespace(apply_chat_template=lambda *a, **k: [1, 2, 3],
                                get_vocab=lambda: {'test': 1}, get_chat_template=lambda: 'template')
    monkeypatch.delenv('VLLM_BASE_URL', raising=False)
    monkeypatch.delenv('VLLM_API_KEY', raising=False)
    monkeypatch.setattr(runtime.requests, 'Session', Session)
    monkeypatch.setattr(runtime.AutoTokenizer, 'from_pretrained', lambda _: tokenizer)
    registry, count, raw_count, info, session, base = runtime.vllm_setup(cfg, 'tokenizer')
    assert raw_count('x') == 3 and count('x') == 515
    assert not registry.resolve('planner').capabilities.structured_output
    assert info['reported_model_capacity'] == 12288
    runtime.verify_remote_identity(info, session, base)
    descriptor.update(created=12345, permission=[{'id': 'new-per-request', 'created': 12345}])
    runtime.verify_remote_identity(info, session, base)
    # Per-request IDs and timestamps must not invalidate an otherwise identical run.
    assert runtime.vllm_setup(cfg, 'tokenizer')[3] == info
    descriptor['max_model_len'] = 8192
    with pytest.raises(ValueError, match='metadata changed'):
        runtime.verify_remote_identity(info, session, base)
    with pytest.raises(ValueError, match='exceeds served'):
        runtime.vllm_setup(cfg, 'tokenizer')


@pytest.mark.parametrize('thinking', [True, False, None])
def test_vllm_accounting_wire_validation_and_cache_identity(monkeypatch, tmp_path, thinking):
    from service.rag.v2.Config import LLMConfig
    from benchmark.search import runtime
    from benchmark.search.input_audit import initialize
    settings = {'base_url': 'http://test/v1', 'options': {'top_p': 0.9, 'seed': 42}}
    if thinking is not None:
        settings['enable_thinking'] = thinking
    cfg = LLMConfig(provider='vllm', model='test-model', num_ctx=16384, max_output_tokens=4096,
        role_max_output_tokens={'planner':4096}, providers={'vllm':settings})
    class Session:
        headers = {}
        def get(self, url, timeout):
            return SimpleNamespace(raise_for_status=lambda: None,
                json=lambda: {'data': [{'id':'test-model','max_model_len':262144}]})
    class Tokenizer:
        init_kwargs = {'_commit_hash':'tokenizer-revision'}
        template = 'template using enable_thinking'
        def get_chat_template(self): return self.template
        def get_vocab(self): return {'test':1}
        def apply_chat_template(self, messages, **kwargs):
            self.last = (messages, kwargs)
            return [1,2,3,4] if kwargs.get('enable_thinking') else [1,2,3]
    tokenizer = Tokenizer()
    monkeypatch.delenv('VLLM_BASE_URL', raising=False)
    monkeypatch.delenv('VLLM_API_KEY', raising=False)
    monkeypatch.setattr(runtime.requests, 'Session', Session)
    monkeypatch.setattr(runtime.AutoTokenizer, 'from_pretrained', lambda _:tokenizer)
    registry, count, raw_count, info, *_ = runtime.vllm_setup(cfg, 'tokenizer')
    wire = registry.resolve('planner').build_payload('observations')
    assert count('observations') == raw_count('observations') + 512
    messages, kwargs = tokenizer.last
    assert messages == wire['messages']
    assert kwargs.get('enable_thinking') == thinking
    assert ('enable_thinking' in kwargs) == (thinking is not None)
    assert info['tokenizer_revision'] == 'tokenizer-revision'
    assert info['tokenizer_template_sha256']
    event = {'sent_parameters':{k:v for k,v in wire.items() if k != 'messages'},
             'reported_model':'test-model'}
    runtime.verify_generation_event(info, event)
    wrong = copy.deepcopy(event); wrong['sent_parameters']['seed'] = 43
    with pytest.raises(ValueError, match='payload differs'):
        runtime.verify_generation_event(info, wrong)
    wrong = copy.deepcopy(event); wrong['reported_model'] = 'other'
    with pytest.raises(ValueError, match='identity differs'):
        runtime.verify_generation_event(info, wrong)
    initialize(tmp_path, {'llm':info})
    initialize(tmp_path, {'llm':info})
    changed = copy.deepcopy(info); changed['request_parameters']['top_p'] = 0.8
    with pytest.raises(ValueError, match='Signature changed'):
        initialize(tmp_path, {'llm':changed})
    changed = copy.deepcopy(info); changed['thinking'] = not thinking
    with pytest.raises(ValueError, match='Signature changed'):
        initialize(tmp_path, {'llm':changed})
    tokenizer.template = 'template without thinking support'
    if thinking is not None:
        with pytest.raises(ValueError, match='does not support'):
            runtime.vllm_setup(cfg, 'tokenizer')
    cfg.max_output_tokens = cfg.num_ctx
    with pytest.raises(ValueError, match='no input budget'):
        runtime.vllm_setup(cfg, 'tokenizer')


def test_vllm_tokenizer_failure_blocks_readiness(monkeypatch):
    from service.rag.v2.Config import LLMConfig
    from benchmark.search import runtime
    class Session:
        headers = {}
        def get(self, *a, **k):
            return SimpleNamespace(raise_for_status=lambda: None,
                json=lambda: {'data':[{'id':'test-model','max_model_len':16384}]})
    monkeypatch.delenv('VLLM_BASE_URL', raising=False)
    monkeypatch.setattr(runtime.requests, 'Session', Session)
    def unavailable(_): raise OSError('synthetic tokenizer unavailable')
    monkeypatch.setattr(runtime.AutoTokenizer, 'from_pretrained', unavailable)
    with pytest.raises(ValueError, match='Cannot prepare configured'):
        runtime.vllm_setup(LLMConfig(provider='vllm',model='test-model',
            providers={'vllm':{'base_url':'http://test/v1'}}), 'missing-tokenizer')


def test_served_metadata_keeps_model_fields_but_excludes_request_timestamps():
    from benchmark.search.runtime import stable_served_metadata
    metadata = {'id': 'model', 'root': 'model', 'max_model_len': 12288,
                'weights_digest': 'reported-digest', 'created': 100, 'permission': [{'id': 'random'}]}
    assert stable_served_metadata(metadata) == {'id': 'model', 'root': 'model',
        'max_model_len': 12288, 'weights_digest': 'reported-digest'}


def test_synthetic_readiness_records_model_mistakes_but_transport_errors_abort():
    from benchmark.search.run import preflight
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
    class FakeRegistry:
        def __init__(self, transport_error=False):
            self.calls = []
            self.transport_error = transport_error
        def structured(self, role, prompt, model, **kwargs):
            self.calls.append({'status': 'error' if self.transport_error else 'ok',
                               'usage': {'prompt_tokens': 1}, 'prompt': prompt})
            if self.transport_error:
                raise TimeoutError('Endpoint timed out')
            needs = ([{'need_id': 'N1', 'text': 'identidade de quem criou Prisma', 'depends_on': []},
                      {'need_id': 'N2', 'text': 'formação dessa pessoa', 'depends_on': ['N1']}]
                     if len(self.calls) == 3 else
                     [{'need_id': 'N1', 'text': 'formação', 'depends_on': []}])
            return model.model_validate({'needs': needs, 'supports': [], 'action': 'search',
                'queries': [{'text': 'formação de Eva', 'document_id': None}], 'reason': 'Falta formação.'})
    registry = FakeRegistry()
    planner = InvestigationPlanner(registry, [], [], lambda _: 100)
    result = preflight(planner, registry, lambda _: 100)
    assert result['status'] == 'passed' and result['accepted_decisions'] == 2
    assert result['examples'][2]['result']['error']['message'] == 'Search budget exhausted'
    registry = FakeRegistry(transport_error=True)
    with pytest.raises(TimeoutError, match='Endpoint timed out'):
        preflight(InvestigationPlanner(registry, [], [], lambda _: 100), registry, lambda _: 100)
    assert len(registry.calls) == 1


def test_contract_reporting_pairs_quality_not_protocol_acceptance(tmp_path):
    from benchmark.core.artifacts import save_json
    from benchmark.search.report import report
    from tests.test_evidence_selection_benchmark import row, with_scopes
    signature = {'study': 'decision_contract', 'conditions': ['A_baseline', 'B_full_contract', 'C_minimal_contract'],
                 'llm': {'model': 'synthetic', 'provider': 'ollama'}}
    save_json(tmp_path / 'signature.json', signature)
    save_json(tmp_path / 'execution_status.json', {'status': 'complete'})
    for arm, complete in [('A_baseline', False), ('B_full_contract', False), ('C_minimal_contract', True)]:
        rows = with_scopes([row(1, 'multi-hop', complete)])
        for r in rows:
            r.update(candidate_evaluation=r['evaluations'], search_count=1, reranker_pairs_logical=1,
                planning_calls=1, planning_prompt_tokens=100, planning_completion_tokens=30,
                stop_reason='finish_sufficient', declared_sufficient=True, plan={'events': []},
                diagnostics={'searches': []})
        save_json(tmp_path / arm / 'retrieval.json', {'signature': signature, 'results': rows})
    result = report(tmp_path)
    assert result['decision'] == 'pending_user_review'
    assert result['comparisons']['simplified_contract']['collection']['complete_gains'] == ['1']
    assert result['costs']['B_full_contract']['collection']['false_sufficiency'] == ['1:collection']
    assert not result['costs']['C_minimal_contract']['collection']['false_sufficiency']
    assert 'unverified' in (tmp_path / 'report.md').read_text()
