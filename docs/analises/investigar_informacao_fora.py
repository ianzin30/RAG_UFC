"""Investigação da informação que ficou de fora e das duas perguntas que melhoraram.

Read-only, offline packing audit. Reproduces saved G/L states, evaluates exact
source spans, and diagnoses single-block exclusions using gold only offline.
No new policy is selected, no retrieval/reranking/generation is executed.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmark.core import artifacts
from benchmark.core.bootstrap import bootstrap_python_path
from benchmark.core.reproducibility import CORPUS, sha
from benchmark.evaluation.evidence import SourceAligner
from benchmark.search.global_order_replay import offline_only
from benchmark.selection.run import digest

CASES = ('REAL-C08', 'REAL-C02', 'REAL-L05')
LABELS = {'G_global': 'Juntar e reordenar', 'L_local': 'Alternar entre buscas'}


def same(actual, expected, label):
    if digest(actual) != digest(expected):
        raise ValueError('Divergência nos registros: ' + label)


def contribution(entry, case, aligner):
    """Count exact required nonspace source characters covered by this parent."""
    aligned = aligner.align(entry)
    result = {}
    for aid in case.metadata['evidence_ids']:
        rule = aligner.rules['anchors'][aid]
        _, text, mapping = aligner.sources[rule['document']]
        positions = {mapping[i] for req in rule['requirements']
                     for i in range(req['normalized_start'], req['normalized_end']) if not text[i].isspace()}
        covered = {i for i in positions if aligned['document'] == rule['document']
                   and any(a <= i < b for a, b in aligned['spans'])}
        result[aid] = {'required_characters': len(positions), 'covered_characters': len(covered),
                       'complete': covered == positions}
    return result


def local_positions(searches, chunks):
    positions = {}
    for search in searches:
        seen = set()
        for child_rank, item in enumerate(search['diagnostics']['stages']['reranker'], 1):
            pid = chunks[item['position']]['parent_id']
            if pid in seen:
                continue
            seen.add(pid)
            positions.setdefault(pid, []).append({'query_id': search['query_id'], 'parent_rank': len(seen),
                'child_rank': child_rank, 'local_score': item['reranker_score']})
    return positions


def inspect_order(trace, parents, annotations):
    by_id = {p.parent_id: p for p in parents}
    used, events = 0, []
    for i, record in enumerate(trace, 1):
        p = by_id[record['parent_id']]
        before = used
        accepted = used + p.tokens <= 3000
        same(record['reason'], 'selected' if accepted else 'token_budget', 'budget acceptance')
        same(record['tokens'], p.tokens, 'parent tokens')
        if accepted:
            used += p.tokens
        events.append({'position': i, 'parent_id': p.parent_id, 'document': Path(p.entry['relative_path']).name,
            'section': p.entry.get('section_title', ''), 'excerpt': p.entry['text'][:240],
            'tokens': p.tokens, 'used_before': before, 'free_before': 3000 - before,
            'deficit_to_fit': max(0, p.tokens - (3000 - before)), 'accepted': accepted,
            'used_after': used, 'covered_annotations': [aid for aid, c in annotations[p.parent_id].items() if c['complete']],
            'annotation_characters': annotations[p.parent_id]})
    return events


def audit(source, output):
    if output.exists():
        raise ValueError('Use um diretório de saída novo')
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError('Não escreva dentro da rodada histórica')
    bootstrap_python_path()
    import numpy as np
    from service.rag.v2.EvidenceSelection import Parent, pack_order, round_robin
    signature = artifacts.read_json(source / 'signature.json')
    same(artifacts.read_json(source / 'execution_status.json')['status'], 'complete', 'source complete')
    protected = dict(signature['input_sha256'])
    protected.update({str(p.resolve()): sha(p) for p in source.rglob('*') if p.is_file()})
    for relative in ('application/service/rag/v2/EvidenceSelection.py', 'benchmark/evaluation/evidence.py'):
        same(sha(ROOT / relative), signature['code_sha256'][relative], 'same executed selection/evaluation code')
        protected[str(ROOT / relative)] = sha(ROOT / relative)
    for filename, expected in protected.items():
        same(sha(Path(filename)), expected, 'input hash ' + filename)
    index = next(Path(p) for p in protected if p.endswith('.npz') and 'rag_v2' in p)
    with np.load(index, allow_pickle=False) as bundle:
        metadata = json.loads(str(bundle['metadata']))
    chunks, texts = metadata['chunks'], metadata['parents']
    chunk_by_id = {c['chunk_id']: c for c in chunks}
    original = Path(signature['source_run'])
    source_rows = {r['key']: r for r in artifacts.read_json(original / 'D_feedback/retrieval.json')['results']}
    result_rows = {r['key']: r for r in artifacts.read_json(source / 'results.json')['rows']}
    trajectories = {r['key']: r for r in artifacts.read_json(source / 'trajectories.json')['rows']}
    aligner = SourceAligner(CORPUS, artifacts.read_json(original / 'evaluation_rules.json'))
    cases, snapshot_count = [], 0
    for case_id in CASES:
        key = case_id + ':collection'
        final_row, original_row = result_rows[key], source_rows[key]
        case = SimpleNamespace(metadata={'evidence_ids': list(final_row['candidate_evaluation']['evidence_v2']['selected_hits'])})
        snapshots = []
        all_local = local_positions(original_row['diagnostics']['searches'], chunks)
        for state in trajectories[key]['snapshots']:
            parents = []
            for i, item in enumerate(state['candidate_parents']):
                chunk = chunk_by_id[item['representative_chunk_id']]
                text = texts[item['parent_id']]
                same(digest(text), item['text_sha256'], 'parent source text')
                entry = {**chunk, 'text': text, 'excerpt': text, 'context': text}
                parents.append(Parent(item['parent_id'], entry, i, item['tokens'], np.zeros(0)))
            g, gt = pack_order(parents)
            local_searches = original_row['diagnostics']['searches'][:state['search_count']]
            local, lt = round_robin(parents, local_searches, [SimpleNamespace(**c) for c in chunks])
            selections = {'G_global': (g, gt), 'L_local': (local, lt)}
            annotations = {p.parent_id: contribution(p.entry, case, aligner) for p in parents}
            arms = {}
            for arm, (selected, trace) in selections.items():
                expected = state['arms'][arm]
                same(trace, expected['packing_trace'], key + '/' + state['query_id'] + '/' + arm + ' trace')
                same([p.parent_id for p in selected], expected['selected_parent_ids'], 'selected IDs')
                same(sum(p.tokens for p in selected), expected['context_tokens'], 'selected tokens')
                score = aligner.score(case, [p.entry for p in selected])
                same(score, expected['evaluations']['evidence_v2'], 'source-position evidence evaluation')
                events = inspect_order(trace, parents, annotations)
                arms[arm] = {'label': LABELS[arm], 'selected_hits': score['selected_hits'],
                    'complete': score['complete_selected_anchors'], 'tokens': sum(p.tokens for p in selected),
                    'events': events,
                    'selected_tokens_without_annotated_character': sum(p.tokens for p in selected
                        if not any(c['covered_characters'] for c in annotations[p.parent_id].values()))}
            same(aligner.score(case, [p.entry for p in parents]), state['candidate_evaluation']['evidence_v2'], 'candidate evidence')
            snapshots.append({'query_id': state['query_id'],
                'candidate_hits': state['candidate_evaluation']['evidence_v2']['selected_hits'], 'arms': arms})
            snapshot_count += 1
        # Diagnose each single exclusion, without adding a deployable rule or
        # optimizing the policy to the benchmark. Inputs are the final saved order.
        diagnostic_exclusions = {}
        by_id = {p.parent_id: p for p in parents}
        for arm, (selected, trace) in selections.items():
            checks = []
            for omit in selected:
                if any(c['covered_characters'] for c in annotations[omit.parent_id].values()):
                    continue
                chosen, _ = pack_order([by_id[t['parent_id']] for t in trace if t['parent_id'] != omit.parent_id])
                score = aligner.score(case, [p.entry for p in chosen])
                checks.append({'omitted_parent_id': omit.parent_id, 'omitted_tokens': omit.tokens,
                    'omitted_document': Path(omit.entry['relative_path']).name,
                    'selected_hits': score['selected_hits'], 'complete': score['complete_selected_anchors'],
                    'context_tokens': sum(p.tokens for p in chosen), 'selected_parent_ids': [p.parent_id for p in chosen]})
            diagnostic_exclusions[arm] = checks
        final_events = {a: {e['parent_id']: e for e in snapshots[-1]['arms'][a]['events']} for a in LABELS}
        evidence_events = []
        for witness in final_row['minimum_witness']:
            pid = witness['parent_id']
            p = by_id[pid]
            global_item = next(r for r in trajectories[key]['snapshots'][-1]['candidate_ranking']
                               if chunks[r['position']]['parent_id'] == pid)
            evidence_events.append({'parent_id': pid, 'document': Path(p.entry['relative_path']).name,
                'section': p.entry.get('section_title', ''), 'tokens': p.tokens,
                'covered_annotations': [aid for aid, c in annotations[pid].items() if c['complete']],
                'global_parent_rank': p.rank + 1, 'global_score': global_item['reranker_score'],
                'local_positions': all_local[pid], 'events': {a: final_events[a][pid] for a in LABELS}})
        first_recovered = {aid: next((s['query_id'] for s in snapshots if s['candidate_hits'][aid]), None)
                           for aid in case.metadata['evidence_ids']}
        cases.append({'key': key, 'question': final_row['question'],
            'queries': [{k: s[k] for k in ('query_id', 'text', 'document_ids')} for s in original_row['diagnostics']['searches']],
            'first_candidate_coverage': first_recovered, 'minimum_parent_cover': final_row['minimum_parent_cover'],
            'snapshots': snapshots, 'evidence_parent_events': evidence_events,
            'single_parent_exclusion_diagnostic': {'gold_informed': True, 'used_by_selector': False,
                'selection_rule_changed': False, 'cases': diagnostic_exclusions}})
    for filename, expected in protected.items():
        same(sha(Path(filename)), expected, 'preservation ' + filename)
    result = {'title': 'Investigação da informação que ficou de fora e das duas perguntas que melhoraram',
        'date': '2026-10-16', 'source_run': str(source.resolve()), 'new_model_calls': 0,
        'new_retrieval_calls': 0, 'new_reranker_calls': 0, 'new_policy_comparison': False,
        'gold_used_only_offline_for_diagnosis': True,
        'validation': {'cases': len(cases), 'snapshots_reproduced': snapshot_count,
            'selections_reproduced': snapshot_count * 2, 'historical_inputs_unchanged': True},
        'input_sha256': protected, 'script_sha256': sha(Path(__file__)), 'cases': cases}
    output.mkdir(parents=True)
    artifacts.save_json(output / 'investigation.json', result)
    print(json.dumps({'validation': result['validation'], 'final_hits': {
        c['key']: {a: d['selected_hits'] for a, d in c['snapshots'][-1]['arms'].items()} for c in cases}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, default=ROOT / 'benchmark/results/rounds/global_order_replay_2026-10-15/run_02')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        audit(args.source_run, args.output_dir)
