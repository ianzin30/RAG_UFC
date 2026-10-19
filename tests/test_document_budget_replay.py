"""Budget-only selection and local, non-generating Qwen window audit."""
from types import SimpleNamespace

import numpy as np
import pytest

from benchmark.core import artifacts
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.search import document_budget_replay as study

bootstrap_python_path()
from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
from service.rag.v2.EvidenceSelection import Parent
from tests.test_adaptive_retrieval import fixtures

SOURCE=PROJECT_ROOT/'benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01'


def test_doubling_can_displace_previously_selected_evidence(monkeypatch):
    from service.rag.v2 import EvidenceSelection
    parents=[Parent('large',{},0,4000,np.zeros(0)),Parent('needed',{},1,2500,np.zeros(0))]
    monkeypatch.setattr(EvidenceSelection,'parents_from_ranking',lambda *args:parents)
    ref={k:None for k in ('chunks','parents','vectors','tokens')}
    state={'query_id':'Q0','ranking':[], 'searches':[]}
    result=study.select_states([state],ref)[0]
    assert [p.parent_id for p in result['selected']['D3000']]==['needed']
    assert [p.parent_id for p in result['selected']['D6000']]==['large']
    assert [r['parent_id'] for r in result['traces']['D3000']]==[r['parent_id'] for r in result['traces']['D6000']]


def make_planners(window):
    old,registry,parents,snapshot=fixtures([])
    snapshot.ranking=[{'position':i,'chunk_id':c.chunk_id} for i,c in enumerate(old.chunks)]
    snapshot.parents=parents
    snapshot.runs=[(snapshot.runs[0][0],snapshot.ranking,{})]
    catalog=[{'document_id':d['document_id'],'document_name':d['name']} for d in old.catalog]
    options=dict(input_format='compact_v1',decision_contract='document_search_v1',reason_validation='soft_length_v1')
    planner=InvestigationPlanner(None,catalog,old.chunks,lambda p:len(p)//4,window,100,**options)
    measuring=InvestigationPlanner(None,catalog,old.chunks,lambda p:len(p)//4,1_000_000,100,**options)
    case=SimpleNamespace(question='Qual a formação?',metadata={'history':[]})
    return planner,measuring,snapshot,case,registry


def test_window_failure_does_not_truncate_documentary_context():
    planner,measuring,snapshot,case,registry=make_planners(1)
    before=[p.entry['text'] for p in snapshot.selected]
    record=study.audit_request(planner,measuring,snapshot,case,{'remaining_decisions':2},None,3)
    assert not record['fits'] and record['status']=='does_not_fit'
    assert record['minimum_total_without_samples']>1
    assert before==[p.entry['text'] for p in snapshot.selected]
    assert not registry.calls


def test_window_audit_reproduces_request_and_feedback_budget():
    planner,measuring,snapshot,case,registry=make_planners(16384)
    ledger={'remaining_decisions':2,'tool_feedback':{'code':'INVALID_ARGUMENTS','message':'corrija'}}
    expected=planner.prepare('adaptive',case.question,[],snapshot,ledger,None,3)
    record=study.audit_request(planner,measuring,snapshot,case,ledger,None,3,expected=expected)
    assert record['fits']
    assert record['total_including_output']==expected['input_tokens_counted']+100
    assert not registry.calls


def test_sample_reduction_is_reported_and_document_is_kept():
    planner,measuring,snapshot,case,_=make_planners(16384)
    full=measuring.prepare('adaptive',case.question,[],snapshot,{'remaining_decisions':4},None,3)
    assert full['payload']['retrieved_samples']
    planner.window=full['input_tokens_counted']+99
    record=study.audit_request(planner,measuring,snapshot,case,{'remaining_decisions':4},None,3)
    assert record['fits'] and record['samples_removed']>0
    assert record['status']=='fits_after_sample_reduction'
    assert record['context_parent_ids']==snapshot.context_ids()


def test_cli_dispatches_budget_study_without_live_setup(monkeypatch,tmp_path):
    from benchmark.search import run as command
    calls=[]
    monkeypatch.setattr(study,'run',lambda output,source:calls.append((output,source)))
    monkeypatch.setattr(command,'llm_setup',lambda:pytest.fail('Live setup attempted'))
    monkeypatch.setattr('sys.argv',['benchmark','--study','document_budget_replay','--source-run',str(tmp_path/'source'),
                                  '--output-dir',str(tmp_path/'out')])
    command.main()
    assert calls==[(tmp_path/'out',tmp_path/'source')]


@pytest.mark.skipif(not (SOURCE/'signature.json').exists(),reason='Historical local artifacts unavailable')
def test_real_experiment_is_offline_reproducible_and_keeps_current_window(tmp_path,monkeypatch):
    from benchmark.search import runtime
    from service.rag.v2.AdaptiveRetrieval import InvestigationPlanner
    from service.rag.v2.Providers import ProviderRegistry
    from service.rag.v2.Retrieval import HybridRetriever,BGEReranker,BGEEncoder
    def forbidden(*args,**kwargs):pytest.fail('Live operation attempted')
    monkeypatch.setattr(runtime,'llm_setup',forbidden)
    monkeypatch.setattr(runtime,'build_retriever',forbidden)
    monkeypatch.setattr(InvestigationPlanner,'execute',forbidden)
    for cls in (ProviderRegistry,HybridRetriever,BGEReranker,BGEEncoder):
        monkeypatch.setattr(cls,'__init__',forbidden)
    one,two=tmp_path/'one',tmp_path/'two'
    result=study.run(one,SOURCE)
    assert result['costs']['new_model_calls']==0
    assert result['costs']['changed_document_budget_only']
    reproduction=artifacts.read_json(one/'reproduction.json')
    assert reproduction=={'status':'passed','rows':140,'snapshots':174,'historical_requests_reproduced':182}
    profile=artifacts.read_json(one/'window_audit.json')['profile']
    assert profile['window']==16384 and profile['output_reserved']==4096 and profile['input_margin']==512
    assert not profile['remote_capacity_validated']
    study.run(two,SOURCE)
    for name in ('signature.json','results.json','trajectories.json','window_audit.json','comparison.json',
                 'reproduction.json','preservation.json','execution_status.json'):
        assert artifacts.read_json(one/name)==artifacts.read_json(two/name),name
    assert (one/'report.md').read_text()==(two/'report.md').read_text()
    signature=artifacts.read_json(one/'signature.json')
    signature['document_budgets']['D6000']=7000
    artifacts.save_json(one/'signature.json',signature)
    with pytest.raises(ValueError,match='resume signature'):
        study.run(one,SOURCE)
