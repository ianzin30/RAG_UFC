"""Post-selection diagnosis only; never affects live requests or selection."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from benchmark.core import artifacts
from benchmark.core.bootstrap import bootstrap_python_path
from benchmark.core.reproducibility import CORPUS, sha
from benchmark.search.global_order_replay import offline_only, hits_change


def main(run):
    bootstrap_python_path()
    with offline_only():
        from huggingface_hub import snapshot_download
        from benchmark.search.runtime import load_reference
        from benchmark.evaluation.evidence import SourceAligner
        from benchmark.selection.diagnostic import minimum_parent_cover
        from service.rag.v2.EvidenceSelection import parents_from_ranking
        status=artifacts.read_json(run/'execution_status.json')
        if status['status']!='complete':raise ValueError('Wait for a completed run')
        protected={str(p):sha(p) for p in run.rglob('*') if p.is_file()}
        ref=load_reference(snapshot_download('BAAI/bge-m3',local_files_only=True))
        aligner=SourceAligner(CORPUS,artifacts.read_json(ref['rules_path']))
        cases={c.id:c for c in ref['cases']}
        rows=[]; costs={}
        cache=artifacts.read_json(run/'cache.json')
        for arm,budget in [('D3000',3000),('D6000',6000)]:
            data=artifacts.read_json(run/arm/'retrieval.json')['results']
            costs[arm]={'logical_decisions':sum(len(r['plan']['decisions']) for r in data),
                'logical_searches_including_initial':sum(r['search_count'] for r in data),
                'logical_prompt_tokens':sum((e.get('usage') or {}).get('prompt_tokens',0) for r in data for e in r['plan']['events']),
                'logical_completion_tokens':sum((e.get('usage') or {}).get('completion_tokens',0) for r in data for e in r['plan']['events']),
                'logical_model_seconds':sum(e.get('logical_latency_seconds',e.get('latency_seconds',0)) for r in data for e in r['plan']['events']),
                'operation_origins':{g:{origin:sum(o['kind']==g and o['origin']==origin for r in data for o in r['operations'])
                    for origin in ['live','shared_cache','historical']} for g in ['decision','queries','global']}}
            for r in data:
                parents=parents_from_ranking(r['diagnostics']['stages']['reranker'],ref['chunks'],ref['parents'],ref['vectors'],ref['tokens'])
                cover=minimum_parent_cover(cases[r['case_id']],parents,aligner,budget=budget)
                complete=r['evaluations']['evidence_v2']['complete_selected_anchors']
                previous=r['initial_evaluations']['evidence_v2']['selected_hits']
                intermediate=[]
                for step in r['plan']['steps']:
                    current=step['context_evaluation']['evidence_v2']['selected_hits']
                    intermediate.append({'decision_index':step['decision_index'],
                        'action_executed':step['action_executed'],**hits_change(previous,current)})
                    previous=current
                reason=('complete' if complete else 'candidate_coverage_not_proven' if cover['status']=='not_proven_in_candidates'
                    else 'whole_parent_budget' if cover['status']=='over_budget' else 'selection_loss' if cover['status']=='feasible' else 'diagnostic_pending')
                rows.append({'key':r['key'],'arm':arm,'scope':r['condition'],'document_failure_stage':reason,
                    'operational_error':r['status']!='ok','stop_reason':r['stop_reason'],'declared_sufficient':r['declared_sufficient'],
                    'false_sufficiency':r['declared_sufficient'] and not complete,'minimum_parent_cover':cover,
                    'intermediate_changes':intermediate,
                    'selected_hits':r['evaluations']['evidence_v2']['selected_hits'],
                    'candidate_hits':r['candidate_evaluation']['evidence_v2']['selected_hits'],
                    'pending_alignment':r['evaluations']['evidence_v2']['pending_anchors'],
                    'context_tokens':r['context_tokens'],'search_count':r['search_count']})
        physical={g:{'operations':sum(v.get('operation_origin')=='live' for v in cache[g].values()),
            'seconds':sum(v.get('latency_seconds',0) for v in cache[g].values() if v.get('operation_origin')=='live'),
            'reranker_pairs':sum(v.get('physical_reranker_pairs',0) for v in cache[g].values() if v.get('operation_origin')=='live')}
            for g in ['queries','global']}
        physical['queries']['stages_seconds']={stage:sum(v.get('diagnostics',{}).get('latencies',{}).get(stage,0)
            for v in cache['queries'].values() if v.get('operation_origin')=='live')
            for stage in ['query_encoding','dense','sparse','rrf','reranker']}
        scopes={s:{a:{stage:sum(r['scope']==s and r['arm']==a and r['document_failure_stage']==stage for r in rows)
            for stage in ['complete','candidate_coverage_not_proven','whole_parent_budget','selection_loss','diagnostic_pending']}
            for a in ['D3000','D6000']} for s in ['collection','oracle_scope']}
        result={'gold_informed':True,'used_by_selector':False,'source_hashes':protected,
            'analysis_script_sha256':sha(Path(__file__)),'rows':rows,
            'document_failure_counts':scopes,'logical_costs':costs,'physical_retrieval_costs':physical,
            'interpretation_limits':['Absent candidate evidence does not distinguish poor query from retrieval miss.',
                'Operational errors are reported separately and can coexist with document failures.',
                'Effective execution order: D3000 first in collection; D6000 first in oracle_scope.',
                'Shared/historical caches prevent interpreting physical arm time as uncached system speed.']}
        for path,h in protected.items():
            if sha(path)!=h:raise ValueError('Input changed during diagnosis')
        artifacts.save_json(run/'post_selection_diagnosis.json',result)
        print(json.dumps({'failure_counts':scopes,'physical_retrieval_costs':physical,'logical_costs':costs},ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]).resolve())
