"""Compare completed selection experiments on identical frozen candidates."""
import argparse
from pathlib import Path

from benchmark.core.artifacts import read_json, save_json
from benchmark.evaluation.comparison import paired, clustered_ci, grouped
from benchmark.selection.run import metrics


def compare_runs(before, after):
    """Refuse comparisons that changed questions, candidates or documentary rules."""
    for field in ('implementation_sha256', 'index_sha256', 'models', 'corpus_sha256',
                  'config_sha256', 'datasets', 'evaluation_versions'):
        if before['signature'][field] != after['signature'][field]:
            raise ValueError('Incompatible comparison: ' + field)
    old = {row['key']: row for row in before['results']}
    new = {row['key']: row for row in after['results']}
    if old.keys() != new.keys():
        raise ValueError('Unpaired experiment')
    if any(old[key]['source_candidate_digest'] != new[key]['source_candidate_digest'] for key in old):
        raise ValueError('Candidate rankings differ')
    return {scope: {**paired(before['results'], after['results'], scope),
                    'confidence_interval': clustered_ci(before['results'], after['results'], scope)}
            for scope in ('collection', 'oracle_scope')}


def report(run_dirs, output):
    runs = {}
    for folder in run_dirs:
        paths = sorted(folder.glob('*/*/retrieval.json'))
        if not paths:
            raise ValueError('No selection results found: ' + str(folder))
        for path in paths:
            data = read_json(path)
            rows = data['results']
            if not data.get('finished_at') or not rows or len({r['key'] for r in rows}) != len(rows):
                raise ValueError('Incomplete execution: ' + str(path))
            scopes = [{r['case_id'] for r in rows if r['condition'] == scope}
                      for scope in ('collection', 'oracle_scope')]
            if scopes[0] != scopes[1] or len(rows) != 2 * len(scopes[0]):
                raise ValueError('Incomplete scope coverage: ' + str(path))
            pool, policy = path.parent.parent.name, path.parent.name
            key = pool + '/' + policy
            if key in runs:
                raise ValueError('Duplicate condition: ' + key)
            runs[key] = {'path': str(path), 'signature': data['signature'], 'results': rows}
    comparisons = {}
    for name, data in runs.items():
        pool, policy = name.split('/')
        baseline = pool + ('/global_full' if pool == 'reference' else '/round_robin_full')
        if baseline in runs and name != baseline:
            comparisons[name] = compare_runs(runs[baseline], data)
    result = {'sources': {k: v['path'] for k, v in runs.items()},
              'metrics': {k: metrics(v['results']) for k, v in runs.items()},
              'groups': {k: grouped(v['results']) for k, v in runs.items()},
              'comparisons': comparisons}
    save_json(output / 'comparison.json', result)
    lines = ['# Seleção de evidências', '', 'Avaliação principal: evidence_v2. Erros de execução contam como falhas.', '',
             '| Condição | Coleção | Documentos delimitados | Erros |', '|---|---:|---:|---:|']
    for name, values in result['metrics'].items():
        coll, scoped = (values['evidence_v2'][s] for s in ('collection', 'oracle_scope'))
        lines.append(f"| {name} | {coll['complete']}/{coll['total']} | {scoped['complete']}/{scoped['total']} | {coll['errors'] + scoped['errors']} |")
    for name, scopes in comparisons.items():
        lines += ['', '## ' + name, '']
        for scope, values in scopes.items():
            lines.append(f"- {scope}: ganhos {values['complete_gains']}; regressões {values['complete_losses']}.")
    lines += ['', 'Métricas por categoria, evidência e família, cobertura parcial e intervalos de confiança estão em comparison.json.',
              'Os candidatos foram compartilhados. A melhoria do seletor não comprova transferência para outro acervo.', '']
    (output / 'report.md').write_text('\n'.join(lines))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, action='append', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    report(args.run_dir, args.output_dir)


if __name__ == '__main__':
    main()
