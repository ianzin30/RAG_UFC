"""Read-only case audit: frozen index, historical searches and actual observations.

No new query, reranking, model decision or answer. Gold is diagnostic only.
"""
from pathlib import Path
import sys
from collections import Counter

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from benchmark.core import artifacts
from benchmark.core.bootstrap import bootstrap_python_path
from benchmark.core.reproducibility import CORPUS,sha,implementation_hash
from benchmark.search.global_order_replay import offline_only,equal,load_history
from benchmark.selection.run import digest


def run(source,output):
    bootstrap_python_path()
    if output.exists():raise ValueError('Use a new output directory')
    protected={str(p.resolve()):sha(p) for p in source.rglob('*') if p.is_file()}
    with offline_only():
        from huggingface_hub import snapshot_download
        from benchmark.search.runtime import load_reference
        from benchmark.evaluation.evidence import SourceAligner
        from service.rag.v2.EvidenceSelection import parents_from_ranking,pack_order
        signature=artifacts.read_json(source/'signature.json')
        equal(artifacts.read_json(source/'execution_status.json')['status'],'complete','source complete')
        equal(signature['implementation_sha256'],implementation_hash(),'executed code unchanged')
        for name,h in signature['source_hashes'].items():equal(sha(name),h,'historical input')
        ref=load_reference(snapshot_download('BAAI/bge-m3',local_files_only=True))
        _,_,ops,_=load_history(Path(signature['source_run']))
        cache=artifacts.read_json(source/'cache.json')
        equal(cache['signature'],signature,'cache signature')
        for group in ops:ops[group].update(cache[group])
        aligner=SourceAligner(CORPUS,artifacts.read_json(ref['rules_path']))
        cases={c.id:c for c in ref['cases']}
        data=artifacts.read_json(source/'D6000/retrieval.json')['results']
        failed=[r for r in data if r['condition']=='collection' and not r['evaluations']['evidence_v2']['complete_selected_anchors']]
        equal(len(failed),14,'incomplete case count')
        oracle={r['case_id']:r for r in data if r['condition']=='oracle_scope'}
        chunks={c.chunk_id:c for c in ref['chunks']}
        target_docs={aligner.rules['anchors'][aid]['document'] for r in failed for aid in r['evaluations']['evidence_v2']['selected_hits']}
        # Every child can be the first retrieved child used to materialize a parent.
        index_entries=[{**c.model_dump(),'text':ref['parents'][c.parent_id],'excerpt':ref['parents'][c.parent_id]}
            for c in ref['chunks'] if Path(c.relative_path).name in target_docs]
        def expand(ranking):return parents_from_ranking(ranking,ref['chunks'],ref['parents'],ref['vectors'],ref['tokens'])
        def score(case,entries):return aligner.score(case,entries)
        def aligned_hits(case,aligned):
            result={}
            for aid in case.metadata['evidence_ids']:
                rule=aligner.rules['anchors'][aid];_,text,mapping=aligner.sources[rule['document']]
                spans=[s for a in aligned if a['document']==rule['document'] for s in a['spans']]
                result[aid]=all(text[i].isspace() or any(a<=mapping[i]<b for a,b in spans)
                    for q in rule['requirements'] for i in range(q['normalized_start'],q['normalized_end']))
            return result
        anchor_index={}
        for aid in sorted({aid for r in failed for aid,hit in r['evaluations']['evidence_v2']['selected_hits'].items() if not hit}):
            rule=aligner.rules['anchors'][aid]
            one=type('AnchorCase',(),{'metadata':{'evidence_ids':[aid]}})()
            entries=[e for e in index_entries if Path(e['relative_path']).name==rule['document']]
            coverage=score(one,entries)
            witnesses=[]
            for e in entries:
                aligned=aligner.align(e)
                if any(a<q['source_end'] and b>q['source_start'] for a,b in aligned['spans'] for q in rule['requirements']):
                    witnesses.append({'parent_id':e['parent_id'],'chunk_id':e['chunk_id'],'alignment':aligned,
                        'text':e['text'],'tokens':ref['tokens'](e['text'])})
            anchor_index[aid]={'document':rule['document'],'requirements':rule['requirements'],
                'covered_by_full_index':coverage['selected_hits'][aid],'pending':coverage['pending_anchors'],
                'witnesses':witnesses,'document_parent_count':len({e['parent_id'] for e in entries})}
        output_rows=[]
        for row in failed:
            case=cases[row['case_id']];searches=row['diagnostics']['searches'];states=[];runs=[]
            for i,search in enumerate(searches):
                local=search['diagnostics']['stages']['reranker'];args={k:v for k,v in search.items() if k!='diagnostics'}
                runs.append((args,local))
                ranking=local if i==0 else ops['global'][digest([row['query'],runs])]['ranking']
                parents=expand(ranking);selected,trace=pack_order(parents,budget=6000)
                stage_scores={}
                for stage,rank in search['diagnostics']['stages'].items():
                    if isinstance(rank,list) and all(isinstance(x,dict) and 'position' in x for x in rank):
                        stage_scores[stage]=score(case,[p.entry for p in expand(rank)])['selected_hits']
                states.append({'query_id':search['query_id'],'query':search['text'],'scope':search['document_ids'],
                    'stage_parent_coverage':stage_scores,'candidate_hits':score(case,[p.entry for p in parents])['selected_hits'],
                    'selected_hits':score(case,[p.entry for p in selected])['selected_hits'],
                    'parents':parents,'selected':selected,'trace':trace})
            equal(states[-1]['candidate_hits'],row['candidate_evaluation']['evidence_v2']['selected_hits'],'final candidate hits')
            equal(states[-1]['selected_hits'],row['evaluations']['evidence_v2']['selected_hits'],'final selected hits')
            observations=[]
            for i,decision in enumerate(row['plan']['decisions']):
                req=decision.get('request')
                if req is None:raise ValueError('Missing actual observation')
                payload=req['payload'];state=states[len(payload['previous_queries'])-1]
                equal([(e['parent_id'],e['text']) for e in payload['selected_context']],
                    [(p.parent_id,p.entry['text']) for p in state['selected']],'actual shown context')
                aligned=[aligner.align(p.entry) for p in state['selected']]
                equal(aligned_hits(case,aligned),state['selected_hits'],'same coverage semantics')
                samples=[]
                for sample in payload['retrieved_samples']:
                    c=chunks[sample['chunk_id']];equal(c.text,sample['text'],'actual child sample text')
                    entry=c.model_dump();entry['excerpt']=c.text
                    loc=aligner.align(entry,parent=False);aligned.append(loc)
                    samples.append({'chunk_id':c.chunk_id,'parent_id':c.parent_id,'alignment':loc})
                observations.append({'decision_index':i+1,'after_query':state['query_id'],
                    'remaining_searches':payload['remaining_searches'],'remaining_decisions':payload['remaining_decisions'],
                    'selected_hits':state['selected_hits'],'shown_context_and_samples_hits':aligned_hits(case,aligned),
                    'samples':samples,'samples_removed':req['samples_removed'],
                    'decision':decision.get('decision'),'error':decision.get('error'),
                    'feedback_received':payload.get('tool_feedback')})
            missing=[aid for aid,hit in row['evaluations']['evidence_v2']['selected_hits'].items() if not hit]
            evidence_excerpts=[]
            for p in states[-1]['selected']:
                text=p.entry['text']
                if any(word in text.casefold() for word in ['coordenador','videoconferência','híbrida','ck0211','data de início']):
                    evidence_excerpts.append({'parent_id':p.parent_id,'document':Path(p.entry['relative_path']).name,'text':text})
            o=oracle[row['case_id']]
            output_rows.append({'key':row['key'],'question':case.question,'history':case.metadata.get('history',[]),
                'missing_anchors':missing,'full_index_hits':score(case,index_entries)['selected_hits'],
                'candidate_hits':row['candidate_evaluation']['evidence_v2']['selected_hits'],
                'context_hits':row['evaluations']['evidence_v2']['selected_hits'],
                'candidate_pending':row['candidate_evaluation']['evidence_v2']['pending_anchors'],
                'oracle_context_hits':o['evaluations']['evidence_v2']['selected_hits'],
                'oracle_candidate_hits':o['candidate_evaluation']['evidence_v2']['selected_hits'],
                'oracle_searches':[{k:s[k] for k in ['query_id','text','document_ids']} for s in o['diagnostics']['searches']],
                'search_states':[{k:v for k,v in s.items() if k not in ('parents','selected')} for s in states],
                'observations':observations,'selected_relevant_texts':evidence_excerpts,
                'stop_reason':row['stop_reason'],'status':row['status']})
        for name,h in protected.items():equal(sha(name),h,'preserved source '+name)
        output.mkdir(parents=True)
        artifacts.save_json(output/'audit.json',{'name':'Por que faltou evidência? Análise das 14 perguntas',
            'source':str(source),'source_hashes':protected,'analysis_script_sha256':sha(Path(__file__)),
            'gold_informed':True,'used_by_selector':False,'new_model_calls':0,'new_searches':0,
            'new_rerankings':0,'anchor_index':anchor_index,'rows':output_rows})
        artifacts.save_json(output/'preservation.json',{'status':'passed','files_verified':len(protected)})
        print('Index coverage:',{aid:a['covered_by_full_index'] for aid,a in anchor_index.items()})
        for r in output_rows:print(r['key'],r['missing_anchors'],'index',r['full_index_hits'],
            'shown',r['observations'][-1]['shown_context_and_samples_hits'],'oracle',r['oracle_context_hits'])


if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
