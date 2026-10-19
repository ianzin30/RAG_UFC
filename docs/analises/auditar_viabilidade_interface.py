"""Read-only, gold-informed audit of D's saved final candidate pools.

Run from repository root with .venv/bin/python. No retrieval or generation.
Writes a separate artifact; refuses to overwrite it or change historical files.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(source, output):
    if output.exists() or source.resolve() in output.resolve().parents:
        raise ValueError('Use a new output path outside the historical run')
    started = time.perf_counter()
    before = {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    import scipy
    from benchmark.search.runtime import load_reference
    from benchmark.evaluation.evidence import SourceAligner
    from benchmark.selection.diagnostic import minimum_parent_cover
    from benchmark.core.reproducibility import CORPUS
    ref = load_reference()  # validates frozen corpus, index, questions and settings
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    rules_path = source / 'evaluation_rules.json'
    rules = json.loads(rules_path.read_text())
    assert rules == json.loads(ref['rules_path'].read_text())
    aligner = SourceAligner(CORPUS, rules)
    data = json.loads((source / 'D_feedback/retrieval.json').read_text())
    assert data['signature'] == json.loads((source / 'signature.json').read_text())
    assert sha(ref['index']) == data['signature']['index_sha256']
    assert {r['key'] for r in data['results']} == set(ref['rows'])
    cases = {c.id: c for c in ref['cases']}
    rows = []
    for row in data['results']:
        ranking = row['diagnostics']['stages']['reranker']
        assert all(ref['chunks'][r['position']].chunk_id == r['chunk_id'] for r in ranking)
        parents = parents_from_ranking(ranking, ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
        selected, trace = pack_order(parents)
        case = cases[row['case_id']]
        assert trace == row['packing_trace'], row['key']
        assert [p.parent_id for p in selected] == [p['parent_id'] for p in row['evidence']]
        assert sum(p.tokens for p in selected) == row['context_tokens']
        candidate_score = aligner.score(case, [p.entry for p in parents])
        selected_score = aligner.score(case, [p.entry for p in selected])
        assert json.loads(json.dumps(candidate_score)) == row['candidate_evaluation']['evidence_v2'], row['key']
        assert json.loads(json.dumps(selected_score)) == row['evaluations']['evidence_v2'], row['key']
        minimum = minimum_parent_cover(case, parents, aligner)
        if minimum['status'] in ('feasible', 'over_budget'):
            witness = [p for p in parents if p.parent_id in minimum['parents']]
            assert aligner.score(case, [p.entry for p in witness])['complete_selected_anchors']
            assert sum(p.tokens for p in witness) == minimum['minimum_tokens']
            minimum['witness'] = [{'parent_id': p.parent_id, 'tokens': p.tokens,
                                   'global_parent_rank': p.rank + 1,
                                   'document': Path(p.entry['relative_path']).name,
                                   'selected_in_D': p.parent_id in {s.parent_id for s in selected}}
                                  for p in witness]
        complete = selected_score['complete_selected_anchors']
        stage = ('complete' if complete else
                 'selection_loss_feasible' if minimum['status'] == 'feasible' else
                 'whole_parent_budget' if minimum['status'] == 'over_budget' else
                 'candidate_coverage_not_proven' if minimum['status'] == 'not_proven_in_candidates' else
                 'diagnostic_pending')
        rows.append({'key': row['key'], 'condition': row['condition'], 'stage': stage,
                     'minimum': minimum, 'pending_anchors': candidate_score['pending_anchors'],
                     'selected_hits': selected_score['selected_hits'],
                     'candidate_hits': candidate_score['selected_hits']})
    after = {str(p.relative_to(source)): sha(p) for p in source.rglob('*') if p.is_file()}
    assert before == after, 'Historical files changed during audit'
    result = {'kind': 'final_pool_feasibility_diagnostic', 'gold_informed': True,
              'used_by_selector': False, 'new_model_calls': 0, 'new_searches': 0,
              'selection_comparison_executed': False,
              'source_run': str(source.resolve()), 'source_sha256': before,
              'code_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                              [Path(__file__), ROOT / 'benchmark/selection/diagnostic.py',
                               ROOT / 'benchmark/evaluation/evidence.py',
                               ROOT / 'application/service/rag/v2/EvidenceSelection.py',
                               ROOT / 'benchmark/search/runtime.py']},
              'index_sha256': sha(ref['index']), 'scipy_version': scipy.__version__,
              'python_version': sys.version, 'budget': 3000,
              'validation': {'historical_files_unchanged': True, 'rows_reproduced': len(rows),
                             'witnesses_rescored': True},
              'summary': {s: dict(Counter(r['stage'] for r in rows if r['condition'] == s))
                          for s in ('collection', 'oracle_scope')},
              'elapsed_seconds': time.perf_counter() - started, 'rows': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    for row in rows:
        if row['stage'] in ('selection_loss_feasible', 'whole_parent_budget'):
            print(row['key'], row['stage'], row['minimum']['minimum_tokens'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.source, args.output)
