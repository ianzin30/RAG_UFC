"""Offline planner-input audit and paired timing checks on frozen observations."""
import copy
import json
import statistics
import time
import zipfile
from pathlib import Path

from transformers import AutoTokenizer

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.config import load_benchmark_llm
from benchmark.core.reproducibility import code_files, implementation_hash, sha
from benchmark.search.runtime import load_reference, llm_setup, verify_remote_identity
from benchmark.selection.run import digest

REPLAY = PROJECT_ROOT / 'benchmark/results/rounds/cumbuco_adaptive_2026-10-09/run_04/cache.json'


def observations(ref):
    from benchmark.search.run import original_run
    from service.rag.v2.AdaptiveRetrieval import Snapshot
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    for case in ref['cases']:
        for scope in ('collection', 'oracle_scope'):
            saved = ref['rows'][f'{case.id}:{scope}']
            original = original_run(saved)
            parents = parents_from_ranking(original[1], ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
            selected, trace = pack_order(parents)
            snapshot = Snapshot(original[1], [original], parents, selected, trace)
            yield case, saved, snapshot


def tokenizers(name):
    tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=True)
    def raw(text):
        return len(tokenizer.apply_chat_template([{'role': 'user', 'content': text}],
                                                tokenize=True, add_generation_prompt=True))
    def component(text):
        return len(tokenizer.encode(text, add_special_tokens=False))
    return tokenizer, raw, component


def check_preservation(request):
    """Check the readable view against its canonical retained observation."""
    view, payload = request['planner_view'], request['payload']
    for key in ('question', 'history', 'remaining_searches'):
        if view[key] != payload[key]:
            raise AssertionError(f'Changed {key}')
    for key in ('selected_context', 'retrieved_samples'):
        if [v['text'] for v in view[key]] != [v['text'] for v in payload[key]]:
            raise AssertionError('Documentary text changed')
    if request['input_format'] == 'compact_v1':
        maps = request['id_maps']
        for key in ('catalog', 'selected_context', 'retrieved_samples'):
            for shown, original in zip(view[key], payload[key], strict=True):
                for field in ('document_id', 'parent_id', 'chunk_id'):
                    if field in original and maps[field].get(shown[field]) != original[field]:
                        raise AssertionError('Reference did not round trip')
        ledger = copy.deepcopy(view.get('ledger', {}))
        for support in ledger.get('supports', []):
            for citation in support.get('citations', []):
                citation['parent_id'] = maps['parent_id'][citation['parent_id']]
        if ledger != payload.get('ledger', {}):
            raise AssertionError('Ledger changed')
        for shown, original in zip(view['previous_queries'], payload['previous_queries'], strict=True):
            scope = None if shown['scope'] is None else [maps['document_id'][d] for d in shown['scope']]
            if shown['text'] != original['text'] or scope != original['scope']:
                raise AssertionError('Previous search changed')
        scope = None if view['scope'] is None else [maps['document_id'][d] for d in view['scope']]
        if scope != payload['scope']:
            raise AssertionError('Scope changed')
    return True


def initialize(output, signature):
    signature = {**signature, 'implementation_sha256': implementation_hash(),
                 'config_sha256': sha(PROJECT_ROOT / 'config/config.toml')}
    signature['fingerprint'] = digest(signature)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'signature.json'
    if path.exists() and artifacts.read_json(path) != signature:
        raise ValueError('Signature changed; use a new directory')
    artifacts.save_json(path, signature)
    if not (output / 'code.zip').exists():
        with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')) + [PROJECT_ROOT / 'config/config.toml']:
                archive.write(file, file.relative_to(PROJECT_ROOT))
    return signature


def protected_files(output):
    """Historical artifacts are read-only; exclude this diagnostic's directory."""
    result = {}
    for base in (PROJECT_ROOT / 'benchmark/results', PROJECT_ROOT / 'benchmark/datasets', PROJECT_ROOT / 'docs'):
        for path in base.rglob('*'):
            if path.is_file() and not path.is_relative_to(output):
                result[str(path.relative_to(PROJECT_ROOT))] = sha(path)
    return result


def verify_preserved(manifest):
    changed = [p for p, expected in manifest.items() if not (PROJECT_ROOT / p).is_file()
               or sha(PROJECT_ROOT / p) != expected]
    if changed:
        raise AssertionError(f'Historical artifacts changed: {changed}')
    return {'checked_files': len(manifest), 'changed_files': changed}


def stats(values):
    ordered = sorted(values)
    return {'median': statistics.median(ordered), 'p95': __import__('numpy').percentile(ordered, 95).item(),
            'minimum': ordered[0], 'maximum': ordered[-1]}


def audit(output):
    bootstrap_python_path()
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner, INPUT_FORMATS
    manifest = protected_files(output)
    ref = load_reference()
    cfg, configured_tokenizer = load_benchmark_llm()
    profiles = [('qwen35_16k', 'Qwen/Qwen3.5-9B', 16384, 4096),
                ('configured_llm', configured_tokenizer, cfg.num_ctx, cfg.max_output_tokens)]
    signature = initialize(output, {'experiment': 'planner_input_compaction_v1', 'generation_calls': 0,
        'index_sha256': sha(ref['index']), 'datasets': ref['source']['signature']['dataset_sha256'],
        'profiles': profiles, 'margin': 512, 'replay_sha256': sha(REPLAY) if REPLAY.exists() else None})
    artifacts.save_json(output / 'protected_before.json', manifest)
    initial = list(observations(ref))
    replay = artifacts.read_json(REPLAY) if REPLAY.exists() else None
    state = {'signature': signature, 'status': 'running', 'generation_calls': 0, 'retrieval_calls': 0,
             'component_accounting': 'standalone tokens; not additive because token boundaries differ', 'profiles': []}
    for name, source, window, reserve in profiles:
        tokenizer, raw, component = tokenizers(source)
        count = lambda text: raw(text) + 512
        result = {'name': name, 'tokenizer': source, 'tokenizer_digest': digest(tokenizer.get_vocab()),
                  'window': window, 'output_reserved_tokens': reserve, 'rows': [], 'replay_rows': []}
        for fmt in INPUT_FORMATS:
            bounded = InvestigationPlanner(None, ref['catalog'], ref['chunks'], count, window, reserve, fmt)
            unbounded = InvestigationPlanner(None, ref['catalog'], ref['chunks'], count, 1000000, reserve, fmt)
            def measure(kind, key, mode, payload):
                all_input = unbounded.prepare_payload(mode, payload)
                check_preservation(all_input)
                parts = {k: component(json.dumps(v, ensure_ascii=False,
                         **({'separators': (',', ':')} if fmt == 'compact_v1' else {})))
                         for k, v in all_input['planner_view'].items()}
                parts['schema'] = component(json.dumps(all_input['schema'], ensure_ascii=False,
                         **({'separators': (',', ':')} if fmt == 'compact_v1' else {})))
                parts['instruction'] = component(all_input['prompt'].rsplit('\n', 1)[0])
                row = {'key': key, 'policy': mode, 'input_format': fmt,
                       'all_samples_total_tokens': all_input['input_tokens_counted'] + reserve,
                       'component_tokens': parts, 'preservation_verified': True,
                       'document_text_sha256': digest([p['text'] for p in payload['selected_context']]
                                                      + [p['text'] for p in payload['retrieved_samples']])}
                try:
                    request = bounded.prepare_payload(mode, payload)
                    check_preservation(request)
                    row.update(status='fits', input_tokens=request['input_tokens_counted'],
                               total_tokens=request['input_tokens_counted'] + reserve,
                               samples_removed=request['samples_removed'])
                except ValueError as exc:
                    row.update(status='oversized', error=str(exc))
                result[kind].append(row)
            for case, saved, snap in initial:
                for mode in ('single_shot', 'adaptive'):
                    payload = unbounded.prepare(mode, case.question, case.metadata.get('history', []),
                                                snap, {}, saved['scope'], 3)['payload']
                    measure('rows', saved['key'], mode, payload)
            if replay:
                for key, value in replay['decisions'].items():
                    request = value.get('request')
                    if request:
                        measure('replay_rows', key, request['mode'], request['payload'])
        result['summary'] = {}
        for fmt in INPUT_FORMATS:
            rows = [r for r in result['rows'] if r['input_format'] == fmt]
            later = [r for r in result['replay_rows'] if r['input_format'] == fmt]
            result['summary'][fmt] = {'initial_requests': len(rows),
                'oversized_question_scopes': len({r['key'] for r in rows if r['status'] != 'fits'}),
                'requests_needing_sample_removal': sum(r.get('samples_removed', 0) > 0 for r in rows),
                'all_samples_total_tokens': stats([r['all_samples_total_tokens'] for r in rows]),
                'saved_requests': len(later), 'saved_requests_oversized': sum(r['status'] != 'fits' for r in later)}
        state['profiles'].append(result)
        artifacts.save_json(output / 'audit.json', state)
        print(name, json.dumps(result['summary']), flush=True)
    state.update(status='complete', preservation=verify_preserved(manifest))
    artifacts.save_json(output / 'audit.json', state)
    lines = ['# Planner input compaction audit', '',
             'Offline audit: 70 original questions × two scopes × two policies = 280 initial preparations per format/profile. No LLM or retrieval calls.', '',
             '| Profile | Format | Oversized pairs / 140 | Requests removing samples / 280 | Maximum total, all samples | Saved requests oversized |',
             '|---|---|---:|---:|---:|---:|']
    for profile in state['profiles']:
        for fmt, summary in profile['summary'].items():
            lines.append(f"| {profile['name']} | {fmt} | {summary['oversized_question_scopes']} | {summary['requests_needing_sample_removal']} | {summary['all_samples_total_tokens']['maximum']} | {summary['saved_requests_oversized']} / {summary['saved_requests']} |")
    lines += ['', 'Totals include model chat formatting, a 512-token safety margin and the full output reserve. Exact text and typed-reference preservation were checked. All source coordinates remain in canonical observations; the compact view retains known page numbers.', '',
              'Legacy rendering uses corrected schema rebuilding when samples are removed, so trimming counts may differ from historical audits. No planning quality or retrieval improvement is established by this audit.', '',
              f"Historical preservation: {state['preservation']['checked_files']} files checked, zero changed."]
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def speed_test(output):
    """Two balanced repeats on two fitting frozen observations; same visible texts."""
    bootstrap_python_path()
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
    from benchmark.search.run import get_plan, is_transport_error
    manifest = protected_files(output)
    ref = load_reference()
    registry, count, raw, model, session, base = llm_setup()
    planners = {fmt: InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count,
                 model['num_ctx'], model['max_output_tokens'], fmt) for fmt in ('legacy_v1', 'compact_v1')}
    eligible = []
    for case, saved, snap in observations(ref):
        try:
            legacy = planners['legacy_v1'].prepare('single_shot', case.question,
                case.metadata.get('history', []), snap, {}, saved['scope'], 3)
            compact = planners['compact_v1'].prepare_payload('single_shot', legacy['payload'])
        except ValueError:
            continue
        if legacy['payload'] != compact['payload']:
            raise AssertionError('Speed comparison changed observations')
        check_preservation(compact)
        eligible.append((saved['key'], legacy, compact))
    # Selection depends only on input feasibility/size, never retrieval success.
    eligible.sort(key=lambda item: (-item[1]['input_tokens_counted'], item[0]))
    chosen = eligible[:2]
    if not chosen:
        raise ValueError('No same-observation pair fits configured window')
    signature = initialize(output, {'experiment': 'planner_input_speed_v1', 'model': model,
        'index_sha256': sha(ref['index']), 'selected_requests': [(k, digest(a), digest(b)) for k, a, b in chosen],
        'repeats': 2, 'order': ['legacy_v1', 'compact_v1', 'compact_v1', 'legacy_v1']})
    artifacts.save_json(output / 'protected_before.json', manifest)
    path = output / 'timings.json'
    state = artifacts.read_json(path) if path.exists() else {'signature': signature, 'status': 'running',
        'eligible_pairs': len(eligible), 'calls': [], 'cache': {}, 'retrieval_calls': 0,
        'selection_policy': 'two largest fitting legacy initial requests; compact sees exactly the retained legacy observation',
        'generation_only_rate_available': False, 'transport_failures': 0}
    if state['signature'] != signature:
        raise ValueError('Timing signature differs')
    def save(): artifacts.save_json(path, state)
    stop = False
    for key, legacy, compact in chosen:
        for repeat, order in enumerate((('legacy_v1', 'compact_v1'), ('compact_v1', 'legacy_v1'))):
            for fmt in order:
                request = legacy if fmt == 'legacy_v1' else compact
                ck = digest([signature['fingerprint'], key, repeat, fmt])
                if any(row['cache_key'] == ck for row in state['calls']):
                    continue
                def callback():
                    before = len(registry.calls); start = time.perf_counter()
                    try:
                        value = planners[fmt].execute(request)
                    except Exception as exc:
                        value = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
                    value.update(events=copy.deepcopy(registry.calls[before:]), elapsed_seconds=time.perf_counter()-start)
                    return value
                value = get_plan(state['cache'], ck, callback, save)
                event = (value.get('events') or [{}])[-1]
                if event.get('prompt') and event['prompt'] != request['rendered_request']:
                    raise AssertionError('Transmitted request differs from counted message')
                usage = event.get('usage') or {}
                if usage.get('prompt_tokens') is not None and usage['prompt_tokens'] > request['input_tokens_counted']:
                    raise ValueError('Observed input exceeds safe count')
                row = {'key': key, 'input_format': fmt, 'repeat': repeat, 'cache_key': ck,
                       'input_tokens_counted': request['input_tokens_counted'], 'samples_removed_from_shared_observation': request['samples_removed'],
                       'usage': usage, 'latency_seconds': value.get('elapsed_seconds'), 'status': value['status'],
                       'error': value.get('error'), 'request': request, 'result': value}
                state['calls'].append(row)
                transport = any(e.get('status') == 'error' and is_transport_error({'message': e.get('error', '')})
                                for e in value.get('events', []))
                state['transport_failures'] = state['transport_failures'] + 1 if transport else 0
                save(); print(key, fmt, json.dumps({k: row[k] for k in ('latency_seconds', 'usage', 'status', 'error')}), flush=True)
                if state['transport_failures'] >= 3 or value.get('planning_calls_unknown'):
                    stop = True; break
            if stop: break
        if stop: break
    try:
        verify_remote_identity(model, session, base)
    except Exception as exc:
        state['identity_error'] = {'type': type(exc).__name__, 'message': str(exc)}
        stop = True
    state.update(status='incomplete' if stop else 'complete', preservation=verify_preserved(manifest))
    state['summary'] = {}
    for fmt in planners:
        rows = [r for r in state['calls'] if r['input_format'] == fmt]
        latencies = [r['latency_seconds'] for r in rows if r['latency_seconds'] is not None]
        state['summary'][fmt] = {'attempts': len(rows), 'valid_decisions': sum(r['status'] == 'ok' for r in rows),
            'latency_seconds': stats(latencies) if latencies else None,
            'prompt_tokens': stats([r['usage']['prompt_tokens'] for r in rows if r['usage'].get('prompt_tokens') is not None])
                if any(r['usage'].get('prompt_tokens') is not None for r in rows) else None}
    save()
    lines = ['# Paired planner latency diagnostic', '', f"Model: {model['model']} via {model['provider']}. Same temperature, window, output allowance, timeout and observations in both formats. Balanced AB/BA order, two repeats per observation.", '',
             '| Format | Calls | Valid decisions | Median wall time, s | Observed median prompt tokens |', '|---|---:|---:|---:|---:|']
    for fmt, s in state['summary'].items():
        lines.append(f"| {fmt} | {s['attempts']} | {s['valid_decisions']} | {s['latency_seconds']['median'] if s['latency_seconds'] else 'unknown'} | {s['prompt_tokens']['median'] if s['prompt_tokens'] else 'unknown'} |")
    lines += ['', f"{len(eligible)} / 140 original observations fit legacy input preparation in this model profile; the two largest fitting observations were chosen by token size, not expected answers or performance. This small, fitting subset is not representative of every question.", '',
              'Wall time combines server queue, prefill, generation and transport. Server prefix caching and varying output length can affect results. No generation-only rate is available. Invalid decisions are reported separately; no repair, fallback, new retrieval or final-answer generation occurs. This is not an accuracy benchmark.', '',
              f"Execution status: {state['status']}. Historical preservation: {state['preservation']['checked_files']} files checked, zero changed."]
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def contract_requests(ref, registry, count, model):
    """Pair observations before any model output; optional texts are shared."""
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
    planners = {name: InvestigationPlanner(registry, ref['catalog'], ref['chunks'], count,
        model['num_ctx'], model['max_output_tokens'], 'compact_v1', name)
        for name in ('full_evidence_v1', 'minimal_action_v1')}
    pairs = []
    for case, saved, snap in observations(ref):
        full = planners['full_evidence_v1'].prepare('adaptive', case.question,
            case.metadata.get('history', []), snap, {}, saved['scope'], 3)
        minimal = planners['minimal_action_v1'].prepare_payload('adaptive', full['payload'])
        # If either schema needs fewer samples, render both on that intersection.
        while full['payload']['retrieved_samples'] != minimal['payload']['retrieved_samples']:
            payload = copy.deepcopy(full['payload'])
            payload['retrieved_samples'] = minimal['payload']['retrieved_samples']
            full = planners['full_evidence_v1'].prepare_payload('adaptive', payload)
            minimal = planners['minimal_action_v1'].prepare_payload('adaptive', full['payload'])
        for request in (full, minimal):
            check_preservation(request)
        pairs.append((saved['key'], saved['condition'], full, minimal))
    return planners, pairs


def contract_audit(output):
    """All 140 initial states, both contracts; no generation or retrieval."""
    ref = load_reference()
    registry, count, raw, model, session, base = llm_setup()
    signature = initialize(output, {'experiment': 'decision_contract_input_audit_v1', 'model': model,
        'index_sha256': sha(ref['index']), 'dataset_sha256': ref['source']['signature']['dataset_sha256']})
    planners, pairs = contract_requests(ref, registry, count, model)
    result = {'signature': signature, 'status': 'passed', 'generation_calls': 0, 'retrieval_calls': 0,
        'question_scope_pairs': len(pairs), 'results': [{ 'key': key, 'scope': scope,
            'contracts': {r['decision_contract']: {'input_tokens_counted': r['input_tokens_counted'],
                'output_reserved_tokens': r['output_reserved_tokens'],
                'samples': len(r['payload']['retrieved_samples']), 'preservation_verified': True}
                for r in (full, minimal)}} for key, scope, full, minimal in pairs]}
    artifacts.save_json(output / 'audit.json', result)
    print(json.dumps({'status': result['status'], 'pairs': len(pairs), 'generation_calls': 0}), flush=True)


def contract_speed_test(output):
    """Median/largest observation per scope; sixteen balanced planner calls."""
    from benchmark.search.run import get_plan, is_transport_error
    from benchmark.search.runtime import verify_generation_event
    ref = load_reference()
    registry, count, raw, model, session, base = llm_setup()
    planners, pairs = contract_requests(ref, registry, count, model)
    chosen = []
    for scope in ('collection', 'oracle_scope'):
        group = sorted((p for p in pairs if p[1] == scope), key=lambda p: (p[2]['input_tokens_counted'], p[0]))
        chosen.extend([group[(len(group)-1)//2], group[-1]])
    signature = initialize(output, {'experiment': 'decision_contract_speed_v1', 'model': model,
        'index_sha256': sha(ref['index']), 'selected_requests': [(k, digest(a), digest(b)) for k, _, a, b in chosen],
        'repeats': 2, 'seed': model['sampling']['seed'], 'order': ['full', 'minimal', 'minimal', 'full']})
    manifest_path = output / 'protected_before.json'
    manifest = artifacts.read_json(manifest_path) if manifest_path.exists() else protected_files(output)
    artifacts.save_json(manifest_path, manifest)
    path = output / 'timings.json'
    state = artifacts.read_json(path) if path.exists() else {'signature': signature, 'status': 'running',
        'calls': [], 'cache': {}, 'retrieval_calls': 0, 'transport_failures': 0,
        'selected_keys': [p[0] for p in chosen],
        'selection_policy': 'median and largest initial full-contract input per scope; chosen before generation'}
    if state['signature'] != signature:
        raise ValueError('Speed signature differs')
    def save(): artifacts.save_json(path, state)
    stop = False
    for key, scope, full, minimal in chosen:
        for repeat, order in enumerate(((full, minimal), (minimal, full))):
            for request in order:
                contract = request['decision_contract']
                ck = digest([signature['fingerprint'], key, repeat, contract])
                if any(r['cache_key'] == ck for r in state['calls']):
                    continue
                def callback():
                    before = len(registry.calls); start = time.perf_counter()
                    try:
                        value = planners[contract].execute(request)
                    except Exception as exc:
                        value = {'status': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}}
                    value.update(events=copy.deepcopy(registry.calls[before:]), elapsed_seconds=time.perf_counter()-start)
                    return value
                value = get_plan(state['cache'], ck, callback, save)
                event = (value.get('events') or [{}])[-1]
                accounting_error = None
                if event.get('sent_parameters'):
                    try:
                        verify_generation_event(model, event)
                        if event.get('prompt') != request['rendered_request']:
                            raise ValueError('Transmitted prompt differs from counted prompt')
                        if (event.get('usage') or {}).get('prompt_tokens', 0) > request['input_tokens_counted']:
                            raise ValueError('Server input exceeds safe count')
                    except Exception as exc:
                        accounting_error = str(exc); stop = True
                row = {'key': key, 'scope': scope, 'decision_contract': contract, 'repeat': repeat, 'cache_key': ck,
                    'status': value['status'], 'error': value.get('error'), 'accounting_error': accounting_error,
                    'latency_seconds': value.get('elapsed_seconds'), 'usage': event.get('usage'),
                    'server_timings': event.get('server_timings'), 'output_at_limit': event.get('output_at_limit'),
                    'request': request, 'result': value}
                state['calls'].append(row)
                transport = any(e.get('status') == 'error' and is_transport_error({'message': e.get('error', '')}) for e in value.get('events', []))
                state['transport_failures'] = state['transport_failures'] + 1 if transport else 0
                save()
                print(key, contract, json.dumps({k: row[k] for k in ('status', 'error', 'latency_seconds', 'usage')}), flush=True)
                if state['transport_failures'] >= 3 or value.get('planning_calls_unknown') or stop:
                    stop = True; break
            if stop: break
        if stop: break
    verify_remote_identity(model, session, base)
    state.update(status='incomplete' if stop else 'complete', preservation=verify_preserved(manifest))
    state['summary'] = {}
    for contract in planners:
        rows = [r for r in state['calls'] if r['decision_contract'] == contract]
        def timing(key):
            values = [r['server_timings'][key]/1e9 for r in rows if (r.get('server_timings') or {}).get(key) is not None]
            return stats(values) if values else None
        state['summary'][contract] = {'attempts': len(rows), 'valid_decisions': sum(r['status'] == 'ok' for r in rows),
            'errors': dict(__import__('collections').Counter((r.get('error') or {}).get('type') for r in rows if r['status'] != 'ok')),
            'wall_seconds_all_attempts': stats([r['latency_seconds'] for r in rows if r['latency_seconds'] is not None]) if rows else None,
            'load_seconds': timing('load_duration'), 'prefill_seconds': timing('prompt_eval_duration'),
            'generation_seconds': timing('eval_duration'), 'output_at_limit': sum(bool(r.get('output_at_limit')) for r in rows)}
    save()
    lines = ['# Decision-contract speed pilot', '', f"Status: {state['status']}. Local {model['model']}, thinking enabled.", '',
        '| Contract | Attempts | Valid | Median wall seconds, all attempts | Output exhausted |', '|---|---:|---:|---:|---:|']
    for name, s in state['summary'].items():
        lines.append(f"| {name} | {s['attempts']} | {s['valid_decisions']} | {s['wall_seconds_all_attempts']['median'] if s['wall_seconds_all_attempts'] else None} | {s['output_at_limit']} |")
    lines += ['', 'Sixteen calls, four observations selected by input size before model outcomes, two matched-seed balanced repeats. No new retrieval or final answers.',
        'Load, prefill and generation times are separated in timings.json. Cached prefixes and seed/backend variability limit inference from this small timing sample.',
        'Valid decisions measure controller compatibility, not documentary completeness. Thinking consumes the same 4096-token output budget as the JSON.',
        'Decision: pending user review. Quality comparison follows separately.']
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    if stop:
        raise RuntimeError('Speed pilot incomplete; inspect timings.json')
