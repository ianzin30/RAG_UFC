"""Document choice, bounded corrective observations and frozen historical behavior."""
import copy
import json
from types import SimpleNamespace

import pytest

from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
from service.rag.v2.AdaptiveRetrieval import (
    InvestigationPlanner, InvestigationController, Snapshot, DocumentSearchDecision,
    TolerantDocumentSearchDecision, decision_failure, tool_feedback)
from service.rag.v2.Providers import ProviderRegistry
from tests.test_adaptive_retrieval import fixtures


class WireRegistry:
    structured = ProviderRegistry.structured
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, role, prompt, schema=None):
        assert role == 'planner'
        value = next(self.outputs)
        event = {'status': 'ok', 'finish_reason': 'stop', 'prompt': prompt,
                 'latency_seconds': .01, 'usage': {'prompt_tokens': 1, 'completion_tokens': 5}}
        self.calls.append(event)
        if isinstance(value, Exception):
            event.update(status='error', error=str(value))
            raise value
        if isinstance(value, tuple):
            value, event['finish_reason'] = value
            event['output_at_limit'] = event['finish_reason'] == 'length'
        value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        event['raw_response'] = value
        return value


def action(kind='search', text='formação de Eva', document_id=None, reason='Falta a formação.'):
    return {'action': kind, 'queries': [{'text': text, 'document_id': document_id}] if kind == 'search' else [], 'reason': reason}


def setup(outputs, scope=None):
    old, _, parents, initial = fixtures([])
    registry = WireRegistry(outputs)
    planner = InvestigationPlanner(registry, old.catalog, old.chunks, lambda t: len(t)//4,
        input_format='compact_v1', decision_contract='document_search_v1', reason_validation='soft_length_v1')
    initial.runs[0][0].document_ids = scope
    return planner, registry, parents, initial


def execute(planner, registry, initial, advance=None, policy='bounded_feedback_v1', scope=None):
    def decide(mode, current, ledger, remaining):
        before = len(registry.calls)
        request = None
        try:
            request = planner.prepare(mode, initial.runs[0][0].text, [], current, ledger, scope, remaining)
            result = planner.execute(request)
            if any(e.get('output_at_limit') for e in registry.calls[before:]):
                raise RuntimeError('Output limit reached')
        except Exception as exc:
            result = {'status': 'error', 'error': decision_failure(exc, registry.calls[before:], request)}
        return {**result, 'events': registry.calls[before:], 'request': request}
    if advance is None:
        def advance(search, previous):
            return Snapshot(previous.ranking, previous.runs + [(search, [], {})], previous.parents, previous.selected, [])
    return InvestigationController(interface='document_search_v1', error_policy=policy).run('adaptive', initial, decide, advance, scope)


def test_only_query_text_and_document_are_in_the_wire_contract():
    p, _, _, initial = setup([])
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    fields = request['schema']['$defs']['DocumentSearchRequest']['properties']
    assert set(fields) == {'text', 'document_id'}
    assert 'scope_source' not in request['rendered_request'] and 'scope_quote' not in request['rendered_request']
    assert request['schema']['properties']['reason']['maxLength'] == 300
    assert 'maxLength' not in TolerantDocumentSearchDecision.model_json_schema()['properties']['reason']
    assert 'ledger' not in request['payload']


def test_document_filter_executes_without_quotes_and_has_no_invented_proof():
    p, registry, _, initial = setup([action(document_id='D2'), action('finish_incomplete')])
    searches = []
    def advance(search, previous):
        searches.append(search)
        return Snapshot(previous.ranking, previous.runs + [(search, [], {})], previous.parents, previous.selected, [])
    _, trace = execute(p, registry, initial, advance)
    assert searches[0].document_ids == ['doc1'] and searches[0].source_proof == []
    assert trace['status'] == 'ok' and not trace['incidents']


@pytest.mark.parametrize('document', ['D999', 'D3'])
def test_invalid_or_forbidden_document_never_opens_scope(document):
    p, registry, _, initial = setup([action(document_id=document), action('finish_incomplete')], ['doc0', 'doc1'])
    _, trace = execute(p, registry, initial, lambda *_: pytest.fail('Invalid filter executed'), scope=['doc0', 'doc1'])
    assert trace['incidents'][0]['code'] == 'INVALID_DOCUMENT'
    assert trace['incidents'][0]['recovered'] and trace['status'] == 'ok'
    assert len(registry.calls) == 2


def test_open_then_restricted_search_is_not_a_repeat():
    p, registry, _, initial = setup([action(text=initial_question(), document_id='D2'), action('finish_incomplete')])
    final, trace = execute(p, registry, initial)
    assert len(final.runs) == 2 and final.runs[-1][0].document_ids == ['doc1']
    assert trace['status'] == 'ok'


def initial_question(): return 'Onde se formou quem inventou Prisma?'


def test_repeat_returns_previous_result_reference_without_retrieval():
    p, registry, _, initial = setup([action(text=initial_question()), action('finish_incomplete')])
    final, trace = execute(p, registry, initial, lambda *_: pytest.fail('Repeated retrieval'))
    assert final is initial and len(registry.calls) == 2
    assert trace['recovered_incidents'] == 1 and not trace['without_incident']
    feedback = trace['decisions'][1]['request']['payload']['tool_feedback']
    assert feedback['previous_query_id'] == 'Q0' and feedback['remaining_decisions'] == 3


def test_stop_control_and_feedback_receive_identical_initial_requests():
    prompts = []
    for policy in ('stop_on_error', 'bounded_feedback_v1'):
        p, registry, _, initial = setup([action(document_id='D999'), action('finish_incomplete')])
        final, trace = execute(p, registry, initial, lambda *_: pytest.fail('Invalid search'), policy)
        prompts.append(registry.calls[0]['prompt'])
        assert len(registry.calls) == (1 if policy == 'stop_on_error' else 2)
        assert (trace['status'] == 'ok') == (policy == 'bounded_feedback_v1')
        assert final is initial
    assert prompts[0] == prompts[1]


@pytest.mark.parametrize('bad', ['not json', {'action': 'search', 'queries': [], 'reason': 'Falta.'},
                                action(reason='   '), action(text='  ')])
def test_completed_protocol_errors_can_be_corrected(bad):
    p, registry, _, initial = setup([bad, action('finish_incomplete')])
    _, trace = execute(p, registry, initial, lambda *_: pytest.fail('Invalid search'))
    assert trace['status'] == 'ok' and len(trace['incidents']) == 1
    assert trace['incidents'][0]['recovered']


def test_four_bad_decisions_stop_with_last_context_and_no_fifth_call():
    p, registry, _, initial = setup([action(document_id='D999')] * 5)
    final, trace = execute(p, registry, initial, lambda *_: pytest.fail('Invalid search'))
    assert final is initial and len(registry.calls) == 4
    assert trace['status'] == 'error' and trace['stop_reason'] == 'decision_limit'
    assert len(trace['incidents']) == 4 and not trace['recovered_incidents']


@pytest.mark.parametrize('bad,code', [(TimeoutError('timeout'), 'TRANSPORT_OR_GENERATION'),
                                    (('not json', 'length'), 'OUTPUT_EXHAUSTED'),
                                    ((action('finish_incomplete'), 'length'), 'OUTPUT_EXHAUSTED')])
def test_transport_and_exhaustion_are_terminal(bad, code):
    p, registry, _, initial = setup([bad, action('finish_incomplete')])
    final, trace = execute(p, registry, initial, lambda *_: None)
    assert final is initial and len(registry.calls) == 1
    assert trace['errors'][0]['code'] == code and not trace['errors'][0]['recoverable']


def test_input_budget_and_unknown_outcome_are_not_recoverable():
    assert not decision_failure(ValueError('InputBudget: too long'))['recoverable']
    assert decision_failure(ValueError('InputBudget: too long'))['code'] == 'INPUT_BUDGET'
    assert not decision_failure(RuntimeError('InterruptedPlanning: unknown outcome'))['recoverable']


def test_feedback_counts_against_real_token_budget():
    p, _, _, initial = setup([])
    plain = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    ledger = {'remaining_decisions': 3, 'tool_feedback': tool_feedback({'code': 'INVALID_DOCUMENT'}, 3, 3)}
    with_feedback = p.prepare('adaptive', 'Formação?', [], initial, ledger, None, 3)
    assert with_feedback['input_tokens_counted'] > plain['input_tokens_counted']
    p.window = with_feedback['input_tokens_counted'] + p.output_tokens - 1
    with pytest.raises(ValueError, match='InputBudget'):
        p.prepare('adaptive', 'Formação?', [], initial, ledger, None, 3)


def test_reason_is_tolerant_but_required_and_nonblank():
    p, registry, _, initial = setup([action('finish_sufficient', reason='r'*301)])
    _, trace = execute(p, registry, initial)
    assert trace['decisions'][0]['issues'][0]['reason'] == 'reason_length_exceeded'
    for invalid in [None, '', 123, {}, []]:
        with pytest.raises(Exception):
            TolerantDocumentSearchDecision.model_validate(action('finish_sufficient', reason=invalid))


def test_search_limits_survive_corrections_and_empty_scope_has_no_calls():
    p, registry, parents, initial = setup([action(document_id='D999')] + [action(text=f'busca {i}') for i in range(3)])
    def advance(search, old):
        i = len(old.runs)
        return Snapshot(old.ranking, old.runs + [(search, [], {})], parents[:i+1], parents[:i+1], [])
    final, trace = execute(p, registry, initial, advance)
    assert len(final.runs) == 4 and len(registry.calls) == 4
    assert trace['status'] == 'ok' and trace['stop_reason'] == 'decision_limit'
    p, registry, _, initial = setup([])
    _, trace = execute(p, registry, initial, scope=[])
    assert not registry.calls and trace['stop_reason'] == 'empty_scope'


def test_retrieval_failure_after_recovery_keeps_last_context():
    p, registry, _, initial = setup([action(document_id='D999'), action()])
    def advance(*_): raise RuntimeError('reranker failed')
    final, trace = execute(p, registry, initial, advance)
    assert final is initial and trace['errors'][0]['code'] == 'RETRIEVAL_FAILURE'
    assert trace['incidents'][0]['recovered'] and not trace['incidents'][1]['recovered']
    assert trace['steps'][-1]['effective_query']['text'] == 'formação de Eva'


def test_no_annotations_or_private_state_enter_the_request():
    p, _, _, initial = setup([])
    ledger = {'needs': ['secret'], 'supports': ['secret'], 'private_thinking': 'secret'}
    request = p.prepare('adaptive', 'Qual a tolerância do sensor?', [], initial, ledger, None, 3)
    for forbidden in ('secret', 'expected_answer', 'evidence_ids', 'category', 'case_id', 'REAL-'):
        assert forbidden not in request['rendered_request']


def test_runner_reproduces_controls_shares_prefix_and_resumes_without_calls(tmp_path, monkeypatch):
    from benchmark.search import agent_interface as study
    from benchmark.search.reason_validation import replay_decision
    from benchmark.core.artifacts import save_json, read_json
    from benchmark.selection.run import digest
    from tests.test_evidence_selection_benchmark import row as sample_row
    import service.rag.v2.EvidenceSelection as selection
    import benchmark.search.input_audit as audit

    old, _, parents, initial = fixtures([])
    old.input_format, old.output_tokens, old.decision_contract, old.reason_validation = 'compact_v1', 4096, 'minimal_action_v1', 'soft_length_v1'
    from service.rag.v2.AdaptiveRetrieval import MinimalDecision
    old.decision_model = MinimalDecision
    initial.ranking[0].update(reranker_score=1., dense_rank=1, sparse_rank=1, rrf_score=1.)
    case = SimpleNamespace(id='1', question=initial_question(), category='multi-hop', metadata={'history': [], 'evidence_ids': ['a', 'b']})
    reference, a_rows, b_rows, decisions = {}, [], [], {}
    scores = sample_row(1, 'multi-hop', False)['evaluations']
    for scope in ('collection', 'oracle_scope'):
        allowed = None if scope == 'collection' else ['doc0']
        search = copy.deepcopy(initial.runs[0][0]); search.document_ids = allowed
        diagnostics = {'stages': {'reranker': initial.ranking}}
        snap = Snapshot(initial.ranking, [(search, initial.ranking, diagnostics)], initial.parents, initial.selected, [])
        request = old.prepare('adaptive', case.question, [], snap, {}, allowed, 3)
        event = {'status': 'ok', 'finish_reason': 'stop', 'latency_seconds': 1., 'prompt': request['rendered_request'],
                 'raw_response': json.dumps(action('finish_incomplete'))}
        saved = replay_decision(old, request, {'events': [event]})
        saved['events'][0]['latency_seconds'] = 1.
        decisions[digest(request)] = saved
        base = sample_row(1, 'multi-hop', False)
        base.update(key='1:'+scope, condition=scope, scope=allowed, query=case.question,
            evidence=[p.entry for p in snap.selected], packing_trace=[], context_tokens=20,
            candidate_evaluation=copy.deepcopy(scores), stage_evaluations={'rrf': {'all': copy.deepcopy(scores)}},
            diagnostics={'stages': {'reranker': snap.ranking}, 'searches': [{**search.to_dict(), 'diagnostics': diagnostics, 'candidates_added': 1}]},
            latency_seconds=0., costs={}, search_count=1, planning_calls=0, planning_prompt_tokens=0,
            planning_completion_tokens=0, reranker_pairs_logical=1, stop_reason='baseline', declared_sufficient=False, plan={'events': []})
        reference[base['key']] = copy.deepcopy(base); a_rows.append(copy.deepcopy(base))
        _, plan = InvestigationController().run('adaptive', snap, lambda *args: saved, lambda *args: pytest.fail('Historical search'))
        base.update(status=plan['status'], error=None, plan=plan, stop_reason=plan['stop_reason'], planning_calls=1)
        b_rows.append(base)
    model = {'provider': 'vllm', 'model': 'synthetic', 'thinking': False, 'num_ctx': 16384,
             'max_output_tokens': 4096, 'timeout_seconds': 420, 'request_parameters': {}}
    signature = {'study': 'reason_validation', 'llm': model, 'parameters': {}, 'datasets': {}, 'index_sha256': 'index'}
    source = tmp_path/'source'; output = tmp_path/'output'
    contents = [('signature.json', signature), ('cache.json', {'signature': signature, 'decisions': decisions, 'queries': {}, 'global': {}}),
        ('A_baseline/retrieval.json', {'signature': signature, 'results': a_rows}),
        ('C_tolerant/retrieval.json', {'signature': signature, 'results': b_rows}), ('execution_status.json', {'status': 'complete'})]
    for name, value in contents: save_json(source/name, value)
    fixture_source = {'signature': signature, 'cache': contents[1][1], 'A': contents[2][1], 'B': contents[3][1],
                      'historical': {'signature': {'llm': model}}, 'operations': {'queries': {}, 'global': {}}}
    rules = tmp_path/'rules.json'; save_json(rules, {'anchors': {}})
    ref = {'cases': [case], 'rows': reference, 'chunks': old.chunks,
           'catalog': [{'document_id': d['document_id'], 'document_name': d['name']} for d in old.catalog],
           'parents': {}, 'vectors': [], 'tokens': lambda _: 20, 'anchors': {}, 'rules_path': rules}
    live = WireRegistry([action(document_id='D999'), action('finish_incomplete')] * 2)
    monkeypatch.setattr(study, 'load_source', lambda _: fixture_source)
    monkeypatch.setattr(study, 'load_reference', lambda: ref)
    monkeypatch.setattr(study, 'frozen_setup', lambda *args: (live, old.count, old.count))
    monkeypatch.setattr(study, 'llm_setup', lambda: (live, old.count, old.count, model, None, None))
    monkeypatch.setattr(study, 'verify_generation_event', lambda *args: None)
    monkeypatch.setattr(study, 'verify_remote_identity', lambda *args: None)
    monkeypatch.setattr(study, 'preflight', lambda *args: {'status': 'passed', 'synthetic_planning_calls': 2})
    monkeypatch.setattr(study, 'SourceAligner', lambda *args: SimpleNamespace(score=lambda *args: copy.deepcopy(scores['evidence_v2'])))
    monkeypatch.setattr(study, 'anchor_coverage', lambda *args: copy.deepcopy(scores['literal_v1']))
    monkeypatch.setattr(study.artifacts, 'source_corpus', lambda *args: {})
    monkeypatch.setattr(study, 'code_files', lambda: [])
    monkeypatch.setattr(selection, 'parents_from_ranking', lambda *args: initial.parents)
    monkeypatch.setattr(audit, 'protected_files', lambda *args: {})
    monkeypatch.setattr(study, 'build_retriever', lambda *_: pytest.fail('No valid search was proposed'))
    study.run(output, source)
    assert all(r['status'] == 'error' for r in read_json(output/'C_simple/retrieval.json')['results'])
    assert all(r['status'] == 'ok' and r['recovered_incidents'] == 1 for r in read_json(output/'D_feedback/retrieval.json')['results'])
    status = read_json(output/'execution_status.json')
    assert status['status'] == 'complete' and status['completed_original_questions'] == 1
    assert status['physical_planning_calls'] == 4 and len(live.calls) == 4
    comparison = read_json(output/'comparison.json')
    assert len(comparison['interface_audit']['sharing_checks']) == 2
    assert all(r['passed'] for r in comparison['interface_audit']['sharing_checks'])
    assert status['answer_generation_calls'] == 0
    assert read_json(output/'control_reproduction.json')['status'] == 'passed'
    study.run(output, source)
    assert len(live.calls) == 4
    # Changing even one effective signed model setting prevents resuming.
    fixture_source['signature']['llm'] = {**model, 'max_output_tokens': 5000}
    fixture_source['historical']['signature']['llm'] = fixture_source['signature']['llm']
    with pytest.raises(ValueError, match='signature changed'):
        study.run(output, source)
