"""Teste com o dobro de documentos: fixed global order, 3000 vs 6000 BGE tokens.

Runs whole-parent packing and evidence evaluation on D's saved search trajectories.
Audits frozen Qwen input-window sizes locally, never invoking an LLM or retriever.
"""
import copy
from functools import lru_cache
from importlib.metadata import version
import json
from pathlib import Path
import time
import zipfile

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.reproducibility import CORPUS, code_files, implementation_hash, sha
from benchmark.search.global_order_replay import (
    equal, hits_change, load_history, offline_only, reconstruct_states, verify_control)
from benchmark.selection.run import digest

TITLE = 'Teste com o dobro de documentos'
VERSION = 'document_budget_replay_v1'
ARMS = {'D3000': 3000, 'D6000': 6000}
SCOPES = ('collection', 'oracle_scope')


def select_states(states, ref):
    """Only budget changes. Both arms share order, parent objects and tokenization."""
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order
    result = []
    for state in states:
        parents = parents_from_ranking(state['ranking'], ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
        selected, traces = {}, {}
        for arm, budget in ARMS.items():
            selected[arm], traces[arm] = pack_order(parents, budget=budget)
            equal([t['parent_id'] for t in traces[arm]], [p.parent_id for p in parents], 'identical order at both budgets')
        # Adapter for the already-tested control-reproduction helper.
        selected['G_global'], traces['G_global'] = selected['D3000'], traces['D3000']
        result.append({**state, 'parents': parents, 'selected': selected, 'traces': traces})
    return result


def setup_window_audit(source_signature, ref):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
    model = source_signature['llm']
    if (model['num_ctx'], model['max_output_tokens'], model['input_safety_margin'], model['thinking']) != (16384, 4096, 512, False):
        raise ValueError('Expected frozen 16384/4096/512 no-thinking profile')
    directory = snapshot_download(model['tokenizer'], local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    equal(digest(tokenizer.get_vocab()), model['tokenizer_digest'], 'Qwen vocabulary')
    equal(digest(tokenizer.get_chat_template()), model['tokenizer_template_sha256'], 'Qwen chat template')
    kwargs = model['request_parameters'].get('chat_template_kwargs', {})
    @lru_cache(maxsize=2048)
    def count(prompt):
        return len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
            tokenize=True, add_generation_prompt=True, **kwargs)) + model['input_safety_margin']
    options = dict(input_format='compact_v1', decision_contract='document_search_v1', reason_validation='soft_length_v1')
    planner = InvestigationPlanner(None, ref['catalog'], ref['chunks'], count, model['num_ctx'], model['max_output_tokens'], **options)
    # Measurement only: build the complete observation before the normal policy
    # drops supplementary samples. No such large window is sent to any server.
    measuring_planner = InvestigationPlanner(None, ref['catalog'], ref['chunks'], count, 1_000_000, model['max_output_tokens'], **options)
    return planner, measuring_planner, {'model': model['model'], 'window': model['num_ctx'],
        'output_reserved': model['max_output_tokens'], 'input_margin': model['input_safety_margin'],
        'tokenizer': model['tokenizer'], 'tokenizer_revision': Path(directory).name,
        'vocabulary_sha256': model['tokenizer_digest'], 'template_sha256': model['tokenizer_template_sha256'],
        'remote_capacity_validated': False, 'method': 'frozen_local_template_not_a_server_or_latency_test'}


def audit_request(planner, measuring_planner, snapshot, case, ledger, scope, remaining_searches, expected=None):
    raw = measuring_planner.prepare('adaptive', case.question, case.metadata.get('history', []),
        snapshot, ledger, scope, remaining_searches)
    # prepare_payload expects the pre-render ledger, not the already-rendered
    # remaining_decisions field. Restore it to avoid accidentally changing budgets.
    payload = copy.deepcopy(raw['payload'])
    payload['ledger'] = ledger
    minimum = copy.deepcopy(payload)
    minimum['retrieved_samples'] = []
    minimum_request = measuring_planner.prepare_payload('adaptive', minimum)
    record = {'full_input_tokens_including_margin': raw['input_tokens_counted'],
        'full_total_including_output': raw['input_tokens_counted'] + planner.output_tokens,
        'minimum_total_without_samples': minimum_request['input_tokens_counted'] + planner.output_tokens,
        'samples_available': len(raw['payload']['retrieved_samples']),
        'context_parent_ids': snapshot.context_ids(), 'document_bge_tokens': sum(p.tokens for p in snapshot.selected)}
    try:
        request = planner.prepare_payload('adaptive', payload)
    except ValueError as exc:
        if not str(exc).startswith('InputBudget:'):
            raise
        if expected is not None:
            raise ValueError('Historical 3000-token request no longer fits') from exc
        record.update(status='does_not_fit', fits=False, samples_removed=record['samples_available'],
                      input_tokens_including_margin=None, total_including_output=None, rendered_request_sha256=None)
        return record
    if expected is not None:
        equal(request, expected, 'exact historical decision request and token count')
    record.update(status='fits_after_sample_reduction' if request['samples_removed'] else 'fits', fits=True,
        samples_removed=request['samples_removed'], input_tokens_including_margin=request['input_tokens_counted'],
        total_including_output=request['input_tokens_counted'] + request['output_reserved_tokens'],
        rendered_request_sha256=digest(request['rendered_request']))
    return record


def summarize(rows, trajectories, windows):
    import numpy as np
    scopes = {}
    for scope in SCOPES:
        rr = [r for r in rows if r['condition'] == scope]
        if len(rr) != 70 or len({r['case_id'] for r in rr}) != 70:
            raise ValueError('Expected the same 70 original questions in each scope')
        item = {}
        for evaluator in ('evidence_v2', 'literal_v1'):
            gains, regressions, evidence_gained, evidence_lost = [], [], [], []
            for r in rr:
                g, large = (r['arms'][a]['evaluations'][evaluator] for a in ARMS)
                if large['complete_selected_anchors'] and not g['complete_selected_anchors']:
                    gains.append(r['key'])
                if g['complete_selected_anchors'] and not large['complete_selected_anchors']:
                    regressions.append(r['key'])
                change = hits_change(g['selected_hits'], large['selected_hits'])
                evidence_gained += [{'key': r['key'], 'evidence_id': a} for a in change['gained']]
                evidence_lost += [{'key': r['key'], 'evidence_id': a} for a in change['lost']]
            item[evaluator] = {'arms': {a: {'complete': sum(r['arms'][a]['evaluations'][evaluator]['complete_selected_anchors'] for r in rr),
                'mean_anchor_recall': sum(r['arms'][a]['evaluations'][evaluator]['selected_anchor_recall'] for r in rr) / 70}
                for a in ARMS}, 'question_gains': gains, 'question_regressions': regressions,
                'evidence_gained': evidence_gained, 'evidence_lost': evidence_lost}
        tt = [t for t in trajectories if t['condition'] == scope]
        item['initial_complete'] = {a: sum(t['snapshots'][0]['arms'][a]['evaluations']['evidence_v2']['complete_selected_anchors'] for t in tt) for a in ARMS}
        item['candidate_complete'] = sum(r['candidate_evaluation']['evidence_v2']['complete_selected_anchors'] for r in rr)
        item['context_tokens'] = {a: {'median': float(np.median([r['arms'][a]['context_tokens'] for r in rr])),
            'p95': float(np.percentile([r['arms'][a]['context_tokens'] for r in rr],95)),
            'max': max(r['arms'][a]['context_tokens'] for r in rr)} for a in ARMS}
        item['alignment_pending'] = {a: [{'key': r['key'], 'anchors': r['arms'][a]['evaluations']['evidence_v2']['pending_anchors']}
            for r in rr if r['arms'][a]['evaluations']['evidence_v2']['pending_anchors']] for a in ARMS}
        item['intermediate_losses'] = {a: [{'key': t['key'], 'after_query': s['query_id'],
            'evidence_ids': s['arms'][a]['change_since_previous_search']['lost']}
            for t in tt for s in t['snapshots'] if s['arms'][a]['change_since_previous_search']['lost']] for a in ARMS}
        item['window_audit'] = {}
        for kind in ('historical_decision', 'final_sizing_only'):
            ww = [w for w in windows if w['condition'] == scope and w['kind'] == kind]
            item['window_audit'][kind] = {a: {'total': len(ww), 'fits': sum(w['arms'][a]['fits'] for w in ww),
                'samples_reduced': sum(w['arms'][a]['status']=='fits_after_sample_reduction' for w in ww),
                'does_not_fit': [w['key'] + (f"/decision{w['decision_index']}" if kind=='historical_decision' else '') for w in ww if not w['arms'][a]['fits']],
                'max_minimum_total_without_samples': max(w['arms'][a]['minimum_total_without_samples'] for w in ww),
                'median_input_tokens_including_margin': (float(np.median([w['arms'][a]['input_tokens_including_margin'] for w in ww if w['arms'][a]['fits']]))
                                                       if any(w['arms'][a]['fits'] for w in ww) else None)}
                for a in ARMS}
        scopes[scope] = item
    checks = {'no_complete_question_regressions': all(not s['evidence_v2']['question_regressions'] for s in scopes.values()),
              'no_final_evidence_losses': all(not s['evidence_v2']['evidence_lost'] for s in scopes.values()),
              'all_audited_requests_fit_current_local_window': all(w['arms']['D6000']['fits'] for w in windows)}
    return {'title': TITLE, 'scopes': scopes, 'checks': checks,
        'recommendation': 'eligible_for_future_full_cycle_test' if all(checks.values()) else 'revise',
        'costs': {'new_model_calls': 0, 'new_retrieval_calls': 0, 'new_reranker_calls': 0,
                 'changed_document_budget_only': True, 'measured_full_cycle_latency_or_model_quality': False}}


def report(output, summary, rows, validation):
    lines = ['# ' + TITLE, '', 'Comparação: **3.000 contra 6.000 tokens de documentos**, com a mesma ordem global e as mesmas buscas salvas de D.', '',
        'O código de montagem do contexto foi executado nos dois limites. Não foram feitas novas buscas, chamadas ao modelo ou respostas finais. As 70 perguntas são as mesmas nos dois escopos.', '',
        '| Escopo | Completas com 3.000 | Completas com 6.000 | Ganhos | Regressões | Evidências ganhas/perdidas |',
        '|---|---:|---:|---:|---:|---:|']
    for scope, s in summary['scopes'].items():
        m = s['evidence_v2']
        lines.append(f"| {scope} | {m['arms']['D3000']['complete']}/70 | {m['arms']['D6000']['complete']}/70 | {len(m['question_gains'])} | {len(m['question_regressions'])} | {len(m['evidence_gained'])}/{len(m['evidence_lost'])} |")
    for scope, s in summary['scopes'].items():
        lines += ['', '## ' + ('Coleção inteira' if scope=='collection' else 'Documentos corretos: controle diagnóstico'), '']
        for ev in ('evidence_v2','literal_v1'):
            m = s[ev]
            lines += [f"### {ev}", '', f"Cobertura parcial média: {m['arms']['D3000']['mean_anchor_recall']:.2%} → {m['arms']['D6000']['mean_anchor_recall']:.2%}.", '',
                'Perguntas ganhas: ' + (', '.join(m['question_gains']) or 'nenhuma') + '.', '',
                'Perguntas perdidas: ' + (', '.join(m['question_regressions']) or 'nenhuma') + '.', '',
                'Evidências ganhas: ' + (', '.join(x['key']+'/'+x['evidence_id'] for x in m['evidence_gained']) or 'nenhuma') + '.', '',
                'Evidências perdidas: ' + (', '.join(x['key']+'/'+x['evidence_id'] for x in m['evidence_lost']) or 'nenhuma') + '.']
        lines += ['', f"Já completas na busca inicial, com 3.000/6.000: {s['initial_complete']['D3000']}/{s['initial_complete']['D6000']}. Isso não mede quais buscas o agente dispensaria.", '',
            f"Candidatos finais completos: {s['candidate_complete']}/70, iguais nos dois limites. O espaço maior não encontra evidências ausentes desse conjunto."]
    lines += ['', '## Os contextos cabem na janela atual?', '',
        'Janela local mantida em **16.384 tokens Qwen**, incluindo mensagem com schema, pergunta, histórico, catálogo, contexto e amostras; reserva de 4.096 para saída e margem de 512. Os documentos usam contagem BGE; por isso 6.000 tokens de documentos não são 6.000 tokens Qwen.', '',
        'A conferência foi feita com o tokenizer e o template congelados do Qwen, incluindo thinking desligado. A regra existente pode retirar amostras adicionais, mas não corta os parents selecionados. Isso é uma conferência local de tamanho; não valida o limite ou alterações de template do Open WebUI atual.', '',
        '| Escopo e situação | Conferências | Cabem com 3.000 | Cabem com 6.000 | Com 6.000: amostras reduzidas |', '|---|---:|---:|---:|---:|']
    for scope, s in summary['scopes'].items():
        for kind, mm in s['window_audit'].items():
            lines.append(f"| {scope} / {'decisões históricas' if kind=='historical_decision' else 'dimensionamento final'} | {mm['D3000']['total']} | {mm['D3000']['fits']} | {mm['D6000']['fits']} | {mm['D6000']['samples_reduced']} |")
            if mm['D6000']['does_not_fit']:
                lines += ['', 'Não cabem nem removendo as amostras: ' + ', '.join(mm['D6000']['does_not_fit']) + '.', '']
    lines += ['', 'O dimensionamento final é uma conferência hipotética do contexto final de cada caso, não uma decisão adicional do agente. As conferências repetem perguntas e não representam novos exemplos ou chamadas.', '',
        '## Quatro casos já investigados', '', '| Caso na coleção | Com 3.000 | Com 6.000 | Tokens efetivamente selecionados: 3.000 / 6.000 |', '|---|---|---|---:|']
    for r in rows:
        if r['condition']=='collection' and r['case_id'] in ('REAL-C01','REAL-C02','REAL-C08','REAL-L05'):
            statuses=['completa' if r['arms'][a]['evaluations']['evidence_v2']['complete_selected_anchors'] else 'incompleta' for a in ARMS]
            lines.append(f"| {r['case_id']} | {statuses[0]} | {statuses[1]} | {r['arms']['D3000']['context_tokens']} / {r['arms']['D6000']['context_tokens']} |")
    lines += ['', '## Recomendação e limites', '',
        '**' + ('Elegível para um teste completo posterior.' if summary['recommendation']!='revise' else 'Revisar antes de aplicar ou iniciar o teste completo.') + '**', '',
        'Critérios: nenhuma pergunta completa perdida, nenhuma evidência final perdida por evidence_v2 nos dois escopos e todas as observações auditadas cabendo na janela local atual. Os resultados de qualidade e os problemas de janela são reportados separadamente.', '',
        'Mais espaço pode aceitar blocos grandes antes rejeitados e deslocar outros trechos. Por isso a seleção de 6.000 não é presumida como um superconjunto da de 3.000. Não foram alterados ranking, chunking, prompts, avaliadores, consultas, janela ou configuração do servidor.', '',
        f"Controle reproduzido: {validation['rows']} resultados finais, {validation['snapshots']} estados e {validation['historical_requests_reproduced']} requisições históricas com o mesmo texto e contagem de entrada.", '',
        'Os tempos em timing.json são deste teste local. Não medimos latência de geração, novos encerramentos do agente, respostas finais ou economia de chamadas. O contexto diferente pode mudar a investigação em um ciclo completo.', '',
        'results.json contém os contextos; trajectories.json, as escolhas após cada busca; window_audit.json, os tamanhos e impedimentos; comparison.json, os ganhos e perdas; signature.json e code.zip fixam a execução; preservation.json verifica os históricos.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')


def run(output, source):
    output, source = Path(output).resolve(), Path(source).resolve()
    if output==source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Use a new output directory outside the source')
    with offline_only():
        try:
            return _run(output, source)
        except BaseException as exc:
            if not output.exists() or not any(output.iterdir()):
                artifacts.save_json(output/'execution_status.json', {'status':'incomplete','stage':'preparation',
                    'error':str(exc),'new_model_calls':0,'new_retrieval_calls':0})
            raise


def _run(output, source):
    started=time.perf_counter()
    bootstrap_python_path()
    from huggingface_hub import snapshot_download
    from benchmark.search.runtime import load_reference
    from benchmark.core.timing import RunClock
    from benchmark.evaluation.evidence import SourceAligner
    from benchmark.evaluation.literal import anchor_coverage
    from benchmark.selection.diagnostic import minimum_parent_cover
    from service.rag.v2.AdaptiveRetrieval import Snapshot
    from service.rag.v2.DirectedRetrieval import DirectedSearch
    source_signature, source_rows, operations, protected=load_history(source)
    if any(output.is_relative_to(Path(p).parent) for p in protected if Path(p).name=='signature.json'):
        raise ValueError('Output overlaps a historical ancestor')
    ref=load_reference(context_tokenizer=snapshot_download('BAAI/bge-m3',local_files_only=True))
    equal(sorted(r['key'] for r in source_rows),sorted(ref['rows']),'same 70 questions and scopes')
    equal(sha(ref['index']),source_signature['index_sha256'],'index')
    equal(sha(PROJECT_ROOT/'config/config.toml'),source_signature['config_sha256'],'frozen configuration')
    rules_path=source/'evaluation_rules.json'
    equal(artifacts.read_json(rules_path),artifacts.read_json(ref['rules_path']),'frozen rules')
    equal({'questions':sha(ref['directory']/'questions.json'),'anchors':sha(ref['directory']/'evidence.json'),
           'rules':sha(ref['rules_path'])},source_signature['datasets'],'datasets')
    protected.update({str(p.resolve()):sha(p) for p in [ref['index'],ref['rules_path'],ref['directory']/'questions.json',
        ref['directory']/'evidence.json',PROJECT_ROOT/'config/config.toml']})
    protected.update({str(p.resolve()):sha(p) for p in CORPUS.glob('*') if p.is_file()})
    planner,measuring_planner,window_profile=setup_window_audit(source_signature,ref)
    signature={'study':'document_budget_replay','title':TITLE,'version':VERSION,'source_run':str(source),
        'source_signature':source_signature,'input_sha256':protected,'implementation_sha256':implementation_hash(),
        'code_sha256':{str(p.relative_to(PROJECT_ROOT)):sha(p) for p in code_files()},
        'dependencies':{n:version(n) for n in ('numpy','scipy','transformers','tokenizers','pydantic')},
        'document_budgets':ARMS,'context_policy':'global_whole_parent_greedy','window_audit':window_profile,
        'evaluation_versions':['evidence_v2','literal_v1'],'new_model_calls':0}
    signature['fingerprint']=digest(signature)
    if (output/'signature.json').exists():
        equal(artifacts.read_json(output/'signature.json'),signature,'resume signature; use a new directory')
    elif output.exists() and any(output.iterdir()):
        raise ValueError('Nonempty output without matching signature')
    output.mkdir(parents=True,exist_ok=True)
    artifacts.save_json(output/'signature.json',signature)
    if not (output/'code.zip').exists():
        with zipfile.ZipFile(output/'code.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for p in code_files()+sorted((PROJECT_ROOT/'tests').rglob('*.py')):
                archive.write(p,p.relative_to(PROJECT_ROOT))
    clock=RunClock(output/'timing.json')
    clock.session['pre_signature_preparation_seconds']=time.perf_counter()-started
    artifacts.save_json(output/'execution_status.json',{'status':'running','title':TITLE,'new_model_calls':0})
    try:
        cases={c.id:c for c in ref['cases']}
        aligner=SourceAligner(CORPUS,artifacts.read_json(rules_path))
        corpus=artifacts.source_corpus(ref['anchors'])
        def evaluate(case, pp):
            entries=[p.entry for p in pp]
            return {'evidence_v2':aligner.score(case,entries),
                    'literal_v1':anchor_coverage(case,{'evidence':entries},ref['anchors'],corpus)}
        prepared=[]
        validation={'status':'passed','rows':0,'snapshots':0,'historical_requests_reproduced':0}
        clock.set_phase('control_reproduction')
        for row in source_rows:
            states,_=reconstruct_states(row,operations,ref)
            selected=select_states(states,ref)
            case=cases[row['case_id']]
            links=verify_control(row,selected,lambda pp:evaluate(case,pp),ref['chunks'])
            prepared.append((row,selected,links))
            validation['rows']+=1; validation['snapshots']+=len(states)
        rows,trajectories,windows=[],[],[]
        clock.set_phase('budget_selection_and_evaluation')
        for row,states,links in prepared:
            case=cases[row['case_id']]
            previous={a:{} for a in ARMS}
            snapshots=[]
            for state in states:
                arms={}
                for arm in ARMS:
                    chosen=state['selected'][arm]
                    scores=state['control_evaluation'] if arm=='D3000' else evaluate(case,chosen)
                    hits=scores['evidence_v2']['selected_hits']
                    arms[arm]={'selected_parent_ids':[p.parent_id for p in chosen],
                        'context_tokens':sum(p.tokens for p in chosen),'packing_trace':state['traces'][arm],
                        'evaluations':scores,'change_since_previous_search':hits_change(previous[arm],hits)}
                    previous[arm]=hits
                snapshots.append({'query_id':state['query_id'],'candidate_ranking_digest':digest(state['ranking']),
                    'candidate_evaluation':state['candidate_evaluation'],'arms':arms})
            final=states[-1]
            minimum=minimum_parent_cover(case,final['parents'],aligner,budget=6000)
            if minimum['status'] not in ('feasible','over_budget','not_proven_in_candidates'):
                raise ValueError('Unresolved minimum-parent diagnostic')
            rows.append({'key':row['key'],'case_id':row['case_id'],'condition':row['condition'],'question':case.question,
                'search_count':len(states),'arms':{a:{**snapshots[-1]['arms'][a],
                    'evidence':[p.entry for p in final['selected'][a]]} for a in ARMS},
                'candidate_evaluation':final['candidate_evaluation'],'minimum_parent_cover':minimum})
            trajectories.append({'key':row['key'],'condition':row['condition'],'snapshots':snapshots,
                'historical_decision_state_links':links})
        clock.set_phase('local_window_audit')
        for row,states,links in prepared:
            case=cases[row['case_id']]
            state_by_id={s['query_id']:s for s in states}
            def check_state(state,ledger,remaining,expected=None):
                runs=[(DirectedSearch(**{k:s[k] for k in ('query_id','text','document_ids','field','origin','source_proof')}),
                       s['diagnostics']['stages']['reranker'],s['diagnostics']) for s in state['searches']]
                result={}
                for a in ARMS:
                    snapshot=Snapshot(state['ranking'],runs,state['parents'],state['selected'][a],state['traces'][a])
                    result[a]=audit_request(planner,measuring_planner,snapshot,case,ledger,row['scope'],remaining,
                                            expected=expected if a=='D3000' else None)
                return result
            for link,decision in zip(links,row['plan']['decisions']):
                request=decision.get('request')
                if request is None:
                    raise ValueError('Saved decision has no observation for window audit')
                payload=request['payload']
                ledger={'remaining_decisions':payload['remaining_decisions']}
                if 'tool_feedback' in payload:ledger['tool_feedback']=payload['tool_feedback']
                record={'key':row['key'],'condition':row['condition'],'kind':'historical_decision',
                    'decision_index':link['decision_index'],'arms':check_state(state_by_id[link['state_before']],
                        ledger,payload['remaining_searches'],expected=request)}
                windows.append(record);validation['historical_requests_reproduced']+=1
            windows.append({'key':row['key'],'condition':row['condition'],'kind':'final_sizing_only',
                'arms':check_state(states[-1],{'remaining_decisions':max(0,4-len(links))},4-len(states))})
        summary=summarize(rows,trajectories,windows)
        clock.set_phase('reporting_and_persistence')
        for filename,value in [('results.json',{'signature_fingerprint':signature['fingerprint'],'rows':rows}),
            ('trajectories.json',{'rows':trajectories}),('window_audit.json',{'profile':window_profile,'rows':windows}),
            ('comparison.json',summary),('reproduction.json',validation)]:
            artifacts.save_json(output/filename,value)
        report(output,summary,rows,validation)
        changed=[p for p,h in protected.items() if not Path(p).is_file() or sha(Path(p))!=h]
        if changed:raise ValueError('Historical inputs changed: '+', '.join(changed))
        artifacts.save_json(output/'preservation.json',{'status':'passed','files_verified':len(protected),'changed':[]})
        artifacts.save_json(output/'execution_status.json',{'status':'complete','title':TITLE,'original_questions':70,
            'question_scope_pairs':len(rows),'new_model_calls':0,'new_retrieval_calls':0,'new_reranker_calls':0,
            'recommendation':summary['recommendation']})
        clock.finish('complete')
        clock.data['total_measured_replay_seconds']=sum(s['active_seconds']+s.get('pre_signature_preparation_seconds',0) for s in clock.data['sessions'])
        artifacts.save_json(clock.path,clock.data)
        print(json.dumps({'title':TITLE,'recommendation':summary['recommendation'],
            'scopes':{s:{'quality':v['evidence_v2'],'window':v['window_audit']} for s,v in summary['scopes'].items()}},ensure_ascii=False,indent=2))
        return summary
    except BaseException as exc:
        artifacts.save_json(output/'execution_status.json',{'status':'incomplete','error':str(exc),'new_model_calls':0,
            'new_retrieval_calls':0,'recommendation':'blocked_do_not_interpret_as_complete'})
        clock.finish('incomplete')
        raise
