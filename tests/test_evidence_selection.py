from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
import json
import numpy as np
import pytest
from types import SimpleNamespace
from service.rag.v2.EvidenceSelection import (Parent, shortlist, pack_order, round_robin,
    mmr, CoverageSelector, Needs, Bundles, optimize, dependency_closure, source_segments, parent_segments)


def parent(pid, rank, tokens=1000, vector=(1., 0.), text='O ensaio Prisma registrou pressão de 450 unidades.'):
    return Parent(pid, {'parent_id': pid, 'text': text, 'document_id': 'doc-' + pid,
                       'document_name': 'Registro ' + pid}, rank, tokens, np.array(vector))


def test_shortlist_reserves_local_evidence_deduplicates_and_orders_globally():
    pp = [parent(str(i), i) for i in range(60)]
    chunks = [SimpleNamespace(parent_id=str(i)) for i in range(60)]
    searches = [{'query_id': 'Q1', 'diagnostics': {'stages': {'reranker': [
        {'position': i} for i in (59, 59, 58, 57, 56, 55)]}}}]
    ss = shortlist(pp, searches, chunks)
    assert len(ss) == 32 and {p.parent_id for p in ss} >= {'59', '58', '57', '56'}
    assert [p.rank for p in ss] == sorted(p.rank for p in ss)


def test_skip_large_parent_and_preserve_whole_text():
    pp = [parent('a', 0, 2800), parent('b', 1, 500), parent('c', 2, 200)]
    selected, trace = pack_order(pp)
    assert [p.parent_id for p in selected] == ['a', 'c']
    assert trace[1]['reason'] == 'token_budget'
    assert selected[0].entry['text'] == pp[0].entry['text']


def test_round_robin_repeated_parent_does_not_consume_turn():
    pp = [parent(x, i, 600) for i, x in enumerate('abcd')]
    chunks = [SimpleNamespace(parent_id=x) for x in 'abcd']
    searches = [{'query_id': str(q), 'diagnostics': {'stages': {'reranker': [
        {'position': i} for i in ranks]}}} for q, ranks in enumerate(([0, 1, 2], [0, 3, 2]))]
    selected, _ = round_robin(pp, searches, chunks)
    assert [p.parent_id for p in selected] == ['a', 'd', 'b', 'c']


def test_mmr_diversity_and_deterministic_ties():
    pp = [parent('a', 0, 1500), parent('b', 1, 1500), parent('c', 2, 1500, (0., 1.)),
          parent('d', 9, 500)]
    selected, _ = mmr(pp)
    assert [p.parent_id for p in selected] == ['a', 'c']
    assert [p.parent_id for p in mmr(pp)[0]] == [p.parent_id for p in selected]


def contract():
    return Needs.model_validate({'needs': [
        {'need_id': 'N1', 'text': 'inventora do sensor', 'requested': False},
        {'need_id': 'N2', 'text': 'formação da inventora', 'depends_on': ['N1']}]})


def test_bundle_requires_bridge_and_shared_parent_cost_is_once():
    needs = contract(); pp = [parent('a', 0, 1400), parent('b', 1, 1400), parent('c', 2, 400)]
    support = {'S1': {'parent_id': 'a', 'need_ids': ['N1']}, 'S2': {'parent_id': 'b', 'need_ids': ['N2']}}
    bad = Bundles.model_validate({'bundles': [{'support_ids': ['S2'], 'full_need_ids': ['N2']}]})
    with pytest.raises(ValueError, match='intermediate'): optimize(pp, needs, bad, support)
    good = Bundles.model_validate({'bundles': [{'support_ids': ['S1', 'S2'], 'full_need_ids': ['N2']},
                                             {'support_ids': ['S1'], 'partial_need_ids': ['N1']}]})
    selected, _, diag = optimize(pp, needs, good, support)
    assert [p.parent_id for p in selected] == ['a', 'b']
    assert diag['bundle_parents'] == ['a', 'b']


@pytest.mark.parametrize('raw', [
    [{'need_id': 'N1', 'text': 'x', 'depends_on': ['N1']}],
    [{'need_id': 'N1', 'text': 'x', 'depends_on': ['missing']}],
    [{'need_id': 'N1', 'text': 'x'}, {'need_id': 'N1', 'text': 'y'}],
])
def test_invalid_dependency_graph(raw):
    with pytest.raises(ValueError): dependency_closure(Needs.model_validate({'needs': raw}).needs)


class Registry:
    def __init__(self, answers): self.answers = iter(answers); self.calls = []; self.prompts = []
    def structured(self, role, prompt, schema, **kwargs):
        assert kwargs['max_attempts'] == 1 and role.startswith('selection_')
        self.calls.append({'status': 'ok'}); self.prompts.append(prompt)
        raw = next(self.answers)
        if role == 'selection_support':
            payload = json.loads(prompt.rsplit('\n', 1)[1])
            by_id = {p['parent_id']: [{'quote_id': u[0], 'text': u[1]} for u in p['segments']] for p in payload['parents']}
            for item in raw['supports']:
                if 'quotes' in item:
                    item['quote_ids'] = []
                    for quote in item.pop('quotes'):
                        unit = next((u for u in by_id.get(item['parent_id'], []) if quote in u['text']), None)
                        item['quote_ids'].append(unit['quote_id'] if unit else 'invalid-segment')
        return schema.model_validate(raw)


def outputs(quote='pressão de 450 unidades', pid='a'):
    return [{'needs': [{'need_id': 'N1', 'text': 'pressão do ensaio'}]},
            {'supports': [{'parent_id': pid, 'status': 'full', 'need_ids': ['N1'],
                           'quotes': [quote], 'reason': 'campo e valor'}]},
            {'bundles': [{'support_ids': ['S1'], 'full_need_ids': ['N1']}]}]


def test_free_field_no_standard_title_three_calls_and_literal_offsets():
    registry = Registry(outputs()); selector = CoverageSelector(registry, lambda text: 100, 8192)
    pp = [parent('a', 0)]; chosen, _, diag = selector.select('Qual pressão do ensaio?', [], pp)
    assert chosen == pp and diag['calls'] == 3
    quote = diag['supports'][0]['quotes'][0]; location = diag['supports'][0]['quote_offsets'][0]
    assert pp[0].entry['text'][location['parent_start']:location['parent_end']] == quote
    assert all('expected_answer' not in p and 'category' not in p for p in registry.prompts)


@pytest.mark.parametrize('quote,pid', [('valor inventado', 'a'), ('x' * 241, 'a'), ('pressão de 450 unidades', 'desconhecido')])
def test_bad_literal_or_parent_fails_without_fallback(quote, pid):
    selector = CoverageSelector(Registry(outputs(quote, pid)), lambda text: 100, 8192)
    with pytest.raises(ValueError): selector.select('pressão?', [], [parent('a', 0)])
    assert len(selector.events) == 2


def test_window_failure_before_model_call_and_empty_input():
    registry = Registry(outputs()); selector = CoverageSelector(registry, lambda text: 9000, 8192)
    with pytest.raises(ValueError, match='window'): selector.select('x', [], [parent('a', 0)])
    assert not registry.calls
    assert selector.select('x', [], [])[2]['calls'] == 0


def test_maximum_call_budget_32_parents():
    pp = [parent(str(i), i, 50) for i in range(32)]
    answers = [{'needs': [{'need_id': 'N1', 'text': 'pressão'}]}]
    for i in range(0, 32, 4):
        answers.append({'supports': [{'parent_id': p.parent_id, 'status': 'none',
            'need_ids': [], 'quotes': [], 'reason': 'sem suporte'} for p in pp[i:i+4]]})
    answers.append({'bundles': []})
    selector = CoverageSelector(Registry(answers), lambda text: 100, 8192)
    selected, _, diag = selector.select('x', [], pp)
    assert diag['calls'] == 10 and len(selected) == 32
    with pytest.raises(ValueError, match='parent limit'): selector.select('x', [], pp + [parent('extra', 32)])


def test_segment_ids_preserve_exact_original_including_repeated_spaces_and_headers():
    text = ('## Cabeçalho\n\nCampo:  valor.\n\nTexto contínuo com acentos: pressão. ' * 25) + 'fim'
    units = source_segments(text, 'P1')
    assert ''.join(u['text'] for u in units) == text
    assert all(len(u['text']) <= 240 for u in units)
    assert all(text[u['parent_start']:u['parent_end']] == u['text'] for u in units)
    assert len({u['quote_id'] for u in units}) == len(units)


def test_presentation_heading_separated_and_only_verified_body_citable():
    p = parent('a', 0, text='Título repetido\nO ensaio Prisma registrou pressão de 450 unidades.')
    p.entry['section_title'] = 'Título repetido'
    units = parent_segments(p, 'P1')
    assert ''.join(u['text'] for u in units) == p.entry['text']
    assert units[0]['text'] == 'Título repetido\n'
    assert all(p.entry['text'][u['parent_start']:u['parent_end']] == u['text'] for u in units)
    witness = lambda entry, quote: {'source_start': 10} if quote.startswith('O ensaio') else None
    registry = Registry(outputs())
    selected, _, diag = CoverageSelector(registry, lambda text: 100, 8192, witness).select('pressão?', [], [p])
    payload = json.loads(registry.prompts[1].rsplit('\n', 1)[1])
    assert payload['parents'][0]['citable_quote_ids'] == [units[1]['quote_id']]
    assert selected == [p] and diag['supports'][0]['quotes'] == [units[1]['text']]


def test_no_verified_segments_can_only_produce_negative_support():
    answers = [{'needs': [{'need_id': 'N1', 'text': 'pressão'}]}, {'supports': [
        {'parent_id': 'a', 'status': 'none', 'need_ids': ['N1'], 'quote_ids': [], 'reason': 'sem origem'}]},
        {'bundles': []}]
    registry = Registry(answers)
    selected, _, diag = CoverageSelector(registry, lambda text: 100, 8192, lambda e, q: None).select('pressão?', [], [parent('a', 0)])
    assert diag['supports'][0]['status'] == 'none' and not diag['supports'][0]['quotes']
    assert selected[0].entry['text'] == parent('a', 0).entry['text']


def test_cross_parent_segment_reference_rejected():
    answers = [{'needs': [{'need_id': 'N1', 'text': 'pressão'}]}, {'supports': [
        {'parent_id': 'a', 'status': 'full', 'need_ids': ['N1'], 'quote_ids': ['P2T1'], 'reason': 'x'},
        {'parent_id': 'b', 'status': 'none', 'need_ids': [], 'quote_ids': [], 'reason': 'x'}]}]
    selector = CoverageSelector(Registry(answers), lambda text: 100, 8192)
    with pytest.raises(ValueError, match='segment reference'):
        selector.select('pressão', [], [parent('a', 0), parent('b', 1)])


def test_negative_need_mapping_is_not_positive_support():
    answers = [{'needs': [{'need_id': 'N1', 'text': 'pressão'}]}, {'supports': [
        {'parent_id': 'a', 'status': 'none', 'need_ids': ['N1'], 'quote_ids': [], 'reason': 'campo ausente'}]},
        {'bundles': []}]
    selector = CoverageSelector(Registry(answers), lambda text: 100, 8192)
    _, _, diag = selector.select('pressão', [], [parent('a', 0)])
    assert diag['bundles']['bundles'] == [] and diag['stop_reason'] == 'all_shortlist_examined'
    assert 'support_id' not in diag['supports'][0]
