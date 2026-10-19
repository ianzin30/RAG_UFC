"""One-variable local acceptance study, with explicit read-only response import."""
import copy
import time
import zipfile
from pathlib import Path

from transformers import AutoTokenizer

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.config import load_benchmark_llm
from benchmark.core.reproducibility import CORPUS, implementation_hash, sha
from benchmark.core.timing import RunClock
from benchmark.evaluation.evidence import SourceAligner
from benchmark.evaluation.literal import anchor_coverage
from benchmark.search.runtime import load_reference, llm_setup, build_retriever, verify_generation_event, verify_remote_identity
from benchmark.search.run import original_run, get_plan, is_transport_error, audit_initial_inputs, preflight
from benchmark.selection.run import digest, metrics

ARMS = ('A_baseline', 'B_strict', 'C_tolerant')


def reason_length_failure(row):
    message = (row.get('error') or {}).get('message', '')
    return '\nreason\n' in message and 'at most 300 characters' in message


def recorded_registry(event, request):
    """Re-run the real parser and reference checks, without any transport."""
    from service.rag.v2.Providers import ProviderRegistry, ProviderError
    class Recorded:
        structured = ProviderRegistry.structured
        def __init__(self):
            self.calls = []
        def generate(self, role, prompt, schema=None):
            if role != 'planner' or prompt != request['rendered_request'] or schema != request['schema']:
                raise AssertionError('Replay changed the actual model-facing request')
            saved = copy.deepcopy(event)
            for key in ('validation_error', 'decision_validation_error', 'rejected_decision', 'structured_attempt'):
                saved.pop(key, None)
            saved.update(operation_origin='historical', historical_latency_seconds=saved['latency_seconds'])
            saved['latency_seconds'] = 0.
            self.calls.append(saved)
            if saved['status'] != 'ok':
                raise ProviderError(saved.get('error', 'Recorded generation failed'))
            if not isinstance(saved.get('raw_response'), str):
                raise ValueError('Replay has no known raw response')
            return saved['raw_response']
    return Recorded()


def replay_decision(planner, request, saved):
    previous = planner.registry
    registry = recorded_registry(saved['events'][0], request)
    planner.registry = registry
    try:
        try:
            result = planner.execute(request)
        except Exception as exc:
            result = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
        return {**result, 'events': registry.calls, 'request': request, 'operation_origin': 'historical'}
    finally:
        planner.registry = previous


def checkpoint_operation(cache, key, callback, save):
    """Retrieval/reranking also retain unknown starts instead of repeating them."""
    if key in cache:
        if cache[key]['status'] == 'started':
            cache[key] = {'status': 'error', 'error': 'Interrupted operation; outcome unknown, not repeated',
                          'operation_origin': 'live', 'latency_seconds': 0., 'usage_unknown': True}
            save()
        return cache[key], False
    cache[key] = {'status': 'started', 'operation_origin': 'live'}
    save()
    started = time.perf_counter()
    try:
        value = {'status': 'ok', **callback()}
    except Exception as exc:
        value = {'status': 'error', 'error': str(exc)}
    value.update(operation_origin='live', latency_seconds=time.perf_counter() - started)
    cache[key] = value
    save()
    return value, True


def frozen_setup(source, ref):
    """Audit the effective local configuration/template before any model call."""
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.AdaptiveRetrieval import COMMON_INSTRUCTION, MINIMAL_INSTRUCTION, MODE_INSTRUCTION, Decision, MinimalDecision
    sig = source['signature']
    cfg, tokenizer_name = load_benchmark_llm()
    model = sig['llm']
    if cfg.provider != 'vllm' or model['thinking'] is not False:
        raise ValueError('This study requires the frozen vLLM no-thinking profile')
    registry = ProviderRegistry(cfg)
    provider = registry.resolve('planner')
    wire = {k: v for k, v in provider.build_payload('').items() if k != 'messages'}
    if wire != model['request_parameters'] or provider.base_url + '/chat/completions' != model['endpoint']:
        raise ValueError('Effective endpoint or generation parameters changed from the source run')
    for key in ('num_ctx', 'max_output_tokens', 'timeout_seconds'):
        if getattr(cfg, key) != model[key]:
            raise ValueError('Frozen budget changed: ' + key)
    if tokenizer_name != model['tokenizer'] or sha(PROJECT_ROOT / 'config/config.toml') != sig['config_sha256']:
        raise ValueError('Frozen configuration/tokenizer changed')
    if sig['planner_prompt_sha256'] != digest([COMMON_INSTRUCTION, MINIMAL_INSTRUCTION, MODE_INSTRUCTION]):
        raise ValueError('Historical planner instructions changed')
    if sig['decision_schema_sha256'] != digest([Decision.model_json_schema(), MinimalDecision.model_json_schema()]):
        raise ValueError('Historical sent schema changed')
    if (sha(ref['index']), ref['source']['signature']['index_fingerprint']) != (sig['index_sha256'], sig['index_fingerprint']):
        raise ValueError('Source index differs')
    if sig['models'] != {k: ref['source']['signature'][k] for k in ('encoder', 'reranker', 'rag_config')}:
        raise ValueError('Source retrieval configuration differs')
    if sig['corpus_sha256'] != ref['source']['signature']['corpus_sha256']:
        raise ValueError('Source corpus differs')
    if sig['frozen_searches_sha256'] != sha(PROJECT_ROOT / 'benchmark/results/rounds/semantic_generalization_2026-10-07/regression/reference/retrieval.json'):
        raise ValueError('Original searches changed')
    for name, expected in sig['datasets'].items():
        path = ref['rules_path'] if name == 'rules' else ref['directory'] / ('questions.json' if name == 'questions' else 'evidence.json')
        if sha(path) != expected:
            raise ValueError('Source dataset/evaluator differs')
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, local_files_only=True)
    if digest(tokenizer.get_vocab()) != model['tokenizer_digest'] or digest(tokenizer.get_chat_template()) != model['tokenizer_template_sha256']:
        raise ValueError('Frozen tokenizer/template differs')
    def raw_count(prompt):
        payload = provider.build_payload(prompt)
        return len(tokenizer.apply_chat_template(payload['messages'], tokenize=True, add_generation_prompt=True,
                   **payload.get('chat_template_kwargs', {})))
    return registry, lambda p: raw_count(p) + 512, raw_count


def run(output, source_run, preflight_only=False):
    output, source_run = output.resolve(), source_run.resolve()
    if output == source_run or output.is_relative_to(source_run) or source_run.is_relative_to(output):
        raise ValueError('Use a separate output directory, outside the source run')
    output.mkdir(parents=True, exist_ok=True)
    clock = RunClock(output / 'timing.json')
    try:
        _run(output, source_run, preflight_only, clock)
    except BaseException as exc:
        artifacts.save_json(output / 'blocked.json', {'type': type(exc).__name__, 'message': str(exc),
                            'instruction': 'Preserve unknown outcomes. No provider fallback or automatic reconnect.'})
        status_path = output / 'execution_status.json'
        status = artifacts.read_json(status_path) if status_path.exists() else {}
        status.update(status='incomplete', stop_reason=type(exc).__name__, blocker=str(exc))
        artifacts.save_json(status_path, status)
        clock.finish('interrupted' if isinstance(exc, KeyboardInterrupt) else 'blocked')
        if (output / 'signature.json').exists() and (output / 'A_baseline/retrieval.json').exists():
            from benchmark.search.report import report
            report(output)
            render_readiness(output)
        raise
    finally:
        if clock.session['status'] == 'running':
            clock.finish('complete' if not preflight_only else 'offline_controls_complete')


def _run(output, source_run, preflight_only, clock):
    bootstrap_python_path()
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner, InvestigationController, Snapshot, MinimalDecision, TolerantMinimalDecision
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.DirectedRetrieval import merge_and_rerank
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    from benchmark.search.input_audit import protected_files, verify_preserved
    source_paths = [source_run / n for n in ('signature.json', 'cache.json', 'A_baseline/retrieval.json',
                   'C_minimal_contract/retrieval.json', 'planner_contracts.json', 'execution_status.json', 'code.zip')]
    source_hashes = {str(p): sha(p) for p in source_paths}
    source = {name: artifacts.read_json(source_run / file) for name, file in
              [('signature', 'signature.json'), ('cache', 'cache.json'), ('A', 'A_baseline/retrieval.json'),
               ('B', 'C_minimal_contract/retrieval.json')]}
    if artifacts.read_json(source_run / 'execution_status.json')['status'] != 'complete':
        raise ValueError('Source run must be complete')
    if source['cache']['signature'] != source['signature']:
        raise ValueError('Source cache signature differs')
    ref = load_reference()
    registry, count, raw_count = frozen_setup(source, ref)
    model = source['signature']['llm']
    source_decisions = {}
    for key, value in source['cache']['decisions'].items():
        if value.get('request', {}).get('decision_contract') != 'minimal_action_v1':
            continue
        if value['status'] == 'started' or len(value.get('events', [])) != 1:
            raise ValueError('Source decision has unknown outcome')
        request = value['request']
        event = value['events'][0]
        if event.get('prompt') != request['rendered_request'] or not isinstance(event.get('raw_response'), str):
            raise ValueError('Source raw request/response is unavailable')
        verify_generation_event(model, event)
        request_key = digest(request)
        if request_key in source_decisions and source_decisions[request_key]['events'][0]['raw_response'] != event['raw_response']:
            raise ValueError('Multiple different source responses for the same exact request; import is ambiguous')
        source_decisions[request_key] = {'key': key, **value}
    source_rows = {a: {r['key']: r for r in source[a]['results']} for a in ('A', 'B')}
    expected_keys = set(ref['rows'])
    if any(set(rows) != expected_keys for rows in source_rows.values()):
        raise ValueError('Source conditions do not cover the same 70 questions in both scopes')
    signature = {'study': 'reason_validation', 'experiment': 'soft_reason_length_v1',
        'implementation_sha256': implementation_hash(), 'config_sha256': sha(PROJECT_ROOT / 'config/config.toml'),
        'source_hashes': source_hashes, 'source_fingerprint': source['signature']['fingerprint'],
        'llm': model, 'parameters': source['signature']['parameters'], 'conditions': list(ARMS),
        'index_sha256': source['signature']['index_sha256'], 'datasets': source['signature']['datasets'],
        'evaluation_versions': ['evidence_v2', 'literal_v1'],
        'sent_schema_sha256': digest(MinimalDecision.model_json_schema()),
        'acceptance_schema_sha256': digest(TolerantMinimalDecision.model_json_schema()),
        'prompt_sha256': source['signature']['planner_prompt_sha256'],
        'reason_policies': {'B_strict': 'strict', 'C_tolerant': 'soft_length_v1'}}
    signature['fingerprint'] = digest(signature)
    path = output / 'signature.json'
    if path.exists() and artifacts.read_json(path) != signature:
        raise ValueError('Execution signature changed; use a new directory')
    artifacts.save_json(path, signature)
    protected_path = output / 'protected_before.json'
    protected = artifacts.read_json(protected_path) if protected_path.exists() else protected_files(output)
    artifacts.save_json(protected_path, protected)
    artifacts.save_json(output / 'evaluation_rules.json', artifacts.read_json(ref['rules_path']))
    artifacts.save_json(output / 'planner_contracts.json', {'sent': artifacts.read_json(source_run / 'planner_contracts.json')['minimal_action_v1'],
                        'local_tolerant_schema': TolerantMinimalDecision.model_json_schema(),
                        'local_strict_schema': MinimalDecision.model_json_schema()})
    if not (output / 'code.zip').exists():
        from benchmark.core.reproducibility import code_files
        with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')) + [PROJECT_ROOT / 'config/config.toml']:
                archive.write(file, file.relative_to(PROJECT_ROOT))
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
    strict = InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'],
                                  input_format='compact_v1', decision_contract='minimal_action_v1')
    tolerant = InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'],
                                    input_format='compact_v1', decision_contract='minimal_action_v1', reason_validation='soft_length_v1')
    records = {a: artifacts.Recorder(output / a, 'retrieval', signature) for a in ARMS}
    cache_path = output / 'cache.json'
    cache = artifacts.read_json(cache_path) if cache_path.exists() else {'signature': signature, 'decisions': {}, 'queries': {}, 'global': {}}
    if cache['signature'] != signature:
        raise ValueError('Cache signature differs')
    def save_cache(): artifacts.save_json(cache_path, cache)
    def status(reason=None):
        live_events = [e for v in cache['decisions'].values() if v.get('operation_origin') == 'live' for e in v.get('events', [])]
        complete_questions = sum(all(f'{c.id}:{s}' in records['C_tolerant'].done for s in ('collection', 'oracle_scope')) for c in ref['cases'])
        operations = [v for g in ('queries', 'global') for v in cache[g].values()]
        artifacts.save_json(output / 'execution_status.json', {
            'status': 'complete' if complete_questions == 70 and reason is None else 'incomplete', 'questions': 70,
            'completed_original_questions': complete_questions, 'conditions': list(ARMS), 'stop_reason': reason,
            'observations': {a: len(r.done) for a, r in records.items()},
            'errors': {a: sum(r['status'] != 'ok' for r in rec.data['results']) for a, rec in records.items()},
            'physical_planning_calls': len(live_events), 'replayed_decisions': sum(v.get('operation_origin') == 'historical' for v in cache['decisions'].values()),
            'physical_retrieval_queries': sum(v.get('operation_origin') == 'live' for v in cache['queries'].values()),
            'physical_global_reranks': sum(v.get('operation_origin') == 'live' for v in cache['global'].values()),
            'physical_reranker_pairs': sum(len(v.get('ranking', [])) for v in operations if v.get('operation_origin') == 'live'),
            'physical_planning_prompt_tokens': sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in live_events),
            'physical_planning_completion_tokens': sum((e.get('usage') or {}).get('completion_tokens', 0) for e in live_events),
            'planning_usage_unknown': any(v.get('planning_calls_unknown') for v in cache['decisions'].values()),
            'synthetic_calls': artifacts.read_json(output / 'preflight.json').get('synthetic_planning_calls', 0) if (output / 'preflight.json').exists() else 0,
            'answer_generation_calls': 0, 'decision': 'pending_user_review', 'timing_file': 'timing.json'})
        clock.flush()
    def saved_advance(search, previous, saved):
        found = source['cache']['queries'][digest([search.text, search.document_ids])]
        if found['status'] != 'ok':
            raise RuntimeError(found['error'])
        runs = previous.runs + [(search, found['ranking'], found['diagnostics'])]
        result = source['cache']['global'][digest([saved['query'], [(s.to_dict(), rr) for s, rr, _ in runs]])]
        if result['status'] != 'ok':
            raise RuntimeError(result['error'])
        return snapshot(result['ranking'], runs)
    # Verify complete strict trajectories and both evaluators before live work.
    audit = []
    with clock.measure('replay'):
        for case in ref['cases']:
            for scope in ('collection', 'oracle_scope'):
                key = f'{case.id}:{scope}'; saved = ref['rows'][key]
                original = original_run(saved); initial = snapshot(original[1], [original])
                def decide(mode, current, ledger, remaining):
                    request = strict.prepare(mode, case.question, case.metadata.get('history', []), current, ledger, saved['scope'], remaining)
                    old = source_decisions.get(digest(request))
                    if old is None:
                        raise AssertionError('Strict replay request has no exact saved match: ' + key)
                    return replay_decision(strict, request, old)
                final, plan = InvestigationController().run('adaptive', initial, decide,
                                 lambda search, previous: saved_advance(search, previous, saved), saved['scope'])
                old = source_rows['B'][key]
                checks = {'status': plan['status'] == old['status'], 'stop_reason': plan['stop_reason'] == old['stop_reason'],
                          'context': final.context_ids() == [e['parent_id'] for e in old['evidence']],
                          'candidate_ranking': final.ranking == old['diagnostics']['stages']['reranker'],
                          'errors': plan['errors'] == old['plan']['errors'],
                          'queries': [s.to_dict() for s, _, _ in final.runs] == [{k: v for k, v in q.items() if k not in ('diagnostics', 'candidates_added')} for q in old['diagnostics']['searches']]}
                baseline_scores, strict_scores = evaluate(case, initial.selected), evaluate(case, final.selected)
                for version in ('evidence_v2', 'literal_v1'):
                    checks['baseline_' + version] = digest(baseline_scores[version]) == digest(source_rows['A'][key]['evaluations'][version])
                    checks['strict_' + version] = digest(strict_scores[version]) == digest(old['evaluations'][version])
                audit.append({'key': key, 'checks': checks})
                if not all(checks.values()):
                    artifacts.save_json(output / 'control_reproduction.json', {'status': 'failed', 'cases': audit})
                    raise ValueError('Strict control reproduction differs: ' + key + ' ' + str(checks))
                for arm, source_arm in (('A_baseline', 'A'), ('B_strict', 'B')):
                    row = copy.deepcopy(source_rows[source_arm][key]); row.pop('key')
                    row.update(operation_origin='historical_control', physical_latency_seconds=0., historical_source=str(source_run))
                    records[arm].add(key, **row)
        artifacts.save_json(output / 'control_reproduction.json', {'status': 'passed', 'cases': audit,
                            'known_saved_decisions': len(source_decisions), 'generation_calls': 0})
    for arm in ARMS[:2]: records[arm].finish(**metrics(records[arm].data['results']))
    revalidation = []
    with clock.measure('replay'):
        for old in source_decisions.values():
            value = replay_decision(tolerant, old['request'], old)
            revalidation.append({'source_decision_key': old['key'], 'before_status': old['status'],
                'after_status': value['status'], 'issues': value.get('issues', []), 'error': value.get('error'),
                'old_error': old.get('error'), 'action': value.get('decision', {}).get('action')})
    artifacts.save_json(output / 'response_revalidation.json', {
        'decisions': revalidation, 'generation_calls': 0, 'searches_executed': 0,
        'notice': 'Validation of saved observations only; not a completed tolerant trajectory or retrieval-quality result.'})
    artifacts.save_json(output / 'input_budget_audit.json', audit_initial_inputs(tolerant, ref['cases'], ref['rows'], snapshot))
    if artifacts.read_json(output / 'input_budget_audit.json')['status'] != 'passed':
        raise ValueError('Initial input budget audit failed')
    status('offline_controls_complete' if preflight_only else 'preparation')
    from benchmark.search.report import report
    report(output)
    render_readiness(output)
    if preflight_only:
        return
    # No remote generation precedes offline reproduction. An unavailable server blocks here.
    live_registry, live_count, live_raw, live_model, session, base = llm_setup()
    if live_model != model:
        raise ValueError('Effective served model/tokenizer/settings differ from historical no-thinking profile')
    original_generate = live_registry.generate
    def guarded(role, prompt, schema=None):
        if role != 'planner': raise AssertionError('Final generation is blocked')
        value = original_generate(role, prompt, schema)
        event = live_registry.calls[-1]; event['operation_origin'] = 'live'
        verify_generation_event(model, event)
        observed = (event.get('usage') or {}).get('prompt_tokens')
        if observed is not None and (observed > count(prompt) or observed + model['max_output_tokens'] > model['num_ctx']):
            raise ValueError('Server input usage exceeds frozen budget')
        return value
    live_registry.generate = guarded
    tolerant.registry = live_registry
    if not (output / 'preflight.json').exists():
        synthetic_path = output / 'preflight_cache.json'
        synthetic_cache = artifacts.read_json(synthetic_path) if synthetic_path.exists() else {}
        with clock.measure('synthetic_live'):
            value = get_plan(synthetic_cache, 'minimal', lambda: preflight(tolerant, live_registry, live_raw, True),
                             lambda: artifacts.save_json(synthetic_path, synthetic_cache))
        if value['status'] != 'passed': raise ValueError('Synthetic preparation failed; unknown starts are not retried')
        artifacts.save_json(output / 'preflight.json', value)
    clock.set_phase('evaluation')
    retriever = None; transport_errors = 0; interrupted = False
    def check_ranking(ranking):
        for item in ranking:
            if ref['chunks'][item['position']].chunk_id != item['chunk_id']:
                raise ValueError('Imported ranking references a different index')
    for case in ref['cases']:
        for scope in ('collection', 'oracle_scope'):
            key = f'{case.id}:{scope}'
            if key in records['C_tolerant'].done: continue
            case_start, started_at = time.perf_counter(), clock.now()
            saved = ref['rows'][key]; original = original_run(saved); initial = snapshot(original[1], [original])
            case_operations = []; physical_start = len(live_registry.calls)
            def decide(mode, current, ledger, remaining):
                decision_physical_start = len(live_registry.calls)
                try:
                    request = tolerant.prepare(mode, case.question, case.metadata.get('history', []), current, ledger, saved['scope'], remaining)
                except Exception as exc:
                    return {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}, 'events': []}
                ck = digest({'signature': signature['fingerprint'], 'request': request})
                def callback():
                    old = source_decisions.get(digest(request))
                    if old is not None:
                        with clock.measure('replay'):
                            value = replay_decision(tolerant, request, old)
                        return {**value, 'source_decision_key': old['key']}
                    before = len(live_registry.calls)
                    with clock.measure('live_work'):
                        try:
                            value = tolerant.execute(request)
                        except Exception as exc:
                            value = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
                    return {**value, 'events': copy.deepcopy(live_registry.calls[before:]), 'request': request, 'operation_origin': 'live'}
                value = get_plan(cache['decisions'], ck, callback, save_cache)
                case_operations.append({'kind': 'decision', 'cache_key': ck, 'origin': value.get('operation_origin'),
                                        'new_physical_call': len(live_registry.calls) > decision_physical_start})
                return value
            def operation(group, ck, callback):
                nonlocal retriever
                if ck not in cache[group] and ck in source['cache'][group]:
                    with clock.measure('replay'):
                        value = copy.deepcopy(source['cache'][group][ck])
                        check_ranking(value.get('ranking', []))
                        value.update(operation_origin='historical', historical_latency_seconds=value['latency_seconds'], latency_seconds=0.)
                        cache[group][ck] = value; save_cache()
                if ck not in cache[group] and retriever is None:
                    with clock.measure('retriever_setup'): retriever = build_retriever(ref)
                if ck in cache[group]:
                    value, physical = checkpoint_operation(cache[group], ck, callback, save_cache)
                else:
                    with clock.measure('live_work'):
                        value, physical = checkpoint_operation(cache[group], ck, callback, save_cache)
                case_operations.append({'kind': group, 'cache_key': ck, 'origin': value['operation_origin'], 'new_physical_call': physical})
                if value['status'] != 'ok': raise RuntimeError(value['error'])
                return value
            def advance(search, previous):
                def search_call():
                    ranking, diag = retriever.search(search.text, search.document_ids, 1)
                    return {'ranking': ranking, 'diagnostics': diag}
                found = operation('queries', digest([search.text, search.document_ids]), search_call)
                runs = previous.runs + [(search, found['ranking'], found['diagnostics'])]
                gk = digest([saved['query'], [(s.to_dict(), rr) for s, rr, _ in runs]])
                result = operation('global', gk, lambda: {'ranking': merge_and_rerank(saved['query'], runs, ref['chunks'], retriever.reranker)})
                return snapshot(result['ranking'], runs)
            final, planning = InvestigationController().run('adaptive', initial, decide, advance, saved['scope'])
            scores, candidates = evaluate(case, final.selected), evaluate(case, final.parents)
            searches, seen = [], set()
            for search, ranking, diag in final.runs:
                ids = {r['chunk_id'] for r in ranking}
                searches.append({**search.to_dict(), 'diagnostics': diag, 'candidates_added': len(ids - seen)})
                seen.update(ids)
            events = planning['events']
            row = copy.deepcopy(source_rows['B'][key])
            row.pop('key')
            row.update(status=planning['status'], error=planning['errors'][0] if planning['errors'] else None,
                evidence=[p.entry for p in final.selected], packing_trace=final.packing_trace,
                context_tokens=sum(p.tokens for p in final.selected), evaluations=scores,
                stage_evaluations={'rrf': {'all': candidates}}, candidate_evaluation=candidates,
                diagnostics={'stages': {'reranker': final.ranking}, 'searches': searches},
                plan=planning, stop_reason=planning['stop_reason'], declared_sufficient=planning['declared_sufficient'],
                source_candidate_digest=digest(final.ranking), shared_queries_digest=digest(searches), planner_digest=digest(planning),
                started_at=started_at, finished_at=clock.now(), physical_latency_seconds=time.perf_counter() - case_start,
                operations=case_operations, historical_comparator_costs=source_rows['B'][key]['costs'],
                latency_seconds=time.perf_counter() - case_start, costs={'physical_case_seconds': time.perf_counter() - case_start},
                search_count=len(searches), planning_calls=len(events),
                planning_prompt_tokens=sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in events),
                planning_completion_tokens=sum((e.get('usage') or {}).get('completion_tokens', 0) for e in events),
                reranker_pairs_logical=sum(len(s['diagnostics']['stages']['reranker']) for s in searches) +
                    sum(len(cache['global'][o['cache_key']]['ranking']) for o in case_operations if o['kind'] == 'global'))
            records['C_tolerant'].add(key, **row)
            for event in live_registry.calls[physical_start:]:
                transport_errors = transport_errors + 1 if event.get('status') == 'error' and is_transport_error({'message': event.get('error', '')}) else 0
            status()
            print(f"Original questions complete: {sum(all(f'{c.id}:{s}' in records['C_tolerant'].done for s in ('collection','oracle_scope')) for c in ref['cases'])}/70; new decisions: {sum(v.get('operation_origin') == 'live' for v in cache['decisions'].values())}", flush=True)
            if transport_errors >= 3:
                interrupted = True; break
        if interrupted: break
    if len(records['C_tolerant'].done) == 140: records['C_tolerant'].finish(**metrics(records['C_tolerant'].data['results']))
    if implementation_hash() != signature['implementation_sha256'] or sha(PROJECT_ROOT / 'config/config.toml') != signature['config_sha256']:
        raise ValueError('Frozen code/configuration changed during execution')
    load_reference()  # Rechecks corpus, index, dataset and retrieval configuration.
    verify_remote_identity(model, session, base)
    artifacts.save_json(output / 'historical_preservation.json', verify_preserved(protected))
    status('three_consecutive_transport_failures' if interrupted else None)
    clock.set_phase('reporting')
    report(output)
    report_acceptance(output)
    clock.finish('incomplete' if interrupted else 'complete')
    result = artifacts.read_json(output / 'comparison.json')
    result['timing'] = artifacts.read_json(output / 'timing.json')
    artifacts.save_json(output / 'comparison.json', result)
    render_visual(output, result)


def report_acceptance(output):
    """Add the operational/physical distinctions to the shared evidence report."""
    import numpy as np
    from collections import Counter
    from zoneinfo import ZoneInfo
    from datetime import datetime
    result = artifacts.read_json(output / 'comparison.json')
    before = artifacts.read_json(output / 'B_strict/retrieval.json')['results']
    after = artifacts.read_json(output / 'C_tolerant/retrieval.json')['results']
    cache = artifacts.read_json(output / 'cache.json')
    physical = [e for v in cache['decisions'].values() if v.get('operation_origin') == 'live' for e in v.get('events', [])]
    def stats(values):
        return {'attempts': len(values), 'median_seconds': float(np.median(values)) if values else None,
                'p95_seconds': float(np.percentile(values, 95)) if values else None}
    audit = {}
    for scope in ('collection', 'oracle_scope'):
        old = {r['key']: r for r in before if r['condition'] == scope}
        rows = [r for r in after if r['condition'] == scope]
        long_decisions = [(r, d) for r in rows for d in r['plan']['decisions'] if any(i['reason'] == 'reason_length_exceeded' for i in d.get('issues', []))]
        changed_reason_cases = [r for r in rows if reason_length_failure(old[r['key']])]
        audit[scope] = {'evaluated': len(rows),
            'complete': sum(r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rows),
            'without_error': sum(r['status'] == 'ok' for r in rows),
            'complete_without_error': sum(r['status'] == 'ok' and r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rows),
            'accepted_long_reasons': len(long_decisions), 'cases_with_accepted_long_reason': sorted({r['case_id'] for r, _ in long_decisions}),
            'old_reason_failures': len(changed_reason_cases),
            'old_reason_failures_now_without_error': [r['case_id'] for r in changed_reason_cases if r['status'] == 'ok'],
            'old_reason_failures_still_failed': [{'case_id': r['case_id'], 'error': r['error']} for r in changed_reason_cases if r['status'] != 'ok'],
            'accepted_long_reasons_that_opened_searches': [{'case_id': r['case_id'], 'query': d['decision']['normalized_queries']} for r, d in long_decisions if d['decision']['action'] == 'search'],
            'pending_false_sufficiency': [r['case_id'] for r in rows if r['declared_sufficient'] and not r['evaluations']['evidence_v2']['complete_selected_anchors'] and r['evaluations']['evidence_v2']['pending_anchors']],
            'confirmed_false_sufficiency': [r['case_id'] for r in rows if r['declared_sufficient'] and not r['evaluations']['evidence_v2']['complete_selected_anchors'] and not r['evaluations']['evidence_v2']['pending_anchors']],
            'incomplete_stop': [r['case_id'] for r in rows if r['stop_reason'] == 'finish_incomplete'],
            'failures': dict(Counter('output_exhausted' if any(e.get('output_at_limit') for e in r['plan']['events']) else r['stop_reason'] for r in rows if r['status'] != 'ok'))}
    timing = artifacts.read_json(output / 'timing.json')
    result.update(acceptance_audit=audit, timing=timing,
                  physical_decision_latency=stats([e['latency_seconds'] for e in physical]),
                  physical_case_latency=stats([r['physical_latency_seconds'] for r in after]),
                  recommendation='revise_incomplete' if result['execution']['status'] != 'complete' else 'pending_critical_review')
    result['recommendation_basis'] = 'Human/agent critical review must consider errors, documentary gains/losses and cost; no automatic threshold or application promotion. User approval pending.'
    artifacts.save_json(output / 'comparison.json', result)
    local_start = datetime.fromisoformat(timing['started_at']).astimezone(ZoneInfo('America/Fortaleza'))
    lines = ['\n## Aceitação e custo físico desta rodada', '', f"Início observado: {local_start.isoformat()} (Fortaleza).",
             f"Tempo ativo acumulado: {timing['active_wall_seconds']:.2f} s. Tempo desde o primeiro início: {timing['elapsed_since_first_start_seconds']:.2f} s (inclui pausas).",
             'B é histórico; suas latências não medem trabalho físico desta rodada. C registra o tempo físico por caso; decisões importadas têm latência histórica em campo separado.',
             f"Novas decisões: {len(physical)}; mediana/p95 incluindo falhas: {result['physical_decision_latency']}.",
             'Preparação sintética, replay, configuração do retriever e trabalho novo estão separados em timing.json.', '']
    for scope, a in audit.items():
        lines += [f"### {scope}", '', f"Completas: {a['complete']}/{a['evaluated']}; sem erro: {a['without_error']}/{a['evaluated']}; completas e sem erro: {a['complete_without_error']}/{a['evaluated']}.",
                  f"Decisões longas aceitas: {a['accepted_long_reasons']}. Falhas antigas de reason recuperadas operacionalmente: {a['old_reason_failures_now_without_error']}.",
                  f"Outros erros após revalidação: {a['old_reason_failures_still_failed']}.",
                  f"Falsas suficiências com alinhamento resolvido: {a['confirmed_false_sufficiency']}; pendências: {a['pending_false_sufficiency']}.", '']
    lines += [f"**Recomendação: {result['recommendation']}. Aprovação pendente da revisão do usuário.**",
              'Ganhos de aceitação não são automaticamente ganhos documentais; o avaliador e os textos de origem foram preservados.']
    with (output / 'report.md').open('a') as file: file.write('\n'.join(lines) + '\n')
    render_visual(output, result)


def render_visual(output, result):
    """Self-contained report; no browser or generation calls."""
    import html
    title = 'Uma justificativa longa deve interromper a busca?'
    figures = []
    labels = {'A_baseline': 'Busca original', 'B_strict': 'Validação estrita', 'C_tolerant': 'Validação tolerante'}
    for scope, name in [('collection', 'Coleção inteira'), ('oracle_scope', 'Documentos corretos fornecidos')]:
        bars = []
        for arm, label in labels.items():
            m = result['metrics'][arm]['evidence_v2'][scope]
            rows = artifacts.read_json(output / arm / 'retrieval.json')['results']
            joint = sum(r['status'] == 'ok' and r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rows if r['condition'] == scope)
            bars.append(f'<div class="bar"><b>{label}</b><span>Contexto completo: {m["complete"]}/70</span><meter min="0" max="70" value="{m["complete"]}"></meter><span>Completo e sem erro: {joint}/70</span><meter class="joint" min="0" max="70" value="{joint}"></meter></div>')
        figures.append(f'<figure><h2>{name}</h2><div class="bars">{"".join(bars)}</div><figcaption>Fig. {len(figures)+1} — Aceitação operacional e evidência documental são medidas separadas.</figcaption></figure>')
    comparison = result['comparisons'].get('tolerant_vs_strict', {})
    rows = []
    for scope, change in comparison.items():
        rows.append(f'<tr><td>{html.escape(scope)}</td><td>{html.escape(", ".join(change["complete_gains"]) or "Nenhum")}</td><td>{html.escape(", ".join(change["complete_losses"]) or "Nenhuma")}</td><td>{change["before_partial"]:.1%} → {change["after_partial"]:.1%}</td></tr>')
    figures.append(f'<figure><h2>O que mudou nas mesmas perguntas</h2><div class="scroll"><table><thead><tr><th>Escopo</th><th>Ganhos completos</th><th>Regressões</th><th>Cobertura parcial</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><figcaption>Fig. 3 — Os ganhos contam apenas evidências verificadas pelo avaliador congelado.</figcaption></figure>')
    case_data = []
    old = {r['key']: r for r in artifacts.read_json(output / 'B_strict/retrieval.json')['results']}
    for r in artifacts.read_json(output / 'C_tolerant/retrieval.json')['results']:
        b = old[r['key']]
        case_data.append({'pergunta': r['case_id'], 'escopo': r['condition'], 'categoria': r['category'],
                         'antes': b['status'], 'depois': r['status'], 'completa_antes': b['evaluations']['evidence_v2']['complete_selected_anchors'],
                         'completa_depois': r['evaluations']['evidence_v2']['complete_selected_anchors'], 'parada': r['stop_reason']})
    import json
    serialized = json.dumps(case_data, ensure_ascii=False).replace('<', '\\u003c')
    timing = result['timing']; sessions = timing['sessions']
    spans = [('Replay', sum(s.get('replay_seconds', 0) for s in sessions)), ('Trabalho novo', sum(s.get('live_work_seconds', 0) for s in sessions)),
             ('Preparação sintética', sum(s.get('synthetic_live_seconds', 0) for s in sessions)), ('Carga do retriever', sum(s.get('retriever_setup_seconds', 0) for s in sessions))]
    maximum = max([v for _, v in spans] + [1])
    time_bars = ''.join(f'<div class="bar"><b>{label}</b><span>{value:.1f} s</span><meter min="0" max="{maximum}" value="{value}"></meter></div>' for label, value in spans)
    figures.append(f'<figure><h2>Quanto trabalho foi realmente executado</h2><div class="bars">{time_bars}</div><figcaption>Fig. 4 — Tempo ativo total: {timing["active_wall_seconds"]:.1f} s; custos históricos não entram nestas barras.</figcaption></figure>')
    page = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Validação tolerante — Qwen3.6</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600&family=Geist+Mono&display=swap" rel="stylesheet"><style>
:root{color-scheme:light dark;--bg:#f4f5f3;--surface:#fff;--text:#121614;--dim:#545e59;--border:#888e8b;--accent:#955700;--ok:#1c7443} @media(prefers-color-scheme:dark){:root{--bg:#0b0d0c;--surface:#121614;--text:#e6ebe8;--dim:#919d97;--border:#5e6662;--accent:#f2a93b;--ok:#6fcf97}}html{font-size:17px}body{margin:0;background:var(--bg);color:var(--text);font-family:Geist,sans-serif;line-height:1.5}main{max-width:64rem;margin:auto;padding:3rem 1.5rem}h1{font-size:clamp(2.25rem,5.5vw,4rem);line-height:1.1;letter-spacing:-.03em;max-width:18ch}h2{font-size:1.625rem;margin:0 0 1.5rem}p{max-width:65ch}figure{margin:3rem 0;padding-top:2rem;border-top:1px solid var(--border)}figcaption{color:var(--dim);font-size:.875rem;margin-top:.75rem}.bars{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr));gap:1.5rem}.bar{display:grid;gap:.5rem;font-variant-numeric:tabular-nums;min-width:0}.bar span{font-size:.875rem}meter{width:100%;height:1.5rem;accent-color:var(--accent)}meter.joint{accent-color:var(--ok)}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:.75rem;border-bottom:1px solid var(--border);font-size:.875rem}th{color:var(--dim)}.scroll{overflow:auto}a{color:var(--accent)}select{font:inherit;padding:.5rem;background:var(--surface);color:var(--text);border:1px solid var(--border)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}.tag{font-family:"Geist Mono",monospace;color:var(--accent);font-size:.875rem}code{overflow-wrap:anywhere}button{font:inherit} .mechanism{display:flex;gap:1.5rem;flex-wrap:wrap}.mechanism span{border:1px solid var(--border);padding:1rem;flex:1;min-width:10rem}footer{margin-top:3rem;color:var(--dim)}</style><main>'''
    page += f'<div class="tag">QWEN3.6 · REASONING DESLIGADO · REVISÃO PENDENTE</div><h1>{title}</h1><p>O modelo recebe a mesma instrução. Apenas o limite local da justificativa deixa de interromper uma decisão utilizável.</p><div class="mechanism" role="img" aria-label="Mesma resposta, validação diferente, possibilidade de continuar a busca"><span>Resposta original preservada</span><span>Validação local aceita o excesso</span><span>Busca continua quando necessária</span></div>'
    page += ''.join(figures)
    page += '<h2>Explore as perguntas</h2><label for="scope">Escopo </label><select id="scope"><option value="collection">Coleção</option><option value="oracle_scope">Documentos corretos</option></select><div class="scroll"><table><thead><tr><th>Pergunta</th><th>Categoria</th><th>Erro antes → depois</th><th>Completa antes → depois</th><th>Parada</th></tr></thead><tbody id="cases"></tbody></table></div><footer>Fonte: <a href="report.md">relatório crítico</a> · <a href="comparison.json">dados e suporte documental</a> · <a href="timing.json">duração por sessão</a>. Aprovação pendente. Mesmas 70 perguntas; esta rodada não demonstra transferência para outros domínios.</footer>'
    page += f'<script>const rows={serialized};const body=document.getElementById("cases");function render(){{body.replaceChildren();for(const r of rows.filter(x=>x.escopo===document.getElementById("scope").value)){{const tr=document.createElement("tr");for(const text of [r.pergunta,r.categoria,r.antes+" → "+r.depois,(r.completa_antes?"Sim":"Não")+" → "+(r.completa_depois?"Sim":"Não"),r.parada]){{const td=document.createElement("td");td.textContent=text;tr.append(td)}}body.append(tr)}}}}document.getElementById("scope").addEventListener("change",render);render();</script></main></html>'
    (output / 'report.html').write_text(page)


def render_readiness(output):
    """An incomplete audit must never look like a finished quality comparison."""
    import html
    from collections import Counter
    status = artifacts.read_json(output / 'execution_status.json')
    if status['status'] == 'complete': return
    path = output / 'response_revalidation.json'
    decisions = artifacts.read_json(path)['decisions'] if path.exists() else []
    released = [d for d in decisions if d['before_status'] == 'error' and d['after_status'] == 'ok']
    actions = Counter(d['action'] for d in released)
    bars = ''.join(f'<div><b>{html.escape(label)}</b><meter min="0" max="{max(len(decisions),1)}" value="{value}"></meter><span>{value}</span></div>' for label, value in
                   [('Respostas revalidadas', len(decisions)), ('Decisões liberadas', len(released)),
                    ('Propõem busca', actions['search']), ('Declaram suficiência', actions['finish_sufficient'])])
    blocker = html.escape(status.get('blocker') or status.get('stop_reason') or 'Preparação em andamento')
    page = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auditoria da validação — execução incompleta</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600&display=swap" rel="stylesheet"><style>
:root{{color-scheme:light dark;--bg:#f4f5f3;--text:#121614;--dim:#545e59;--border:#888e8b;--accent:#955700}}@media(prefers-color-scheme:dark){{:root{{--bg:#0b0d0c;--text:#e6ebe8;--dim:#919d97;--border:#5e6662;--accent:#f2a93b}}}}html{{font-size:17px}}body{{margin:0;background:var(--bg);color:var(--text);font:1rem/1.5 Geist,sans-serif}}main{{max-width:64rem;margin:auto;padding:3rem 1.5rem}}h1{{font-size:clamp(2.25rem,5.5vw,4rem);line-height:1.1;max-width:20ch}}p{{max-width:65ch}}figure{{margin:3rem 0;padding-top:2rem;border-top:1px solid var(--border)}}.bars div{{display:grid;grid-template-columns:minmax(8rem,1fr) 2fr 3rem;gap:1rem;align-items:center;margin:1rem 0}}meter{{width:100%;height:1.5rem;accent-color:var(--accent)}}figcaption,.dim{{color:var(--dim)}}code{{overflow-wrap:anywhere}}a{{color:var(--accent)}}@media(max-width:500px){{.bars div{{grid-template-columns:minmax(0,1fr)}}}}:focus-visible{{outline:3px solid var(--accent)}}</style><main>
<p class="dim">Qwen3.6 · sem reasoning · auditoria offline</p><h1>As respostas podem ser revalidadas. A comparação ainda está incompleta.</h1>
<p><strong>Estado:</strong> <code>{blocker}</code></p><figure class="bars" role="img" aria-label="Respostas revalidadas e ações liberadas">{bars}<figcaption>Fig. 1 — Aceitar uma decisão não comprova que o contexto sustenta a pergunta.</figcaption></figure>
<p>Os controles A e B são reproduções históricas. As decisões liberadas podem encerrar o caso ou abrir uma busca nova. A qualidade da trajetória tolerante só será comparada após sua execução.</p>
<p><a href="report.md">Relatório dos controles</a> · <a href="control_reproduction.json">Conferência dos dois escopos</a> · <a href="response_revalidation.json">Revalidação das respostas</a> · <a href="timing.json">Duração registrada</a></p></main></html>'''
    (output / 'report.html').write_text(page)
