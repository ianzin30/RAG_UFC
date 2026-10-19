"""Offline selection, reconstruction, signed inputs and paired acceptance gate."""
import socket
from types import SimpleNamespace

import numpy as np
import pytest

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.search import global_order_replay as replay

bootstrap_python_path()
from service.rag.v2.EvidenceSelection import Parent, pack_order, round_robin

SOURCE = PROJECT_ROOT / 'benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01'


def parent(pid, tokens):
    return Parent(pid, {'parent_id': pid, 'text': 'original ' + pid}, 0, tokens, np.array([1.]))


def searches(*orders):
    return [{'query_id': f'Q{i}', 'diagnostics': {'stages': {'reranker': [{'position': j} for j in order]}}}
            for i, order in enumerate(orders)]


def test_single_search_empty_repeated_and_exhausted_lists():
    pp = [parent('a', 100), parent('b', 200), parent('c', 300)]
    chunks = [SimpleNamespace(parent_id=p.parent_id) for p in pp]
    single = searches([0, 0, 1, 2])
    assert round_robin(pp, single, chunks) == pack_order(pp)
    multiple = searches([], [0, 0, 1, 2], [0, 2])
    chosen, trace = round_robin(pp, multiple, chunks)
    assert [p.parent_id for p in chosen] == ['a', 'c', 'b']
    assert [p.parent_id for p in round_robin(list(reversed(pp)), multiple, chunks)[0]] == ['a', 'c', 'b']
    assert len(trace) == 3


def test_oversized_block_does_not_prevent_later_small_block():
    pp = [parent('a', 3100), parent('b', 2800), parent('c', 200)]
    chunks = [SimpleNamespace(parent_id=p.parent_id) for p in pp]
    chosen, trace = round_robin(pp, searches([0, 1], [2]), chunks)
    assert [p.parent_id for p in chosen] == ['c', 'b']
    assert sum(p.tokens for p in chosen) == 3000
    assert trace[0] == {'parent_id': 'a', 'tokens': 3100, 'reason': 'token_budget'}
    assert chosen[0].entry['text'] == 'original c'


@pytest.mark.parametrize('entry', [None, {'status': 'started'}, {'status': 'error'},
                                   {'status': 'ok', 'planning_calls_unknown': True}])
def test_missing_failed_unknown_operations_block(entry):
    operations = {'global': {} if entry is None else {'key': entry}}
    with pytest.raises(ValueError, match='Missing, failed or unknown'):
        replay.checked_operation(operations, 'global', 'key')


def minimal_source(tmp_path):
    source = tmp_path / 'source'
    signature = {'study': 'agent_interface'}
    artifacts.save_json(source / 'signature.json', signature)
    artifacts.save_json(source / 'cache.json', {'signature': signature, 'queries': {}, 'global': {}})
    artifacts.save_json(source / 'execution_status.json', {'status': 'complete', 'answer_generation_calls': 0})
    artifacts.save_json(source / 'D_feedback/retrieval.json', {'signature': signature, 'results': [
        {'key': str(i), 'plan': {'decisions': []}} for i in range(140)]})
    return source


def test_missing_artifact_and_signature_mismatch_block(tmp_path):
    source = minimal_source(tmp_path)
    replay.load_history(source)
    cache = artifacts.read_json(source / 'cache.json')
    cache['signature']['study'] = 'changed'
    artifacts.save_json(source / 'cache.json', cache)
    with pytest.raises(ValueError, match='cache signature'):
        replay.load_history(source)
    (source / 'cache.json').unlink()
    with pytest.raises(FileNotFoundError):
        replay.load_history(source)


def test_changed_ancestor_hash_and_unknown_decision_block(tmp_path):
    source = minimal_source(tmp_path)
    signature = artifacts.read_json(source / 'signature.json')
    signature.update(source_run=str(tmp_path / 'ancestor'), source_hashes={'cache.json': 'incorrect'})
    artifacts.save_json(tmp_path / 'ancestor/cache.json', {})
    artifacts.save_json(source / 'signature.json', signature)
    with pytest.raises(ValueError, match='ancestor changed'):
        replay.load_history(source)
    source = minimal_source(tmp_path)
    data = artifacts.read_json(source / 'D_feedback/retrieval.json')
    data['results'][0]['plan']['decisions'] = [{'status': 'started'}]
    artifacts.save_json(source / 'D_feedback/retrieval.json', data)
    with pytest.raises(ValueError, match='Unknown historical decision'):
        replay.load_history(source)


def test_network_access_is_forbidden():
    with replay.offline_only(), socket.socket() as connection:
        with pytest.raises(RuntimeError, match='forbids network'):
            connection.connect(('127.0.0.1', 8000))


def test_preparation_failure_is_marked_incomplete(tmp_path):
    output = tmp_path / 'out'
    with pytest.raises(FileNotFoundError):
        replay.run(output, tmp_path / 'missing')
    status = artifacts.read_json(output / 'execution_status.json')
    assert status['status'] == 'incomplete' and status['stage'] == 'preparation'
    assert status['new_model_calls'] == status['new_retrieval_calls'] == 0


def test_gate_rejects_evidence_loss_even_when_complete_count_is_unchanged():
    rows = []
    for scope in replay.SCOPES:
        for i in range(70):
            g = {'a': True, 'b': False}
            local = {'a': False, 'b': True} if i == 0 and scope == 'oracle_scope' else g
            def scores(hits):
                return {e: {'selected_hits': hits, 'complete_selected_anchors': all(hits.values()),
                            'selected_anchor_recall': sum(hits.values()) / len(hits), 'pending_anchors': []}
                        for e in ('evidence_v2', 'literal_v1')}
            rows.append({'key': f'{i}:{scope}', 'condition': scope, 'minimum_parent_cover': {'status': 'feasible'},
                         'arms': {a: {'evaluations': scores(h)} for a, h in zip(replay.ARMS, (g, local))},
                         'global_operations': []})
    result = replay.comparison(rows, [], [r['key'] for r in rows])
    assert result['gate']['no_complete_question_regressions']
    assert not result['gate']['no_final_evidence_losses']
    assert result['recommendation'] == 'revise'


def test_feedback_and_finish_preserve_the_same_state():
    p = parent('a', 100)
    state = {'query_id': 'Q0', 'searches': [{}], 'parents': [p], 'selected': {'G_global': [p]},
             'traces': {'G_global': [{'parent_id': 'a', 'tokens': 100, 'reason': 'selected'}]}}
    score = {'evidence_v2': {'value': True}}
    step = {'decision_index': 1, 'context_before': ['a'], 'context_after': ['a'], 'observed_parent_ids': ['a'],
            'selected_parent_ids': ['a'], 'action_executed': False, 'requested_action': 'search',
            'context_evaluation': score, 'candidate_evaluation': score, 'discarded_parents': [],
            'context_added': [], 'context_removed': [], 'continuation': 'feedback'}
    finish = {**step, 'decision_index': 2, 'action_executed': True, 'requested_action': 'finish_incomplete',
              'continuation': 'finish_incomplete'}
    row = {'key': 'synthetic', 'evidence': [p.entry], 'packing_trace': state['traces']['G_global'],
           'context_tokens': 100, 'evaluations': score, 'candidate_evaluation': score,
           'plan': {'steps': [step, finish], 'decisions': [{}, {}], 'observations': []}}
    links = replay.verify_control(row, [state], lambda _: score)
    assert [(s['state_before'], s['state_after']) for s in links] == [('Q0', 'Q0'), ('Q0', 'Q0')]
    row['plan']['steps'][0]['effective_query'] = {'query_id': 'Q1'}
    with pytest.raises(ValueError, match='Unexecuted'):
        replay.verify_control(row, [state], lambda _: score)


def test_cli_dispatches_offline_study_without_live_setup(monkeypatch, tmp_path):
    from benchmark.search import run as command
    calls = []
    monkeypatch.setattr(replay, 'run', lambda output, source: calls.append((output, source)))
    monkeypatch.setattr(command, 'llm_setup', lambda: pytest.fail('Live setup attempted'))
    monkeypatch.setattr('sys.argv', ['benchmark', '--study', 'global_order_replay', '--source-run', str(tmp_path / 'source'),
                                    '--output-dir', str(tmp_path / 'out')])
    command.main()
    assert calls == [(tmp_path / 'out', tmp_path / 'source')]


@pytest.mark.skipif(not (SOURCE / 'signature.json').exists(), reason='Historical local artifacts unavailable')
def test_real_offline_replay_is_reproducible_and_resumes_only_same_signature(tmp_path, monkeypatch):
    from benchmark.search import runtime
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.Retrieval import HybridRetriever, BGEReranker, BGEEncoder
    def forbidden(*args, **kwargs):
        pytest.fail('Inference/retrieval initialization attempted')
    monkeypatch.setattr(runtime, 'llm_setup', forbidden)
    monkeypatch.setattr(runtime, 'build_retriever', forbidden)
    for cls in (ProviderRegistry, HybridRetriever, BGEReranker, BGEEncoder):
        monkeypatch.setattr(cls, '__init__', forbidden)
    a, b = tmp_path / 'first', tmp_path / 'second'
    first = replay.run(a, SOURCE)
    assert first['costs']['new_model_calls'] == first['costs']['new_retrieval_calls'] == first['costs']['new_reranker_calls'] == 0
    assert artifacts.read_json(a / 'reproduction.json')['single_search_collection'] == 55
    replay.run(b, SOURCE)
    for name in ('signature.json', 'manifest.json', 'results.json', 'trajectories.json', 'historical_observations.json',
                 'comparison.json', 'reproduction.json', 'preservation.json', 'execution_status.json'):
        assert artifacts.read_json(a / name) == artifacts.read_json(b / name), name
    assert (a / 'report.md').read_text() == (b / 'report.md').read_text()
    signature = artifacts.read_json(a / 'signature.json')
    signature['version'] = 'different'
    artifacts.save_json(a / 'signature.json', signature)
    with pytest.raises(ValueError, match='resume signature'):
        replay.run(a, SOURCE)
