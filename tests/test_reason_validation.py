"""The intervention changes local acceptance, never the wire prompt or scope checks."""
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
from service.rag.v2.AdaptiveRetrieval import MinimalDecision, TolerantMinimalDecision, InvestigationController
from benchmark.search.reason_validation import replay_decision, recorded_registry, checkpoint_operation, reason_length_failure
from benchmark.core.timing import RunClock
from benchmark.core.artifacts import read_json
from tests.test_adaptive_retrieval import minimal_fixtures, minimal


def request_and_event(value):
    import json
    p, _, _, initial = minimal_fixtures([], fmt='compact_v1')
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    event = {'status': 'ok', 'latency_seconds': 9., 'prompt': request['rendered_request'],
             'raw_response': json.dumps(value), 'usage': {'completion_tokens': 20}}
    return p, initial, request, {'events': [event]}


@pytest.mark.parametrize('length', [299, 300, 301, 10000])
def test_only_reason_length_acceptance_changes(length):
    value = minimal('finish_sufficient'); value['reason'] = 'x' * length
    p, _, req, saved = request_and_event(value)
    strict = replay_decision(p, req, saved)
    p.reason_validation = 'soft_length_v1'
    tolerant = replay_decision(p, req, saved)
    assert strict['status'] == ('ok' if length <= 300 else 'error')
    assert tolerant['status'] == 'ok'
    assert tolerant['decision']['reason'] == value['reason']
    assert bool(tolerant['issues']) == (length > 300)
    assert tolerant['request'] == strict['request'] == req
    assert tolerant['events'][0]['prompt'] == req['rendered_request']
    assert tolerant['events'][0]['latency_seconds'] == 0
    assert tolerant['events'][0]['historical_latency_seconds'] == 9


@pytest.mark.parametrize('reason', ['', None, 123, [], {}])
def test_invalid_reason_still_fails(reason):
    value = minimal('finish_sufficient'); value['reason'] = reason
    with pytest.raises(ValidationError): TolerantMinimalDecision.model_validate(value)
    value.pop('reason')
    with pytest.raises(ValidationError): TolerantMinimalDecision.model_validate(value)


def test_long_reason_does_not_hide_another_invalid_field():
    value = minimal(document_id='D999'); value['reason'] = 'x' * 301
    p, _, req, saved = request_and_event(value)
    p.reason_validation = 'soft_length_v1'
    result = replay_decision(p, req, saved)
    assert result['status'] == 'error' and 'Unknown' in result['error']['message']
    value['queries'][0]['document_id'] = None
    value['queries'][0]['scope_quote'] = 'x' * 301
    with pytest.raises(ValidationError, match='scope_quote'):
        TolerantMinimalDecision.model_validate(value)


def test_same_prepare_schema_and_prompt_under_both_local_policies():
    p, initial, req, _ = request_and_event(minimal())
    p.reason_validation = 'soft_length_v1'
    assert p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3) == req
    assert req['schema']['properties']['reason']['maxLength'] == 300
    assert 'maxLength' not in TolerantMinimalDecision.model_json_schema()['properties']['reason']


def test_released_search_uses_existing_controller_and_limits():
    value = minimal(); value['reason'] = 'x' * 301
    p, initial, req, saved = request_and_event(value)
    p.reason_validation = 'soft_length_v1'
    decisions = []
    def decide(mode, current, ledger, remaining):
        if decisions:
            # A new observation requires a new request; old response is not reusable.
            return {'status': 'error', 'error': {'type': 'SyntheticFailure', 'message': 'new-state failure'}, 'events': []}
        decisions.append(remaining)
        return replay_decision(p, req, saved)
    from service.rag.v2.AdaptiveRetrieval import Snapshot
    advanced = []
    def advance(search, old):
        advanced.append(search.text)
        return Snapshot(old.ranking, old.runs + [(search, old.ranking, {})], old.parents, old.selected, old.packing_trace)
    final, trace = InvestigationController().run('adaptive', initial, decide, advance)
    assert len(advanced) == 1 and len(trace['decisions']) == 2
    assert decisions == [3] and trace['preserved_context_on_error']
    assert len(final.runs) == 2 and final.context_ids() == initial.context_ids()


def test_replay_refuses_a_different_actual_wire_request():
    p, _, req, saved = request_and_event(minimal('finish_incomplete'))
    changed = copy.deepcopy(req); changed['rendered_request'] += ' changed'
    reg = recorded_registry(saved['events'][0], req)
    with pytest.raises(AssertionError): reg.generate('planner', changed['rendered_request'], req['schema'])
    assert not reg.calls


def test_unknown_retrieval_start_never_repeats():
    values = {'a': {'status': 'started'}}; saves = []
    def unexpected(): pytest.fail('Unknown outcome must not repeat')
    result, physical = checkpoint_operation(values, 'a', unexpected, lambda: saves.append(1))
    assert result['status'] == 'error' and result['usage_unknown'] and not physical
    assert len(saves) == 1


def test_completed_operation_is_not_counted_twice():
    values = {}; calls = []
    def work(): calls.append(1); return {'ranking': []}
    result, first = checkpoint_operation(values, 'a', work, lambda: None)
    again, second = checkpoint_operation(values, 'a', work, lambda: None)
    assert first and not second and calls == [1] and again == result


def test_timing_resume_accumulates_only_physical_active_sessions(tmp_path):
    state = [0.]
    def now(): return (datetime(2026, 10, 14, tzinfo=timezone.utc) + timedelta(seconds=state[0])).isoformat()
    path = tmp_path / 'timing.json'
    c = RunClock(path, lambda: state[0], now)
    with c.measure('replay'): state[0] += 2
    c.set_phase('evaluation')
    with c.measure('live_work'): state[0] += 3
    c.finish('incomplete')
    state[0] += 100
    c = RunClock(path, lambda: state[0], now)
    with c.measure('replay'): state[0] += 1
    c.finish('complete')
    data = read_json(path)
    assert data['active_wall_seconds'] == 6
    assert data['elapsed_since_first_start_seconds'] == 106
    assert sum(s.get('live_work_seconds', 0) for s in data['sessions']) == 3
    assert sum(sum(s['phases'].values()) for s in data['sessions']) == 6


def test_crash_marks_unobserved_tail_instead_of_inventing_duration(tmp_path):
    state = [0.]; path = tmp_path / 'timing.json'
    c = RunClock(path, lambda: state[0])
    state[0] = 2.; c.flush()
    state[0] = 100.
    resumed = RunClock(path, lambda: state[0])
    assert resumed.data['sessions'][0]['status'] == 'interrupted'
    assert resumed.data['active_wall_seconds'] == 2
    resumed.finish('blocked')


def test_reason_failure_classifier_does_not_include_scope_quote():
    assert reason_length_failure({'error': {'message': 'Invalid output:\nreason\n String should have at most 300 characters'}})
    assert not reason_length_failure({'error': {'message': 'Invalid output:\nqueries.0.scope_quote\n String should have at most 300 characters; reason=abc'}})


def test_runner_replays_then_executes_only_the_new_branch(tmp_path, monkeypatch):
    """Exercise the entire orchestration with a synthetic corpus and fake transport."""
    import json
    from types import SimpleNamespace
    from benchmark.core.artifacts import save_json
    from benchmark.search import reason_validation as study
    from benchmark.selection.run import digest
    from service.rag.v2.Providers import ProviderRegistry
    from tests.test_evidence_selection_benchmark import row as sample_row
    from service.rag.v2.AdaptiveRetrieval import Snapshot
    p, _, parents, initial = minimal_fixtures([], fmt='compact_v1')
    p.output_tokens = 4096
    for rank in initial.ranking:
        rank.update(reranker_score=1., dense_rank=1, sparse_rank=1, rrf_score=1.)
    case = SimpleNamespace(id='1', question='Formação?', category='multi-hop', metadata={'history': [], 'evidence_ids': ['a', 'b']})
    reference, a_rows, b_rows, decision_cache = {}, [], [], {}
    score = sample_row(1, 'multi-hop', False)['evaluations']
    for scope in ('collection', 'oracle_scope'):
        allowed = None if scope == 'collection' else ['doc0']
        original = copy.deepcopy(initial.runs[0][0]); original.document_ids = allowed
        snap = Snapshot(initial.ranking, [(original, initial.ranking, {'stages': {'reranker': initial.ranking}})], initial.parents, initial.selected, [])
        request = p.prepare('adaptive', case.question, [], snap, {}, allowed, 3)
        value = minimal(text='descobrir formação'); value['reason'] = 'x' * 301
        event = {'status': 'ok', 'latency_seconds': 1., 'prompt': request['rendered_request'], 'raw_response': json.dumps(value)}
        saved_decision = replay_decision(p, request, {'events': [event]})
        # Source event must preserve its historical wire latency.
        saved_decision['events'][0]['latency_seconds'] = 1.
        decision_cache[digest(request)] = saved_decision
        base = sample_row(1, 'multi-hop', False)
        searches = [{**original.to_dict(), 'diagnostics': {'stages': {'reranker': initial.ranking}}, 'candidates_added': 1}]
        base.update(key='1:' + scope, condition=scope, scope=allowed, query=original.text,
            evidence=[x.entry for x in snap.selected], diagnostics={'stages': {'reranker': snap.ranking}, 'searches': searches},
            candidate_evaluation=score, latency_seconds=0., costs={'total': 0.}, search_count=1,
            planning_calls=0, planning_prompt_tokens=0, planning_completion_tokens=0, reranker_pairs_logical=1,
            stop_reason='baseline', declared_sufficient=False, plan={'events': []})
        reference[base['key']] = base
        a_rows.append(copy.deepcopy(base))
        _, plan = InvestigationController().run('adaptive', snap, lambda *args: saved_decision, lambda *args: pytest.fail('Strict search'))
        base = copy.deepcopy(base)
        base.update(status=plan['status'], error=plan['errors'][0], plan=plan, stop_reason=plan['stop_reason'], planning_calls=1)
        b_rows.append(base)
    model = {'provider': 'vllm', 'model': 'synthetic', 'thinking': False, 'num_ctx': 16384, 'max_output_tokens': 4096,
             'timeout_seconds': 420, 'request_parameters': {}}
    signature = {'llm': model, 'parameters': {}, 'fingerprint': 'synthetic-source', 'index_sha256': 'index',
                 'datasets': {}, 'planner_prompt_sha256': 'prompt'}
    source = tmp_path / 'source'; output = tmp_path / 'output'
    for name, value in [('signature.json', signature), ('cache.json', {'signature': signature, 'decisions': decision_cache, 'queries': {}, 'global': {}}),
                        ('A_baseline/retrieval.json', {'signature': signature, 'results': a_rows}),
                        ('C_minimal_contract/retrieval.json', {'signature': signature, 'results': b_rows}),
                        ('planner_contracts.json', {'minimal_action_v1': {'instruction': 'frozen'}}),
                        ('execution_status.json', {'status': 'complete'})]: save_json(source / name, value)
    (source / 'code.zip').write_bytes(b'synthetic snapshot')
    rules = tmp_path / 'rules.json'; save_json(rules, {'anchors': {}})
    ref = {'cases': [case], 'rows': reference, 'catalog': [{'document_id': d['document_id'], 'document_name': d['name']} for d in p.catalog], 'chunks': p.chunks, 'parents': {}, 'vectors': [],
           'tokens': lambda _: 20, 'anchors': {}, 'rules_path': rules}
    class FakeRegistry:
        structured = ProviderRegistry.structured
        def __init__(self): self.calls = []
        def generate(self, role, prompt, schema=None):
            assert role == 'planner'
            assert all(key not in prompt for key in ('evidence_ids', 'expected_answer', 'category', 'case_id'))
            value = json.dumps(minimal('finish_incomplete'))
            self.calls.append({'status': 'ok', 'latency_seconds': .01, 'raw_response': value, 'prompt': prompt,
                               'usage': {'prompt_tokens': 1, 'completion_tokens': 5}})
            return value
    live = FakeRegistry()
    monkeypatch.setattr(study, 'load_reference', lambda: ref)
    monkeypatch.setattr(study, 'frozen_setup', lambda *args: (live, p.count, p.count))
    monkeypatch.setattr(study, 'llm_setup', lambda: (live, p.count, p.count, model, None, None))
    monkeypatch.setattr(study, 'verify_generation_event', lambda *args: None)
    monkeypatch.setattr(study, 'verify_remote_identity', lambda *args: None)
    monkeypatch.setattr(study, 'SourceAligner', lambda *args: SimpleNamespace(score=lambda *a: copy.deepcopy(score['evidence_v2'])))
    monkeypatch.setattr(study, 'anchor_coverage', lambda *args: copy.deepcopy(score['literal_v1']))
    monkeypatch.setattr(study.artifacts, 'source_corpus', lambda *args: {})
    import service.rag.v2.EvidenceSelection as selection
    monkeypatch.setattr(selection, 'parents_from_ranking', lambda *args: initial.parents)
    import benchmark.search.input_audit as audit
    monkeypatch.setattr(audit, 'protected_files', lambda *args: {})
    search_calls = []
    class Retriever:
        reranker = SimpleNamespace(score=lambda query, texts: [1.] * len(texts))
        def search(self, query, scope, k):
            search_calls.append((query, scope))
            return initial.ranking, {'stages': {'reranker': initial.ranking}}
    monkeypatch.setattr(study, 'build_retriever', lambda _: Retriever())
    study.run(output, source)
    actual = read_json(output / 'C_tolerant/retrieval.json')['results']
    assert len(actual) == 2 and all(r['status'] == 'ok' for r in actual)
    assert all(r['search_count'] == 2 and len(r['plan']['decisions']) == 2 for r in actual)
    assert len(search_calls) == 2  # scopes differ
    assert len(live.calls) == 4  # two synthetic, two new observations; initial decisions replay
    status = read_json(output / 'execution_status.json')
    assert status['replayed_decisions'] == 2 and status['physical_planning_calls'] == 2
    assert status['synthetic_calls'] == 2 and status['answer_generation_calls'] == 0
    # An identical resume never repeats known generation/retrieval operations.
    study.run(output, source)
    assert len(live.calls) == 4 and len(search_calls) == 2
