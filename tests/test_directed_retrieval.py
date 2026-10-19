from types import SimpleNamespace

import pytest

from application.service.rag.v2.DirectedRetrieval import (
    DirectedPlanner, DirectedSearch, merge_and_rerank, select_round_robin,
)
from application.service.rag.v2.Models import Chunk


def chunk(doc, title, text, parent=None):
    return Chunk(chunk_id=doc + title, document_id=doc, document_name=doc + '.pdf',
                 parent_id=parent or doc + title, section_title=title, text=text,
                 relative_path=doc + '.md')


def planner():
    docs = [chunk('Alpha', 'Projeto', 'Projeto Alpha'),
            chunk('Alpha', 'Coordenador na Instituição', 'Coordenador na Instituição\nPessoa Um'),
            chunk('Beta', 'Coordenador na Instituição', 'Coordenador na Instituição\nPessoa Dois'),
            chunk('Gamma', 'Objetivo Geral', 'Objetivo Geral\nUm objetivo'),
            chunk('Meeting', 'Reunião realizada em 13 de julho de 2022', 'Abertura da reunião'),
            chunk('Other', 'Participantes', 'Coordenador do projeto, pesquisadores')]
    catalog = [{'document_id': c.document_id, 'document_name': c.document_name,
                'relative_path': c.relative_path} for c in docs]
    catalog = list({c['document_id']: c for c in catalog}.values())
    return DirectedPlanner(catalog, docs)


def ranking(p, docs):
    return [{'position': next(i for i,c in enumerate(p.chunks) if c.document_id == d)} for d in docs]


def test_explicit_order_precedes_discovery_and_budget_is_deterministic():
    p = planner()
    q = 'Compare os coordenadores de Beta e Alpha.'
    calls, issues = p.plan(q, q, [], ranking(p, ['Alpha', 'Other', 'Beta']))
    assert [s.document_ids for s in calls] == [None, ['Beta'], ['Alpha']]
    assert not issues
    assert all(s.origin == 'explicit_reference' for s in calls[1:])
    assert p.plan(q, q, [], ranking(p, ['Alpha']), max_searches=2)[0][1].document_ids == ['Beta']
    assert len(p.plan(q, q, [], ranking(p, ['Alpha']), max_searches=1)[0]) == 1


def test_discovery_is_source_bound_and_participants_are_not_coordinators():
    p = planner()
    q = 'Quem coordena o projeto que usa a tecnologia desconhecida?'
    calls, _ = p.plan(q, q, [], ranking(p, ['Other', 'Beta', 'Alpha']))
    assert [s.document_ids for s in calls[1:]] == [['Beta'], ['Alpha']]
    assert calls[1].source_proof[0]['chunk_id'] in {c.chunk_id for c in p.chunks}
    assert calls[1].origin == 'retrieved_document'


def test_meeting_dates_scope_and_empty_scope():
    p = planner()
    q = 'Qual a modalidade da reunião de 13/07/2022?'
    calls, _ = p.plan(q, q, [], [])
    assert calls[1].document_ids == ['Meeting']
    assert calls[1].source_proof[0]['kind'] == 'meeting_date'
    assert len(p.plan(q, q, [], [], scope=['Alpha'])[0]) == 1
    assert p.plan(q, q, [], [], scope=[])[0][0].document_ids == []
    assert len(p.plan(q, q, [], [], scope=[])[0]) == 1
    assert len(p.plan('Quanto custa?', 'Quanto custa?', [], ranking(p, ['Alpha']))[0]) == 1


def test_ambiguous_names_do_not_choose_a_source_arbitrarily():
    docs = [chunk('One', 'Coordenador na Instituição', 'Nome Um'),
            chunk('Two', 'Coordenador na Instituição', 'Nome Dois')]
    catalog = [{'document_id': c.document_id, 'document_name': 'Shared.pdf',
                'relative_path': c.relative_path} for c in docs]
    p = DirectedPlanner(catalog, docs)
    calls, issues = p.plan('Quem coordena Shared?', 'Quem coordena Shared?', [], ranking(p, ['One','Two']))
    assert len(calls) == 1
    assert issues[0]['reason'] == 'ambiguous_reference'


def test_abbreviated_meeting_month_keeps_existing_resolver_reference():
    docs=[chunk('Meeting','Reunião realizada em 13 de julho de 2022','Abertura'),
          chunk('Other','Reunião realizada em 20 de junho de 2024','Abertura')]
    catalog=[{'document_id':'Meeting','document_name':'07-2022_Ata_de_Reuniao.pdf','relative_path':'Meeting.md'},
             {'document_id':'Other','document_name':'06-2024_Ata_de_Reuniao.pdf','relative_path':'Other.md'}]
    p=DirectedPlanner(catalog,docs)
    q='Em que modalidade ocorreu a reunião da ata 07-2022?'
    calls,issues=p.plan(q,q,[],ranking(p,['Other','Meeting']))
    assert not issues
    assert calls[1].document_ids==['Meeting'] and calls[1].origin=='explicit_reference'
    assert calls[1].source_proof[0]['kind']=='meeting_month'


def test_merge_uses_original_query_scores_and_preserves_all_local_occurrences():
    docs = [chunk('A', 'One', 'one'), chunk('B', 'Two', 'two')]
    def row(i, score):
        return {'chunk_id': docs[i].chunk_id, 'position': i, 'reranker_score': score,
                'dense_rank': 1, 'sparse_rank': None, 'rrf_score': 1/61}
    runs = [(DirectedSearch('Q0','original',None), [row(0,-1)], {}),
            (DirectedSearch('Q1','short',['B']), [row(1,100),row(0,99)], {})]
    class Reranker:
        def score(self, query, texts):
            assert query == 'original'
            return [10 if t == 'one' else 0 for t in texts]
    combined = merge_and_rerank('original',runs,docs,Reranker())
    assert len(combined) == 2
    assert combined[0]['position'] == 0
    assert [o['query_id'] for o in combined[0]['query_occurrences']] == ['Q0','Q1']
    assert combined[1]['reranker_score'] == 0


def test_round_robin_preserves_bridge_deduplicates_and_skips_oversized_parents():
    docs = [chunk('A','Bridge','bridge',parent='p0'),chunk('A','Repeated','duplicate',parent='p0'),
            chunk('B','Big','large',parent='p1'),chunk('B','Value','value',parent='p2')]
    items = [SimpleNamespace(parent_id='p0',chunk_id='a',evidence_id='E0',context='bridge'),
             SimpleNamespace(parent_id='p1',chunk_id='b',evidence_id='E1',context='large'),
             SimpleNamespace(parent_id='p2',chunk_id='c',evidence_id='E2',context='value')]
    state = SimpleNamespace(found_evidence=items,current_hop=1,evidence=[])
    flow = SimpleNamespace(state=state,retriever=SimpleNamespace(chunks=docs),
                           config=SimpleNamespace(context_tokens=10),diagnostics={},
                           tokens=lambda t:{'bridge':4,'large':20,'value':6}[t])
    runs=[(DirectedSearch('Q0','original',None),[{'position':0},{'position':1}],{}),
          (DirectedSearch('Q1','short',['B']),[{'position':2},{'position':1},{'position':3}],{})]
    selected=select_round_robin(flow,runs)
    assert [x.context for x in selected] == ['bridge','value']
    assert flow.diagnostics['active_context'][0]['embedding_tokens'] == 10
    assert len(flow.diagnostics['packing_trace']) == 3
    assert flow.diagnostics['context_selection'][0]['parent_id'] == 'p1'


def test_budget_cannot_exceed_four():
    p = planner()
    with pytest.raises(ValueError,match='between 1 and 4'):
        p.plan('Quem coordena?', 'Quem coordena?', [], [], max_searches=5)
