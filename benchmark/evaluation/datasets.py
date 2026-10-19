"""Source-position annotation utilities, outside the retrieval policy boundary."""
import hashlib,json
from collections import Counter
from pathlib import Path
from benchmark.evaluation.evidence import normalized,occurrences,source_end
from benchmark.core.questions import load_questions
from benchmark.core.reproducibility import CORPUS,sha

OLD_FIELDS={'coordinator','objective','chair','modality'}

def compile_dataset(rows,inventory,split,output,*,expected_counts=None):
    families={d['relative_path']:f['family_id'] for f in inventory['families'] for d in f['documents']}
    anchors={};rules={'version':'evidence_v2','definition':'all explicit requirements at verified original positions; ambiguous source mappings receive no credit','anchors':{}}
    fact_use=Counter();cases=[];facts={}
    for index,row in enumerate(rows,1):
        case_id=f'GEN-{split.upper()}-{index:03d}';required=[];family_ids=[]
        for proof in row['evidence']:
            document=proof['document'];raw=(CORPUS/document).read_text();text,mapping=normalized(raw)
            needle=normalized(proof['quote'])[0];matches=occurrences(text,needle)
            if len(matches)!=1:raise ValueError(f'Annotation must uniquely match source: {case_id}/{document}: {len(matches)}')
            a,b=matches[0]
            if len(needle)<15:raise ValueError('Evidence quote too short')
            aid='GF-'+hashlib.sha256(json.dumps([document,a,b]).encode()).hexdigest()[:16]
            if aid not in required:fact_use[aid]+=1
            required.append(aid);family_ids.append(families['uploaded_files/'+document])
            anchors[aid]={'document':document,'section':'','quote':raw[mapping[a]:source_end(raw,mapping[b-1])],
                'accepted_answers':[row['expected_answer']]}
            rules['anchors'][aid]={'document':document,'source_sha256':sha(CORPUS/document),'audited':True,
                'quote_source_start':mapping[a],'quote_source_end':source_end(raw,mapping[b-1]),
                'requirements':[{'name':'explicit_documentary_requirement','normalized_start':a,'normalized_end':b,
                   'source_start':mapping[a],'source_end':source_end(raw,mapping[b-1]),'text':text[a:b]}],
                'audit_note':'Source quote checked for unique raw position; question and relation reviewed separately.'}
            facts[aid]={'document':document,'family_id':family_ids[-1],'source_start':mapping[a],'source_end':source_end(raw,mapping[b-1])}
        if row['category']=='cross-document' and len(set(p['document'] for p in row['evidence']))<2:
            raise ValueError('Cross-document case needs at least two sources')
        if row['category']=='multi-hop' and (len(set(required))<2 or not row.get('bridge')):
            raise ValueError('Multi-hop case needs two requirements and an explicit bridge annotation')
        cases.append({'id':case_id,'collection':'uploaded_files','category':row['category'],'question':row['question'],
            'expected_answer':row['expected_answer'],'metadata':{'evidence_ids':list(dict.fromkeys(required)),
            'split':split,'family_ids':sorted(set(family_ids)),'field':row['field'],'outside_old_fields':row['field'] not in OLD_FIELDS,
            'bridge':row.get('bridge',''),'history':[]}})
    if max(fact_use.values(),default=0)>2:raise ValueError('Same annotated fact used more than twice')
    # Overlapping quotes also count as one fact, avoiding superficial changes in span boundaries.
    for aid,first in facts.items():
        neighbors=[bid for bid,second in facts.items() if first['document']==second['document'] and
            max(first['source_start'],second['source_start'])<min(first['source_end'],second['source_end'])]
        case_count=sum(any(a in neighbors for a in c['metadata']['evidence_ids']) for c in cases)
        if case_count>2:raise ValueError(f'Overlapping fact used in {case_count} cases')
    expected={'development':{'multi-hop':6,'cross-document':6,'single-document factual':8},
              'test':{'multi-hop':20,'cross-document':20,'single-document factual':20}}
    if dict(Counter(c['category'] for c in cases))!=(expected_counts or expected[split]):raise ValueError('Split quotas not satisfied')
    if split=='test' and sum(c['metadata']['outside_old_fields'] for c in cases)*2<len(cases):raise ValueError('At least half need new fields')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for name,value in [('questions.json',cases),('evidence.json',anchors),('evidence_v2_rules.json',rules),('facts.json',facts),('annotation_drafts.json',rows)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return cases

def load_dataset(directory, split=None):
    directory=Path(directory)
    selected=directory/split if split and (directory/split/'questions.json').exists() else directory
    cases=[c for c in load_questions(selected/'questions.json') if c.metadata.get('evidence_ids')]
    anchors=json.loads((selected/'evidence.json').read_text())
    return cases,anchors,selected
