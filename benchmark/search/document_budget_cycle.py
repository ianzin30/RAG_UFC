"""Teste completo com o dobro de documentos: paired live 3000/6000 contexts."""
import copy
from importlib.metadata import version
from pathlib import Path
import time
import zipfile

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.config import load_benchmark_llm
from benchmark.core.reproducibility import CORPUS, code_files, implementation_hash, sha
from benchmark.core.timing import RunClock
from benchmark.search.document_budget_replay import select_states, setup_window_audit
from benchmark.search.global_order_replay import (equal, hits_change, load_history, offline_only,
    reconstruct_states, validate_ranking, verify_control)
from benchmark.search.reason_validation import checkpoint_operation
from benchmark.search.run import get_plan, original_run
from benchmark.search.runtime import build_retriever, load_reference
from benchmark.selection.run import digest

TITLE = 'Teste completo com o dobro de documentos'
ARMS = {'D3000': 3000, 'D6000': 6000}
SCOPES = ('collection', 'oracle_scope')


def spark_registry(model, count):
    """Same provider payload/validation, explicit authenticated HTTPS transport.

    No automatic retries: even a gateway 5xx can hide a completed generation.
    No historical LLM response is reused across the endpoint change.
    """
    from llm_client import LLMClient, LLMError, public_error
    from openai import APIError
    from service.rag.v2.Providers import ProviderRegistry, VLLMProvider, Capabilities
    client = LLMClient(timeout=model['timeout_seconds'], max_retries=0)
    if client.settings.model != model['model']:
        client.close()
        raise ValueError('LLM_MODEL differs from the frozen Qwen model')
    cfg, _ = load_benchmark_llm()

    class SparkProvider(VLLMProvider):
        capabilities = Capabilities()

        def __init__(self, selection, config):
            super().__init__(selection, config)
            self.base_url = client.settings.base_url.rstrip('/')
            # Credentials remain exclusively inside the SDK, never in artifacts.
            self.api_key = None

        def _json(self, method, path, **kwargs):
            if method == 'GET' and path == '/models':
                return {'data': [{'id': m} for m in client.list_models()]}
            if method != 'POST' or path != '/chat/completions':
                raise AssertionError('Unexpected Spark route')
            payload = kwargs['json']
            standard = {'model', 'messages', 'stream', 'temperature', 'max_tokens',
                        'top_p', 'seed', 'stop', 'presence_penalty', 'frequency_penalty'}
            arguments = {k: v for k, v in payload.items() if k in standard}
            arguments['extra_body'] = {k: v for k, v in payload.items() if k not in standard}
            try:
                return client._sdk.chat.completions.create(**arguments).model_dump()
            except APIError as exc:
                raise public_error(exc) from None

    registry = ProviderRegistry(cfg)
    registry.factories['vllm'] = SparkProvider
    registry.capture_payloads = True
    provider = registry.resolve('planner')
    provider.resolve()
    wire = {k: v for k, v in provider.build_payload('').items() if k != 'messages'}
    equal(wire, model['request_parameters'], 'frozen sampling and thinking parameters')
    generate = registry.generate

    def guarded(role, prompt, schema=None):
        if role != 'planner':
            raise AssertionError('Only planner decisions are permitted')
        result = generate(role, prompt, schema)
        event = registry.calls[-1]
        equal(event['sent_parameters'], model['request_parameters'], 'actual wire parameters')
        if event.get('reported_model') != model['model']:
            raise LLMError('API returned a different model')
        usage = event.get('usage') or {}
        observed = usage.get('prompt_tokens')
        if not isinstance(observed, int) or observed <= 0:
            event.update(status='error', error='Missing server token usage')
            raise LLMError('API did not report prompt token usage; input audit unavailable')
        if observed > count(prompt) or observed + model['max_output_tokens'] > model['num_ctx']:
            event.update(status='error', error='Server input accounting exceeds frozen limits')
            raise LLMError('InputBudget: server usage exceeds the frozen local window or margin')
        if event.get('output_at_limit'):
            raise LLMError('Generated decision reached its output limit')
        return result

    registry.generate = guarded
    return registry, client, {'endpoint': provider.base_url + '/chat/completions',
        'model': client.settings.model, 'authentication': 'Bearer; credential excluded',
        'model_identity_limits': 'API ID only; no remote weights/template attestation',
        'context_limits': 'local 16384 cap plus per-call reported usage checks; server settings unchanged',
        'retries': 0, 'concurrency': 1}


def paired_summary(records, historical):
    result = {}
    for scope in SCOPES:
        groups = {a: {r['key']: r for r in rec.data['results'] if r['condition'] == scope}
                  for a, rec in records.items()}
        paired = sorted(set(groups['D3000']) & set(groups['D6000']))
        part = {'paired_questions': len(paired), 'evaluators': {}}
        for evaluator in ('evidence_v2', 'literal_v1'):
            ev = {'arms': {}, 'question_gains': [], 'question_losses': [],
                  'evidence_gained': [], 'evidence_lost': []}
            for arm, rr in groups.items():
                ev['arms'][arm] = {'completed': len(rr),
                    'complete': sum(r['evaluations'][evaluator]['complete_selected_anchors'] for r in rr.values()),
                    'terminal_errors': sum(r['status'] != 'ok' for r in rr.values()),
                    'complete_without_terminal_error': sum(r['status'] == 'ok' and r['evaluations'][evaluator]['complete_selected_anchors'] for r in rr.values()),
                    'candidate_complete': sum(r['candidate_evaluation'][evaluator]['complete_selected_anchors'] for r in rr.values())}
            for key in paired:
                left, right = (groups[a][key]['evaluations'][evaluator] for a in ARMS)
                if right['complete_selected_anchors'] and not left['complete_selected_anchors']:
                    ev['question_gains'].append(key)
                if left['complete_selected_anchors'] and not right['complete_selected_anchors']:
                    ev['question_losses'].append(key)
                changes = hits_change(left['selected_hits'], right['selected_hits'])
                for kind, field in (('gained', 'evidence_gained'), ('lost', 'evidence_lost')):
                    ev[field] += [{'key': key, 'evidence_id': anchor} for anchor in changes[kind]]
            part['evaluators'][evaluator] = ev
        part['false_sufficiency'] = {a: [r['key'] for r in rr.values() if r['declared_sufficient'] and
            not r['evaluations']['evidence_v2']['complete_selected_anchors']] for a, rr in groups.items()}
        part['input_sample_reduction'] = {a: sum(d.get('request', {}).get('samples_removed', 0) > 0
            for r in rr.values() for d in r['plan']['decisions']) for a, rr in groups.items()}
        part['searches_logical'] = {a: sum(r['search_count'] for r in rr.values()) for a, rr in groups.items()}
        part['decisions_logical'] = {a: sum(len(r['plan']['decisions']) for r in rr.values()) for a, rr in groups.items()}
        part['historical_D_complete_secondary_only'] = sum(r['condition'] == scope and
            r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in historical)
        part['changed_trajectories'] = [key for key in paired if
            [(s['text'], s['document_ids']) for s in groups['D3000'][key]['diagnostics']['searches']] !=
            [(s['text'], s['document_ids']) for s in groups['D6000'][key]['diagnostics']['searches']]]
        result[scope] = part
    complete = all(s['paired_questions'] == 70 for s in result.values())
    no_losses = all(not s['evaluators']['evidence_v2']['question_losses'] and
                    not s['evaluators']['evidence_v2']['evidence_lost'] for s in result.values())
    return {'title': TITLE, 'complete': complete, 'scopes': result,
            'recommendation': 'review_for_next_stage' if complete and no_losses else 'revise' if complete else 'incomplete',
            'application_promoted': False}


def write_report(output, summary, status):
    lines = ['# ' + TITLE, '',
        'O agente decidiu novas buscas e encerramentos em dois braços: 3.000 e 6.000 tokens BGE de documentos. '
        'Os dois usam a mesma API atual da Spark; D histórico é apenas referência secundária. '
        'As mesmas 70 perguntas aparecem nos dois escopos. Não há geração de respostas finais.', '',
        'Estado: **' + ('completo' if summary['complete'] else 'incompleto') + '**.', '',
        '| Escopo | Pares | Completas 3.000 / 6.000 | Ganhos / perdas | Evidências ganhas / perdidas | Erros terminais 3.000 / 6.000 |',
        '|---|---:|---:|---:|---:|---:|']
    for scope, s in summary['scopes'].items():
        ev = s['evaluators']['evidence_v2']; a, b = (ev['arms'][arm] for arm in ARMS)
        lines.append(f"| {scope} | {s['paired_questions']}/70 | {a['complete']} / {b['complete']} | {len(ev['question_gains'])} / {len(ev['question_losses'])} | {len(ev['evidence_gained'])} / {len(ev['evidence_lost'])} | {a['terminal_errors']} / {b['terminal_errors']} |")
    for scope, s in summary['scopes'].items():
        ev = s['evaluators']['evidence_v2']
        lines += ['', '## ' + scope, '',
            'Ganhos: ' + (', '.join(ev['question_gains']) or 'nenhum') + '.', '',
            'Perdas: ' + (', '.join(ev['question_losses']) or 'nenhuma') + '.', '',
            'Evidências perdidas: ' + (', '.join(x['key']+'/'+x['evidence_id'] for x in ev['evidence_lost']) or 'nenhuma') + '.', '',
            f"Trajetórias de busca diferentes entre os braços: {len(s['changed_trajectories'])}.", '',
            'Declarações de suficiência com contexto incompleto: ' + str({a: len(v) for a, v in s['false_sufficiency'].items()}) + '.', '',
            'Decisões com amostras extras reduzidas: ' + str(s['input_sample_reduction']) + '.']
    lines += ['', '## Execução e interpretação', '',
        'Recomendação: ' + summary['recommendation'] + '. Nenhuma promoção automática à aplicação.', '',
        'Janela local: 16.384 tokens Qwen; saída reservada: 4.096; margem: 512. Thinking desligado, temperatura 0 e seed 42. '
        'Mesmos prompts, feedback limitado, ranking global, reranking local e quatro buscas/decisões. '
        'A redução existente de amostras extras continua ativa; documentos selecionados não são truncados.', '',
        'Chamadas sequenciais, sem retry automático. Requisições idênticas entre os braços compartilham resultado somente nesta rodada. '
        'Buscas/rankings históricos são reutilizados somente quando a entrada e o índice coincidem. '
        'Custos físicos, lógicos e históricos ficam separados no cache e nos registros; tempo físico não representa latência sem cache.', '',
        f"Novas decisões físicas: {status['physical_planning_calls']}; novas buscas: {status['physical_queries']}; novos rankings globais: {status['physical_global']}. Comparação detalhada, literal_v1 e perdas por evidência: comparison.json.", '',
        'O gateway informa o ID e o uso de tokens, mas não atesta pesos, template remoto ou aplicação de todos os parâmetros. '
        'Ambos os braços recebem o mesmo contrato; não se presume equivalência perfeita com o antigo endpoint localhost.', '',
        'resultados: D3000/retrieval.json e D6000/retrieval.json; decisões/requisições e operações: cache.json; '
        'trajetórias e avaliações após cada decisão nos registros. Gold usado somente na avaliação posterior à seleção.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')


def run(output, source_run, preflight_only=False):
    output, source_run = output.resolve(), source_run.resolve()
    if output == source_run or output.is_relative_to(source_run) or source_run.is_relative_to(output):
        raise ValueError('Use a new output directory outside the source')
    output.mkdir(parents=True, exist_ok=True)
    clock = RunClock(output / 'timing.json')
    try:
        return _run(output, source_run, preflight_only, clock)
    except BaseException as exc:
        artifacts.save_json(output / 'blocked.json', {'type': type(exc).__name__, 'message': str(exc),
            'instruction': 'Preserve unknown outcomes; do not repeat calls or switch provider automatically.'})
        path = output / 'execution_status.json'
        status = artifacts.read_json(path) if path.exists() else {}
        status.update(status='incomplete', blocker=str(exc))
        artifacts.save_json(path, status)
        clock.finish('interrupted' if isinstance(exc, KeyboardInterrupt) else 'blocked')
        raise


def _run(output, source_run, preflight_only, clock):
    bootstrap_python_path()
    from huggingface_hub import snapshot_download
    from service.rag.v2.AdaptiveRetrieval import InvestigationController, Snapshot, decision_failure
    from service.rag.v2.DirectedRetrieval import merge_and_rerank
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    from benchmark.evaluation.evidence import SourceAligner
    from benchmark.evaluation.literal import anchor_coverage
    with offline_only():
        source_sig, historical, operations, protected = load_history(source_run)
        ref = load_reference(snapshot_download('BAAI/bge-m3', local_files_only=True))
        planner, _, window = setup_window_audit(source_sig, ref)
        aligner = SourceAligner(CORPUS, artifacts.read_json(ref['rules_path']))
        corpus = artifacts.source_corpus(ref['anchors'])
        def evaluate(case, parents):
            entries = [p.entry for p in parents]
            return {'evidence_v2': aligner.score(case, entries),
                    'literal_v1': anchor_coverage(case, {'evidence': entries}, ref['anchors'], corpus)}
        reproduction = []
        for row in historical:
            raw_states, _ = reconstruct_states(row, operations, ref)
            states = select_states(raw_states, ref)
            verify_control(row, states, lambda ps, c=next(c for c in ref['cases'] if c.id == row['case_id']): evaluate(c, ps), ref['chunks'])
            reproduction.append(row['key'])
    artifacts.save_json(output / 'control_reproduction.json', {'status': 'passed', 'rows': len(reproduction)})
    from llm_client import LLMSettings
    settings = LLMSettings.from_env()
    extras = [PROJECT_ROOT/'llm_client.py'] + sorted((PROJECT_ROOT/'tests').rglob('*.py'))
    signature = {'study': 'document_budget_cycle', 'version': 'paired_live_budget_v1',
        'title': TITLE, 'implementation_sha256': implementation_hash(),
        'extra_code_sha256': {str(p.relative_to(PROJECT_ROOT)): sha(p) for p in extras},
        'source_run': str(source_run), 'source_hashes': protected,
        'endpoint': settings.base_url.rstrip('/') + '/chat/completions', 'llm': source_sig['llm'],
        'endpoint_identity_limits': 'fresh same-endpoint control; historical D is secondary only',
        'arms': ARMS, 'window': window, 'config_sha256': sha(PROJECT_ROOT/'config/config.toml'),
        'index_sha256': sha(ref['index']), 'question_count': 70, 'scopes': list(SCOPES),
        'policies': {'controller': 'bounded_feedback_v1', 'interface': 'document_search_v1',
            'max_decisions': 4, 'max_searches': 4, 'order': 'global_score', 'initial_search': 'frozen_reference',
            'sample_reduction': 'existing_prepare_payload', 'call_sharing': 'identical_request_within_current_run_only',
            'retry': 0, 'concurrency': 1, 'arm_order': 'alternate_by_question_scope'},
        'dependencies': {p: version(p) for p in ('openai','transformers','torch','numpy','sentence-transformers','python-dotenv')},
        'evaluation_versions': ['evidence_v2','literal_v1'], 'answer_generation_calls': 0}
    signature['fingerprint'] = digest(signature)
    sigpath = output/'signature.json'
    if sigpath.exists(): equal(artifacts.read_json(sigpath), signature, 'resume signature')
    artifacts.save_json(sigpath, signature)
    if not (output/'code.zip').exists():
        with zipfile.ZipFile(output/'code.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in code_files() + extras + [PROJECT_ROOT/'config/config.toml']:
                z.write(p,p.relative_to(PROJECT_ROOT))
    records = {a: artifacts.Recorder(output/a,'retrieval',signature) for a in ARMS}
    cachepath = output/'cache.json'
    cache = artifacts.read_json(cachepath) if cachepath.exists() else {'signature':signature,'decisions':{},'queries':{},'global':{}}
    equal(cache['signature'], signature, 'cache signature')
    def save(): artifacts.save_json(cachepath,cache)
    save()
    def status(reason=None):
        events = [e for d in cache['decisions'].values() for e in d.get('events',[])]
        data = {'status':'complete' if all(len(r.done)==140 for r in records.values()) and reason is None else 'incomplete',
            'observations':{a:len(r.done) for a,r in records.items()}, 'reason':reason,
            'physical_planning_calls':len(events), 'physical_queries':sum(v.get('operation_origin')=='live' for v in cache['queries'].values()),
            'physical_global':sum(v.get('operation_origin')=='live' for v in cache['global'].values()),
            'physical_model_seconds':sum(e.get('latency_seconds',0) for e in events),
            'physical_prompt_tokens':sum((e.get('usage') or {}).get('prompt_tokens',0) for e in events),
            'physical_completion_tokens':sum((e.get('usage') or {}).get('completion_tokens',0) for e in events),
            'planning_usage_unknown':any(v.get('planning_calls_unknown') or v['status']=='started' for v in cache['decisions'].values()),
            'answer_generation_calls':0}
        artifacts.save_json(output/'execution_status.json',data)
        summary=paired_summary(records,historical)
        artifacts.save_json(output/'comparison.json',summary)
        write_report(output,summary,data)
        clock.flush()
        return data
    def snapshot(ranking,runs,budget):
        validate_ranking(ranking,ref['chunks'])
        parents=parents_from_ranking(ranking,ref['chunks'],ref['parents'],ref['vectors'],ref['tokens'])
        selected,trace=pack_order(parents,budget=budget)
        return Snapshot(ranking,runs,parents,selected,trace)
    audit=[]
    for case in ref['cases']:
        for scope in SCOPES:
            saved=ref['rows'][f'{case.id}:{scope}']; initial=original_run(saved)
            for arm,budget in ARMS.items():
                req=planner.prepare('adaptive',case.question,case.metadata.get('history',[]),
                    snapshot(initial[1],[initial],budget),{'remaining_decisions':4},saved['scope'],3)
                audit.append({'key':saved['key'],'arm':arm,'tokens':req['input_tokens_counted'],'samples_removed':req['samples_removed']})
    artifacts.save_json(output/'initial_input_audit.json',{'status':'passed','requests':audit,'generation_calls':0})
    if preflight_only:
        status('offline_preflight_complete'); clock.finish('offline_preflight_complete'); return
    # A fully completed identical resume never initializes transport.
    if all(len(r.done)==140 for r in records.values()):
        status(); clock.finish('complete'); return
    live,client,transport=spark_registry(source_sig['llm'],planner.count)
    artifacts.save_json(output/'transport.json',transport)
    planner.registry=live
    retriever=None
    try:
        clock.set_phase('evaluation')
        for i,case in enumerate(ref['cases']):
            for j,scope in enumerate(SCOPES):
                key=f'{case.id}:{scope}'; saved=ref['rows'][key]
                order=list(ARMS) if (i*2+j)%2==0 else list(reversed(ARMS))
                for arm in order:
                    if key in records[arm].done: continue
                    started=time.perf_counter(); initial=original_run(saved)
                    first=snapshot(initial[1],[initial],ARMS[arm]); observed=[]; advanced={}; used=[]
                    def decide(mode,current,ledger,remaining):
                        observed.append(current)
                        try:
                            request=planner.prepare(mode,case.question,case.metadata.get('history',[]),current,ledger,saved['scope'],remaining)
                        except Exception as exc:
                            return {'status':'error','error':decision_failure(exc),'events':[]}
                        ck=digest(request); before=len(live.calls)
                        def callback():
                            begin=len(live.calls)
                            unknown=False
                            try: value=planner.execute(request)
                            except Exception as exc:
                                from llm_client import LLMConnectionError
                                unknown=isinstance(exc,LLMConnectionError)
                                value={'status':'error','error':decision_failure(exc,live.calls[begin:],request)}
                            return {**value,'events':copy.deepcopy(live.calls[begin:]),'request':request,'planning_calls_unknown':unknown}
                        value=copy.deepcopy(get_plan(cache['decisions'],ck,callback,save))
                        origin='live' if len(live.calls)>before else 'shared_cache'
                        value['operation_origin']=origin
                        if value.get('planning_calls_unknown'):
                            raise RuntimeError('Unknown planning outcome; study incomplete, call not repeated')
                        for event in value.get('events',[]):
                            event['operation_origin']=origin
                            if origin!='live':
                                event['logical_latency_seconds']=event.get('latency_seconds',0)
                                event['latency_seconds']=0.
                        used.append({'kind':'decision','cache_key':ck,'origin':origin})
                        return value
                    def operation(group,ck,callback):
                        nonlocal retriever
                        if ck not in cache[group] and ck in operations[group]:
                            old=copy.deepcopy(operations[group][ck])
                            if old['status']!='ok': raise RuntimeError('Historical operation has failed or unknown outcome')
                            validate_ranking(old['ranking'],ref['chunks'])
                            old.update(operation_origin='historical',historical_latency_seconds=old.get('latency_seconds',0),latency_seconds=0.)
                            cache[group][ck]=old;save()
                        if ck not in cache[group] and retriever is None:
                            with clock.measure('retriever_setup'): retriever=build_retriever(ref)
                        with clock.measure(group): value,physical=checkpoint_operation(cache[group],ck,callback,save)
                        origin=value.get('operation_origin') if physical or value.get('operation_origin')=='historical' else 'shared_cache'
                        used.append({'kind':group,'cache_key':ck,'origin':origin})
                        if value.get('usage_unknown') or value['status']=='started':
                            raise RuntimeError('Unknown retrieval operation; not repeated')
                        if value['status']!='ok': raise RuntimeError(value['error'])
                        return value
                    def advance(search,previous):
                        def query():
                            ranking,diagnostics=retriever.search(search.text,search.document_ids,1)
                            return {'ranking':ranking,'diagnostics':diagnostics,'physical_reranker_pairs':len(ranking)}
                        found=operation('queries',digest([search.text,search.document_ids]),query)
                        runs=previous.runs+[(search,found['ranking'],found['diagnostics'])]
                        gk=digest([saved['query'],[(s.to_dict(),rr) for s,rr,_ in runs]])
                        def rerank():
                            ranking=merge_and_rerank(saved['query'],runs,ref['chunks'],retriever.reranker)
                            return {'ranking':ranking,'physical_reranker_pairs':len(ranking)}
                        result=operation('global',gk,rerank)
                        current=snapshot(result['ranking'],runs,ARMS[arm]); advanced[search.query_id]=current
                        return current
                    final,plan=InvestigationController(interface='document_search_v1',error_policy='bounded_feedback_v1').run('adaptive',first,decide,advance,saved['scope'])
                    for step in plan['steps']:
                        before=observed[step['decision_index']-1]
                        after=advanced.get(step.get('effective_query',{}).get('query_id'),before)
                        step.update(context_evaluation=evaluate(case,after.selected),candidate_evaluation=evaluate(case,after.parents),
                            packing_trace=after.packing_trace,context_tokens=sum(p.tokens for p in after.selected))
                    searches=[{**s.to_dict(),'diagnostics':diag} for s,_,diag in final.runs]
                    records[arm].add(key,status=plan['status'],case_id=case.id,condition=scope,scope=saved['scope'],query=saved['query'],
                        evidence=[p.entry for p in final.selected],packing_trace=final.packing_trace,context_tokens=sum(p.tokens for p in final.selected),
                        evaluations=evaluate(case,final.selected),candidate_evaluation=evaluate(case,final.parents),
                        initial_evaluations=evaluate(case,first.selected),diagnostics={'stages':{'reranker':final.ranking},'searches':searches},
                        plan=plan,stop_reason=plan['stop_reason'],declared_sufficient=plan['declared_sufficient'],
                        search_count=len(searches),operations=used,physical_case_seconds=time.perf_counter()-started)
                    state=status()
                    print(f"{TITLE}: {state['observations']}; decisões físicas {state['physical_planning_calls']}",flush=True)
                    # A transport/accounting incident invalidates continuing the controlled run.
                    bad=[e for d in plan['decisions'] for e in d.get('events',[]) if e.get('status')=='error']
                    if bad or any(d.get('error',{}).get('stage')=='generation' for d in plan['decisions']):
                        raise RuntimeError('Generation incident recorded; stopping without automatic retry')
                    if any(v.get('usage_unknown') or v['status']=='started' for g in ('queries','global') for v in cache[g].values()):
                        raise RuntimeError('Unknown operation outcome; stopping without automatic retry')
        if client.list_models().count(source_sig['llm']['model'])!=1:
            raise ValueError('Model no longer available at the endpoint')
    finally:
        client.close()
    equal(implementation_hash(),signature['implementation_sha256'],'code after execution')
    for name,expected in signature['extra_code_sha256'].items(): equal(sha(PROJECT_ROOT/name),expected,'code '+name)
    changed=[name for name,h in protected.items() if not Path(name).exists() or sha(name)!=h]
    artifacts.save_json(output/'preservation.json',{'status':'failed' if changed else 'passed','files_verified':len(protected),'changed':changed})
    if changed: raise ValueError('Historical input changed during execution')
    load_reference(snapshot_download('BAAI/bge-m3',local_files_only=True))
    for r in records.values(): r.finish()
    state=status();clock.finish('complete')
    return state
