"""Paired document-search interface study; the CLI remains benchmark search."""
import copy
import json
import time
import zipfile
from pathlib import Path

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.reproducibility import CORPUS, implementation_hash, sha, code_files
from benchmark.core.timing import RunClock
from benchmark.evaluation.evidence import SourceAligner
from benchmark.evaluation.literal import anchor_coverage
from benchmark.search.runtime import load_reference, llm_setup, build_retriever, verify_generation_event, verify_remote_identity
from benchmark.search.run import original_run, get_plan, is_transport_error, preflight
from benchmark.search.reason_validation import frozen_setup, replay_decision, checkpoint_operation
from benchmark.selection.run import digest, metrics

ARMS = ('A_baseline', 'B_tolerant', 'C_simple', 'D_feedback')
POLICIES = {'C_simple': 'stop_on_error', 'D_feedback': 'bounded_feedback_v1'}


def load_source(source_run):
    source = {k: artifacts.read_json(source_run / name) for k, name in
              [('signature', 'signature.json'), ('cache', 'cache.json'), ('A', 'A_baseline/retrieval.json'),
               ('B', 'C_tolerant/retrieval.json'), ('execution', 'execution_status.json')]}
    if source['signature']['study'] != 'reason_validation' or source['execution']['status'] != 'complete':
        raise ValueError('agent_interface requires the completed reason_validation source')
    if source['cache']['signature'] != source['signature']:
        raise ValueError('Source cache signature differs')
    for filename, expected in source['signature']['source_hashes'].items():
        if sha(Path(filename)) != expected:
            raise ValueError('Historical ancestor changed: ' + filename)
    ancestor = next(Path(n).parent for n in source['signature']['source_hashes'] if Path(n).name == 'signature.json')
    historical = {'signature': artifacts.read_json(ancestor / 'signature.json')}
    operations = artifacts.read_json(ancestor / 'cache.json')
    for kind in ('queries', 'global'):
        operations[kind].update(source['cache'][kind])
    source['historical'], source['operations'] = historical, operations
    return source


def run(output, source_run, preflight_only=False):
    output, source_run = output.resolve(), source_run.resolve()
    if output == source_run or output.is_relative_to(source_run) or source_run.is_relative_to(output):
        raise ValueError('Use a separate output directory outside the historical source')
    output.mkdir(parents=True, exist_ok=True)
    clock = RunClock(output / 'timing.json')
    try:
        _run(output, source_run, preflight_only, clock)
    except BaseException as exc:
        artifacts.save_json(output / 'blocked.json', {'type': type(exc).__name__, 'message': str(exc),
                            'instruction': 'Do not repeat unknown calls or change provider automatically.'})
        status_path = output / 'execution_status.json'
        status = artifacts.read_json(status_path) if status_path.exists() else {}
        status.update(status='incomplete', stop_reason=type(exc).__name__, blocker=str(exc))
        artifacts.save_json(status_path, status)
        clock.finish('interrupted' if isinstance(exc, KeyboardInterrupt) else 'blocked')
        if (output / 'A_baseline/retrieval.json').exists():
            write_report(output)
        raise
    finally:
        if clock.session['status'] == 'running':
            clock.finish('offline_controls_complete' if preflight_only else 'complete')


def _run(output, source_run, preflight_only, clock):
    bootstrap_python_path()
    from service.rag.v2.AdaptiveRetrieval import (InvestigationPlanner, InvestigationController, Snapshot,
        DOCUMENT_SEARCH_INSTRUCTION, MODE_INSTRUCTION, DocumentSearchDecision, TolerantDocumentSearchDecision, decision_failure)
    from service.rag.v2.DirectedRetrieval import merge_and_rerank
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    from benchmark.search.input_audit import protected_files, verify_preserved

    source = load_source(source_run)
    ref = load_reference()
    registry, count, raw_count = frozen_setup(source['historical'], ref)
    model = source['signature']['llm']
    if model != source['historical']['signature']['llm']:
        raise ValueError('Source no-thinking model/settings differ from the ancestor')
    rows = {name: {r['key']: r for r in source[name]['results']} for name in ('A', 'B')}
    if any(set(data) != set(ref['rows']) for data in rows.values()):
        raise ValueError('Historical conditions do not cover the same questions/scopes')
    signature = {'study': 'agent_interface', 'version': 'document_search_feedback_v1', 'conditions': list(ARMS),
        'implementation_sha256': implementation_hash(), 'config_sha256': sha(PROJECT_ROOT / 'config/config.toml'),
        'source_run': str(source_run), 'source_hashes': {name: sha(source_run / name) for name in
            ('signature.json', 'cache.json', 'A_baseline/retrieval.json', 'C_tolerant/retrieval.json', 'execution_status.json')},
        'llm': model, 'parameters': source['signature']['parameters'], 'datasets': source['signature']['datasets'],
        'index_sha256': source['signature']['index_sha256'], 'evaluation_versions': ['evidence_v2', 'literal_v1'],
        'prompt_sha256': digest([DOCUMENT_SEARCH_INSTRUCTION, MODE_INSTRUCTION['adaptive']]),
        'schema_sha256': digest(DocumentSearchDecision.model_json_schema()),
        'acceptance_schema_sha256': digest(TolerantDocumentSearchDecision.model_json_schema()),
        'controller_policies': POLICIES, 'max_searches': 4, 'max_decisions': 4,
        'context_policy': 'global_score', 'context_tokens': 3000, 'search_k_per_channel': 30,
        'question_count': len(ref['cases']), 'reason_validation': 'soft_length_v1'}
    signature['fingerprint'] = digest(signature)
    sigpath = output / 'signature.json'
    if sigpath.exists() and artifacts.read_json(sigpath) != signature:
        raise ValueError('Execution signature changed; use a new output directory')
    artifacts.save_json(sigpath, signature)
    protected_path = output / 'protected_before.json'
    protected = artifacts.read_json(protected_path) if protected_path.exists() else protected_files(output)
    artifacts.save_json(protected_path, protected)
    artifacts.save_json(output / 'evaluation_rules.json', artifacts.read_json(ref['rules_path']))
    artifacts.save_json(output / 'planner_contracts.json', {'instruction': DOCUMENT_SEARCH_INSTRUCTION,
        'mode_instruction': MODE_INSTRUCTION['adaptive'], 'sent': DocumentSearchDecision.model_json_schema(),
        'accepted': TolerantDocumentSearchDecision.model_json_schema(), 'policies': POLICIES})
    if not (output / 'code.zip').exists():
        with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')) + [PROJECT_ROOT / 'config/config.toml']:
                archive.write(file, file.relative_to(PROJECT_ROOT))
    records = {arm: artifacts.Recorder(output / arm, 'retrieval', signature) for arm in ARMS}
    cache_path = output / 'cache.json'
    cache = artifacts.read_json(cache_path) if cache_path.exists() else {'signature': signature, 'decisions': {}, 'queries': {}, 'global': {}}
    if cache['signature'] != signature:
        raise ValueError('Cache signature differs')
    def save_cache(): artifacts.save_json(cache_path, cache)
    aligner = SourceAligner(CORPUS, artifacts.read_json(ref['rules_path']))
    corpus = artifacts.source_corpus(ref['anchors'])
    def evaluate(case, parents):
        entries = [p.entry for p in parents]
        return {'evidence_v2': aligner.score(case, entries),
                'literal_v1': anchor_coverage(case, {'evidence': entries}, ref['anchors'], corpus)}
    def snapshot(ranking, runs):
        parents = parents_from_ranking(ranking, ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
        selected, trace = pack_order(parents)
        return Snapshot(ranking, runs, parents, selected, trace)
    old_planner = InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'],
        input_format='compact_v1', decision_contract='minimal_action_v1', reason_validation='soft_length_v1')
    planner = InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'],
        input_format='compact_v1', decision_contract='document_search_v1', reason_validation='soft_length_v1')
    saved_decisions = {}
    for value in source['cache']['decisions'].values():
        if value['status'] == 'started' or len(value.get('events', [])) != 1 or not value.get('request'):
            raise ValueError('Source contains unknown decisions or missing requests')
        request, event = value['request'], value['events'][0]
        if event.get('prompt') != request['rendered_request'] or not isinstance(event.get('raw_response'), str):
            raise ValueError('Historical raw request/response is unavailable')
        verify_generation_event(model, event)
        key = digest(request)
        if key in saved_decisions and saved_decisions[key]['events'][0]['raw_response'] != event['raw_response']:
            raise ValueError('Ambiguous historical response for an identical request')
        saved_decisions[key] = value
    def check_ranking(ranking):
        if any(ref['chunks'][r['position']].chunk_id != r['chunk_id'] for r in ranking):
            raise ValueError('Cached ranking references another index')
    def saved_advance(search, previous, saved):
        found = source['operations']['queries'][digest([search.text, search.document_ids])]
        if found['status'] != 'ok': raise RuntimeError(found['error'])
        runs = previous.runs + [(search, found['ranking'], found['diagnostics'])]
        result = source['operations']['global'][digest([saved['query'], [(s.to_dict(), rr) for s, rr, _ in runs]])]
        if result['status'] != 'ok': raise RuntimeError(result['error'])
        check_ranking(result['ranking'])
        return snapshot(result['ranking'], runs)
    audits, input_audit = [], []
    with clock.measure('replay'):
        for case in ref['cases']:
            for scope in ('collection', 'oracle_scope'):
                key = f'{case.id}:{scope}'; saved = ref['rows'][key]
                original = original_run(saved); initial = snapshot(original[1], [original])
                def decide(mode, current, ledger, remaining):
                    request = old_planner.prepare(mode, case.question, case.metadata.get('history', []), current, ledger, saved['scope'], remaining)
                    previous = saved_decisions.get(digest(request))
                    if previous is None: raise ValueError('Historical replay request mismatch: ' + key)
                    return replay_decision(old_planner, request, previous)
                final, plan = InvestigationController().run('adaptive', initial, decide,
                    lambda s, p: saved_advance(s, p, saved), saved['scope'])
                old = rows['B'][key]
                checks = {'context': final.context_ids() == [e['parent_id'] for e in old['evidence']],
                          'A_context': initial.context_ids() == [e['parent_id'] for e in rows['A'][key]['evidence']],
                          'A_status': rows['A'][key]['status'] == 'ok',
                          'A_candidate_ranking': initial.ranking == rows['A'][key]['diagnostics']['stages']['reranker'],
                          'status': plan['status'] == old['status'], 'stop_reason': plan['stop_reason'] == old['stop_reason'],
                          'errors': plan['errors'] == old['plan']['errors'],
                          'candidate_ranking': final.ranking == old['diagnostics']['stages']['reranker'],
                          'queries': [s.to_dict() for s, _, _ in final.runs] == [{k: v for k, v in q.items() if k not in ('diagnostics', 'candidates_added')} for q in old['diagnostics']['searches']]}
                a_scores, b_scores, b_candidates = evaluate(case, initial.selected), evaluate(case, final.selected), evaluate(case, final.parents)
                for version in ('evidence_v2', 'literal_v1'):
                    checks['A_' + version] = digest(a_scores[version]) == digest(rows['A'][key]['evaluations'][version])
                    checks['B_' + version] = digest(b_scores[version]) == digest(old['evaluations'][version])
                    checks['B_candidates_' + version] = digest(b_candidates[version]) == digest(old['candidate_evaluation'][version])
                audits.append({'key': key, 'checks': checks})
                if not all(checks.values()):
                    artifacts.save_json(output / 'control_reproduction.json', {'status': 'failed', 'cases': audits})
                    raise ValueError('A/B reproduction failed: ' + key + ' ' + str(checks))
                for arm, old_arm in (('A_baseline', 'A'), ('B_tolerant', 'B')):
                    row = copy.deepcopy(rows[old_arm][key]); row.pop('key')
                    row.update(operation_origin='historical_control', historical_source=str(source_run), physical_latency_seconds=0.)
                    records[arm].add(key, **row)
                try:
                    request = planner.prepare('adaptive', case.question, case.metadata.get('history', []), initial,
                                              {'remaining_decisions': 4}, saved['scope'], 3)
                    input_audit.append({'key': key, 'status': 'fits', 'tokens_including_margin': request['input_tokens_counted'],
                                        'output_reserved': request['output_reserved_tokens'], 'samples_removed': request['samples_removed']})
                except Exception as exc:
                    input_audit.append({'key': key, 'status': 'error', 'message': str(exc)})
    artifacts.save_json(output / 'control_reproduction.json', {'status': 'passed', 'cases': audits, 'generation_calls': 0})
    artifacts.save_json(output / 'input_budget_audit.json', {'status': 'passed' if all(r['status'] == 'fits' for r in input_audit) else 'failed', 'results': input_audit})
    if any(r['status'] != 'fits' for r in input_audit): raise ValueError('Initial input budget audit failed')
    for arm in ARMS[:2]: records[arm].finish(**metrics(records[arm].data['results']))

    def status(reason=None):
        completed = sum(all(f'{c.id}:{s}' in records[a].done for a in POLICIES for s in ('collection', 'oracle_scope')) for c in ref['cases'])
        physical = [e for v in cache['decisions'].values() for e in v.get('events', [])]
        operations = [v for group in ('queries', 'global') for v in cache[group].values()]
        artifacts.save_json(output / 'execution_status.json', {'status': 'complete' if completed == len(ref['cases']) and reason is None else 'incomplete',
            'questions': len(ref['cases']), 'completed_original_questions': completed, 'conditions': list(ARMS),
            'stop_reason': reason, 'observations': {a: len(rec.done) for a, rec in records.items()},
            'errors': {a: sum(r['status'] != 'ok' for r in rec.data['results']) for a, rec in records.items()},
            'physical_planning_calls': len(physical), 'physical_planning_prompt_tokens': sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in physical),
            'physical_planning_completion_tokens': sum((e.get('usage') or {}).get('completion_tokens', 0) for e in physical),
            'physical_retrieval_queries': sum(v.get('operation_origin') == 'live' for v in cache['queries'].values()),
            'physical_global_reranks': sum(v.get('operation_origin') == 'live' for v in cache['global'].values()),
            'physical_reranker_pairs': sum(v.get('physical_reranker_pairs', 0) for v in operations if v.get('operation_origin') == 'live'),
            'planning_usage_unknown': any(v.get('planning_calls_unknown') for v in cache['decisions'].values()),
            'synthetic_calls': artifacts.read_json(output / 'preflight.json').get('synthetic_planning_calls', 0) if (output / 'preflight.json').exists() else 0,
            'answer_generation_calls': 0, 'decision': 'pending_user_review', 'timing_file': 'timing.json'})
        clock.flush()
        return completed
    status('offline_controls_complete' if preflight_only else 'preparation')
    write_report(output)
    if preflight_only: return

    live, _, live_raw, served, session, base = llm_setup()
    if served != model: raise ValueError('Served model/tokenizer/settings differ from the frozen base')
    generate = live.generate
    def guarded(role, prompt, schema=None):
        if role != 'planner': raise AssertionError('Final-answer generation is blocked')
        result = generate(role, prompt, schema)
        event = live.calls[-1]
        verify_generation_event(model, event)
        observed = (event.get('usage') or {}).get('prompt_tokens')
        if observed is not None and (observed > count(prompt) or observed + model['max_output_tokens'] > model['num_ctx']):
            raise ValueError('InputBudget: server-reported usage exceeds frozen limits')
        return result
    live.generate = guarded
    planner.registry = live
    if not (output / 'preflight.json').exists():
        synthetic_path = output / 'preflight_cache.json'
        synthetic = artifacts.read_json(synthetic_path) if synthetic_path.exists() else {}
        with clock.measure('synthetic_live'):
            value = get_plan(synthetic, 'document_search', lambda: preflight(planner, live, live_raw, True),
                             lambda: artifacts.save_json(synthetic_path, synthetic))
        if value.get('status') != 'passed': raise ValueError('Synthetic readiness failed; unknown calls are not repeated')
        artifacts.save_json(output / 'preflight.json', value)
    clock.set_phase('evaluation')
    retriever, consecutive_transport, interrupted = None, 0, False
    for case in ref['cases']:
        for scope in ('collection', 'oracle_scope'):
            key = f'{case.id}:{scope}'; saved = ref['rows'][key]
            for arm, policy in POLICIES.items():
                if key in records[arm].done: continue
                started, started_at = time.perf_counter(), clock.now()
                original = original_run(saved); initial = snapshot(original[1], [original])
                operations, observed_states, advanced_states = [], [], {}
                def decide(mode, current, ledger, remaining):
                    before = len(live.calls)
                    request = None
                    observed_states.append(current)
                    try:
                        request = planner.prepare(mode, case.question, case.metadata.get('history', []), current, ledger, saved['scope'], remaining)
                    except Exception as exc:
                        return {'status': 'error', 'error': decision_failure(exc), 'events': []}
                    ck = digest({'signature': signature['fingerprint'], 'request': request})
                    def callback():
                        first = len(live.calls)
                        with clock.measure('live_work'):
                            try:
                                value = planner.execute(request)
                                if any(e.get('output_at_limit') or e.get('finish_reason') == 'length' for e in live.calls[first:]):
                                    raise RuntimeError('Generated output reached its token limit')
                            except Exception as exc:
                                value = {'status': 'error', 'error': decision_failure(exc, live.calls[first:], request)}
                        return {**value, 'events': copy.deepcopy(live.calls[first:]), 'request': request, 'operation_origin': 'live'}
                    value = copy.deepcopy(get_plan(cache['decisions'], ck, callback, save_cache))
                    physical = len(live.calls) > before
                    origin = 'live' if physical else 'shared_cache'
                    if value.get('planning_calls_unknown'):
                        value['error'].update(code='UNKNOWN_OUTCOME', stage='generation', recoverable=False, action_executed=False)
                    value['operation_origin'] = origin
                    for event in value.get('events', []):
                        event['operation_origin'] = origin
                        if not physical:
                            event['logical_latency_seconds'] = event.get('latency_seconds', 0.)
                            event['latency_seconds'] = 0.
                    operations.append({'kind': 'decision', 'cache_key': ck, 'origin': origin, 'new_physical_call': physical})
                    return value
                def operation(group, ck, callback):
                    nonlocal retriever
                    if ck not in cache[group] and ck in source['operations'][group]:
                        value = copy.deepcopy(source['operations'][group][ck])
                        if value['status'] != 'ok': raise RuntimeError('Historical operation failed; not silently retried')
                        check_ranking(value.get('ranking', []))
                        value.update(operation_origin='historical', historical_latency_seconds=value['latency_seconds'], latency_seconds=0.)
                        cache[group][ck] = value; save_cache()
                    if ck not in cache[group] and retriever is None:
                        with clock.measure('retriever_setup'): retriever = build_retriever(ref)
                    with clock.measure('live_work' if ck not in cache[group] else 'cache_read'):
                        value, physical = checkpoint_operation(cache[group], ck, callback, save_cache)
                    origin = value.get('operation_origin') if physical or value.get('operation_origin') == 'historical' else 'shared_cache'
                    operations.append({'kind': group, 'cache_key': ck, 'origin': origin, 'new_physical_call': physical})
                    if value['status'] != 'ok': raise RuntimeError(value['error'])
                    return value
                def advance(search, previous):
                    def search_call():
                        ranking, diagnostics = retriever.search(search.text, search.document_ids, 1)
                        return {'ranking': ranking, 'diagnostics': diagnostics,
                                'physical_reranker_pairs': len(diagnostics['stages']['reranker'])}
                    found = operation('queries', digest([search.text, search.document_ids]), search_call)
                    runs = previous.runs + [(search, found['ranking'], found['diagnostics'])]
                    gk = digest([saved['query'], [(s.to_dict(), rr) for s, rr, _ in runs]])
                    def rerank():
                        ranking = merge_and_rerank(saved['query'], runs, ref['chunks'], retriever.reranker)
                        return {'ranking': ranking, 'physical_reranker_pairs': len(ranking)}
                    result = operation('global', gk, rerank)
                    current = snapshot(result['ranking'], runs)
                    advanced_states[search.query_id] = current
                    return current
                final, plan = InvestigationController(interface='document_search_v1', error_policy=policy).run('adaptive', initial, decide, advance, saved['scope'])
                for step in plan['steps']:
                    decision = plan['decisions'][step['decision_index'] - 1]
                    state_before = observed_states[step['decision_index'] - 1]
                    state_after = advanced_states.get(step.get('effective_query', {}).get('query_id'), state_before)
                    request = decision.get('request') or {}
                    step['observed_parent_ids'] = state_before.context_ids()
                    step['sample_chunk_ids'] = [c['chunk_id'] for c in request.get('payload', {}).get('retrieved_samples', [])]
                    step['input_tokens_including_margin'] = request.get('input_tokens_counted')
                    step['output_reserved_tokens'] = request.get('output_reserved_tokens')
                    step['context_evaluation'] = evaluate(case, state_after.selected)
                    step['candidate_evaluation'] = evaluate(case, state_after.parents)
                    step['selected_parent_ids'] = state_after.context_ids()
                    step['discarded_parents'] = [p for p in state_after.packing_trace if p['reason'] != 'selected']
                    step['context_added'] = sorted(set(state_after.context_ids()) - set(state_before.context_ids()))
                    step['context_removed'] = sorted(set(state_before.context_ids()) - set(state_after.context_ids()))
                    step['model_latency_seconds'] = sum(e.get('latency_seconds', 0.) for e in decision.get('events', []))
                    step['operation_origin'] = decision.get('operation_origin', 'input_validation')
                    if step['requested_action'] is None:
                        try:
                            raw = json.loads(decision['events'][0]['raw_response'])
                            if isinstance(raw, dict):
                                step.update(requested_action=raw.get('action'), requested_queries=raw.get('queries'))
                        except (KeyError, IndexError, ValueError): pass
                searches, seen = [], set()
                for search, ranking, diagnostics in final.runs:
                    ids = {r['chunk_id'] for r in ranking}
                    searches.append({**search.to_dict(), 'diagnostics': diagnostics, 'candidates_added': len(ids - seen)})
                    seen.update(ids)
                events = plan['events']; scores, candidates = evaluate(case, final.selected), evaluate(case, final.parents)
                row = copy.deepcopy(rows['B'][key]); row.pop('key')
                duration = time.perf_counter() - started
                row.update(status=plan['status'], error=plan['errors'][0] if plan['errors'] else None,
                    evidence=[p.entry for p in final.selected], packing_trace=final.packing_trace,
                    context_tokens=sum(p.tokens for p in final.selected), evaluations=scores, candidate_evaluation=candidates,
                    stage_evaluations={'rrf': {'all': candidates}}, diagnostics={'stages': {'reranker': final.ranking}, 'searches': searches},
                    plan=plan, stop_reason=plan['stop_reason'], declared_sufficient=plan['declared_sufficient'],
                    source_candidate_digest=digest(final.ranking), shared_queries_digest=digest(searches), planner_digest=digest(plan),
                    started_at=started_at, finished_at=clock.now(), physical_latency_seconds=duration, latency_seconds=duration,
                    operations=operations, costs={'physical_case_seconds': duration}, search_count=len(searches), planning_calls=len(events),
                    planning_prompt_tokens=sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events),
                    planning_completion_tokens=sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events),
                    reranker_pairs_logical=sum(len(s['diagnostics']['stages']['reranker']) for s in searches) +
                        sum(len(cache['global'][o['cache_key']]['ranking']) for o in operations if o['kind'] == 'global'),
                    without_incident=plan['without_incident'], recovered_incidents=plan['recovered_incidents'])
                records[arm].add(key, **row)
                for decision in plan['decisions']:
                    if decision.get('operation_origin') != 'live': continue
                    for event in decision.get('events', []):
                        consecutive_transport = consecutive_transport + 1 if event.get('status') == 'error' and is_transport_error({'message': event.get('error', '')}) else 0
                completed = status()
                print(f"Perguntas originais concluídas: {completed}/{len(ref['cases'])}; {arm} {key}; decisões físicas: {sum(len(v.get('events', [])) for v in cache['decisions'].values())}", flush=True)
                if consecutive_transport >= 3:
                    interrupted = True; break
            if interrupted: break
        if interrupted: break
    for arm in POLICIES:
        if len(records[arm].done) == len(ref['rows']): records[arm].finish(**metrics(records[arm].data['results']))
    if implementation_hash() != signature['implementation_sha256'] or sha(PROJECT_ROOT / 'config/config.toml') != signature['config_sha256']:
        raise ValueError('Frozen code/configuration changed during execution')
    for name, expected in signature['source_hashes'].items():
        if sha(source_run / name) != expected: raise ValueError('Historical source changed during execution')
    load_reference()
    verify_remote_identity(model, session, base)
    artifacts.save_json(output / 'historical_preservation.json', verify_preserved(protected))
    status('three_consecutive_transport_failures' if interrupted else None)
    clock.set_phase('reporting')
    write_report(output)
    clock.finish('incomplete' if interrupted else 'complete')
    # Refresh the recorded wall duration, including report preparation.
    result = artifacts.read_json(output / 'comparison.json')
    result['timing'] = artifacts.read_json(output / 'timing.json')
    artifacts.save_json(output / 'comparison.json', result)


def write_report(output):
    from benchmark.search.report import report, agent_interface_report
    result = report(output)
    return agent_interface_report(output, result)
