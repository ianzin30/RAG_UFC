"""Offline comparison of saved global order and chronological local alternation.

Historical decisions are fixed observations, never decisions attributed to L.
Selection receives no benchmark annotations. No provider/retriever is constructed.
"""
from contextlib import contextmanager
from importlib.metadata import version
import json
from pathlib import Path
import platform
import time
from unittest.mock import patch
import zipfile

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.reproducibility import CORPUS, code_files, implementation_hash, sha
from benchmark.core.timing import RunClock
from benchmark.selection.run import digest

VERSION = 'global_order_replay_v1'
SCOPES = ('collection', 'oracle_scope')
ARMS = ('G_global', 'L_local')
SEARCH_FIELDS = ('query_id', 'text', 'document_ids', 'field', 'origin', 'source_proof')


def equal(actual, expected, label):
    # JSON round-trips source spans from tuples to lists.
    if digest(actual) != digest(expected):
        raise ValueError('Historical reproduction differs: ' + label)


@contextmanager
def offline_only():
    """Fail closed even if a future refactor accidentally introduces transport."""
    with patch('socket.socket.connect', side_effect=RuntimeError('Offline replay forbids network access')), \
         patch('socket.socket.connect_ex', side_effect=RuntimeError('Offline replay forbids network access')), \
         patch('socket.getaddrinfo', side_effect=RuntimeError('Offline replay forbids network access')):
        yield


def tree_hashes(directory):
    return {str(p.resolve()): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def checked_operation(operations, kind, key):
    value = operations[kind].get(key)
    if value is None or value.get('status') != 'ok' or value.get('planning_calls_unknown'):
        raise ValueError(f'Missing, failed or unknown historical operation: {kind}/{key}')
    return value


def load_history(source):
    """Validate the signed ancestor chain, then merge known retrieval operations."""
    visited, caches, protected = set(), [], {}

    def visit(directory):
        directory = directory.resolve()
        if directory in visited:
            return
        visited.add(directory)
        signature_path = directory / 'signature.json'
        signature = artifacts.read_json(signature_path)
        if 'fingerprint' in signature:
            equal(signature['fingerprint'], digest({k: v for k, v in signature.items() if k != 'fingerprint'}),
                  str(signature_path) + ': fingerprint')
        protected.update(tree_hashes(directory))
        hashes = signature.get('source_hashes', {})
        ancestors = set()
        for name, expected in hashes.items():
            path = Path(name)
            if not path.is_absolute():
                if not signature.get('source_run'):
                    raise ValueError('Relative ancestor without source_run: ' + name)
                path = Path(signature['source_run']) / path
            if sha(path) != expected:
                raise ValueError('Historical ancestor changed: ' + str(path))
            if path.name == 'signature.json':
                ancestors.add(path.parent)
        for ancestor in sorted(ancestors):
            visit(ancestor)
        cache = artifacts.read_json(directory / 'cache.json')
        equal(cache['signature'], signature, str(directory) + ': cache signature')
        caches.append(cache)

    visit(source)
    signature = artifacts.read_json(source / 'signature.json')
    status = artifacts.read_json(source / 'execution_status.json')
    if signature.get('study') != 'agent_interface' or status.get('status') != 'complete':
        raise ValueError('A completed agent_interface source is required')
    if status.get('planning_usage_unknown') or status.get('answer_generation_calls') != 0:
        raise ValueError('Unknown source usage or unexpected answer generation')
    operations = {'queries': {}, 'global': {}}
    for cache in caches:
        for kind in operations:
            for key, value in cache.get(kind, {}).items():
                old = operations[kind].get(key)
                if old and old.get('status') == value.get('status') == 'ok':
                    equal(old['ranking'], value['ranking'], kind + '/' + key)
                operations[kind][key] = value
    data = artifacts.read_json(source / 'D_feedback/retrieval.json')
    equal(data['signature'], signature, 'D signature')
    if len(data['results']) != 140 or len({r['key'] for r in data['results']}) != 140:
        raise ValueError('D must contain 140 distinct question/scope rows')
    for row in data['results']:
        for decision in row['plan']['decisions']:
            if decision.get('status') == 'started' or decision.get('planning_calls_unknown'):
                raise ValueError('Unknown historical decision: ' + row['key'])
    return signature, data['results'], operations, protected


def validate_ranking(ranking, chunks):
    ids = []
    for item in ranking:
        position = item['position']
        if not isinstance(position, int) or not 0 <= position < len(chunks):
            raise ValueError('Historical candidate has invalid position')
        equal(chunks[position].chunk_id, item['chunk_id'], 'candidate/index identity')
        ids.append(item['chunk_id'])
    if len(ids) != len(set(ids)):
        raise ValueError('Historical ranking contains duplicate children')


def reconstruct_states(row, operations, ref):
    """Reconstruct only executed searches; no controller or LLM is invoked."""
    searches = row['diagnostics']['searches']
    if not searches or len(searches) > 4:
        raise ValueError('Invalid historical search count: ' + row['key'])
    equal([s['query_id'] for s in searches], [f'Q{i}' for i in range(len(searches))], 'search chronology')
    equal(len(searches), row['search_count'], 'search count')
    original = ref['rows'][row['key']]['diagnostics']['searches'][0]['diagnostics']['stages']['reranker']
    equal(searches[0]['diagnostics']['stages']['reranker'], original, 'original local ranking')
    states, runs, union = [], [], set()
    global_operations = []
    for i, search in enumerate(searches):
        local = search['diagnostics']['stages']['reranker']
        validate_ranking(local, ref['chunks'])
        scope = search['document_ids']
        if row['scope'] is not None and (scope is None or not set(scope) <= set(row['scope'])):
            raise ValueError('Historical search exceeds allowed scope')
        if scope is not None and any(ref['chunks'][r['position']].document_id not in scope for r in local):
            raise ValueError('Historical candidate exceeds effective scope')
        request = {k: search[k] for k in SEARCH_FIELDS}
        runs.append((request, local))
        union.update(r['chunk_id'] for r in local)
        if i == 0:
            ranking = original
        else:
            query_key = digest([search['text'], scope])
            found = checked_operation(operations, 'queries', query_key)
            equal(found['ranking'], local, 'saved query ranking')
            global_key = digest([row['query'], runs])
            value = checked_operation(operations, 'global', global_key)
            ranking = value['ranking']
            global_operations.append({'key': global_key, 'pairs': len(ranking),
                                      'historical_origin': value.get('operation_origin'),
                                      'historical_latency_seconds': value.get('latency_seconds')})
        validate_ranking(ranking, ref['chunks'])
        equal(sorted(r['chunk_id'] for r in ranking), sorted(union), 'global/local candidate union')
        states.append({'query_id': search['query_id'], 'ranking': ranking, 'searches': searches[:i+1]})
    equal(states[-1]['ranking'], row['diagnostics']['stages']['reranker'], 'final candidate order')
    equal([o['key'] for o in global_operations],
          [o['cache_key'] for o in row['operations'] if o['kind'] == 'global'], 'global operation references')
    equal([digest([s['text'], s['document_ids']]) for s in searches[1:]],
          [o['cache_key'] for o in row['operations'] if o['kind'] == 'queries'], 'query operation references')
    return states, global_operations


def select_states(states, ref):
    """Annotation-free policy comparison; same parent objects for both arms."""
    bootstrap_python_path()
    from service.rag.v2.EvidenceSelection import parents_from_ranking, pack_order, round_robin
    result = []
    for state in states:
        parents = parents_from_ranking(state['ranking'], ref['chunks'], ref['parents'], ref['vectors'], ref['tokens'])
        g, gt = pack_order(parents)
        local, lt = round_robin(parents, state['searches'], ref['chunks'])
        if len(state['searches']) == 1:
            equal([p.entry for p in g], [p.entry for p in local], 'single-search selection')
            equal(gt, lt, 'single-search packing')
        equal(sorted(p.parent_id for p in parents), sorted(t['parent_id'] for t in lt), 'same treatment parents')
        result.append({**state, 'parents': parents, 'selected': {'G_global': g, 'L_local': local},
                       'traces': {'G_global': gt, 'L_local': lt}})
    return result


def hits_change(before, after):
    return {'gained': sorted(k for k, v in after.items() if v and not before.get(k)),
            'lost': sorted(k for k, v in before.items() if v and not after.get(k))}


def verify_control(row, states, evaluate, chunks=()):
    """Reproduce final and intermediate records before scoring treatment."""
    for state in states:
        state['control_evaluation'] = evaluate(state['selected']['G_global'])
        state['candidate_evaluation'] = evaluate(state['parents'])
    final = states[-1]
    chunk_by_id = {c.chunk_id: c for c in chunks}
    equal([p.entry for p in final['selected']['G_global']], row['evidence'], row['key'] + ': final texts/metadata')
    equal(final['traces']['G_global'], row['packing_trace'], row['key'] + ': final packing')
    equal(sum(p.tokens for p in final['selected']['G_global']), row['context_tokens'], 'final tokens')
    equal(final['control_evaluation'], row['evaluations'], row['key'] + ': final evaluation')
    equal(final['candidate_evaluation'], row['candidate_evaluation'], row['key'] + ': candidate evaluation')
    steps, decisions = row['plan']['steps'], row['plan']['decisions']
    equal(len(steps), len(decisions), 'step/decision count')
    if len(steps) > 4:
        raise ValueError('Too many historical decisions')
    current = 0
    links = []
    for i, (step, decision) in enumerate(zip(steps, decisions), 1):
        equal(step['decision_index'], i, 'decision chronology')
        before = states[current]
        before_ids = [p.parent_id for p in before['selected']['G_global']]
        equal(step['context_before'], before_ids, 'context before decision')
        equal(step['observed_parent_ids'], before_ids, 'observed context IDs')
        request = decision.get('request')
        if request is not None:
            payload = request['payload']
            equal([{k: p.entry.get(k) for k in ('parent_id', 'document_id', 'document_name', 'provenance', 'text')}
                   for p in before['selected']['G_global']], payload['selected_context'], 'observed exact text')
            equal([s['chunk_id'] for s in payload['retrieved_samples']], step['sample_chunk_ids'], 'observed samples')
            for sample in payload['retrieved_samples']:
                if sample['chunk_id'] not in chunk_by_id:
                    raise ValueError('Observed sample is absent from the frozen index')
                child = chunk_by_id[sample['chunk_id']]
                equal(sample, {k: getattr(child, k) for k in ('chunk_id', 'parent_id', 'document_id', 'provenance', 'text')},
                      'observed sample exact text/metadata')
        if step.get('action_executed') and step.get('requested_action') == 'search':
            current += 1
            if current >= len(states):
                raise ValueError('Executed search missing from historical diagnostics')
            equal(step['effective_query'], {k: states[current]['searches'][-1][k] for k in SEARCH_FIELDS}, 'effective search')
        elif step.get('effective_query'):
            raise ValueError('Unexecuted historical search has an effective query')
        after = states[current]
        after_ids = [p.parent_id for p in after['selected']['G_global']]
        equal(step['context_after'], after_ids, 'context after decision')
        equal(step['selected_parent_ids'], after_ids, 'selected IDs')
        equal(step['context_evaluation'], after['control_evaluation'], 'intermediate context evaluation')
        equal(step['candidate_evaluation'], after['candidate_evaluation'], 'intermediate candidate evaluation')
        equal(step['discarded_parents'], [t for t in after['traces']['G_global'] if t['reason'] != 'selected'], 'discarded parents')
        equal(step['context_added'], sorted(set(after_ids) - set(before_ids)), 'parents added')
        equal(step['context_removed'], sorted(set(before_ids) - set(after_ids)), 'parents removed')
        links.append({'decision_index': i, 'state_before': before['query_id'], 'state_after': after['query_id'],
                      'historical_action': step.get('requested_action'), 'action_executed': step['action_executed'],
                      'historical_continuation': step['continuation']})
    equal(current, len(states) - 1, 'all saved searches accounted for')
    equal(len(row['plan']['observations']), len(states) - 1, 'observation count')
    for previous, state, observation in zip(states, states[1:], row['plan']['observations']):
        equal(observation['query_id'], state['query_id'], 'search observation identity')
        equal(observation['ranking_digest_inputs'], [r['chunk_id'] for r in state['ranking']], 'intermediate ranking order')
        equal(observation['selected_parent_ids'], [p.parent_id for p in state['selected']['G_global']], 'observation selected IDs')
        equal(observation['context_tokens'], sum(p.tokens for p in state['selected']['G_global']), 'observation tokens')
        equal(observation['new_parent_ids'], sorted({p.parent_id for p in state['parents']} - {p.parent_id for p in previous['parents']}), 'new parents')
    return links


def serialize_states(states, evaluate):
    snapshots, previous = [], {arm: {} for arm in ARMS}
    for state in states:
        arms = {}
        for arm in ARMS:
            selected = state['selected'][arm]
            scores = state['control_evaluation'] if arm == 'G_global' else evaluate(selected)
            hits = scores['evidence_v2']['selected_hits']
            arms[arm] = {'selected_parent_ids': [p.parent_id for p in selected],
                         'context_tokens': sum(p.tokens for p in selected), 'packing_trace': state['traces'][arm],
                         'evaluations': scores, 'evidence_change_since_previous_search': hits_change(previous[arm], hits)}
            previous[arm] = hits
        snapshots.append({'query_id': state['query_id'], 'search_count': len(state['searches']),
                          'candidate_ranking': state['ranking'],
                          'candidate_parents': [{'parent_id': p.parent_id, 'tokens': p.tokens,
                              'text_sha256': digest(p.entry['text']), 'representative_chunk_id': p.entry['chunk_id']}
                                               for p in state['parents']],
                          'candidate_evaluation': state['candidate_evaluation'], 'arms': arms})
    return snapshots


def comparison(rows, trajectories, expected_keys):
    equal(sorted(r['key'] for r in rows), sorted(expected_keys), 'complete comparison keys')
    scopes = {}
    for scope in SCOPES:
        rr = [r for r in rows if r['condition'] == scope]
        if len(rr) != 70:
            raise ValueError('Expected 70 questions per scope')
        metrics = {}
        for evaluator in ('evidence_v2', 'literal_v1'):
            gains, regressions, evidence_gained, evidence_lost = [], [], [], []
            for r in rr:
                g, local = (r['arms'][a]['evaluations'][evaluator] for a in ARMS)
                if local['complete_selected_anchors'] and not g['complete_selected_anchors']:
                    gains.append(r['key'])
                if g['complete_selected_anchors'] and not local['complete_selected_anchors']:
                    regressions.append(r['key'])
                change = hits_change(g['selected_hits'], local['selected_hits'])
                evidence_gained += [{'key': r['key'], 'evidence_id': aid} for aid in change['gained']]
                evidence_lost += [{'key': r['key'], 'evidence_id': aid} for aid in change['lost']]
            metrics[evaluator] = {'arms': {a: {
                'complete': sum(r['arms'][a]['evaluations'][evaluator]['complete_selected_anchors'] for r in rr),
                'mean_anchor_recall': sum(r['arms'][a]['evaluations'][evaluator]['selected_anchor_recall'] for r in rr) / len(rr)}
                for a in ARMS}, 'question_gains': gains, 'question_regressions': regressions,
                'evidence_gained': evidence_gained, 'evidence_lost': evidence_lost}
        feasible = [r for r in rr if r['minimum_parent_cover']['status'] == 'feasible']
        metrics['feasible_pool'] = {'count': len(feasible), 'complete': {
            a: sum(r['arms'][a]['evaluations']['evidence_v2']['complete_selected_anchors'] for r in feasible) for a in ARMS}}
        metrics['pending_alignment'] = {a: [{'key': r['key'], 'anchors': r['arms'][a]['evaluations']['evidence_v2']['pending_anchors']}
                                           for r in rr if r['arms'][a]['evaluations']['evidence_v2']['pending_anchors']] for a in ARMS}
        metrics['intermediate_losses'] = {a: [{'key': t['key'], 'after_query': s['query_id'],
            'lost': s['arms'][a]['evidence_change_since_previous_search']['lost']}
            for t in trajectories if t['condition'] == scope for s in t['snapshots']
            if s['arms'][a]['evidence_change_since_previous_search']['lost']] for a in ARMS}
        ops = [o for r in rr for o in r['global_operations']]
        metrics['global_work_dispensed'] = {'logical_operations': len(ops), 'logical_pairs': sum(o['pairs'] for o in ops),
                                           'unique_operations': len({o['key'] for o in ops})}
        scopes[scope] = metrics
    all_ops = {o['key']: o for r in rows for o in r['global_operations']}
    checks = {'complete_reproduction': True,
              'no_complete_question_regressions': all(not m['evidence_v2']['question_regressions'] for m in scopes.values()),
              'no_final_evidence_losses': all(not m['evidence_v2']['evidence_lost'] for m in scopes.values()),
              'treatment_requires_no_global_reranks': True}
    return {'scopes': scopes, 'gate': checks,
            'recommendation': 'recommend_full_cycle_comparison' if all(checks.values()) else 'revise',
            'costs': {'new_model_calls': 0, 'new_retrieval_calls': 0, 'new_reranker_calls': 0,
                      'unique_historical_global_operations': len(all_ops),
                      'unique_historical_global_pairs': sum(o['pairs'] for o in all_ops.values()),
                      'logical_global_operations': sum(len(r['global_operations']) for r in rows),
                      'logical_global_pairs': sum(o['pairs'] for r in rows for o in r['global_operations']),
                      'actual_full_cycle_savings': 'not_measured'}}


def write_report(output, result, rows, validation):
    lines = ['# Replay de ordenação global versus alternância local', '',
             '**Recomendação: ' + ('testar o ciclo completo em uma rodada posterior.' if result['recommendation'] != 'revise' else 'revisar; os critérios de passagem não foram satisfeitos.') + '**', '',
             'As mesmas 70 perguntas em dois escopos; consultas e paradas históricas fixas. Nenhuma nova decisão do agente foi produzida.', '',
             '| Escopo | G: completas | L: completas | Ganhos | Regressões | Evidências ganhas/perdidas |',
             '|---|---:|---:|---:|---:|---:|']
    for scope, summary in result['scopes'].items():
        m = summary['evidence_v2']
        lines.append(f"| {scope} | {m['arms']['G_global']['complete']}/70 | {m['arms']['L_local']['complete']}/70 | {len(m['question_gains'])} | {len(m['question_regressions'])} | {len(m['evidence_gained'])}/{len(m['evidence_lost'])} |")
    for scope, summary in result['scopes'].items():
        lines += ['', '## ' + scope, '']
        for evaluator in ('evidence_v2', 'literal_v1'):
            m = summary[evaluator]
            lines += [f"### {evaluator}", '',
                      f"Completas G/L: {m['arms']['G_global']['complete']}/{m['arms']['L_local']['complete']}. Cobertura parcial média G/L: {m['arms']['G_global']['mean_anchor_recall']:.2%}/{m['arms']['L_local']['mean_anchor_recall']:.2%}.", '',
                      'Ganhos: ' + (', '.join(m['question_gains']) or 'nenhum') + '.', '',
                      'Regressões: ' + (', '.join(m['question_regressions']) or 'nenhuma') + '.', '',
                      'Evidências ganhas: ' + (', '.join(x['key'] + '/' + x['evidence_id'] for x in m['evidence_gained']) or 'nenhuma') + '.', '',
                      'Evidências perdidas: ' + (', '.join(x['key'] + '/' + x['evidence_id'] for x in m['evidence_lost']) or 'nenhuma') + '.']
        f = summary['feasible_pool']
        lines += ['', f"Pools com combinação viável: {f['count']}; contextos completos G/L entre eles: {f['complete']['G_global']}/{f['complete']['L_local']}.", '',
                  'Pendências de alinhamento e perdas intermediárias: ver comparison.json e trajectories.json. Uma perda intermediária não é automaticamente uma regressão final.']
    lines += ['', '## Casos diagnosticados na coleção', '']
    for row in rows:
        if row['condition'] != 'collection' or row['case_id'] not in ('REAL-C01', 'REAL-C02', 'REAL-C08', 'REAL-L05'):
            continue
        minimum = row['minimum_parent_cover']
        lines += ['### ' + row['case_id'], '', row['question'], '',
                  f"Menor conjunto comprovado: {minimum.get('minimum_tokens')} tokens; contexto G/L: {row['arms']['G_global']['context_tokens']}/{row['arms']['L_local']['context_tokens']} tokens.", '',
                  '| Evidência | G | L |', '|---|---|---|']
        for aid, hit in row['arms']['G_global']['evaluations']['evidence_v2']['selected_hits'].items():
            other = row['arms']['L_local']['evaluations']['evidence_v2']['selected_hits'][aid]
            lines.append(f"| {aid} | {'presente' if hit else 'ausente'} | {'presente' if other else 'ausente'} |")
        lines += ['', '| Parent da combinação mínima | Tokens | Ordem global | Ordens locais (busca:posição) | G | L |', '|---|---:|---:|---|---|---|']
        for p in row['minimum_witness']:
            lines.append(f"| {p['parent_id']} | {p['tokens']} | {p['global_rank']} | {', '.join(p['local_ranks'])} | {'entra' if p['G_global'] else 'fora'} | {'entra' if p['L_local'] else 'fora'} |")
        lines += ['', 'Os dois braços usam o mesmo pool e encaixe. As diferenças decorrem da ordem de visita; o trace registra quais blocos ocuparam o orçamento antes dos descartados. A combinação mínima usa o gabarito somente como diagnóstico offline.']
    costs = result['costs']
    lines += ['', '## Validação, custo e limites', '',
              f"Controle reproduzido: {validation['rows']} resultados finais, {validation['snapshots']} estados e {validation['decisions']} decisões históricas. Perguntas da coleção com uma busca e seleção idêntica: {validation['single_search_collection']}/55.", '',
              f"Trabalho global dispensado nas trajetórias fixas: {costs['logical_global_operations']} operações lógicas e {costs['logical_global_pairs']} pares. Sem duplicação entre trajetórias: {costs['unique_historical_global_operations']} operações históricas e {costs['unique_historical_global_pairs']} pares.", '',
              'Chamadas novas ao modelo, retriever e reranker: zero. Os custos acima são demanda lógica e operações históricas, não economia de duração medida. timing.json contém somente o tempo deste replay e de sua preparação/avaliação/persistência.', '',
              'G e L reutilizam o reranking local e a mesma política de 3.000 tokens BGE, com parents inteiros. A primeira busca é idêntica. A política não foi ajustada após a medição.', '',
              'Os registros de observação originais estão em historical_observations.json, identificados como observações de D. Não foram simuladas declarações de suficiência, erros ou consultas novas de L. Uma futura rodada completa pode mudar essas decisões.', '',
              'signature.json fixa código, configuração e entradas; code.zip preserva a implementação. reproduction.json e preservation.json registram reprodução e integridade. results.json e trajectories.json contêm os resultados pareados e traces completos.', '',
              'Não há promoção à aplicação. O monitor não é acessado.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')


def run(output, source):
    output, source = Path(output).resolve(), Path(source).resolve()
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Use a separate output directory outside the historical source')
    with offline_only():
        try:
            return _run(output, source)
        except BaseException as exc:
            # Preparation failures have no compatible signature. Preserve existing
            # outputs (especially a completed incompatible run) without overwrites.
            if not output.exists() or not any(output.iterdir()):
                artifacts.save_json(output / 'execution_status.json', {
                    'status': 'incomplete', 'stage': 'preparation', 'error_type': type(exc).__name__,
                    'error': str(exc), 'new_model_calls': 0, 'new_retrieval_calls': 0,
                    'recommendation': 'blocked_do_not_interpret_as_complete'})
            raise


def _run(output, source):
    preparation_started = time.perf_counter()
    from benchmark.search.runtime import load_reference
    from benchmark.evaluation.evidence import SourceAligner
    from benchmark.evaluation.literal import anchor_coverage
    from benchmark.selection.diagnostic import minimum_parent_cover
    # Read-only validation happens before creating/changing output artifacts.
    source_signature, source_rows, operations, protected = load_history(source)
    if any(output == Path(p).parent or output.is_relative_to(Path(p).parent) for p in protected if Path(p).name == 'signature.json'):
        raise ValueError('Output overlaps a historical ancestor')
    from huggingface_hub import snapshot_download
    # An actual directory also prevents tokenizer metadata probes that some
    # transformers versions perform despite local_files_only on a repository ID.
    tokenizer_directory = snapshot_download('BAAI/bge-m3', local_files_only=True)
    ref = load_reference(context_tokenizer=tokenizer_directory)
    equal({r['key']: r['case_id'] for r in source_rows}, {k: v['case_id'] for k, v in ref['rows'].items()}, 'same questions/scopes')
    equal(sha(ref['index']), source_signature['index_sha256'], 'index hash')
    equal(sha(PROJECT_ROOT / 'config/config.toml'), source_signature['config_sha256'], 'frozen config')
    rules_path = source / 'evaluation_rules.json'
    equal(artifacts.read_json(rules_path), artifacts.read_json(ref['rules_path']), 'frozen evaluator rules')
    equal({'questions': sha(ref['directory'] / 'questions.json'), 'anchors': sha(ref['directory'] / 'evidence.json'),
           'rules': sha(ref['rules_path'])}, source_signature['datasets'], 'frozen dataset hashes')
    # Protect all external inputs loaded by the reference, not only the ancestor caches.
    protected.update({str(p.resolve()): sha(p) for p in [ref['index'], rules_path, ref['rules_path'],
                     ref['directory'] / 'questions.json', ref['directory'] / 'evidence.json', PROJECT_ROOT / 'config/config.toml']})
    protected.update({str(p.resolve()): sha(p) for p in CORPUS.glob('*') if p.is_file()})
    import transformers
    tokenizer = transformers.AutoTokenizer.from_pretrained(tokenizer_directory, local_files_only=True)
    signature = {'study': 'global_order_replay', 'version': VERSION, 'source_run': str(source),
                 'source_signature': source_signature, 'input_sha256': protected,
                 'implementation_sha256': implementation_hash(),
                 'code_sha256': {str(p.relative_to(PROJECT_ROOT)): sha(p) for p in code_files()},
                 'dependencies': {p: version(p) for p in ('numpy', 'scipy', 'transformers', 'tokenizers', 'pydantic')},
                 'python': platform.python_version(), 'context_tokenizer': {
                     'name': 'BAAI/bge-m3', 'vocabulary_sha256': digest(tokenizer.get_vocab()),
                     'cached_revision': Path(tokenizer_directory).name,
                     'backend_sha256': digest(tokenizer.backend_tokenizer.to_str()), 'add_special_tokens': False},
                 'arms': list(ARMS), 'budget': 3000, 'local_policy': 'chronological_parent_round_robin_v1',
                 'evaluation_versions': ['evidence_v2', 'literal_v1'], 'new_model_calls': 0,
                 'gate': 'no_final_evidence_v2_loss_either_scope_v1'}
    signature['fingerprint'] = digest(signature)
    signature_path = output / 'signature.json'
    if signature_path.exists():
        equal(artifacts.read_json(signature_path), signature, 'resume signature; use a new output directory')
    elif output.exists() and any(output.iterdir()):
        raise ValueError('Nonempty output has no compatible signature')
    output.mkdir(parents=True, exist_ok=True)
    artifacts.save_json(signature_path, signature)
    artifacts.save_json(output / 'manifest.json', {'signature_fingerprint': signature['fingerprint'],
                        'source_arm': 'D_feedback', 'comparison': 'fixed_trajectory_selection_only',
                        'original_observations_file': 'historical_observations.json',
                        'source_is_read_only': True, 'new_model_calls': 0, 'new_retrieval_calls': 0})
    if not (output / 'code.zip').exists():
        with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in code_files() + sorted((PROJECT_ROOT / 'tests').rglob('*.py')):
                archive.write(file, file.relative_to(PROJECT_ROOT))
    clock = RunClock(output / 'timing.json')
    # The signature must be validated before touching an existing output. Keep
    # that read-only preparation time explicitly, rather than dropping its cost.
    clock.session['pre_signature_preparation_seconds'] = time.perf_counter() - preparation_started
    artifacts.save_json(output / 'execution_status.json', {'status': 'running', 'stage': 'reproduction', 'new_model_calls': 0})
    try:
        cases = {c.id: c for c in ref['cases']}
        aligner = SourceAligner(CORPUS, artifacts.read_json(rules_path))
        corpus = artifacts.source_corpus(ref['anchors'])
        def evaluate(case, parents):
            entries = [p.entry for p in parents]
            return {'evidence_v2': aligner.score(case, entries),
                    'literal_v1': anchor_coverage(case, {'evidence': entries}, ref['anchors'], corpus)}
        prepared = []
        validation = {'status': 'passed', 'rows': 0, 'snapshots': 0, 'decisions': 0, 'single_search_collection': 0,
                      'all_final_and_available_intermediate_records_reproduced': True}
        # Complete reproduction of every control before evaluating treatment.
        clock.set_phase('control_reproduction')
        for row in source_rows:
            case = cases[row['case_id']]
            states, global_ops = reconstruct_states(row, operations, ref)
            selected = select_states(states, ref)
            links = verify_control(row, selected, lambda pp: evaluate(case, pp), ref['chunks'])
            prepared.append((row, selected, global_ops, links))
            validation['rows'] += 1
            validation['snapshots'] += len(states)
            validation['decisions'] += len(links)
            if row['condition'] == 'collection' and len(states) == 1:
                validation['single_search_collection'] += 1
        equal(validation['single_search_collection'], 55, '55 unchanged single-search collection questions')
        artifacts.save_json(output / 'reproduction.json', validation)
        clock.set_phase('selection_evaluation')
        rows, trajectories, observations = [], [], []
        for row, states, global_ops, links in prepared:
            case = cases[row['case_id']]
            snapshots = serialize_states(states, lambda pp: evaluate(case, pp))
            final = states[-1]
            minimum = minimum_parent_cover(case, final['parents'], aligner)
            if minimum['status'] not in ('feasible', 'over_budget', 'not_proven_in_candidates'):
                raise ValueError('Minimum-cover diagnostic unresolved: ' + row['key'])
            witness = [p for p in final['parents'] if p.parent_id in minimum.get('parents', [])]
            if witness:
                equal(aligner.score(case, [p.entry for p in witness])['complete_selected_anchors'], True, 'minimum-cover witness')
                equal(sum(p.tokens for p in witness), minimum['minimum_tokens'], 'minimum-cover tokens')
            local_positions = {}
            for search in row['diagnostics']['searches']:
                ids = list(dict.fromkeys(ref['chunks'][r['position']].parent_id for r in search['diagnostics']['stages']['reranker']))
                for i, pid in enumerate(ids, 1):
                    local_positions.setdefault(pid, []).append(f"{search['query_id']}:{i}")
            rows.append({'key': row['key'], 'case_id': row['case_id'], 'condition': row['condition'],
                         'question': case.question, 'search_count': len(states),
                         'arms': {a: {**snapshots[-1]['arms'][a], 'evidence': [p.entry for p in final['selected'][a]]} for a in ARMS},
                         'candidate_evaluation': final['candidate_evaluation'], 'minimum_parent_cover': minimum,
                         'minimum_witness': [{'parent_id': p.parent_id, 'tokens': p.tokens, 'global_rank': p.rank + 1,
                                              'local_ranks': local_positions.get(p.parent_id, []),
                                              **{a: p.parent_id in {s.parent_id for s in final['selected'][a]} for a in ARMS}} for p in witness],
                         'global_operations': global_ops})
            trajectories.append({'key': row['key'], 'condition': row['condition'], 'snapshots': snapshots,
                                 'historical_decision_state_links': links})
            observations.append({'key': row['key'], 'attributed_to': 'historical_D_feedback_only',
                                 'decisions': [{'decision_index': i + 1, 'request': d.get('request'),
                                                'historical_status': d['status'],
                                                'historical_action': row['plan']['steps'][i].get('requested_action')}
                                               for i, d in enumerate(row['plan']['decisions'])]})
        result = comparison(rows, trajectories, ref['rows'])
        clock.set_phase('reporting_and_persistence')
        for name, value in [('results.json', {'signature_fingerprint': signature['fingerprint'], 'rows': rows}),
                            ('trajectories.json', {'rows': trajectories}), ('historical_observations.json', {'rows': observations}),
                            ('comparison.json', result)]:
            artifacts.save_json(output / name, value)
        write_report(output, result, rows, validation)
        changed = [p for p, expected in protected.items() if not Path(p).is_file() or sha(Path(p)) != expected]
        if changed:
            raise ValueError('Historical inputs changed: ' + ', '.join(changed))
        artifacts.save_json(output / 'preservation.json', {'status': 'passed', 'verified_files': len(protected), 'changed': []})
        artifacts.save_json(output / 'execution_status.json', {'status': 'complete', 'original_questions': 70,
                            'question_scope_pairs': len(rows), 'scopes': list(SCOPES), 'new_model_calls': 0,
                            'new_retrieval_calls': 0, 'new_reranker_calls': 0, 'recommendation': result['recommendation']})
        clock.finish('complete')
        clock.data['total_measured_replay_seconds'] = sum(
            s['active_seconds'] + s.get('pre_signature_preparation_seconds', 0.) for s in clock.data['sessions'])
        artifacts.save_json(clock.path, clock.data)
        print(json.dumps({'recommendation': result['recommendation'], 'scopes': {
            s: m['evidence_v2']['arms'] for s, m in result['scopes'].items()}}, ensure_ascii=False, indent=2))
        return result
    except BaseException as exc:
        artifacts.save_json(output / 'execution_status.json', {'status': 'incomplete', 'error_type': type(exc).__name__,
                            'error': str(exc), 'new_model_calls': 0, 'new_retrieval_calls': 0,
                            'recommendation': 'blocked_do_not_interpret_as_complete'})
        clock.finish('incomplete')
        clock.data['total_measured_replay_seconds'] = sum(
            s['active_seconds'] + s.get('pre_signature_preparation_seconds', 0.) for s in clock.data['sessions'])
        artifacts.save_json(clock.path, clock.data)
        raise
