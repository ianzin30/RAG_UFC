"""Gold-informed diagnostic upper bound; never imported by selectors."""
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint


def minimum_parent_cover(case, parents, aligner, budget=3000):
    aligned = [aligner.align(p.entry) for p in parents]
    constraints = set()
    for aid in case.metadata['evidence_ids']:
        rule = aligner.rules['anchors'][aid]
        _, text, mapping = aligner.sources[rule['document']]
        for req in rule['requirements']:
            for index in range(req['normalized_start'], req['normalized_end']):
                if not text[index].isspace():
                    constraints.add(tuple(j for j, entry in enumerate(aligned)
                        if entry['document'] == rule['document'] and
                        any(a <= mapping[index] < b for a, b in entry['spans'])))
    if () in constraints:
        return {'status': 'not_proven_in_candidates', 'minimum_tokens': None,
                'ambiguous_parents': [p.parent_id for p, a in zip(parents, aligned)
                                     if a['status'] in ('ambiguous', 'unaligned', 'invalid_offsets')]}
    if not constraints:
        raise ValueError('Diagnostic requires explicit evidence requirements')
    relevant = sorted({j for c in constraints for j in c}); columns = {j: k for k, j in enumerate(relevant)}
    matrix = np.zeros((len(constraints), len(relevant)))
    for i, c in enumerate(sorted(constraints)):
        for j in c: matrix[i, columns[j]] = 1
    result = milp(np.array([parents[j].tokens for j in relevant], float),
        integrality=np.ones(len(relevant)), bounds=Bounds(0, 1),
        constraints=LinearConstraint(matrix, 1, np.inf), options={'time_limit': 30})
    if not result.success:
        return {'status': 'solver_failure', 'minimum_tokens': None, 'message': result.message}
    cost = round(result.fun)
    return {'status': 'feasible' if cost <= budget else 'over_budget', 'minimum_tokens': cost,
            'parents': [parents[relevant[j]].parent_id for j, value in enumerate(result.x) if value > .5],
            'budget': budget, 'gold_informed': True, 'used_by_selector': False}


def run(output, dataset=None, frozen_dir=None, rules=None):
    from functools import lru_cache
    from transformers import AutoTokenizer
    from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
    from benchmark.selection.run import read_inputs
    from benchmark.evaluation.evidence import SourceAligner
    from benchmark.core.reproducibility import CORPUS
    from benchmark.core import artifacts as inv
    bootstrap_python_path()
    from service.rag.v2.Cache import load_bundle
    from service.rag.v2.EvidenceSelection import parents_from_ranking, shortlist
    inputs = list(read_inputs(dataset, frozen_dir, rules))
    signature = inputs[0][-1]['reference']['signature']
    chunks, texts, _, vectors, _ = load_bundle(PROJECT_ROOT / 'data/cache/rag_v2' / (signature['index_fingerprint'] + '.npz'))
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-m3', local_files_only=True)
    @lru_cache(None)
    def count(text): return len(tokenizer.encode(text, add_special_tokens=False))
    rows = []
    for part, cases, _, _, rules, frozen in inputs:
        aligner = SourceAligner(CORPUS, inv.read_json(rules)); mapping = {c.id: c for c in cases}
        for pool, data in frozen.items():
            for row in data['results']:
                pp = parents_from_ranking(row['diagnostics']['stages']['reranker'], chunks, texts, vectors, count)
                ss = shortlist(pp, row['diagnostics']['searches'], chunks)
                full = minimum_parent_cover(mapping[row['case_id']], pp, aligner)
                short = minimum_parent_cover(mapping[row['case_id']], ss, aligner)
                selected = row['evaluations']['evidence_v2']['complete_selected_anchors']
                reason = ('complete' if selected else 'candidate_evidence_absent' if full['status'] == 'not_proven_in_candidates'
                          else 'whole_parent_budget' if full['status'] == 'over_budget'
                          else 'shortlist_loss' if short['status'] == 'not_proven_in_candidates'
                          else 'selection_loss' if full['status'] == 'feasible' else 'diagnostic_pending')
                rows.append({'key': row['key'], 'source_split': part, 'pool': pool,
                             'condition': row['condition'], 'selected_complete': selected,
                             'union_minimum': full, 'shortlist_minimum': short, 'failure_stage': reason})
    inv.save_json(output, {'gold_informed': True, 'used_by_selector': False, 'rows': rows})


def main():
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--dataset-dir', type=Path)
    p.add_argument('--frozen-search-dir', type=Path)
    p.add_argument('--rules', type=Path)
    args = p.parse_args()
    run(args.output, args.dataset_dir, args.frozen_search_dir, args.rules)


if __name__ == '__main__':
    main()
