from types import SimpleNamespace
import numpy as np
import pytest


def test_model_signature_ignores_volatile_cards_but_tracks_actual_descriptor():
    from benchmark.selection.run import stable_served_model
    a = {'id': 'synthetic-model', 'root': 'synthetic-model', 'max_model_len': 8192,
         'created': 1, 'permission': [{'id': 'random-one'}]}
    b = {**a, 'created': 2, 'permission': [{'id': 'random-two'}]}
    assert stable_served_model(a) == stable_served_model(b)
    assert stable_served_model(a) != stable_served_model({**b, 'max_model_len': 4096})
from benchmark.selection.diagnostic import minimum_parent_cover
from benchmark.selection.report import compare_runs
from benchmark.selection.run import CorpusWitness
from benchmark.evaluation.evidence import normalized
from tests.test_evidence_selection import parent, Registry, outputs
from service.rag.v2.EvidenceSelection import CoverageSelector, optimize, Bundles


class Aligner:
    rules = {'anchors': {'A': {'document': 'source', 'requirements': [
        {'normalized_start': 0, 'normalized_end': 6}]}}}
    sources = {'source': ('abcdef', 'abcdef', list(range(6)))}
    def align(self, entry):
        spans = {'a': [(0, 3)], 'b': [(3, 6)], 'c': [(0, 6)]}
        return {'document': 'source', 'spans': spans[entry['parent_id']], 'status': 'explicit_offsets'}


def test_oracle_counts_fragmented_requirement_and_whole_parent_budget():
    case = SimpleNamespace(metadata={'evidence_ids': ['A']})
    pp = [parent('a', 0, 1600), parent('b', 1, 1700), parent('c', 2, 3500)]
    d = minimum_parent_cover(case, pp, Aligner())
    assert d['minimum_tokens'] == 3300 and d['status'] == 'over_budget'
    assert minimum_parent_cover(case, pp[:1], Aligner())['status'] == 'not_proven_in_candidates'
    assert d['gold_informed'] and not d['used_by_selector']


def test_selector_requires_source_witness_when_configured():
    selector = CoverageSelector(Registry(outputs()), lambda text: 100, 8192,
                                quote_validator=lambda entry, quote: None)
    with pytest.raises(ValueError, match='at most 0'):
        selector.select('pressão?', [], [parent('a', 0)])


def test_corpus_witness_rejects_synthetic_heading_and_unproved_repeated_value(tmp_path):
    source = tmp_path / 'source.md'; source.write_text('## Ensaio\nPressão: 450.\n## Outro\nPressão: 450.\n')
    verifier = CorpusWitness(tmp_path)
    entry = {'relative_path': 'source.md', 'section_title': '', 'text': 'Título inventado\nPressão: 450.'}
    assert verifier(entry, 'Título inventado') is None
    assert verifier(entry, '450') is None
    body = '## Ensaio\nPressão: 450.'
    entry.update(text=body, metadata={'parent_source_start': 0, 'parent_source_end': len(body)})
    assert verifier(entry, '450')['source_start'] == source.read_text().index('450')


def row(i, category, full, partial=None, status='ok'):
    hits = {'a': full, 'b': full if partial is None else partial}
    score = {'selected_hits': hits, 'complete_selected_anchors': all(hits.values()),
             'selected_anchor_recall': sum(hits.values()) / 2, 'pending_anchors': []}
    return {'key': f'{i}:collection', 'case_id': str(i), 'condition': 'collection', 'category': category,
        'field': 'pressure', 'family_ids': ['synthetic'], 'fact_ids': list(hits), 'status': status,
        'evaluations': {'evidence_v2': score, 'literal_v1': score}, 'selector': {'calls': 3}, 'context_tokens': 1000,
        'stage_evaluations': {'rrf': {'all': {'evidence_v2': score}}}}


def with_scopes(rows):
    return rows + [{**r, 'key': r['case_id'] + ':oracle_scope', 'condition': 'oracle_scope'} for r in rows]


def test_comparison_rejects_candidate_changes():
    signature = {k: 'frozen' for k in ('implementation_sha256', 'index_sha256', 'models',
        'corpus_sha256', 'config_sha256', 'datasets', 'evaluation_versions')}
    before = with_scopes([row(1, 'multi-hop', False)])
    after = with_scopes([row(1, 'multi-hop', True)])
    for r in before + after:
        r['source_candidate_digest'] = 'same-candidates'
    baseline = {'signature': signature, 'results': before}
    variant = {'signature': signature, 'results': after}
    assert compare_runs(baseline, variant)['collection']['complete_gains'] == ['1']
    after[0]['source_candidate_digest'] = 'different-candidates'
    with pytest.raises(ValueError, match='Candidate rankings differ'):
        compare_runs(baseline, variant)
