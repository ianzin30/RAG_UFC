"""Independent documentary checklist and explicit investigation/failure attribution."""
import argparse
import copy
from collections import Counter
from pathlib import Path
import numpy as np

from benchmark.core.artifacts import read_json, save_json
from benchmark.core.bootstrap import PROJECT_ROOT
from benchmark.core.reproducibility import CORPUS, sha
from benchmark.evaluation.comparison import paired
from benchmark.selection.run import metrics


def compare(before, after, selection_only=False):
    if before['signature'] != after['signature']:
        raise ValueError('Conditions have different experiment signatures')
    old = {r['key']: r for r in before['results']}; new = {r['key']: r for r in after['results']}
    if old.keys() != new.keys():
        raise ValueError('Conditions are incomplete or unpaired')
    if selection_only:
        for key in old:
            for field in ('planner_digest', 'shared_queries_digest', 'source_candidate_digest'):
                if old[key][field] != new[key][field]:
                    raise ValueError('Alternation changed shared searches/plans/scores: ' + key)
    return {scope: paired(before['results'], after['results'], scope) for scope in ('collection', 'oracle_scope')}


def preservation_replay():
    """Counterfactual of retaining A on old errors; never rewrite the historical run."""
    result = []
    for folder in ('cumbuco_directed_alternation_2026-10-08/run_02', 'cumbuco_context_16384_2026-10-08/run_01'):
        root = PROJECT_ROOT / 'benchmark/results/rounds' / folder
        baseline_path = root / 'A_baseline/retrieval.json'
        if not baseline_path.exists(): continue
        baseline = read_json(baseline_path); original = {r['key']: r for r in baseline['results']}
        for arm in ('B_directed', 'C_alternation'):
            path = root / arm / 'retrieval.json'
            if not path.exists(): continue
            data = read_json(path); changed = copy.deepcopy(data['results']); replaced = []
            for row in changed:
                if row['status'] == 'ok': continue
                row['evaluations'] = copy.deepcopy(original[row['key']]['evaluations'])
                replaced.append(row['key'])
            result.append({'historical_run': folder, 'arm': arm, 'historical_sha256': sha(path),
                           'original_metrics': metrics(data['results']), 'preserved_baseline_metrics': metrics(changed),
                           'replaced_error_contexts': replaced,
                           'interpretation': 'counterfactual replay on old errors, not a new execution or an adaptive-search gain'})
    return result


def report(root):
    from benchmark.search.run import CONDITIONS
    status = read_json(root / 'execution_status.json'); signature = read_json(root / 'signature.json')
    arms = signature.get('conditions', list(CONDITIONS)); complete = status['status'] == 'complete'
    loaded = {}
    for arm in arms:
        path = root / arm / 'retrieval.json'
        if path.exists(): loaded[arm] = read_json(path)
        elif not complete: loaded[arm] = {'signature': signature, 'results': []}
        else: raise ValueError('Completed execution is missing condition: ' + arm)
    contract_study = signature.get('study') == 'decision_contract'
    reason_study = signature.get('study') == 'reason_validation'
    interface_study = signature.get('study') == 'agent_interface'
    adaptive = interface_study or reason_study or contract_study or 'C_adaptive' in arms or 'B_single_shot' in arms
    pairs = ([('simple_vs_tolerant', 'B_tolerant', 'C_simple', False),
              ('feedback_vs_simple', 'C_simple', 'D_feedback', False),
              ('simple_vs_original', 'A_baseline', 'C_simple', False),
              ('feedback_vs_original', 'A_baseline', 'D_feedback', False)] if interface_study else
             [('tolerant_vs_strict', 'B_strict', 'C_tolerant', False),
              ('strict_vs_original', 'A_baseline', 'B_strict', False),
              ('tolerant_vs_original', 'A_baseline', 'C_tolerant', False)] if reason_study else
             [('simplified_contract', 'B_full_contract', 'C_minimal_contract', False),
              ('full_contract_vs_original', 'A_baseline', 'B_full_contract', False),
              ('minimal_contract_vs_original', 'A_baseline', 'C_minimal_contract', False)] if contract_study else
             [('single_shot_searches', 'A_baseline', 'B_single_shot', False),
              ('adaptive_cycle', 'B_single_shot', 'C_adaptive', False),
              ('adaptive_vs_original', 'A_baseline', 'C_adaptive', False)] if adaptive else
             [('directed_searches', 'A_baseline', 'B_directed', False),
              ('query_alternation', 'B_directed', 'C_alternation', True),
              ('combined', 'A_baseline', 'C_alternation', False)])
    pairs = [p for p in pairs if p[1] in loaded and p[2] in loaded]
    result = {'decision': 'pending_user_review', 'execution': status,
              'metrics': {a: metrics(d['results']) for a, d in loaded.items()}, 'comparisons': {},
              'costs': {}, 'documentary_support': [],
              'historical_preservation_replay': preservation_replay() if adaptive and not reason_study and not interface_study else []}
    if complete:
        for label, before, after, selection_only in pairs:
            result['comparisons'][label] = compare(loaded[before], loaded[after], selection_only)
    else:
        result['comparison_pending_reason'] = 'Complete all 140 observations in each requested condition'
    for arm, data in loaded.items():
        result['costs'][arm] = {}
        for scope in ('collection', 'oracle_scope'):
            rows = [r for r in data['results'] if r['condition'] == scope]
            def percentile(field, p):
                return float(np.percentile([r.get(field, 0) for r in rows], p)) if rows else None
            missing = []
            for row in rows:
                score = row['evaluations']['evidence_v2']
                for aid, found in score['selected_hits'].items():
                    if found: continue
                    stage = 'context_selection' if row['candidate_evaluation']['evidence_v2']['selected_hits'][aid] else 'not_proven_in_candidates'
                    missing.append({'key': row['key'], 'evidence_id': aid, 'stage': stage,
                                    'execution_error': row['status'] != 'ok', 'pending': aid in score['pending_anchors']})
            declared = [r for r in rows if r.get('declared_sufficient')]
            incomplete = [r for r in rows if r.get('stop_reason') == 'finish_incomplete']
            events = [e for r in rows for e in r.get('plan', {}).get('events', [])]
            def event_stats(values):
                return {'median': float(np.percentile(values, 50)), 'p95': float(np.percentile(values, 95))} if values else None
            result['costs'][arm][scope] = {
                'total_latency_median': percentile('latency_seconds', 50), 'total_latency_p95': percentile('latency_seconds', 95),
                'query_counts': dict(Counter(r['search_count'] for r in rows)),
                'reranker_pairs_logical': sum(r['reranker_pairs_logical'] for r in rows),
                'planning_calls': sum(r['planning_calls'] for r in rows),
                'planning_prompt_tokens': sum(r['planning_prompt_tokens'] for r in rows),
                'planning_completion_tokens': sum(r['planning_completion_tokens'] for r in rows),
                'planning_latency_seconds': event_stats([e['latency_seconds'] for e in events]),
                'server_seconds': {key: event_stats([e['server_timings'][key]/1e9 for e in events
                    if (e.get('server_timings') or {}).get(key) is not None]) for key in
                    ('load_duration', 'prompt_eval_duration', 'eval_duration')},
                'decision_failure_types': dict(Counter('output_exhausted' if e.get('output_at_limit') else
                    'schema_validation' if e.get('validation_error') else 'decision_validation' if e.get('decision_validation_error')
                    else 'transport_or_generation' for e in events if e.get('status') == 'error'
                    or e.get('validation_error') or e.get('decision_validation_error'))),
                'missing_by_stage': dict(Counter(m['stage'] for m in missing)), 'missing_evidence': missing,
                'stop_reasons': dict(Counter(r.get('stop_reason', 'legacy') for r in rows)),
                'execution_errors': [{'key': r['key'], 'error': r.get('error'),
                                      'preserved_context': r.get('plan', {}).get('preserved_context_on_error', False)} for r in rows if r['status'] != 'ok'],
                'sufficiency_claims': len(declared),
                'locally_rejected_sufficiency': [{'key': r['key'], 'error': e.get('decision_validation_error')}
                    for r in rows for e in r.get('plan', {}).get('events', [])
                    if e.get('rejected_decision', {}).get('action') == 'finish_sufficient'],
                'false_sufficiency': [r['key'] for r in declared if not r['evaluations']['evidence_v2']['complete_selected_anchors']],
                'incomplete_stop_with_complete_context': [r['key'] for r in incomplete if r['evaluations']['evidence_v2']['complete_selected_anchors']],
                'incomplete_stop_with_complete_candidates': [r['key'] for r in incomplete if r['candidate_evaluation']['evidence_v2']['complete_selected_anchors'] and not r['evaluations']['evidence_v2']['complete_selected_anchors']],
                'shared_cost_notice': ('A/B are historical; C/D share exact requests and operations. Unique physical costs are counted once in interface_audit.' if interface_study else
                    'B is historical; C explicitly imports exact requests and performs only new work. Physical totals are separate.' if reason_study else
                    'B/C have separate decisions and trajectories; retrieval caches may be shared. Physical work is in execution_status.' if adaptive else 'B and C share all planning and retrieval work; do not sum calls'),
                'latency_notice': ('A/B are historical; C/D wall times depend on shared cache hits and are not independent model-speed measurements.' if interface_study else
                    'A/B values are historical; C is current physical case wall time, including local replay. Do not compare these as model speed.' if reason_study else
                    'historical original plus measured decision/query/rerank/selection durations; cache replays retain original cost, not isolated live latency')}
    rules_path = root / 'evaluation_rules.json'
    if rules_path.exists() and complete:
        rules = read_json(rules_path)['anchors']
        for label, _, _, _ in pairs:
            for scope, comparison in result['comparisons'][label].items():
                for change in comparison['evidence_changes']:
                    for aid in change['gained']:
                        rule = rules[aid]; source = (CORPUS / rule['document']).read_text()
                        result['documentary_support'].append({'intervention': label, 'case_id': change['case_id'],
                            'scope': scope, 'evidence_id': aid, 'document': rule['document'],
                            'source_sha256': rule['source_sha256'], 'requirements': [{**r, 'source_excerpt': source[r['source_start']:r['source_end']]}
                                for r in rule['requirements']]})
    save_json(root / 'comparison.json', result)
    model = signature.get('llm', {}).get('model', 'modelo registrado na assinatura')
    lines = [f'# Interface documental simples e feedback — {model}, sem reasoning' if interface_study else
             f'# Tolerância da justificativa — {model}, sem reasoning' if reason_study else
             f'# Decision-contract comparison — {model} via {signature.get("llm", {}).get("provider", "recorded provider")}' if contract_study else
             f'# Recuperação adaptativa com {model} via {signature.get("llm", {}).get("provider", "recorded provider")}' if adaptive else '# Cumbuco-directed searches and alternation', '',
             '**Decisão: pendente da sua revisão.**', '',
             '70 perguntas originais, dois escopos. Nenhuma resposta final gerada.', '',
             '| Condição | Coleção completas / avaliadas | Escopo restrito completas / avaliadas | Erros |', '|---|---:|---:|---:|']
    for arm, values in result['metrics'].items():
        a, b = (values['evidence_v2'][s] for s in ('collection', 'oracle_scope'))
        coll = f"{a['complete']}/{a['total']}" if a['total'] else 'Not executed'
        scoped = f"{b['complete']}/{b['total']}" if b['total'] else 'Not executed'
        lines.append(f"| {arm} | {coll} | {scoped} | {a['errors'] + b['errors']} |")
    for scope in ('collection', 'oracle_scope'):
        categories = sorted({c for values in result['metrics'].values() for c in values['evidence_v2'][scope]['categories']})
        lines += ['', '## Categorias — ' + scope, '', '| Categoria | ' + ' | '.join(arms) + ' |', '|---|' + '---:|' * len(arms)]
        for category in categories:
            values = [result['metrics'][a]['evidence_v2'][scope]['categories'].get(category, {}) for a in arms]
            lines.append('| ' + category + ' | ' + ' | '.join(f"{v.get('complete', 0)}/{v.get('total', 0)}" for v in values) + ' |')
    if not reason_study and not interface_study:
        lines += ['', '## Custos e encerramentos', '',
              '| Condição / escopo | Mediana (s) | p95 (s) | Chamadas | Buscas | Pares reranker |', '|---|---:|---:|---:|---|---:|']
        for arm, scopes in result['costs'].items():
            for scope, cost in scopes.items():
                lines.append(f"| {arm}/{scope} | {cost['total_latency_median']} | {cost['total_latency_p95']} | {cost['planning_calls']} | {cost['query_counts']} | {cost['reranker_pairs_logical']} |")
    lines += (['', 'A/B são históricos; C/D compartilham operações idênticas. A latência de um replay não representa velocidade do modelo. Custos físicos únicos estão em interface_audit e timing.json.', ''] if interface_study else
              ['', 'Nesta rodada B é histórico e C mistura replay com trabalho novo. As latências desta tabela não são comparáveis como tempo físico; veja a seção de custo físico e timing.json.', ''] if reason_study else
              ['', 'Latências incluem o custo histórico da busca original e o custo registrado das operações, inclusive replays de cache.',
               'Chamadas de B e C são independentes nesta rodada; buscas idênticas podem compartilhar cache. Custos físicos estão em execution_status.json.', ''])
    for label, scopes in result['comparisons'].items():
        lines += ['', '## ' + label, '']
        for scope, comparison in scopes.items():
            lines += [f"- {scope}: {len(comparison['complete_gains'])} ganhos, {len(comparison['complete_losses'])} regressões; cobertura parcial {comparison['before_partial']:.2%} → {comparison['after_partial']:.2%}.",
                      f"  Ganhos: {comparison['complete_gains']}. Regressões: {comparison['complete_losses']}.",
                      f"  Concentração dos ganhos por evidência: {comparison['gain_concentration']}."]
    if adaptive:
        lines += ['', '## Auditoria do encerramento', '']
        for arm in arms[1:]:
            for scope, cost in result['costs'][arm].items():
                lines += [f"- {arm}/{scope}: motivos {cost['stop_reasons']}.",
                          f"  Suficiência declarada incorretamente: {cost['false_sufficiency']}.",
                          f"  Encerramento incompleto apesar de contexto completo: {cost['incomplete_stop_with_complete_context']}.",
                          f"  Encerramento incompleto com candidatos completos e contexto incompleto: {cost['incomplete_stop_with_complete_candidates']}."]
        if not reason_study and not interface_study:
            lines += ['', '## Proteção contra perda de contexto — replay histórico', '',
                  'Este diagnóstico substitui contextos vazios de falhas antigas pelo contexto A já salvo. Não representa uma nova execução nem ganho do ciclo.']
        for replay in result['historical_preservation_replay']:
            for scope in ('collection', 'oracle_scope'):
                old = replay['original_metrics']['evidence_v2'][scope]; new = replay['preserved_baseline_metrics']['evidence_v2'][scope]
                lines.append(f"- {replay['historical_run']}/{replay['arm']}/{scope}: {old['complete']}/{old['total']} → {new['complete']}/{new['total']} apenas pela preservação.")
    lines += ['', '## Checklist de revisão', '',
              '- [ ] Conferir configurações comuns e completude da execução.',
              '- [ ] Examinar a interface C contra B e o feedback D contra C, separadamente.' if interface_study else
              '- [ ] Examinar a tolerância local da justificativa, C contra B.' if reason_study else
              '- [ ] Examinar o efeito do contrato simplificado, C contra B.' if contract_study else '- [ ] Examinar o efeito do ciclo adaptativo, C contra B.',
              '- [ ] Examinar ambas as intervenções contra a busca original A.',
              '- [ ] Auditar ganhos/regressões, fontes e concentração em fatos repetidos.',
              '- [ ] Conferir suficiência declarada, paradas prematuras e falhas operacionais.',
              '- [ ] Comparar custos adicionais com os ganhos documentais.',
              '- [ ] Decidir sobre uma futura integração à aplicação.', '',
              'comparison.json contém métricas por categoria, mudanças por evidência, posições no Markdown e custos.',
              'A validade literal da citação não garante a interpretação da relação. O avaliador documental é independente.',
              'A rodada mede um mecanismo genérico nas perguntas originais; não comprova transferência para novos domínios.', '']
    if contract_study:
        lines += ['', '## Interpretation and recommendation', '',
            'C removes the mandatory evidence ledger. Its sufficiency declaration is unverified; easier protocol acceptance alone is not a retrieval gain.',
            'One seeded run on the original questions does not characterize stochastic variation or transfer to unseen domains. Thinking and JSON share 4096 generated tokens.']
        result['recommendation'] = 'review_incomplete' if not complete else 'review_documentary_gains_and_costs'
        result['adaptive_examples'] = [{'arm': arm, 'key': r['key'], 'queries': [q['text'] for q in r['diagnostics']['searches']],
            'observations': r.get('plan', {}).get('observations', []), 'complete': r['evaluations']['evidence_v2']['complete_selected_anchors']}
            for arm, data in loaded.items() for r in data['results'] if r.get('search_count', 0) > 1]
        save_json(root / 'comparison.json', result)
    if not complete: lines += ['**Execução incompleta. Comparações pareadas não publicadas.**', '']
    (root / 'report.md').write_text('\n'.join(lines))
    return result


def agent_interface_report(root, result):
    """Operational incidents, unique physical costs and inspectable trajectories."""
    import html
    import json
    from datetime import datetime
    from zoneinfo import ZoneInfo
    arms = result['execution']['conditions']
    loaded = {arm: read_json(root / arm / 'retrieval.json')['results'] if (root / arm / 'retrieval.json').exists() else [] for arm in arms}
    cache = read_json(root / 'cache.json') if (root / 'cache.json').exists() else {'decisions': {}, 'queries': {}, 'global': {}}
    def stats(values):
        return {'attempts': len(values), 'median_seconds': float(np.median(values)) if values else None,
                'p95_seconds': float(np.percentile(values, 95)) if values else None, 'sum_seconds': float(sum(values))}
    physical = [e for value in cache['decisions'].values() for e in value.get('events', [])]
    audit = {'physical_decisions': len(physical), 'physical_decision_latency': stats([e['latency_seconds'] for e in physical]),
        'physical_prompt_tokens': sum((e.get('usage') or {}).get('prompt_tokens', 0) for e in physical),
        'physical_completion_tokens': sum((e.get('usage') or {}).get('completion_tokens', 0) for e in physical),
        'unknown_decisions': sum(bool(v.get('planning_calls_unknown')) for v in cache['decisions'].values()),
        'output_exhaustions': sum(bool(e.get('output_at_limit')) for e in physical),
        'input_limit_failures': sum(any(d.get('error', {}).get('code') == 'INPUT_BUDGET' for d in r.get('plan', {}).get('decisions', []))
                                  for arm in ('C_simple', 'D_feedback') for r in loaded.get(arm, [])),
        'operations': {}, 'conditions': {}, 'sharing_checks': [], 'decision': 'pending_user_review'}
    for group in ('queries', 'global'):
        values = [v for v in cache[group].values() if v.get('operation_origin') == 'live']
        audit['operations'][group] = {'physical_attempts': len(values), 'latency': stats([v.get('latency_seconds', 0.) for v in values]),
            'reranker_pairs': sum(v.get('physical_reranker_pairs', 0) for v in values),
            'historical_operations': sum(v.get('operation_origin') == 'historical' for v in cache[group].values()),
            'unknown_outcomes': sum(bool(v.get('usage_unknown')) for v in values)}
    for arm, rows in loaded.items():
        audit['conditions'][arm] = {}
        for scope in ('collection', 'oracle_scope'):
            rr = [r for r in rows if r['condition'] == scope]
            incidents = [i for r in rr for i in r.get('plan', {}).get('incidents', [])]
            confirmed, pending = [], []
            for r in rr:
                if r.get('declared_sufficient') and not r['evaluations']['evidence_v2']['complete_selected_anchors']:
                    (pending if r['evaluations']['evidence_v2']['pending_anchors'] else confirmed).append(r['case_id'])
            useful = []
            for row in rr:
                old = next((r for r in loaded['A_baseline'] if r['key'] == row['key']), None)
                if old is None: continue
                before_context = old['evaluations']['evidence_v2']['selected_hits']
                before_candidates = old['candidate_evaluation']['evidence_v2']['selected_hits']
                for step in row.get('plan', {}).get('steps', []):
                    after_context = step['context_evaluation']['evidence_v2']['selected_hits']
                    after_candidates = step['candidate_evaluation']['evidence_v2']['selected_hits']
                    if step.get('effective_query'):
                        useful.append({'case_id': row['case_id'], 'decision_index': step['decision_index'],
                            'query': step['effective_query']['text'],
                            'candidate_gains': [k for k, v in after_candidates.items() if v and not before_candidates.get(k)],
                            'context_gains': [k for k, v in after_context.items() if v and not before_context.get(k)],
                            'context_losses': [k for k, v in before_context.items() if v and not after_context.get(k)]})
                    before_context, before_candidates = after_context, after_candidates
            audit['conditions'][arm][scope] = {
                'evaluated': len(rr), 'complete': sum(r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rr),
                'without_terminal_error': sum(r['status'] == 'ok' for r in rr),
                'without_incident': sum(r.get('without_incident', r['status'] == 'ok') for r in rr),
                'complete_without_terminal_error': sum(r['status'] == 'ok' and r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rr),
                'incidents': dict(Counter(i['code'] for i in incidents)), 'recovered_incidents': sum(i['recovered'] for i in incidents),
                'cases_with_recovered_incidents': [r['case_id'] for r in rr if r.get('recovered_incidents', 0)],
                'terminal_errors': [{'case_id': r['case_id'], 'error': r.get('error')} for r in rr if r['status'] != 'ok'],
                'false_sufficiency_confirmed': confirmed, 'sufficiency_pending_alignment': pending,
                'logical_decision_latency': stats([e.get('logical_latency_seconds', e.get('latency_seconds', 0.))
                    for r in rr for e in r.get('plan', {}).get('events', [])]),
                'physical_case_latency': stats([r.get('physical_latency_seconds', 0.) for r in rr]) if arm in ('C_simple', 'D_feedback') else None,
                'search_effects': useful}
    simple = {r['key']: r for r in loaded.get('C_simple', [])}
    for r in loaded.get('D_feedback', []):
        if r['key'] not in simple: continue
        left, right = simple[r['key']]['plan']['decisions'], r['plan']['decisions']
        checks = [{'decision_index': i+1, 'same_request': left[i].get('request') == right[i].get('request'),
                   'same_raw_response': [e.get('raw_response') for e in left[i].get('events', [])] ==
                                        [e.get('raw_response') for e in right[i].get('events', [])]}
                  for i in range(min(len(left), len(right)))]
        if not all(c['same_request'] and c['same_raw_response'] for c in checks):
            raise ValueError('C/D changed a shared pre-error trajectory: ' + r['key'])
        audit['sharing_checks'].append({'key': r['key'], 'checks': checks, 'passed': True})
    result['interface_audit'] = audit
    result['timing'] = read_json(root / 'timing.json')
    result['recommendations'] = {'document_search_v1': {'recommendation': 'pending_critical_review' if result['execution']['status'] == 'complete' else 'revise_incomplete', 'approval': 'pending_user_review'},
                                 'bounded_feedback_v1': {'recommendation': 'pending_critical_review' if result['execution']['status'] == 'complete' else 'revise_incomplete', 'approval': 'pending_user_review'}}
    save_json(root / 'comparison.json', result)
    lines = ['', '## Incidentes não são erros factuais', '',
        'Cada escopo contém as mesmas 70 perguntas. A/B são históricos; C/D compartilham pedidos idênticos até a primeira rejeição em C.',
        'Sem falha terminal permite incidentes corrigidos. Sem incidente exige que nenhum tenha ocorrido. O julgamento de suficiência continua sem verificador semântico novo.', '']
    for scope in ('collection', 'oracle_scope'):
        lines += ['### ' + scope, '', '| Condição | Evidência completa | Sem falha terminal | Sem incidente | Completa e sem falha |', '|---|---:|---:|---:|---:|']
        for arm in arms:
            x = audit['conditions'][arm][scope]; n = x['evaluated']
            lines.append(f"| {arm} | {x['complete']}/{n} | {x['without_terminal_error']}/{n} | {x['without_incident']}/{n} | {x['complete_without_terminal_error']}/{n} |")
        for arm in ('C_simple', 'D_feedback'):
            x = audit['conditions'][arm][scope]
            lines += ['', f"{arm}: incidentes {x['incidents']}; recuperados: {x['recovered_incidents']}.",
                      f"Falsas suficiências confirmadas: {x['false_sufficiency_confirmed']}; pendências documentais: {x['sufficiency_pending_alignment']}."]
    timing = result['timing']
    local_start = datetime.fromisoformat(timing['started_at']).astimezone(ZoneInfo('America/Fortaleza'))
    lines += ['', '## Custos físicos únicos', '', f"Início: {local_start.isoformat()} (Fortaleza).",
        'A duração final, sessões e fases estão em timing.json; o valor registrado antes da escrita deste relatório é parcial.',
        f"Chamadas físicas de qualidade: {audit['physical_decisions']}; estatísticas incluindo falhas: {audit['physical_decision_latency']}.",
        f"Tokens físicos de entrada/saída: {audit['physical_prompt_tokens']}/{audit['physical_completion_tokens']}.",
        f"Operações físicas e históricas: {audit['operations']}.",
        f"Saídas esgotadas: {audit['output_exhaustions']}; falhas de entrada: {audit['input_limit_failures']}; chamadas de resultado desconhecido: {audit['unknown_decisions']}.",
        'As duas chamadas sintéticas são separadas das chamadas de qualidade. Replays não demonstram aceleração do modelo.', '',
        '## Decisão por intervenção', '',
        'A recomendação exige examinar completude, regressões por evidência, falsas suficiências e custo. Aprovação pendente do usuário; aplicação não promovida.',
        'Enquanto incompleto, nenhum ganho de qualidade é definitivo. report.html permite inspecionar cada trajetória disponível.']
    with (root / 'report.md').open('a') as file: file.write('\n'.join(lines) + '\n')
    _render_agent_interface(root, result, loaded)
    return result


def _render_agent_interface(root, result, loaded):
    """One figure-driven page with all per-question trajectories; no extra runner."""
    import html
    import json
    labels = {'A_baseline': 'A · Busca original', 'B_tolerant': 'B · Agente tolerante anterior',
              'C_simple': 'C · Busca simples', 'D_feedback': 'D · Busca simples + feedback'}
    status = result['execution']
    finished = status['status'] == 'complete'
    audit = result['interface_audit']
    blocks = []
    for scope, title in [('collection', 'Coleção inteira'), ('oracle_scope', 'Documentos corretos fornecidos')]:
        bars = []
        for arm, label in labels.items():
            m = audit['conditions'][arm][scope]; n = m['evaluated']
            measures = [('complete', 'Evidência completa'), ('without_terminal_error', 'Sem falha terminal'), ('without_incident', 'Sem incidente')]
            drawings = ''.join(f'<div class="measure"><span>{name}</span><meter min="0" max="70" value="{m[key]}"></meter><b>{m[key]}/{n}</b></div>' for key, name in measures) if n else '<p>Não executado.</p>'
            bars.append(f'<div class="series"><h3>{label}</h3>{drawings}</div>')
        blocks.append(f'<figure><h2>{title}</h2><div class="grid">{"".join(bars)}</div><figcaption>Fig. {len(blocks)+1} — Evidência completa, falha terminal e incidente medem coisas diferentes. Barras usam escala de 70 perguntas; o denominador mostra quantas foram avaliadas.</figcaption></figure>')
    options = ''.join(f'<option value="{arm}">{html.escape(label)}</option>' for arm, label in labels.items())
    ids = list(dict.fromkeys(r['case_id'] for r in loaded['A_baseline']))
    questions = ''.join(f'<option value="{html.escape(i)}">{html.escape(i)}</option>' for i in ids)
    failures = ''
    for arm in ('C_simple', 'D_feedback'):
        for scope in ('collection', 'oracle_scope'):
            m = audit['conditions'][arm][scope]
            failures += f'<tr><td>{html.escape(labels[arm])} / {scope}</td><td>{html.escape(str(m["incidents"]))}</td><td>{m["recovered_incidents"]}</td><td>{html.escape(str(m["false_sufficiency_confirmed"]))}</td><td>{html.escape(str(m["sufficiency_pending_alignment"]))}</td></tr>'
    # Keep only human-inspection data; original responses remain in signed artifacts.
    parent_details = {}
    for rows in loaded.values():
        for r in rows:
            entries = list(r.get('evidence', []))
            for d in r.get('plan', {}).get('decisions', []):
                entries.extend((d.get('request') or {}).get('payload', {}).get('selected_context', []))
            for entry in entries:
                if entry.get('parent_id') and entry.get('text'):
                    parent_details[entry['parent_id']] = {k: entry.get(k) for k in ('text', 'document_name', 'document_id', 'relative_path')}
    data = {arm: [{k: r.get(k) for k in ('case_id', 'condition', 'query', 'status', 'error', 'stop_reason', 'evaluations', 'candidate_evaluation', 'diagnostics', 'plan')} | {'final_parent_ids': [e['parent_id'] for e in r.get('evidence', [])]} for r in rows] for arm, rows in loaded.items()}
    for rows in data.values():
        for r in rows:
            r['diagnostics'] = {'searches': [{k: q.get(k) for k in ('query_id', 'text', 'document_ids')} for q in r['diagnostics']['searches']]}
            r['plan'] = {k: r['plan'].get(k) for k in ('steps', 'decisions', 'incidents')} if r['plan'] else {}
            r['plan']['decisions'] = [{'status': d.get('status'), 'decision': d.get('decision'), 'error': d.get('error'),
                                      'issues': d.get('issues')} for d in r['plan'].get('decisions') or []]
    data['__parents'] = parent_details
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    timing = result['timing']
    message = 'Rodada concluída; aprovação pendente.' if finished else 'Rodada incompleta: resultados novos ainda não permitem conclusão.'
    blocker = status.get('blocker') or status.get('stop_reason') or ''
    page = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Busca simples e feedback · Qwen3.6</title><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M4 8h12v8H4zm12 8h12v8H16z' fill='%23955700'/%3E%3C/svg%3E">
<style>@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;600&family=Geist+Mono:wght@400;600&display=swap');
:root{color-scheme:light dark;--bg:#f4f5f3;--surface:#fff;--border:#dfe3e0;--border-bright:#888e8b;--text:#121614;--text-dim:#545e59;--accent:#955700;--ok:#1c7443;--risk:#b0341e;--s-1:.25rem;--s-2:.5rem;--s-3:.75rem;--s-4:1rem;--s-5:1.5rem;--s-6:2rem;--s-7:3rem;--s-8:4.5rem;--r-1:4px;--r-2:10px}
@media(prefers-color-scheme:dark){:root{--bg:#0b0d0c;--surface:#121614;--border:#1f2522;--border-bright:#5e6662;--text:#e6ebe8;--text-dim:#919d97;--accent:#f2a93b;--ok:#6fcf97;--risk:#ef6f5c}}
*{box-sizing:border-box}html{font-size:17px}body{margin:0;background:var(--bg);color:var(--text);font:1rem/1.6 Geist,'Helvetica Neue',sans-serif}main{max-width:64rem;margin:auto;padding:var(--s-6) var(--s-5)}h1{font-size:clamp(2.25rem,5.5vw,4rem);line-height:1.1;letter-spacing:-.04em;font-weight:600;max-width:22ch}h2{font-size:1.625rem;line-height:1.2;letter-spacing:-.01em}h3{font-size:1rem}p{max-width:68ch}a{color:var(--accent)}figure{margin:var(--s-8) 0}figcaption{margin-top:var(--s-3);color:var(--text-dim)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(14.5rem,1fr));gap:var(--s-5)}.grid>*{min-width:0}.series{border-top:1px solid var(--border-bright);padding-top:var(--s-3)}.measure{display:grid;grid-template-columns:minmax(0,1fr) 4rem;gap:var(--s-2);padding:var(--s-2) 0}.measure span{grid-column:1/-1;color:var(--text-dim)}meter{width:100%;height:1rem;accent-color:var(--accent)}b{font-variant-numeric:tabular-nums}.controls{display:flex;flex-wrap:wrap;gap:var(--s-3)}label{display:grid;gap:var(--s-2);font-size:.875rem}select,button{font:inherit;background:var(--surface);color:var(--text);border:1px solid var(--border-bright);border-radius:var(--r-1);padding:var(--s-2);max-width:100%}:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.frame{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-2);padding:var(--s-5)}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:var(--s-3);border-bottom:1px solid var(--border);vertical-align:top;overflow-wrap:anywhere}th{font-family:'Geist Mono',monospace;font-size:.75rem}.step{padding:var(--s-5) 0;border-top:1px solid var(--border-bright)}.step h3{margin:0}.tag{font:.75rem 'Geist Mono',monospace;color:var(--text-dim)}.chain{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:var(--s-5)}.chain>div{min-width:0}.chain span{display:block;color:var(--text-dim);font-size:.875rem}.risk{color:var(--risk)}.status{font: .875rem 'Geist Mono',monospace;border:1px solid var(--border-bright);padding:var(--s-4)}pre{font:.875rem/1.6 'Geist Mono',monospace;white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}.path{overflow-wrap:anywhere}.cost{font-size:1.25rem;max-width:68ch}@media print{body{background:white;color:black}.controls{display:none}figure,.step{break-inside:avoid}}</style></head><body><main>
<p class="tag">Qwen3.6 · Sem reasoning · Mesmas 70 perguntas</p><h1>A busca ficou mais simples. O agente consegue continuar?</h1>
<p class="status">__MESSAGE__ <span class="risk">__BLOCKER__</span></p>
<p>C contra B mede a interface documental. D contra C mede o feedback. O agente continua limitado a quatro decisões e quatro buscas, incluindo a original.</p>
__FIGURES__
<figure><h2>Acompanhe uma pergunta, etapa por etapa</h2><div class="controls"><label>Escopo<select id="scope"><option value="collection">Coleção inteira</option><option value="oracle_scope">Documentos corretos fornecidos</option></select></label><label>Condição<select id="arm">__OPTIONS__</select></label><label>Pergunta<select id="question">__QUESTIONS__</select></label></div><div id="trajectory" class="frame" aria-live="polite"></div><figcaption>Fig. 3 — Pedido → ação efetiva → evidência no contexto → continuação ou encerramento. Justificativas do modelo são interpretações, não evidências.</figcaption></figure>
<figure><h2>Corrigir um incidente não comprova suficiência</h2><div class="scroll frame"><table><thead><tr><th>Condição / escopo</th><th>Incidentes por código</th><th>Recuperados</th><th>Falsas suficiências</th><th>Pendências documentais</th></tr></thead><tbody>__FAILURES__</tbody></table></div><figcaption>Fig. 4 — Incidentes, falhas terminais e julgamentos incorretos permanecem separados. C09 não recebe crédito automático.</figcaption></figure>
<figure><h2>O tempo físico conta cada operação uma vez</h2><div class="frame"><p class="cost">__COST__</p><p>Chamadas físicas de qualidade: __CALLS__. Replays compartilhados não são novas chamadas nem demonstram aceleração do modelo.</p><p>Entrada e saída físicas: __TOKENS__. Chamadas sintéticas e preparação ficam separadas em timing.json e preflight.json.</p><meter min="0" max="__CALLS_MAX__" value="__CALLS__"></meter><details><summary>Tempos e sessões registrados</summary><pre>__TIMING__</pre></details></div><figcaption>Fig. 5 — Duração física inclui preparação, reprodução e relatório. As latências históricas de A/B não medem a duração desta rodada.</figcaption></figure>
<p>Fontes: <a href="report.md">relatório completo</a> · <a href="comparison.json">comparação estruturada</a> · <a href="control_reproduction.json">reprodução dos controles</a>. Aprovação de cada intervenção pendente da revisão do usuário.</p>
<script type="application/json" id="data">__DATA__</script><script>
const rows=JSON.parse(document.getElementById('data').textContent);const $=id=>document.getElementById(id);
function el(tag,text,parent,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;if(parent)parent.appendChild(node);return node}
function detail(title,value,parent){const d=el('details',undefined,parent);el('summary',title,d);el('pre',JSON.stringify(value,null,2),d)}
function showParents(ids,host){const d=el('details',undefined,host);el('summary','Ler os trechos originais selecionados',d);for(const id of ids||[]){const p=rows.__parents[id];if(p){el('h3',p.document_name||p.relative_path||p.document_id,d);el('p',id,d,'tag');el('pre',p.text,d)}}}
function render(){const host=$('trajectory');host.replaceChildren();const r=(rows[$('arm').value]||[]).find(x=>x.case_id===$('question').value&&x.condition===$('scope').value);if(!r){el('p','Esta condição ainda não foi executada para a pergunta.',host);return}el('h3',r.query,host);const ev=r.evaluations.evidence_v2;el('p',(ev.complete_selected_anchors?'● Evidência completa':'▲ Evidência incompleta')+' · '+(r.status==='ok'?'Sem falha terminal':'Falha terminal')+' · Encerramento: '+r.stop_reason,host);detail('Evidências avaliadas e pendências',ev,host);showParents(r.final_parent_ids,host);const steps=r.plan.steps||[];if(!steps.length){el('p','Referência histórica: buscas e decisões preservadas abaixo.',host);detail('Buscas executadas',r.diagnostics.searches,host);detail('Decisões históricas',r.plan.decisions,host);return}for(const s of steps){const box=el('div',undefined,host,'step');el('p','Decisão '+s.decision_index+' · Restam '+s.remaining_decisions+' decisões e '+s.remaining_searches+' buscas',box,'tag');const chain=el('div',undefined,box,'chain');for(const [name,value] of [['Pedido',s.requested_action||'Saída inválida'],['Execução',s.action_executed?'Executada':'Não executada'],['Contexto',s.context_evaluation.evidence_v2.complete_selected_anchors?'Evidência completa':'Evidência incompleta'],['Continuação',s.continuation]]){const d=el('div',undefined,chain);el('span',name,d);el('b',value,d)}if(s.error)el('p',s.error.code+' · '+s.error.message,box,'risk');if(s.feedback_received)detail('Feedback recebido',s.feedback_received,box);detail('Busca solicitada / executada',{requested:s.requested_queries,effective:s.effective_query||null},box);detail('Trechos observados, selecionados e descartados',{observed:s.observed_parent_ids,samples:s.sample_chunk_ids,selected:s.selected_parent_ids,added:s.context_added,removed:s.context_removed,discarded:s.discarded_parents},box);detail('Evidência por etapa',{context:s.context_evaluation.evidence_v2,candidates:s.candidate_evaluation.evidence_v2},box);showParents(s.selected_parent_ids,box)}}
for(const id of ['scope','arm','question'])$(id).addEventListener('change',render);$('arm').value='D_feedback';render();
</script></main></body></html>'''
    replacements = {'MESSAGE': html.escape(message), 'BLOCKER': html.escape(str(blocker)), 'FIGURES': ''.join(blocks),
        'OPTIONS': options, 'QUESTIONS': questions, 'FAILURES': failures, 'DATA': payload,
        'COST': f"Tempo ativo registrado: {timing['active_wall_seconds']/60:.2f} min; consulte timing.json para a duração final.",
        'CALLS': str(audit['physical_decisions']), 'CALLS_MAX': str(max(1, audit['physical_decisions'])),
        'TOKENS': f"{audit['physical_prompt_tokens']} / {audit['physical_completion_tokens']} tokens",
        'TIMING': html.escape(json.dumps(timing, ensure_ascii=False, indent=2))}
    for key, value in replacements.items(): page = page.replace('__' + key + '__', value)
    (root / 'report.html').write_text(page, encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, required=True)
    report(p.parse_args().root)


if __name__ == '__main__': main()
