"""Paired metrics and uncertainty from shared documentary facts."""
from collections import Counter, defaultdict
import numpy as np

BOOTSTRAP_SEED = 20261007
BOOTSTRAP_RESAMPLES = 10000

def paired(before,after,scope):
 b={r['key']:r for r in before if r['condition']==scope};a={r['key']:r for r in after if r['condition']==scope}
 if set(b)!=set(a):raise ValueError('Unpaired experiment')
 gains=[];losses=[];changes=[];missing=[]
 for key,row in a.items():
  old=b[key]['evaluations']['evidence_v2'];new=row['evaluations']['evidence_v2']
  if new['complete_selected_anchors'] and not old['complete_selected_anchors']:gains.append(row['case_id'])
  if old['complete_selected_anchors'] and not new['complete_selected_anchors']:losses.append(row['case_id'])
  gained=[aid for aid,h in new['selected_hits'].items() if h and not old['selected_hits'][aid]]
  lost=[aid for aid,h in old['selected_hits'].items() if h and not new['selected_hits'][aid]]
  if gained or lost:changes.append({'case_id':row['case_id'],'field':row['field'],'families':row['family_ids'],'gained':gained,'lost':lost})
  union=row['stage_evaluations']['rrf']['all']['evidence_v2']['selected_hits']
  for aid,h in new['selected_hits'].items():
   if not h:missing.append({'case_id':row['case_id'],'anchor':aid,'stage':'selector_execution' if row['status']!='ok' else 'context_selection' if union[aid] else 'not_proven_in_candidates','pending':aid in new['pending_anchors']})
 return {'complete_gains':gains,'complete_losses':losses,'net_gain':len(gains)-len(losses),'evidence_changes':changes,
  'gain_concentration':dict(Counter(a for c in changes for a in c['gained'])),'loss_concentration':dict(Counter(a for c in changes for a in c['lost'])),
  'before_partial':float(np.mean([r['evaluations']['evidence_v2']['selected_anchor_recall'] for r in b.values()])),
  'after_partial':float(np.mean([r['evaluations']['evidence_v2']['selected_anchor_recall'] for r in a.values()])),
  'missing_by_stage':dict(Counter(r['stage'] for r in missing)),'missing_evidence':missing}


def clustered_ci(before,after,scope):
 b={r['key']:r for r in before if r['condition']==scope};a={r['key']:r for r in after if r['condition']==scope}
 keys=sorted(a);roots=list(range(len(keys)))
 def find(i):
  while roots[i]!=i:i=roots[i]
  return i
 owners={}
 for i,key in enumerate(keys):
  for label in ['family:'+f for f in a[key]['family_ids']]+['fact:'+f for f in a[key]['fact_ids']]:
   if label in owners:roots[find(i)]=find(owners[label])
   else:owners[label]=i
 groups=defaultdict(list)
 for i,key in enumerate(keys):groups[find(i)].append(key)
 clusters=list(groups.values());rng=np.random.default_rng(BOOTSTRAP_SEED);values=[]
 for _ in range(BOOTSTRAP_RESAMPLES):
  sample=[key for i in rng.integers(0,len(clusters),len(clusters)) for key in clusters[i]]
  values.append(np.mean([int(a[k]['evaluations']['evidence_v2']['complete_selected_anchors'])-int(b[k]['evaluations']['evidence_v2']['complete_selected_anchors']) for k in sample]))
 return {'clusters':len(clusters),'cluster_sizes':sorted(map(len,clusters)),'complete_rate_difference_ci95':list(map(float,np.percentile(values,[2.5,97.5]))),
  'method':'paired bootstrap of connected components sharing a documentary family or annotated fact; varying cluster sizes retained'}


def grouped(rows):
 result={}
 for field in ('category','field','family_ids','fact_ids'):
  groups=defaultdict(list)
  for r in rows:
   for v in r[field] if isinstance(r[field],list) else [r[field]]:groups[v].append(r)
  result[field]={v:{s:{'cases':sum(r['condition']==s for r in rr),'complete':sum(r['condition']==s and r['evaluations']['evidence_v2']['complete_selected_anchors'] for r in rr)} for s in ('collection','oracle_scope')} for v,rr in groups.items()}
 return result

