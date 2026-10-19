from pathlib import Path
import json,sys
ROOT=Path('/Users/fernandotrinta/Desktop/RAG-UFC/RAG_UFC');sys.path.insert(0,str(ROOT))
from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
from benchmark.core import artifacts
from benchmark.core.reproducibility import CORPUS,sha
from benchmark.search.global_order_replay import offline_only,load_history
from benchmark.search.runtime import load_reference
from benchmark.evaluation.evidence import SourceAligner
from service.rag.v2.EvidenceSelection import parents_from_ranking
from huggingface_hub import snapshot_download
OUT=ROOT/'docs/analises/14_incompletas_2026-10-16'
with offline_only():
 audit=artifacts.read_json(OUT/'audit.json');source=Path(audit['source']);sig=artifacts.read_json(source/'signature.json')
 _,_,ops,protected=load_history(Path(sig['source_run']))
 cache=artifacts.read_json(source/'cache.json')
 ref=load_reference(snapshot_download('BAAI/bge-m3',local_files_only=True));aligner=SourceAligner(CORPUS,artifacts.read_json(ref['rules_path']))
 cases={c.id:c for c in ref['cases']}
 def expand(ranking):return parents_from_ranking(ranking,ref['chunks'],ref['parents'],ref['vectors'],lambda _:0)
 initial={}
 for row in audit['rows']:
  case=cases[row['key'].split(':')[0]];initial[row['key']]={}
  for scope in ['collection','oracle_scope']:
   r=ref['rows'][case.id+':'+scope];ranking=r['diagnostics']['searches'][0]['diagnostics']['stages']['reranker']
   initial[row['key']][scope]=aligner.score(case,[p.entry for p in expand(ranking)])['selected_hits']
 onecases={aid:type('One',(),{'metadata':{'evidence_ids':[aid]}})() for aid in audit['anchor_index']}
 successes={aid:[] for aid in onecases}
 for origin,queries in [('historical',ops['queries']),('current',cache['queries'])]:
  for key,value in queries.items():
   if value['status']!='ok':continue
   pids={ref['chunks'][r['position']].parent_id for r in value['ranking']}
   aids=[aid for aid in onecases if pids & {w['parent_id'] for w in audit['anchor_index'][aid]['witnesses']}]
   if not aids:continue
   pp=expand(value['ranking']);entries=[p.entry for p in pp]
   for aid in aids:
    if aligner.score(onecases[aid],entries)['selected_hits'][aid]:
     successes[aid].append({'query':value['diagnostics']['query'],'scope':value['diagnostics']['scope'],
       'cache_key':key,'origin':origin})
 for name,h in protected.items():assert sha(name)==h
 result={'audit_sha256':sha(OUT/'audit.json'),'script_sha256':sha(Path(__file__)),
  'new_calls':0,'gold_informed':True,'used_by_selector':False,'initial_scope_diagnostic':initial,
  'previously_executed_successful_queries':successes,
  'limits':'Saved successes establish recoverability for those inputs only; no new policy, query or model result is measured.'}
 artifacts.save_json(OUT/'supplement.json',result)
 for key,x in initial.items():print(key,'initial oracle',x['oracle_scope'])
 print('Known successful saved queries by anchor',{a:len(v) for a,v in successes.items()})
 for aid in ['AFO_NAME','RACK_NAME','SAAR_NAME']:
  print(aid,successes[aid][:4])
