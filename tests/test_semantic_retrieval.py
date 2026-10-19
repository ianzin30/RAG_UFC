from benchmark.core.bootstrap import bootstrap_python_path
bootstrap_python_path()
import json
from types import SimpleNamespace
import pytest
from service.rag.v2.SemanticRetrieval import SemanticPlanner,SemanticPlan

class Registry:
 def __init__(self,raw):self.raw=raw;self.calls=[];self.prompts=[]
 def structured(self,role,prompt,schema,**kw):
  assert role=='planner' and kw['max_attempts']==1
  self.calls.append({'status':'ok'});self.prompts.append(prompt)
  return schema.model_validate(self.raw)

def planner(raw,counter=lambda x:len(x)//5,window=8192):
 chunks=[SimpleNamespace(chunk_id=f'c{i}',document_id=f'd{i//3}',text='A rubrica Delta recebeu 450 unidades.') for i in range(9)]
 catalog=[{'document_id':f'd{i}','document_name':f'Registro {i}'} for i in range(3)]
 return SemanticPlanner(Registry(raw),catalog,chunks,counter,window),[{'position':i} for i in range(9)]

def test_free_field_and_question_scope_single_call():
 p,r=planner({'needs':['rubrica contábil'],'queries':[{'text':'Qual dotação da rubrica Delta?','need':'dotação',
  'document_ids':['d1'],'scope_source':'question','scope_quote':'Registro 1'}]})
 searches,diag=p.plan('No Registro 1, qual dotação?', 'No Registro 1, qual dotação?',[],r)
 assert len(searches)==2 and searches[1].document_ids==['d1'] and diag['calls']==1
 assert len(diag['sample_chunk_ids'])==6
 assert all(diag['sample_chunk_ids'].count(f'c{i}')<=1 for i in range(9))
 assert 'meeting_dates' not in diag['prompt'] and 'aliases' not in diag['prompt']

def test_chunk_scope_must_belong_to_document_and_exact_quote():
 p,r=planner({'needs':['dotação'],'queries':[{'text':'Qual dotação?','need':'dotação','document_ids':['d2'],
 'scope_source':'c0','scope_quote':'450 unidades'}]})
 searches,diag=p.plan('Informe a dotação','Informe a dotação',[],r)
 assert searches[1].document_ids is None and diag['issues'][0]['reason']=='unproved_scope_opened'

def test_unknown_id_rejected():
 p,r=planner({'needs':['dotação'],'queries':[{'text':'Qual dotação?','need':'dotação','document_ids':['inventado']}]})
 with pytest.raises(ValueError,match='Unknown'):p.plan('x','x',[],r)
 assert len(p.registry.calls)==1

def test_duplicates_budget_empty_scope_and_oracle():
 p,r=planner({'needs':['x'],'queries':[{'text':'x','need':'x'},{'text':'Nova consulta','need':'x'},
 {'text':'nova   consulta','need':'x'}]})
 searches,diag=p.plan('x','x',[],r,scope=['d0'])
 assert len(searches)==2 and searches[1].document_ids==['d0']
 assert len(diag['issues'])==2
 p,r=planner({'needs':['x'],'queries':[]})
 assert p.plan('x','x',[],r,scope=[])[1]['calls']==0 and p.registry.calls==[]

def test_drop_samples_before_call_and_fail_without_window():
 p,r=planner({'needs':['x'],'queries':[]},counter=lambda s:1200+json.loads(s.split('\nReturn only')[0].rsplit('\n',1)[1])['initial_results'].__len__()*500,window=2500)
 _,diag=p.plan('x','x',[],r)
 assert len(diag['sample_chunk_ids'])==0 and diag['input_tokens_counted']+1024<=2500
 p,r=planner({'needs':['x'],'queries':[]},counter=lambda s:9000)
 with pytest.raises(ValueError,match='window'):p.plan('x','x',[],r)
 assert not p.registry.calls

def test_malformed_and_more_than_three_queries_fail():
 p,r=planner({'needs':['x'],'queries':[{'text':'x','need':'x'}]*4})
 with pytest.raises(ValueError):p.plan('x','x',[],r)
 assert len(p.registry.calls)==1

def test_catalog_ids_constrain_schema_without_specific_fields():
 p,r=planner({'needs':['pressão de ensaio'],'queries':[]})
 observed={}
 original=p.registry.structured
 def capture(*args,**kwargs):
  observed.update(kwargs)
  return original(*args,**kwargs)
 p.registry.structured=capture
 p.plan('Qual pressão do ensaio?', 'Qual pressão do ensaio?', [], r)
 assert observed['references']=={'document_ids':['d0','d1','d2']}

def test_explicit_lower_query_budget_and_sample_order():
 p,r=planner({'needs':['responsabilidade e prazo'],'queries':[{'text':'Responsável por ensaio','need':'responsabilidade'}, {'text':'Prazo do ensaio','need':'prazo'}]})
 p.max_searches=2
 searches,diag=p.plan('Qual responsável e prazo?', 'Qual responsável e prazo?', [], r)
 assert len(searches)==2
 assert diag['sample_chunk_ids']==['c0','c1','c3','c4','c6','c7']
 assert searches[1].text=='Responsável por ensaio'
