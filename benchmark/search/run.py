"""Original retrieval, single-shot planning and bounded adaptive investigation."""
import argparse
import copy
import time
import zipfile
from pathlib import Path
from unittest.mock import patch

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.config import load_planner_input_format
from benchmark.core.reproducibility import CORPUS, code_files, implementation_hash, sha
from benchmark.evaluation.evidence import SourceAligner
from benchmark.evaluation.literal import anchor_coverage
from benchmark.selection.run import digest, metrics
from benchmark.search.runtime import load_reference, llm_setup, build_retriever, verify_remote_identity

CONDITIONS = ('A_baseline', 'B_single_shot', 'C_adaptive')
POLICIES = {'B_single_shot': 'single_shot', 'C_adaptive': 'adaptive'}
CONTRACT_CONDITIONS = ('A_baseline', 'B_full_contract', 'C_minimal_contract')
CONTRACTS = {'B_full_contract': 'full_evidence_v1', 'C_minimal_contract': 'minimal_action_v1'}


def original_run(saved):
    from service.rag.v2.DirectedRetrieval import DirectedSearch
    return (DirectedSearch('Q0', saved['query'], saved['scope']),
            copy.deepcopy(saved['diagnostics']['searches'][0]['diagnostics']['stages']['reranker']),
            copy.deepcopy(saved['diagnostics']['searches'][0]['diagnostics']))


def get_plan(cache, key, callback, save):
    """Never repeat a remotely started decision with unknown outcome on resume."""
    if key in cache:
        value = cache[key]
        if value['status'] == 'started':
            value = {'status': 'error', 'error': {'type': 'InterruptedPlanning',
                     'message': 'Planning was interrupted; remote usage unknown, call will not be repeated'},
                     'events': [], 'planning_calls_unknown': True}
            cache[key] = value; save()
        return value
    cache[key] = {'status': 'started'}; save()
    try:
        value = callback()
    except Exception as exc:
        value = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}, 'events': []}
    cache[key] = value; save()
    return value


def is_transport_error(error):
    message = (error or {}).get('message', '').lower()
    return any(s in message for s in ('timeout', 'timed out', 'could not connect', 'http ',
                                    'connection', 'network', 'remotedisconnected', 'ufc llm request failed'))


def audit_initial_inputs(planner, cases, rows, make_snapshot):
    """Readiness audit, using only legitimate question/history/retrieval input."""
    results = []
    for case in cases:
        for scope in ('collection', 'oracle_scope'):
            saved = rows[f'{case.id}:{scope}']
            initial = original_run(saved)
            snap = make_snapshot(initial[1], [initial])
            for policy in (('adaptive',) if planner.decision_contract == 'minimal_action_v1' else ('single_shot', 'adaptive')):
                row = {'key': saved['key'], 'policy': policy, 'decision_contract': planner.decision_contract}
                try:
                    request = planner.prepare(policy, case.question, case.metadata.get('history', []),
                                              snap, {}, saved['scope'], 3)
                    row.update(status='fits', input_tokens_counted=request['input_tokens_counted'],
                               samples_removed=request['samples_removed'])
                except Exception as exc:
                    row.update(status='error', error={'type': type(exc).__name__, 'message': str(exc)})
                results.append(row)
    return {'status': 'passed' if all(r['status'] == 'fits' for r in results) else 'failed',
            'scope': 'initial states only; later states still checked before each call',
            'failed_question_scopes': sorted({r['key'] for r in results if r['status'] != 'fits'}),
            'generation_calls': 0, 'results': results}


def preflight(planner, registry, raw_count, contract_study=False):
    """Check transport/accounting; invalid model decisions are recorded outcomes."""
    import numpy as np
    from types import SimpleNamespace
    from service.rag.v2.AdaptiveRetrieval import Snapshot, InvestigationPlanner
    from service.rag.v2.DirectedRetrieval import DirectedSearch
    from service.rag.v2.EvidenceSelection import Parent
    docs = [{'document_id': 'synthetic-prisma', 'document_name': 'Registro Prisma'},
            {'document_id': 'synthetic-eva', 'document_name': 'Currículo Eva'}]
    texts = ['Eva criou o sensor Prisma.', 'Eva concluiu Engenharia na Universidade Aurora.']
    chunks = [SimpleNamespace(chunk_id=f'S{i}', parent_id=f'P{i}', document_id=docs[i]['document_id'],
                              text=text, provenance={}) for i, text in enumerate(texts)]
    parents = [Parent(f'P{i}', {'parent_id': f'P{i}', 'document_id': docs[i]['document_id'], 'text': t},
                      i, 20, np.array([1.])) for i, t in enumerate(texts)]
    instance = InvestigationPlanner(registry, docs, chunks, planner.count, planner.window, planner.output_tokens,
                                    input_format=planner.input_format, decision_contract=planner.decision_contract,
                                    reason_validation=planner.reason_validation)
    ranking = [{'position': 0, 'chunk_id': 'S0'}]
    original = DirectedSearch('Q0', 'Onde se formou quem criou Prisma?', None)
    initial = Snapshot(ranking, [(original, ranking, {})], parents[:1], parents[:1], [])
    rows = []
    # Test both interfaces plus final support on a dependent relation.
    examples = (
        ('single_shot', initial, {}, 3), ('adaptive', initial, {}, 3),
        ('adaptive', Snapshot(ranking, [(original, ranking, {}),
             (DirectedSearch('Q1', 'formação acadêmica de Eva', None), ranking, {})], parents, parents, []),
         {'needs': [{'need_id': 'N1', 'text': 'identidade de quem criou Prisma', 'depends_on': []},
                    {'need_id': 'N2', 'text': 'formação dessa pessoa', 'depends_on': ['N1']}]}, 0))
    if contract_study:
        examples = examples[1:]
    for mode, snap, ledger, remaining in examples:
        request = instance.prepare(mode, original.text, [], snap, ledger, None, remaining)
        before = len(registry.calls)
        try:
            result = instance.execute(request)
        except Exception as exc:
            events = registry.calls[before:]
            # Generation failures abort readiness. Locally rejected decisions
            # are model behaviour for the measured experiment, not transport.
            if len(events) != 1 or (events[0].get('status') != 'ok' and
                not events[0].get('output_at_limit')):
                raise
            result = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
        event = registry.calls[-1]
        if getattr(getattr(registry, 'config', None), 'provider', None) == 'ollama':
            # The common generate guard verifies every successful wire request.
            if event.get('sent_parameters', {}).get('think') is not True:
                raise ValueError('Synthetic thinking mode was not enabled')
        observed = (event.get('usage') or {}).get('prompt_tokens')
        exact = raw_count(event.get('prompt', request['prompt']))
        if observed is not None and observed > exact + 512:
            raise ValueError('Cumbuco input accounting exceeds tokenizer margin')
        rows.append({'mode': mode, 'remaining_searches': remaining, 'result': result,
                     'event': event, 'local_prompt_tokens': exact, 'observed_prompt_tokens': observed})
        if len(registry.calls) - before != 1:
            raise AssertionError('Synthetic call count exceeded')
    return {'status': 'passed', 'readiness': 'transport_and_accounting; not model correctness',
            'synthetic_planning_calls': len(rows), 'examples': rows,
            'accepted_decisions': sum(r['result']['status'] == 'ok' for r in rows),
            'warning': 'Reported model capacity does not prove effective context or constrained JSON decoding'}


def run(output, preflight_only=False, search_policy='all', planner_input_format=None, study='adaptive'):
    bootstrap_python_path()
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.AdaptiveRetrieval import (InvestigationPlanner, InvestigationController, Snapshot,
                                                COMMON_INSTRUCTION, MINIMAL_INSTRUCTION, MODE_INSTRUCTION, VERSION, Decision, MinimalDecision)
    from service.rag.v2.DirectedRetrieval import merge_and_rerank
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    ref = load_reference()
    registry, count, raw_count, model, session, base = llm_setup()
    if not 0 < model['max_output_tokens'] < model['num_ctx'] or model['timeout_seconds'] <= 0:
        raise ValueError('Invalid benchmark output budget or timeout')
    if study == 'decision_contract' and search_policy != 'all':
        raise ValueError('Decision-contract study compares both adaptive contracts; use --search-policy all')
    if study == 'decision_contract' and (planner_input_format or load_planner_input_format()) != 'compact_v1':
        raise ValueError('Decision-contract study freezes compact_v1 input rendering')
    arms = CONDITIONS if search_policy == 'all' else ('A_baseline', next(a for a, p in POLICIES.items() if p == search_policy))
    if study == 'decision_contract':
        arms = CONTRACT_CONDITIONS
    input_format = planner_input_format or load_planner_input_format()
    planner = InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'],
                                   input_format=input_format)
    planners = ({a: InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'],
                model['max_output_tokens'], input_format=input_format, decision_contract=CONTRACTS[a]) for a in arms[1:]}
                if study == 'decision_contract' else {a: planner for a in arms[1:]})
    signature = {'study': study, 'experiment': 'decision_contract_v1' if study == 'decision_contract' else VERSION, 'implementation_sha256': implementation_hash(),
        'index_sha256': sha(ref['index']), 'index_fingerprint': ref['source']['signature']['index_fingerprint'],
        'models': {k: ref['source']['signature'][k] for k in ('encoder', 'reranker', 'rag_config')},
        'llm': model, 'planner_prompt_sha256': digest([COMMON_INSTRUCTION, MINIMAL_INSTRUCTION, MODE_INSTRUCTION]),
        'decision_schema_sha256': digest([Decision.model_json_schema(), MinimalDecision.model_json_schema()]),
        'decision_contracts': {a: p.decision_contract for a, p in planners.items()},
        'config_sha256': sha(PROJECT_ROOT / 'config/config.toml'),
        'corpus_sha256': ref['source']['signature']['corpus_sha256'],
        'datasets': {'questions': sha(ref['directory'] / 'questions.json'), 'anchors': sha(ref['directory'] / 'evidence.json'),
                     'rules': sha(ref['rules_path'])},
        'frozen_searches_sha256': sha(PROJECT_ROOT / 'benchmark/results/rounds/semantic_generalization_2026-10-07/regression/reference/retrieval.json'),
        'conditions': list(arms), 'evaluation_versions': ['evidence_v2', 'literal_v1'],
        'parameters': {'search_k': 30, 'rerank_k': 60, 'context_tokens': 3000, 'context_policy': 'global_score',
                       'max_searches': 4, 'max_decisions': {'single_shot': 1, 'adaptive': 4},
                       'sample_limit': 6, 'sample_per_document': 2, 'needs_limit': 6, 'planner_input_format': input_format,
                       'answer_generation_calls': 0, 'failure_policy': 'preserve_last_context', 'reindexing': False}}
    signature['fingerprint'] = digest(signature)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'signature.json'
    if path.exists() and artifacts.read_json(path) != signature:
        raise ValueError('Execution signature changed; use a new output directory')
    artifacts.save_json(path, signature)
    if study == 'decision_contract':
        artifacts.save_json(output / 'planner_contracts.json', {
            'full_evidence_v1': {'instruction': COMMON_INSTRUCTION, 'schema': Decision.model_json_schema()},
            'minimal_action_v1': {'instruction': MINIMAL_INSTRUCTION, 'schema': MinimalDecision.model_json_schema()},
            'mode_instruction': MODE_INSTRUCTION['adaptive']})
    from benchmark.search.input_audit import protected_files, verify_preserved
    protected_path = output / 'protected_before.json'
    protected = artifacts.read_json(protected_path) if protected_path.exists() else protected_files(output)
    artifacts.save_json(protected_path, protected)
    artifacts.save_json(output / 'evaluation_rules.json', artifacts.read_json(ref['rules_path']))
    if not (output / 'code.zip').exists():
        with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')):
                z.write(file, file.relative_to(PROJECT_ROOT))
            z.write(PROJECT_ROOT / 'config/config.toml', 'config/config.toml')
    aligner = SourceAligner(CORPUS, artifacts.read_json(ref['rules_path']))
    corpus = artifacts.source_corpus(ref['anchors'])
    records = {a: artifacts.Recorder(output / a, 'retrieval', signature) for a in arms}
    cache_path = output / 'cache.json'
    cache = artifacts.read_json(cache_path) if cache_path.exists() else {'signature': signature, 'decisions': {}, 'queries': {}, 'global': {}}
    if cache['signature'] != signature:
        raise ValueError('Cache signature differs')
    def save_cache(): artifacts.save_json(cache_path, cache)
    def evaluate(case, parents):
        entries = [p.entry for p in parents]
        return {'evidence_v2': aligner.score(case, entries),
                'literal_v1': anchor_coverage(case, {'evidence': entries}, ref['anchors'], corpus)}
    def snapshot(ranking, runs):
        parents = parents_from_ranking(ranking, ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
        selected, trace = pack_order(parents)
        return Snapshot(ranking, runs, parents, selected, trace)
    def add_row(arm, case, saved, snap, planning, costs):
        scores = evaluate(case, snap.selected); full = evaluate(case, snap.parents)
        searches, seen = [], set()
        for search, ranking, diag in snap.runs:
            ids = {r['chunk_id'] for r in ranking}
            searches.append({**search.to_dict(), 'diagnostics': diag, 'candidates_added': len(ids - seen)})
            seen.update(ids)
        events = planning.get('events', [])
        timing = {k: v for k, v in costs.items() if k != 'reranks'}
        timing['planning'] = sum(e['latency_seconds'] for e in events)
        timing['total'] = sum(timing.get(k, 0) for k in ('historical_original', 'planning', 'query_seconds', 'global_rerank_seconds', 'selection'))
        records[arm].add(saved['key'], status=planning['status'], error=planning.get('errors', [None])[0] if planning.get('errors') else None,
            case_id=case.id, condition=saved['condition'], category=case.category, field=case.metadata.get('field', 'legacy'),
            family_ids=case.metadata.get('family_ids', []), fact_ids=case.metadata['evidence_ids'],
            query=saved['query'], scope=saved['scope'], evidence=[p.entry for p in snap.selected],
            packing_trace=snap.packing_trace, context_tokens=sum(p.tokens for p in snap.selected), evaluations=scores,
            stage_evaluations={'rrf': {'all': full}}, candidate_evaluation=full,
            diagnostics={'stages': {'reranker': snap.ranking}, 'searches': searches, 'global_reranks': costs.get('reranks', [])},
            plan=planning, stop_reason=planning.get('stop_reason'), declared_sufficient=planning.get('declared_sufficient', False),
            shared_search_id=saved['key'], source_candidate_digest=digest(snap.ranking),
            shared_queries_digest=digest(searches), planner_digest=digest(planning),
            latency_seconds=timing['total'], costs=timing, search_count=len(searches),
            planning_calls=len(events), planning_prompt_tokens=sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events),
            planning_completion_tokens=sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events),
            reranker_pairs_logical=sum(len(s['diagnostics']['stages']['reranker']) for s in searches) + sum(r['pairs'] for r in costs.get('reranks', [])))
    original_generate = ProviderRegistry.generate
    def guarded(self, role, *args, **kwargs):
        if self is not registry or role != 'planner':
            raise AssertionError('Only configured investigation decisions are allowed; final answer blocked')
        result = original_generate(self, role, *args, **kwargs)
        event = self.calls[-1]
        from benchmark.search.runtime import verify_generation_event
        verify_generation_event(model, event)
        observed = (event.get('usage') or {}).get('prompt_tokens')
        request = event.get('prompt', args[0])
        if observed is not None and (observed > count(request) or observed + model['max_output_tokens'] > model['num_ctx']):
            raise ValueError('Server input usage exceeds safe decision budget')
        return result
    def execution_status(reason=None):
        complete = all(len(r.data['results']) == 140 for r in records.values())
        events = [e for p in cache['decisions'].values() for e in p.get('events', [])]
        value = {'status': 'complete' if complete and reason is None else 'incomplete',
                 'questions': 70, 'conditions': list(arms), 'observations': sum(len(r.data['results']) for r in records.values()),
                 'errors': {a: sum(r['status'] != 'ok' for r in rec.data['results']) for a, rec in records.items()},
                 'planning_calls': len(events), 'synthetic_calls': artifacts.read_json(output / 'preflight.json').get('synthetic_planning_calls', 0) if (output / 'preflight.json').exists() else len(registry.calls),
                 'planning_usage_unknown': any(p.get('planning_calls_unknown') for p in cache['decisions'].values()),
                 'physical_retrieval_queries': len(cache['queries']), 'physical_global_reranks': len(cache['global']),
                 'physical_reranker_pairs': sum(len(v.get('ranking', [])) for group in ('queries', 'global') for v in cache[group].values()),
                 'physical_planning_prompt_tokens': sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events),
                 'physical_planning_completion_tokens': sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events),
                 'answer_generation_calls': 0, 'decision': 'pending_user_review', 'stop_reason': reason}
        artifacts.save_json(output / 'execution_status.json', value)
    retriever = None; interrupted = False; transport_errors = 0
    with patch.object(ProviderRegistry, 'generate', guarded):
        for case in ref['cases']:
            for scope in ('collection', 'oracle_scope'):
                saved = ref['rows'][f'{case.id}:{scope}']; initial = original_run(saved)
                snap = snapshot(initial[1], [initial]); scores = evaluate(case, snap.selected)
                if snap.context_ids() != [e['parent_id'] for e in saved['evidence']]:
                    raise ValueError('Original baseline parent order differs')
                if any(scores[v]['selected_hits'] != saved['evaluations'][v]['selected_hits'] for v in scores):
                    raise ValueError('Original baseline evaluation differs')
                if saved['key'] not in records['A_baseline'].done:
                    add_row('A_baseline', case, saved, snap, {'status': 'ok', 'events': [], 'stop_reason': 'baseline'},
                            {'historical_original': saved['latency_seconds']})
        records['A_baseline'].finish(**metrics(records['A_baseline'].data['results']))
        audits = {a: audit_initial_inputs(p, ref['cases'], ref['rows'], snapshot) for a, p in planners.items()}
        input_audit = {'status': 'passed' if all(v['status'] == 'passed' for v in audits.values()) else 'failed', 'contracts': audits}
        artifacts.save_json(output / 'input_budget_audit.json', input_audit)
        if not (output / 'preflight.json').exists():
            try:
                synthetic_path = output / 'preflight_cache.json'
                synthetic_cache = artifacts.read_json(synthetic_path) if synthetic_path.exists() else {}
                examples = []
                for arm, instance in (planners.items() if study == 'decision_contract' else [('shared', planner)]):
                    value = get_plan(synthetic_cache, arm,
                        lambda: preflight(instance, registry, raw_count, study == 'decision_contract'),
                        lambda: artifacts.save_json(synthetic_path, synthetic_cache))
                    if value['status'] != 'passed':
                        raise ValueError('Synthetic preflight did not finish; inspect preflight_cache.json')
                    examples.append({'arm': arm, **value})
                if model['provider'] == 'ollama':
                    response = session.get(base + '/api/ps', timeout=30); response.raise_for_status()
                    resident = next((m for m in response.json()['models'] if m.get('digest') == model['digest']), None)
                    if not resident or resident.get('context_length') != model['num_ctx']:
                        raise ValueError('Actual local model residency does not match requested context')
                artifacts.save_json(output / 'preflight.json', {'status': 'passed', 'examples': examples,
                    'resident_model': resident if model['provider'] == 'ollama' else None,
                    'synthetic_planning_calls': sum(v['synthetic_planning_calls'] for v in examples)})
            except Exception as exc:
                artifacts.save_json(output / 'preflight_failure.json', {'status': 'failed', 'type': type(exc).__name__, 'message': str(exc), 'events': registry.calls})
                execution_status('preflight_failure')
                from benchmark.search.report import report
                report(output)
                raise
        if preflight_only:
            execution_status('preflight_only'); return
        if input_audit['status'] != 'passed':
            execution_status('initial_input_budget_failure')
            from benchmark.search.report import report
            report(output)
            raise ValueError('Initial planner inputs exceed configured window; see input_budget_audit.json. Measured run not started.')
        retriever = build_retriever(ref)
        # Case IDs/categories/evaluation exist only in this orchestration layer.
        for case_index, case in enumerate(ref['cases']):
            for scope in ('collection', 'oracle_scope'):
                key = f'{case.id}:{scope}'; saved = ref['rows'][key]
                order = arms[1:] if study != 'decision_contract' or case_index % 2 == 0 else tuple(reversed(arms[1:]))
                for arm in order:
                    if key in records[arm].done:
                        continue
                    planner = planners[arm]
                    physical_start = len(registry.calls)
                    mode = 'adaptive' if study == 'decision_contract' else POLICIES[arm]; initial = original_run(saved); first = snapshot(initial[1], [initial])
                    costs = {'historical_original': saved['latency_seconds'], 'query_seconds': 0., 'global_rerank_seconds': 0., 'selection': 0., 'reranks': []}
                    def decide(policy, current, ledger, remaining):
                        before = len(registry.calls)
                        try:
                            request = planner.prepare(policy, case.question, case.metadata.get('history', []), current,
                                                      ledger, saved['scope'], remaining)
                        except Exception as exc:
                            return {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}, 'events': []}
                        ck = digest({'signature': signature['fingerprint'], 'request': request})
                        def callback():
                            before_call = len(registry.calls)
                            try:
                                result = planner.execute(request)
                            except Exception as exc:
                                result = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
                            result.update(events=copy.deepcopy(registry.calls[before_call:]), request=request)
                            return result
                        return get_plan(cache['decisions'], ck, callback, save_cache)
                    def advance(search, previous):
                        ck = digest([search.text, search.document_ids])
                        if ck not in cache['queries']:
                            t = time.perf_counter()
                            try:
                                ranking, diag = retriever.search(search.text, search.document_ids, 1)
                                value = {'status': 'ok', 'ranking': ranking, 'diagnostics': diag, 'latency_seconds': time.perf_counter()-t}
                            except Exception as exc:
                                value = {'status': 'error', 'error': str(exc), 'latency_seconds': time.perf_counter()-t}
                            cache['queries'][ck] = value; save_cache()
                        found = cache['queries'][ck]; costs['query_seconds'] += found['latency_seconds']
                        if found['status'] != 'ok':
                            raise RuntimeError(found['error'])
                        runs = previous.runs + [(search, found['ranking'], found['diagnostics'])]
                        gk = digest([saved['query'], [(s.to_dict(), rr) for s, rr, _ in runs]])
                        cached = gk in cache['global']
                        if not cached:
                            t = time.perf_counter()
                            try:
                                ranking = merge_and_rerank(saved['query'], runs, ref['chunks'], retriever.reranker)
                                value = {'status': 'ok', 'ranking': ranking, 'latency_seconds': time.perf_counter()-t}
                            except Exception as exc:
                                value = {'status': 'error', 'error': str(exc), 'latency_seconds': time.perf_counter()-t}
                            cache['global'][gk] = value; save_cache()
                        result = cache['global'][gk]; costs['global_rerank_seconds'] += result['latency_seconds']
                        if result['status'] != 'ok':
                            raise RuntimeError(result['error'])
                        costs['reranks'].append({'pairs': len(result['ranking']), 'cache_hit': cached, 'latency_seconds': result['latency_seconds']})
                        t = time.perf_counter(); new = snapshot(result['ranking'], runs)
                        costs['selection'] += time.perf_counter()-t
                        return new
                    final, planning = InvestigationController().run(mode, first, decide, advance, saved['scope'])
                    add_row(arm, case, saved, final, planning, costs)
                    # Count consecutive transport failures per physical decision, not repeated cached errors.
                    for event in registry.calls[physical_start:]:
                        transport_errors = transport_errors + 1 if event.get('status') == 'error' and is_transport_error({'message': event.get('error', '')}) else 0
                    execution_status()
                    print(f"progress: {sum(len(r.data['results']) for r in records.values())}/{140*len(arms)}, measured decisions {sum(len(d.get('events', [])) for d in cache['decisions'].values())}", flush=True)
                    if transport_errors >= 3:
                        interrupted = True; break
                if interrupted: break
            if interrupted: break
    for record in records.values():
        if len(record.data['results']) == 140:
            record.finish(**metrics(record.data['results']))
    for name, expected in signature['datasets'].items():
        file = ref['rules_path'] if name == 'rules' else ref['directory'] / ('questions.json' if name == 'questions' else 'evidence.json')
        if sha(file) != expected:
            raise ValueError('Frozen dataset or evaluation changed during execution')
    if sha(PROJECT_ROOT / 'config/config.toml') != signature['config_sha256']:
        raise ValueError('Configuration changed during execution')
    if implementation_hash() != signature['implementation_sha256'] or sha(ref['index']) != signature['index_sha256']:
        raise ValueError('Code or index changed during execution')
    for name, expected in signature['corpus_sha256'].items():
        if sha(CORPUS / name) != expected:
            raise ValueError('Corpus changed during execution')
    verify_remote_identity(model, session, base)
    artifacts.save_json(output / 'historical_preservation.json', verify_preserved(protected))
    execution_status('three_consecutive_transport_failures' if interrupted else None)
    from benchmark.search.report import report
    report(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--study', choices=('adaptive', 'decision_contract', 'reason_validation', 'agent_interface', 'global_order_replay', 'document_budget_replay', 'document_budget_cycle'), default='adaptive')
    parser.add_argument('--source-run', type=Path, help='Read-only historical source for the selected study')
    parser.add_argument('--search-policy', choices=('all', 'single_shot', 'adaptive'), default='all')
    parser.add_argument('--planner-input-format', choices=('legacy_v1', 'compact_v1'))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--audit-inputs', action='store_true', help='Offline size/preservation audit; no endpoint or retrieval calls')
    group.add_argument('--speed-test', action='store_true', help='Paired legacy/compact planner timings; no new retrieval or answer generation')
    args = parser.parse_args()
    if args.study == 'document_budget_cycle':
        if (args.source_run is None or args.audit_inputs or args.speed_test
                or args.search_policy != 'all' or args.planner_input_format is not None):
            parser.error('document_budget_cycle requires --source-run; fixed paired 3000/6000 live study')
        from benchmark.search.document_budget_cycle import run as run_document_budget_cycle
        run_document_budget_cycle(args.output_dir, args.source_run, args.preflight_only)
        return
    if args.study == 'document_budget_replay':
        if (args.source_run is None or args.preflight_only or args.audit_inputs or args.speed_test
                or args.search_policy != 'all' or args.planner_input_format is not None):
            parser.error('document_budget_replay requires --source-run; this fixed 3000/6000 comparison is entirely offline')
        from benchmark.search.document_budget_replay import run as run_document_budget_replay
        run_document_budget_replay(args.output_dir, args.source_run)
        return
    if args.study == 'global_order_replay':
        if (args.source_run is None or args.preflight_only or args.audit_inputs or args.speed_test
                or args.search_policy != 'all' or args.planner_input_format is not None):
            parser.error('global_order_replay requires --source-run; it is always offline and accepts no live-run options')
        from benchmark.search.global_order_replay import run as run_global_order_replay
        run_global_order_replay(args.output_dir, args.source_run)
        return
    if args.study == 'agent_interface':
        if args.source_run is None or args.audit_inputs or args.speed_test or args.search_policy != 'all' or args.planner_input_format not in (None, 'compact_v1'):
            parser.error('agent_interface requires --source-run and compact_v1; --preflight-only performs offline reproduction')
        from benchmark.search.agent_interface import run as run_agent_interface
        run_agent_interface(args.output_dir, args.source_run, args.preflight_only)
        return
    if args.study == 'reason_validation':
        if args.source_run is None or args.audit_inputs or args.speed_test or args.search_policy != 'all' or args.planner_input_format not in (None, 'compact_v1'):
            parser.error('reason_validation requires --source-run, all policies and compact_v1; use --preflight-only for offline control reproduction')
        from benchmark.search.reason_validation import run as run_reason_validation
        run_reason_validation(args.output_dir, args.source_run, args.preflight_only)
        return
    if args.audit_inputs or args.speed_test:
        from benchmark.search.input_audit import audit, speed_test
        if args.study == 'decision_contract':
            from benchmark.search.input_audit import contract_audit, contract_speed_test
            (contract_audit if args.audit_inputs else contract_speed_test)(args.output_dir)
        else:
            (audit if args.audit_inputs else speed_test)(args.output_dir)
    else:
        run(args.output_dir, args.preflight_only, args.search_policy, args.planner_input_format, args.study)


if __name__ == '__main__': main()
