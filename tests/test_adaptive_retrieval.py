"""Behavioral tests for generic closed-loop retrieval and independent evaluation."""
from types import SimpleNamespace
import copy
import json
import numpy as np
import pytest

from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
from service.rag.v2.AdaptiveRetrieval import (Decision, InvestigationPlanner, InvestigationController,
                                             Snapshot, validate_decision)
from service.rag.v2.DirectedRetrieval import DirectedSearch
from service.rag.v2.EvidenceSelection import Parent, pack_order


class Registry:
    def __init__(self, values):
        self.values = iter(values); self.calls = []
    def structured(self, role, prompt, model, references=None, max_attempts=1, compact_json=False):
        assert role == 'planner' and max_attempts == 1
        self.calls.append({'prompt': prompt, 'latency_seconds': 0.01})
        value = next(self.values)
        if isinstance(value, Exception): raise value
        return model.model_validate(value)


def parent(i, text, tokens=20):
    return Parent(f'P{i}', {'parent_id': f'P{i}', 'document_id': f'doc{i}', 'document_name': f'Registro {i}',
                           'text': text, 'relative_path': f'doc{i}.md'}, i, tokens, np.array([1.]))


def fixtures(values, initial_ids=(0,)):
    texts = ['Prisma é um sensor de pressão.', 'Eva criou o sensor Prisma.',
             'Eva concluiu Engenharia na Universidade Aurora.', 'Leo concluiu Medicina em 2000.']
    parents = [parent(i, t) for i, t in enumerate(texts)]
    chunks = [SimpleNamespace(chunk_id=f'C{i}', parent_id=f'P{i}', document_id=f'doc{i}',
                              text=t, provenance=[]) for i, t in enumerate(texts)]
    catalog = [{'document_id': f'doc{i}', 'document_name': f'Registro {i}'} for i in range(len(texts))]
    registry = Registry(values)
    planner = InvestigationPlanner(registry, catalog, chunks, lambda t: len(t)//4, window=16384)
    rr = [{'position': i, 'chunk_id': f'C{i}'} for i in initial_ids]
    original = DirectedSearch('Q0', 'Onde se formou quem inventou Prisma?', None)
    initial = Snapshot(rr, [(original, rr, {})], [parents[i] for i in initial_ids], [parents[i] for i in initial_ids], [])
    return planner, registry, parents, initial


NEEDS = [{'need_id': 'N1', 'text': 'inventor do sensor', 'depends_on': []},
         {'need_id': 'N2', 'text': 'formação dessa pessoa', 'depends_on': ['N1']}]


def decision(action='search', text='inventor do sensor Prisma', needs=None, supports=None, **query):
    return {'needs': copy.deepcopy(NEEDS if needs is None else needs), 'supports': supports or [],
            'action': action, 'queries': [{'text': text, **query}] if action == 'search' else [],
            'reason': 'Falta uma ligação documental.'}


def support(nid, pid, quote, status='full'):
    return {'need_id': nid, 'status': status, 'citations': [{'parent_id': pid, 'quote': quote}]}


def execute(planner, registry, initial, advance, mode='adaptive', scope=None):
    def decide(policy, snap, ledger, remaining):
        before = len(registry.calls)
        try:
            req = planner.prepare(policy, initial.runs[0][0].text, [], snap, ledger, scope, remaining)
            result = planner.execute(req)
        except Exception as exc:
            result = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
        result['events'] = registry.calls[before:]
        return result
    return InvestigationController().run(mode, initial, decide, advance, scope)


def test_discovery_changes_next_query_and_closes_with_both_links():
    values = [decision(), decision(text='formação acadêmica de Eva', supports=[support('N1', 'P1', 'Eva criou o sensor Prisma.')]),
              decision('finish_sufficient', supports=[support('N1', 'P1', 'Eva criou o sensor Prisma.'),
                        support('N2', 'P2', 'Eva concluiu Engenharia na Universidade Aurora.')])]
    p, registry, pp, initial = fixtures(values)
    searched = []
    def advance(search, old):
        searched.append(search.text)
        i = len(searched)
        rr = [{'position': i, 'chunk_id': f'C{i}'}]
        all_parents = old.parents + [pp[i]]
        return Snapshot(old.ranking + rr, old.runs + [(search, rr, {})], all_parents, all_parents, [])
    final, trace = execute(p, registry, initial, advance)
    assert searched == ['inventor do sensor Prisma', 'formação acadêmica de Eva']
    assert len(registry.calls) == 3 and trace['stop_reason'] == 'finish_sufficient'
    assert final.context_ids() == ['P0', 'P1', 'P2']
    assert 'Eva criou o sensor Prisma.' in registry.calls[1]['prompt']
    assert 'Eva criou o sensor Prisma.' not in registry.calls[0]['prompt']
    assert trace['declared_sufficient']


def test_already_complete_needs_no_additional_search():
    value = decision('finish_sufficient', supports=[support('N1', 'P1', 'Eva criou o sensor Prisma.'),
                     support('N2', 'P2', 'Eva concluiu Engenharia na Universidade Aurora.')])
    p, reg, pp, initial = fixtures([value], (1, 2))
    final, trace = execute(p, reg, initial, lambda *_: pytest.fail('Unexpected search'))
    assert final is initial and len(reg.calls) == 1 and trace['declared_sufficient']


def test_missing_intermediate_link_cannot_declare_sufficiency():
    value = decision('finish_sufficient', supports=[support('N2', 'P2', 'Eva concluiu Engenharia na Universidade Aurora.')])
    p, reg, _, initial = fixtures([value], (2,))
    final, trace = execute(p, reg, initial, lambda *_: None)
    assert final is initial and trace['status'] == 'error'
    assert 'need or dependency' in trace['errors'][0]['message']


def test_sample_is_a_clue_not_sufficient_final_evidence():
    p, reg, pp, initial = fixtures([], (1, 2))
    initial.selected = [pp[1]]
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    value = decision('finish_sufficient', supports=[support('N1', 'P1', 'Eva criou o sensor Prisma.'),
                        support('N2', 'P2', 'Eva concluiu Engenharia na Universidade Aurora.')])
    with pytest.raises(ValueError, match='outside selected context'):
        validate_decision(Decision.model_validate(value), request, [])


@pytest.mark.parametrize('value', [ValueError('malformed JSON'), TimeoutError('timeout'),
    decision(document_id='invented'), decision('finish_sufficient', supports=[support('N1', 'P0', 'invented quote')])])
def test_failure_preserves_initial_context(value):
    p, reg, _, initial = fixtures([value])
    final, trace = execute(p, reg, initial, lambda *_: pytest.fail('Search on invalid decision'))
    assert final is initial and final.context_ids() == ['P0']
    assert trace['status'] == 'error' and trace['preserved_context_on_error']
    assert len(reg.calls) == 1


def test_failure_after_discovery_preserves_new_context():
    p, reg, pp, initial = fixtures([decision(), ValueError('invalid decision')])
    def advance(search, old):
        rr = [{'position': 1, 'chunk_id': 'C1'}]
        return Snapshot(rr, old.runs + [(search, rr, {})], pp[:2], pp[:2], [])
    final, trace = execute(p, reg, initial, advance)
    assert final.context_ids() == ['P0', 'P1'] and len(reg.calls) == 2
    assert trace['preserved_context_on_error']


def test_retrieval_error_is_transactional():
    p, reg, _, initial = fixtures([decision()])
    def broken(*_): raise RuntimeError('reranker failed')
    final, trace = execute(p, reg, initial, broken)
    assert final is initial and trace['stop_reason'] == 'retrieval_error'


def test_four_searches_include_original_and_final_assessment():
    values = [decision(text=f'lacuna {i}') for i in range(3)] + [decision('finish_incomplete')]
    p, reg, pp, initial = fixtures(values)
    def advance(search, old):
        i = len(old.runs); rr = [{'position': i, 'chunk_id': f'C{i}'}]
        return Snapshot(old.ranking + rr, old.runs + [(search, rr, {})], pp[:i+1], pp[:i+1], [])
    final, trace = execute(p, reg, initial, advance)
    assert len(final.runs) == 4 and len(reg.calls) == 4
    assert trace['stop_reason'] == 'finish_incomplete'
    assert json.loads(reg.calls[-1]['prompt'].split('\n')[-1])['remaining_searches'] == 0


def test_no_fifth_search_when_model_ignores_limit():
    p, reg, pp, initial = fixtures([decision(text=f'lacuna {i}') for i in range(4)])
    def advance(search, old):
        i = len(old.runs); rr = [{'position': i, 'chunk_id': f'C{i}'}]
        return Snapshot(old.ranking + rr, old.runs + [(search, rr, {})], pp[:i+1], pp[:i+1], [])
    final, trace = execute(p, reg, initial, advance)
    assert len(final.runs) == 4 and len(reg.calls) == 4
    assert trace['status'] == 'error' and 'budget exhausted' in trace['errors'][0]['message']


def test_repeated_query_stops_without_searching_again():
    p, reg, _, initial = fixtures([decision(text=initial_text())])
    final, trace = execute(p, reg, initial, lambda *_: pytest.fail('Repeated search'))
    assert trace['stop_reason'] == 'repeated_query' and final is initial


def initial_text(): return 'Onde se formou quem inventou Prisma?'


def test_no_progress_after_two_searches():
    p, reg, _, initial = fixtures([decision(text='busca um'), decision(text='busca dois')])
    def advance(search, old):
        return Snapshot(old.ranking, old.runs + [(search, [], {})], old.parents, old.selected, [])
    final, trace = execute(p, reg, initial, advance)
    assert len(final.runs) == 3 and len(reg.calls) == 2 and trace['stop_reason'] == 'no_progress'


def test_single_shot_executes_queries_without_replanning():
    value = decision(); value['queries'].append({'text': 'formação da pessoa inventora'})
    p, reg, pp, initial = fixtures([value])
    def advance(search, old):
        i = len(old.runs); rr = [{'position': i, 'chunk_id': f'C{i}'}]
        return Snapshot(old.ranking + rr, old.runs + [(search, rr, {})], pp[:i+1], pp[:i+1], [])
    final, trace = execute(p, reg, initial, advance, 'single_shot')
    assert len(reg.calls) == 1 and len(final.runs) == 3 and trace['stop_reason'] == 'single_shot_executed'


def test_unsupported_scope_stays_within_oracle_boundary():
    p, _, _, initial = fixtures([])
    request = p.prepare('single_shot', 'Formação?', [], initial, {}, ['doc0', 'doc1'], 3)
    value = decision(document_id='doc1', scope_source='question', scope_quote='Formação?')
    issues = []; result = validate_decision(Decision.model_validate(value), request, issues)
    assert result['normalized_queries'][0]['document_ids'] == ['doc0', 'doc1']
    assert issues[0]['reason'] == 'unproved_scope_opened'


def test_document_reference_requires_its_own_literal_source():
    p, _, _, initial = fixtures([], (1,))
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    value = decision(document_id='doc1', scope_source='P1', scope_quote='Eva criou o sensor Prisma.')
    issues = []; result = validate_decision(Decision.model_validate(value), request, issues)
    assert result['normalized_queries'][0]['document_ids'] == ['doc1'] and not issues
    value['queries'][0]['document_id'] = 'doc2'
    result = validate_decision(Decision.model_validate(value), request, issues)
    assert result['normalized_queries'][0]['document_ids'] is None


def test_question_scope_accepts_catalog_name_without_project_aliases():
    p, _, _, initial = fixtures([])
    request = p.prepare('adaptive', 'Qual a pressão no Registro 2?', [], initial, {}, None, 3)
    value = decision(document_id='doc2', scope_source='question', scope_quote='Registro 2')
    result = validate_decision(Decision.model_validate(value), request, [])
    assert result['normalized_queries'][0]['document_ids'] == ['doc2']


def test_query_deduplication_ignores_spacing_and_case_in_single_shot():
    p, _, _, initial = fixtures([])
    request = p.prepare('single_shot', 'Pergunta', [], initial, {}, None, 3)
    value = decision(text='pressão registrada'); value['queries'].append({'text': '  PRESSÃO   registrada '})
    issues = []; result = validate_decision(Decision.model_validate(value), request, issues)
    assert len(result['normalized_queries']) == 1 and issues[0]['reason'] == 'duplicate_query_deduplicated'


@pytest.mark.parametrize('needs', [NEEDS[:1], [{'need_id': 'N1', 'text': 'outro assunto', 'depends_on': []}, NEEDS[1]]])
def test_existing_needs_cannot_disappear_or_change(needs):
    p, _, _, initial = fixtures([])
    request = p.prepare('adaptive', 'Pergunta', [], initial, {'needs': NEEDS}, None, 3)
    with pytest.raises(ValueError, match='removed or changed'):
        validate_decision(Decision.model_validate(decision(needs=needs)), request, [])


def test_cyclic_dependencies_and_missing_dependency_fail():
    p, _, _, initial = fixtures([]); request = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    needs = copy.deepcopy(NEEDS); needs[0]['depends_on'] = ['N2']
    with pytest.raises(ValueError, match='Cyclic'):
        validate_decision(Decision.model_validate(decision(needs=needs)), request, [])
    needs[0]['depends_on'] = ['N9']
    with pytest.raises(ValueError, match='Unknown'):
        validate_decision(Decision.model_validate(decision(needs=needs)), request, [])


def test_empty_scope_never_calls_model():
    p, reg, _, initial = fixtures([])
    final, trace = execute(p, reg, initial, lambda *_: None, scope=[])
    assert final is initial and not reg.calls and trace['stop_reason'] == 'empty_scope'


def test_token_budget_removes_samples_first_then_fails_without_calling():
    p, reg, pp, initial = fixtures([], (0, 1, 2, 3)); initial.selected = pp[:1]
    full = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    p.window = full['input_tokens_counted'] + p.output_tokens - 10
    reduced = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    assert len(reduced['payload']['retrieved_samples']) < len(full['payload']['retrieved_samples'])
    assert reduced['payload']['selected_context'] == full['payload']['selected_context']
    p.window = 1100
    with pytest.raises(ValueError, match='InputBudget'):
        p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    assert not reg.calls


def test_parent_packing_preserves_text_skips_oversized_and_deduplicates():
    big = parent(0, 'oversized', 3500); a = parent(1, 'literal one', 1000); b = parent(2, 'literal two', 1800)
    selected, trace = pack_order([big, a, a, b])
    assert [p.parent_id for p in selected] == ['P1', 'P2']
    assert sum(p.tokens for p in selected) == 2800
    assert [p.entry['text'] for p in selected] == ['literal one', 'literal two']


def test_literal_citation_does_not_prove_semantic_relation(tmp_path):
    # The model asserts identity from a visit. Local validation accepts the real
    # quotation; the independent source evaluator rejects the expected identity.
    from benchmark.evaluation.evidence import SourceAligner, freeze_rules
    text = 'Eva visitou o laboratório.\nLeo criou o sensor Prisma.'
    (tmp_path / 'doc0.md').write_text(text)
    anchors = {'IDENTITY': {'document': 'doc0.md', 'quote': 'Leo criou o sensor Prisma.', 'section': 'Registro'}}
    rules = freeze_rules(anchors, tmp_path)
    p, _, _, initial = fixtures([])
    initial.selected[0].entry['text'] = 'Eva visitou o laboratório.'
    request = p.prepare('adaptive', 'Quem criou Prisma?', [], initial, {}, None, 3)
    value = decision('finish_sufficient', needs=NEEDS[:1], supports=[support('N1', 'P0', 'Eva visitou o laboratório.')])
    assert validate_decision(Decision.model_validate(value), request, [])['action'] == 'finish_sufficient'
    case = SimpleNamespace(metadata={'evidence_ids': ['IDENTITY']})
    score = SourceAligner(tmp_path, rules).score(case, [initial.selected[0].entry])
    assert not score['complete_selected_anchors']


def test_prompt_has_no_annotations_and_samples_respect_limits():
    p, _, pp, initial = fixtures([], (0, 1, 2, 3)); initial.selected = []
    request = p.prepare('adaptive', 'Qual a pressão e tolerância?', [], initial, {}, None, 3)
    for forbidden in ('expected_answer', 'category', 'REAL-', 'evidence_ids'):
        assert forbidden not in request['prompt']
    assert len(request['payload']['retrieved_samples']) <= 6
    assert 'DocumentResolver' not in request['prompt']
    assert request['payload']['question'] == 'Qual a pressão e tolerância?'


def test_controller_deterministic_for_identical_observations():
    outputs = []
    for _ in range(2):
        p, reg, _, initial = fixtures([decision('finish_incomplete')])
        final, trace = execute(p, reg, initial, lambda *_: None)
        outputs.append((final.context_ids(), trace))
    assert outputs[0] == outputs[1]


def test_internal_search_metadata_never_leaks_into_decision_input():
    p, _, _, initial = fixtures([])
    prior = DirectedSearch('Q1', 'inventor do sensor Prisma', None, 'free_form', 'adaptive', [])
    initial.runs.append((prior, initial.ranking, {}))
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 2)
    assert request['payload']['previous_queries'][-1] == {'text': 'inventor do sensor Prisma', 'scope': None}
    for q in request['payload']['previous_queries']:
        assert not {'query_id', 'field', 'origin', 'source_proof', 'document_ids'} & q.keys()


@pytest.mark.parametrize('did', [None, 'doc1'])
def test_optional_scope_proof_can_be_null_without_rejecting_open_search(did):
    p, _, _, initial = fixtures([])
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    value = decision(document_id=did, scope_source=None, scope_quote=None)
    issues = []
    result = validate_decision(Decision.model_validate(value), request, issues)
    assert result['normalized_queries'][0]['document_ids'] is None
    assert bool(issues) == (did is not None)


def compact_fixture(initial_ids=(1, 2)):
    p, _, pp, initial = fixtures([], initial_ids)
    p.input_format = 'compact_v1'
    for parent in pp:
        parent.entry['provenance'] = [{'page_no': 2, 'bbox': {'l': 1.23456789}, 'charspan': [0, 50]}]
    return p, pp, initial


def test_compact_view_preserves_text_and_keeps_technical_metadata_canonical():
    from benchmark.search.input_audit import check_preservation
    p, pp, initial = compact_fixture()
    pp[1].entry['text'] += '\nThe literal labels P1 and doc1 must remain unchanged.\nA | B\n1 | 2'
    history = [{'role': 'user', 'content': 'A pergunta anterior menciona P1.'}]
    ledger = {'needs': NEEDS, 'supports': [support('N1', 'P1', 'Eva criou o sensor Prisma.')]}
    request = p.prepare('adaptive', 'Qual a formação?', history, initial, ledger, None, 3)
    assert check_preservation(request)
    assert request['payload']['selected_context'][0]['provenance'][0]['bbox']
    assert 'bbox' not in request['rendered_request'] and 'charspan' not in request['rendered_request']
    assert request['planner_view']['selected_context'][0]['pages'] == [2]
    assert 'document_name' not in request['planner_view']['selected_context'][0]
    assert request['planner_view']['catalog'][1]['name'] == 'Registro 1'
    assert request['planner_view']['selected_context'][0]['text'] == pp[1].entry['text']
    assert request['payload']['ledger'] == ledger and request['planner_view']['history'] == history


def test_aliases_are_stable_across_observations_and_index_order():
    p, pp, initial = compact_fixture()
    before = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    initial.selected = [pp[2]]
    after = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 2)
    alias = after['planner_view']['selected_context'][0]['parent_id']
    assert before['id_maps']['parent_id'][alias] == after['id_maps']['parent_id'][alias] == 'P2'
    other = InvestigationPlanner(None, list(reversed(p.catalog)), list(reversed(p.chunks)), p.count,
                                 input_format='compact_v1')
    assert other.reference_map.encode == p.reference_map.encode


def test_compact_decision_round_trip_retains_scope_and_citation_validation():
    from service.rag.v2.AdaptiveRetrieval import canonical_decision
    p, pp, initial = compact_fixture()
    request = p.prepare('adaptive', 'Qual a formação?', [], initial, {}, None, 3)
    parent_alias = p.reference_map.encode['parent_id']['P1']
    document_alias = p.reference_map.encode['document_id']['doc1']
    value = decision(text='formação de Eva', document_id=document_alias, scope_source=parent_alias,
                     scope_quote='Eva criou o sensor Prisma.',
                     supports=[support('N1', parent_alias, 'Eva criou o sensor Prisma.')])
    parsed = canonical_decision(Decision.model_validate(value), request)
    result = validate_decision(parsed, request, [])
    assert result['supports'][0]['citations'][0]['parent_id'] == 'P1'
    assert result['normalized_queries'][0]['document_ids'] == ['doc1']
    value['queries'][0]['document_id'] = 'D999'
    with pytest.raises(ValueError, match='Unknown document_id'):
        canonical_decision(Decision.model_validate(value), request)
    value['queries'][0]['document_id'] = document_alias
    value['queries'][0]['scope_source'] = 'P999'
    with pytest.raises(ValueError, match='unavailable scope'):
        canonical_decision(Decision.model_validate(value), request)


def test_compact_citations_cannot_use_hidden_or_sample_only_evidence_for_sufficiency():
    from service.rag.v2.AdaptiveRetrieval import canonical_decision
    p, pp, initial = compact_fixture((1, 2, 3))
    initial.selected = [pp[1]]
    request = p.prepare('adaptive', 'Qual a formação?', [], initial, {}, None, 3)
    alias = p.reference_map.encode['parent_id']
    value = decision('finish_sufficient', supports=[support('N1', alias['P1'], 'Eva criou o sensor Prisma.'),
                    support('N2', alias['P2'], 'Eva concluiu Engenharia na Universidade Aurora.')])
    parsed = canonical_decision(Decision.model_validate(value), request)
    with pytest.raises(ValueError, match='outside selected context'):
        validate_decision(parsed, request, [])
    value['supports'][0]['citations'][0]['parent_id'] = alias['P0']
    with pytest.raises(ValueError, match='unavailable parent'):
        canonical_decision(Decision.model_validate(value), request)


def test_removed_samples_are_removed_from_schema_before_budget_check():
    p, pp, initial = compact_fixture((0, 1, 2, 3))
    initial.selected = pp[:1]
    p.count = len
    full = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    p.window = full['input_tokens_counted'] + p.output_tokens - 1
    reduced = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    assert reduced['samples_removed'] == 1
    shown = {x['parent_id'] for x in reduced['planner_view']['selected_context']
             + reduced['planner_view']['retrieved_samples']}
    assert set(reduced['schema']['$defs']['Citation']['properties']['parent_id']['enum']) == shown
    assert len(reduced['rendered_request']) + p.output_tokens <= p.window
    p.window = 1100
    with pytest.raises(ValueError, match='InputBudget'):
        p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)


@pytest.mark.parametrize('fmt', ['legacy_v1', 'compact_v1'])
def test_counted_message_is_exactly_the_message_transmitted_by_registry(fmt):
    from service.rag.v2.Providers import ProviderRegistry, Capabilities
    from service.rag.v2.Config import LLMConfig
    p, _, initial = compact_fixture()
    p.input_format = fmt
    sent = []
    parent_alias = p.reference_map.encode['parent_id']['P1'] if fmt == 'compact_v1' else 'P1'
    value = decision('finish_incomplete', supports=[support('N1', parent_alias, 'Eva criou o sensor Prisma.')])
    class Fake:
        capabilities = Capabilities()
        def __init__(self, *args): pass
        def identity(self): return {'provider': 'fake'}
        def generate(self, prompt, schema=None):
            assert schema is None
            sent.append(prompt)
            return json.dumps(value)
    registry = ProviderRegistry(LLMConfig())
    registry.factories['ollama'] = Fake
    registry.capture_payloads = True
    p.registry = registry
    counted = []
    p.count = lambda text: counted.append(text) or len(text)
    request = p.prepare('adaptive', 'Pergunta', [], initial, {}, None, 3)
    result = p.execute(request)
    assert result['decision']['supports'][0]['citations'][0]['parent_id'] == 'P1'
    assert sent == [counted[-1]] == [request['rendered_request']]
    assert len(registry.calls) == 1


def minimal(action='search', text='inventor de Prisma', **query):
    return {'action': action, 'queries': [{'text': text, **query}] if action == 'search' else [],
            'reason': 'Investigar a informação necessária.'}


def minimal_fixtures(values, initial_ids=(0,), fmt='legacy_v1'):
    p, reg, pp, initial = fixtures(values, initial_ids)
    return InvestigationPlanner(reg, p.catalog, p.chunks, p.count, window=16384,
        input_format=fmt, decision_contract='minimal_action_v1'), reg, pp, initial


def test_minimal_discovery_controls_next_search_without_ledger():
    p, reg, pp, initial = minimal_fixtures([minimal(), minimal(text='formação de Eva'), minimal('finish_sufficient')])
    searched = []
    def advance(search, old):
        searched.append(search.text)
        i = len(searched); rr = [{'position': i, 'chunk_id': f'C{i}'}]
        entries = old.parents + [pp[i]]
        return Snapshot(old.ranking + rr, old.runs + [(search, rr, {})], entries, entries, [])
    final, trace = execute(p, reg, initial, advance)
    assert searched == ['inventor de Prisma', 'formação de Eva']
    assert trace['ledger'] == {} and trace['declared_sufficient']
    assert 'Eva criou o sensor Prisma.' in reg.calls[1]['prompt']
    request = p.prepare('adaptive', 'Formação?', [], final, {'needs': [{'secret': 'unused'}]}, None, 1)
    assert 'ledger' not in request['payload']
    assert 'needs' not in request['schema']['properties'] and 'supports' not in request['schema']['properties']
    assert 'secret' not in request['prompt']


def test_minimal_valid_sufficiency_is_unverified_not_documentary_credit():
    p, reg, _, initial = minimal_fixtures([minimal('finish_sufficient')], (3,))
    final, trace = execute(p, reg, initial, lambda *_: pytest.fail('Unexpected retrieval'))
    assert trace['status'] == 'ok' and trace['declared_sufficient']
    # Only Leo's education is present: model acceptance is not proof about Prisma/Eva.
    assert final.selected[0].entry['text'] == 'Leo concluiu Medicina em 2000.'


@pytest.mark.parametrize('value', [minimal(document_id='unknown'), ValueError('malformed JSON'),
    TimeoutError('timeout'), {'action': 'search', 'queries': [], 'reason': 'missing query'},
    {'action': 'finish_incomplete', 'queries': [{'text': 'extra'}], 'reason': 'unexpected query'}])
def test_minimal_errors_preserve_context(value):
    p, reg, _, initial = minimal_fixtures([value])
    final, trace = execute(p, reg, initial, lambda *_: pytest.fail('Invalid decision cannot search'))
    assert final is initial and trace['status'] == 'error'
    assert trace['preserved_context_on_error'] and len(reg.calls) == 1


def test_minimal_shared_scope_proof_and_compact_references():
    p, reg, _, initial = minimal_fixtures([minimal(document_id='D2', scope_source='P1', scope_quote='Prisma')], fmt='compact_v1')
    request = p.prepare('adaptive', 'Formação?', [], initial, {}, ['doc0', 'doc1'], 3)
    result = p.execute(request)
    # Quote/source belongs to doc0, not requested doc1; open only inside allowed scope.
    assert result['decision']['normalized_queries'][0]['document_ids'] == ['doc0', 'doc1']
    assert result['issues'][0]['reason'] == 'unproved_scope_opened'


def test_minimal_budget_and_empty_scope_do_not_generate():
    p, reg, _, initial = minimal_fixtures([])
    final, trace = execute(p, reg, initial, lambda *_: None, scope=[])
    assert trace['stop_reason'] == 'empty_scope' and not reg.calls
    p.count = lambda _: 20000
    with pytest.raises(ValueError, match='InputBudget'):
        p.prepare('adaptive', 'Formação?', [], initial, {}, None, 3)
    assert not reg.calls


def test_minimal_repeated_query_and_search_limit_use_shared_controller():
    p, reg, _, initial = minimal_fixtures([minimal(text= 'Onde se formou quem inventou Prisma?')])
    _, trace = execute(p, reg, initial, lambda *_: pytest.fail('Repeated search'))
    assert trace['stop_reason'] == 'repeated_query'
    p, reg, _, initial = minimal_fixtures([minimal()])
    req = p.prepare('adaptive', 'Formação?', [], initial, {}, None, 0)
    with pytest.raises(ValueError, match='budget exhausted'):
        p.execute(req)
