"""Frozen-search replay for experimental whole-parent selection.

Default: the original 70 answerable questions, original search, global selection.
Use explicit options to compare selectors or evaluate supplementary datasets.
No retrieval, document indexing or answer generation occurs in replay mode.
"""
import argparse
import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
from transformers import AutoTokenizer

from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core import artifacts as inv
from benchmark.evaluation.evidence import SourceAligner, normalized, occurrences, source_end
from benchmark.evaluation.datasets import load_dataset
from benchmark.evaluation.literal import anchor_coverage
from benchmark.core.reproducibility import CORPUS, sha
from benchmark.core.reproducibility import implementation_hash

OLD = PROJECT_ROOT / 'benchmark/results/rounds/semantic_generalization_2026-10-07'
RULES = PROJECT_ROOT / 'benchmark/results/rounds/medicao_candidatos_blocos_2026-10-05/rescore/evidence_v2_rules.json'
POLICIES = ('global_full', 'round_robin_full', 'global_32', 'round_robin_32', 'mmr_parent_v1', 'evidence_coverage_v1')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def stable_served_model(model):
    """OpenAI model-card timestamps/permission IDs are generated per request."""
    return {key: model.get(key) for key in ('id', 'object', 'owned_by', 'root', 'parent', 'max_model_len', 'digest', 'revision')}


def provider_setup():
    bootstrap_python_path()
    from service.rag.v2.Config import load_settings, ModelSelection
    from service.rag.v2.Providers import ProviderRegistry
    cfg, _ = load_settings()
    if (cfg.provider, cfg.model) != ('vllm', 'Qwen/Qwen2.5-7B-Instruct-AWQ'):
        raise ValueError('Expected configured Qwen/vLLM')
    roles = {**cfg.roles, **{f'selection_{s}': ModelSelection(provider=cfg.provider, model=cfg.model)
                            for s in ('needs', 'support', 'bundles')}}
    limits = {**cfg.role_max_output_tokens, 'selection_needs': 1024,
              'selection_support': 2048, 'selection_bundles': 2048}
    cfg = cfg.model_copy(update={'temperature': 0, 'roles': roles, 'role_max_output_tokens': limits})
    registry = ProviderRegistry(cfg); registry.capture_payloads = True
    provider = registry.resolve('selection_needs'); provider.resolve()
    observation = provider._json('GET', '/models')
    model = next(r for r in observation['data'] if r['id'] == cfg.model)
    window = model.get('max_model_len', cfg.num_ctx)
    server = provider.transport.get(provider.base_url.rsplit('/v1', 1)[0] + '/version', timeout=30)
    server.raise_for_status()
    def count(request):
        r = provider.transport.post(provider.base_url.rsplit('/v1', 1)[0] + '/tokenize',
            json={'model': cfg.model, 'messages': [{'role': 'user', 'content': request}],
                  'add_generation_prompt': True}, timeout=30)
        r.raise_for_status(); return r.json()['count']
    return registry, count, window, {'identity': provider.identity(), 'served_model': stable_served_model(model),
        'server_version': server.json(), 'base_url': provider.base_url, 'window': window,
        'temperature': 0, 'output_limits': {k: v for k, v in limits.items() if k.startswith('selection_')}}


def read_inputs(dataset=None, frozen_dir=None, rules=None):
    """Load annotated questions and previously saved candidate rankings."""
    directory = Path(dataset) if dataset else PROJECT_ROOT / 'benchmark/datasets/real'
    source = Path(frozen_dir) if frozen_dir else OLD / 'regression'
    cases, anchors, selected = load_dataset(directory)
    rule_path = Path(rules) if rules else (selected / 'evidence_v2_rules.json' if dataset else RULES)
    frozen = {pool: inv.read_json(source / pool / 'retrieval.json') for pool in ('reference', 'directed')}
    yield 'custom' if dataset else 'regression', cases, anchors, selected, rule_path, frozen


def metrics(rows):
    result = {}
    for version in ('evidence_v2', 'literal_v1'):
        result[version] = {}
        for scope in ('collection', 'oracle_scope'):
            rr = [r for r in rows if r['condition'] == scope]
            def group(values):
                return {'total': len(values), 'complete': sum(r['evaluations'][version]['complete_selected_anchors'] for r in values),
                        'partial': float(np.mean([r['evaluations'][version]['selected_anchor_recall'] for r in values])) if values else None,
                        'errors': sum(r['status'] != 'ok' for r in values)}
            result[version][scope] = {**group(rr), 'categories': {
                c: group([r for r in rr if r['category'] == c]) for c in sorted({r['category'] for r in rr})}}
    return result


class CorpusWitness:
    """Source-only provenance validation. Constructed without annotation data."""
    def __init__(self, root):
        self.aligner = SourceAligner(root, {'anchors': {p.name: {
            'document': p.name, 'source_sha256': sha(p)} for p in root.glob('*.md')}})

    def __call__(self, entry, quote):
        alignment = self.aligner.align(entry)
        raw, text, mapping = self.aligner.sources[alignment['document']]
        needle = normalized(quote)[0]
        matches = [(a, b) for a, b in occurrences(text, needle) if all(
            text[i].isspace() or any(x <= mapping[i] < y for x, y in alignment['spans'])
            for i in range(a, b))]
        if len(matches) != 1:
            return None
        a, b = matches[0]
        return {'document': alignment['document'], 'source_start': mapping[a],
                'source_end': source_end(raw, mapping[b - 1]), 'alignment_status': alignment['status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir', type=Path, help='Optional annotated dataset; default: original 70 questions')
    parser.add_argument('--frozen-search-dir', type=Path, help='Optional source of frozen reference/directed rankings')
    parser.add_argument('--rules', type=Path, help='Optional frozen evidence_v2 rules')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--context-policy', choices=['all', *POLICIES], default='global_full',
                        help='global_full: baseline (default); all: all six selectors, including Qwen')
    parser.add_argument('--search-policy', choices=['all', 'single', 'directed_v1'], default='single',
                        help='single: original frozen search (default); directed_v1: directed searches; all: both')
    args = parser.parse_args(); bootstrap_python_path()
    from service.rag.v2.Cache import load_bundle
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.EvidenceSelection import (CoverageSelector, NEEDS_PROMPT, SUPPORT_PROMPT, BUNDLES_PROMPT,
        parents_from_ranking, shortlist, pack_order, round_robin, mmr)
    inputs = list(read_inputs(args.dataset_dir, args.frozen_search_dir, args.rules))
    source_root = args.frozen_search_dir or OLD / 'regression'
    source = inputs[0][-1]['reference']['signature']
    index = PROJECT_ROOT / 'data/cache/rag_v2' / (source['index_fingerprint'] + '.npz')
    loaded = load_bundle(index)
    if loaded is None:
        raise ValueError('Frozen index missing or corrupt; rebuilding prohibited')
    chunks, texts, catalog, vectors, _ = loaded
    if sha(index) != source['index_verification']['active_index_sha256']:
        raise ValueError('Frozen index changed')
    for name, expected in source['corpus_sha256'].items():
        if sha(CORPUS / name) != expected:
            raise ValueError('Frozen corpus changed: ' + name)
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-m3', local_files_only=True)
    @lru_cache(None)
    def tokens(text):
        return len(tokenizer.encode(text, add_special_tokens=False))
    policies = POLICIES if args.context_policy == 'all' else (args.context_policy,)
    pools = ('reference', 'directed') if args.search_policy == 'all' else (('reference',) if args.search_policy == 'single' else ('directed',))
    registry, counter, window, llm = provider_setup() if 'evidence_coverage_v1' in policies else (None, None, None, None)
    witness = CorpusWitness(CORPUS) if registry else None
    signature = {'experiment': 'evidence_selection_v1', 'implementation_sha256': implementation_hash(),
        'dataset': str(inputs[0][3]), 'policies': list(policies), 'pools': list(pools), 'index_sha256': sha(index),
        'index_fingerprint': source['index_fingerprint'], 'models': {k: source[k] for k in ('encoder', 'reranker', 'rag_config')},
        'corpus_sha256': source['corpus_sha256'], 'config_sha256': sha(PROJECT_ROOT / 'config/config.toml'),
        'datasets': {part: {'questions': sha(selected / 'questions.json'), 'anchors': sha(selected / 'evidence.json'), 'rules': sha(rules)}
                     for part, _, _, selected, rules, _ in inputs},
        'frozen_searches': {part: {p: sha(source_root / p / 'retrieval.json') for p in pools} for part, *_, frozen in inputs},
        'selector_model': llm, 'prompts': {s: digest(p) for s, p in [('needs', NEEDS_PROMPT), ('support', SUPPORT_PROMPT), ('bundles', BUNDLES_PROMPT)]},
        'parameters': {'context_tokens': 3000, 'shortlist': 32, 'global_reserve': 8, 'local_reserve': 4,
                       'mmr_weight': .7, 'max_selector_calls': 10},
        'evaluation_versions': ['literal_v1', 'evidence_v2'], 'answer_generation_calls': 0,
        'retrieval_calls': 0, 'reindexed': False,
        'selector_cache': 'exact role/prompt/schema under identical complete execution signature; no transport-error caching'}
    signature['support_protocol'] = {'citations': 'exact original source segment IDs; reconstructed quotes <=240 characters',
        'segmentation': 'disjoint character spans; entire parent preserved in source order',
        'provenance': 'repeated section prefix segmented separately; only source-verified segments are citable',
        'support_stop': 'all requested needs and dependencies have estimated direct full support; synthesis validates coherent bundles',
        'candidate_limit': 32, 'unexamined_candidates': 'remain in global fill; always diagnosed'}
    signature['fingerprint'] = digest(signature)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / 'signature.json'
    if path.exists() and inv.read_json(path) != signature:
        raise ValueError('Execution signature differs; use another directory')
    inv.save_json(path, signature)
    if not (args.output_dir / 'code.zip').exists():
        import zipfile
        with zipfile.ZipFile(args.output_dir / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            from benchmark.core.reproducibility import code_files
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')):
                archive.write(file, file.relative_to(PROJECT_ROOT))
            archive.write(PROJECT_ROOT / 'config/config.toml', 'config/config.toml')
    records = {(pool, policy): inv.Recorder(args.output_dir / pool / policy, 'retrieval', signature)
               for pool in pools for policy in policies}
    cache_path = args.output_dir / 'selector_cache.json'
    model_cache = inv.read_json(cache_path) if cache_path.exists() else {'signature': signature, 'responses': {}}
    if model_cache['signature'] != signature:
        raise ValueError('Selector cache signature differs')
    original_generate = ProviderRegistry.generate
    def guarded_generate(self, role, *a, **kw):
        if self is not registry or role not in ('selection_needs', 'selection_support', 'selection_bundles'):
            raise AssertionError('Answer generation is blocked')
        cache_key = digest([role, a, kw])
        if cache_key in model_cache['responses']:
            saved = model_cache['responses'][cache_key]
            event = copy.deepcopy(saved['event'])
            event.update(cache_hit=True, original_generation_latency_seconds=event['latency_seconds'], latency_seconds=0.)
            self.calls.append(event)
            return saved['text']
        result = original_generate(self, role, *a, **kw)
        self.calls[-1]['cache_hit'] = False
        model_cache['responses'][cache_key] = {'text': result, 'event': copy.deepcopy(self.calls[-1])}
        inv.save_json(cache_path, model_cache)
        return result
    controls = []
    with patch.object(ProviderRegistry, 'generate', guarded_generate):
        for part, cases, anchors, selected, rulespath, frozen in inputs:
            aligner = SourceAligner(CORPUS, inv.read_json(rulespath)); corpus = inv.source_corpus(anchors)
            rows = {pool: {r['key']: r for r in data['results']} for pool, data in frozen.items()}
            for pool in pools:
                for case in cases:
                    for scope in ('collection', 'oracle_scope'):
                        key = f'{case.id}:{scope}'; saved = rows[pool][key]
                        if saved['status'] != 'ok':
                            raise ValueError('Cannot silently replay failed retrieval')
                        if all(key in records[pool, policy].done for policy in policies):
                            continue
                        ranking = saved['diagnostics']['stages']['reranker']
                        searches = saved['diagnostics']['searches']
                        parents = parents_from_ranking(ranking, chunks, texts, vectors, tokens)
                        short = shortlist(parents, searches, chunks)
                        short_score = aligner.score(case, [p.entry for p in short])
                        for policy in policies:
                            recorder = records[pool, policy]
                            if key in recorder.done:
                                continue
                            start = time.perf_counter(); selector = None; diag = {'calls': 0}; status = 'ok'; error = None
                            pp = parents if policy.endswith('_full') else short
                            try:
                                if policy.startswith('global'):
                                    chosen, trace = pack_order(pp)
                                elif policy.startswith('round_robin'):
                                    chosen, trace = round_robin(pp, searches, chunks)
                                elif policy == 'mmr_parent_v1':
                                    chosen, trace = mmr(pp)
                                else:
                                    selector = CoverageSelector(registry, counter, window, witness)
                                    chosen, trace, diag = selector.select(case.question, case.metadata.get('history', []), pp)
                            except Exception as exc:
                                chosen, trace = [], []
                                status = 'error'; error = {'type': type(exc).__name__, 'message': str(exc)}
                                diag = {'status': 'error', 'calls': len(selector.events) if selector else 0,
                                        'events': selector.events if selector else []}
                            entries = [p.entry for p in chosen]
                            latency = time.perf_counter() - start
                            evaluations = {'evidence_v2': aligner.score(case, entries),
                                           'literal_v1': anchor_coverage(case, {'evidence': entries}, anchors, corpus)}
                            if policy == ('global_full' if pool == 'reference' else 'round_robin_full'):
                                if [e['parent_id'] for e in entries] != [e['parent_id'] for e in saved['evidence']]:
                                    raise AssertionError('Historical parent order not reproduced')
                                for version in evaluations:
                                    if evaluations[version]['selected_hits'] != saved['evaluations'][version]['selected_hits']:
                                        raise AssertionError('Historical evaluation not reproduced')
                                controls.append(key + '/' + pool)
                            events = [event for call in diag.get('events', []) for event in call['generation_events']]
                            recorder.add(key, status=status, error=error, case_id=case.id, condition=scope,
                                source_split=part, query=saved['query'], scope=saved['scope'], category=case.category,
                                field=case.metadata.get('field', 'legacy'), family_ids=case.metadata.get('family_ids', []),
                                fact_ids=case.metadata['evidence_ids'], evidence=entries, packing_trace=trace,
                                diagnostics=saved['diagnostics'], stage_evaluations=saved['stage_evaluations'],
                                shortlist_parent_ids=[p.parent_id for p in short], shortlist_evaluation=short_score,
                                evaluations=evaluations, selector=diag, context_tokens=sum(p.tokens for p in chosen),
                                latency_seconds=latency, historical_retrieval_latency_seconds=saved.get('reused_control', {}).get('historical_latency_seconds', saved['latency_seconds']),
                                total_latency_seconds=saved.get('reused_control', {}).get('historical_latency_seconds', saved['latency_seconds']) + latency,
                                selector_prompt_tokens=sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events),
                                selector_completion_tokens=sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events),
                                selector_physical_calls=sum(not e.get('cache_hit', False) for e in events),
                                selector_cache_hits=sum(e.get('cache_hit', False) for e in events),
                                selector_physical_prompt_tokens=sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events if not e.get('cache_hit', False)),
                                selector_physical_completion_tokens=sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events if not e.get('cache_hit', False)),
                                source_candidate_digest=digest(ranking), frozen_search_sha256=signature['frozen_searches'][part][pool])
    expected = 2 * sum(len(cases) for _, cases, *_ in inputs)
    for recorder in records.values():
        rr = recorder.data['results']
        if len(rr) != expected or len({r['key'] for r in rr}) != expected:
            raise AssertionError('Incomplete experiment')
        recorder.finish(**metrics(rr))
    inv.save_json(args.output_dir / 'execution_status.json', {'status': 'complete', 'observations': expected * len(records),
        'questions': expected // 2, 'controls_checked_this_invocation': len(controls),
        'errors': {f'{pool}/{policy}': sum(r['status'] != 'ok' for r in rec.data['results']) for (pool, policy), rec in records.items()},
        'answer_generation_calls': 0, 'retrieval_calls': 0, 'signature': signature['fingerprint']})
    if implementation_hash() != signature['implementation_sha256'] or sha(index) != signature['index_sha256']:
        raise ValueError('Code or index changed during execution')
    for filename, expected_sha in signature['corpus_sha256'].items():
        if sha(CORPUS / filename) != expected_sha:
            raise ValueError('Source changed during execution')


if __name__ == '__main__':
    main()
