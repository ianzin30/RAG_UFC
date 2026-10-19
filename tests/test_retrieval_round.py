import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from application.service.rag.v2.Config import V2Config
from application.service.rag.v2.Documents import build_document_chunks
from benchmark.evaluation.evidence import SourceAligner, freeze_rules


@pytest.fixture(scope="module")
def tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained('BAAI/bge-m3', local_files_only=True)


def doc(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return SimpleNamespace(page_content=text, metadata={'source': str(path)})


def test_contiguous_markdown_offsets_limits_and_determinism(tmp_path, tokenizer):
    text = '# Identidade\n\n## Projeto\n\n## Cargo\n\nNome completo\n\n' + 'Uma frase partida em parágrafos.\n\n' * 80 + '| Campo | Valor |\n|---|---|\n| Data | 2026 |\n'
    documents = [doc(tmp_path, 'a.md', text), doc(tmp_path, 'b.md', '# B\n\nOutro documento.')]
    config = V2Config(chunking_strategy='markdown_blocks_v1', child_tokens=32, parent_tokens=64)
    result = build_document_chunks(documents, tmp_path, tokenizer, config, lambda *a: [])
    chunks, parents, _ = result
    assert result == build_document_chunks(documents, tmp_path, tokenizer, config, lambda *a: [])
    for document in documents:
        group = [c for c in chunks if c.source == document.metadata['source']]
        assert ''.join(c.text for c in group) == document.page_content
        for c in group:
            m = c.metadata
            assert c.text == document.page_content[m['source_start']:m['source_end']]
            assert parents[c.parent_id] == document.page_content[m['parent_source_start']:m['parent_source_end']]
            assert len(tokenizer.encode(c.text, add_special_tokens=False)) <= 32
            assert len(tokenizer.encode(parents[c.parent_id], add_special_tokens=False)) <= 64
    assert '# Identidade\n\n## Projeto\n\n## Cargo\n\nNome completo' in next(iter(parents.values()))
    assert len({c.document_id for c in chunks}) == 2
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_oversized_single_block_preserves_every_character(tmp_path, tokenizer):
    text = 'palavra ' * 1000
    d = doc(tmp_path, 'long.md', text)
    chunks, parents, _ = build_document_chunks([d], tmp_path, tokenizer,
        V2Config(chunking_strategy='markdown_blocks_v1', child_tokens=32, parent_tokens=64), lambda *a: [])
    assert ''.join(c.text for c in chunks) == text
    assert all(len(tokenizer.encode(c.text, add_special_tokens=False)) <= 32 for c in chunks)


def test_spreadsheet_specialization_and_default_are_preserved(tmp_path, tokenizer):
    d = doc(tmp_path, 'sheet.md', '# Sheet\nDocument type: spreadsheet\n')
    item = SimpleNamespace(page_content='row with exact column values', metadata={'sheet_name': 'S', 'chunk_kind': 'spreadsheet_row', 'row': 3})
    legacy = build_document_chunks([d], tmp_path, tokenizer, V2Config(), lambda *a: [item])
    new = build_document_chunks([d], tmp_path, tokenizer, V2Config(chunking_strategy='markdown_blocks_v1'), lambda *a: [item])
    assert legacy == new
    assert V2Config().chunking_strategy == 'legacy'
    assert new[0][0].metadata['row'] == 3


def test_sidecar_provenance_only_for_unique_original_match(tmp_path, tokenizer):
    text = '# T\n\núnico texto\n\nrepetido\n\nrepetido\n'
    d = doc(tmp_path, 'a.md', text)
    (tmp_path / 'a.structure.json').write_text(json.dumps({'markdown_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'sections': [{'title': 'T', 'text': 'único texto', 'provenance': [{'page_no': 1}]},
                     {'title': 'T', 'text': 'repetido', 'provenance': [{'page_no': 2}]}]}))
    chunks, *_ = build_document_chunks([d], tmp_path, tokenizer, V2Config(chunking_strategy='markdown_blocks_v1'), lambda *a: [])
    assert chunks[0].provenance == [{'page_no': 1}]


def test_large_escaped_sidecar_keeps_provenance_for_partial_children(tmp_path, tokenizer):
    body = 'Pesquisa P&D e verificação documental. ' * 150
    text = '# T\n\n' + body.replace('&', '&amp;')
    d = doc(tmp_path, 'a.md', text)
    (tmp_path / 'a.structure.json').write_text(json.dumps({'markdown_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'sections': [{'title': 'T', 'text': body, 'provenance': [{'page_no': 2, 'bbox': {'l': 1}}]}]}))
    chunks, *_ = build_document_chunks([d], tmp_path, tokenizer, V2Config(chunking_strategy='markdown_blocks_v1'), lambda *a: [])
    assert len(chunks) > 1
    assert all(c.provenance == [{'page_no': 2, 'bbox': {'l': 1}}] for c in chunks)
    assert ''.join(c.text for c in chunks) == text


def test_partial_multipage_sidecar_does_not_invent_child_page(tmp_path, tokenizer):
    text = 'um bloco longo ' * 300
    d = doc(tmp_path, 'a.md', text)
    (tmp_path / 'a.structure.json').write_text(json.dumps({'markdown_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'sections': [{'title': '', 'text': text, 'provenance': [{'page_no': 2}, {'page_no': 3}]}]}))
    chunks, *_ = build_document_chunks([d], tmp_path, tokenizer, V2Config(chunking_strategy='markdown_blocks_v1'), lambda *a: [])
    assert all(not c.provenance for c in chunks)


def test_dates_in_wrong_section_and_ambiguous_dates_receive_no_credit(tmp_path):
    text = '## Duração\n\nData de início:\n\n01/03/2026\n\nData de estimada de término:\n\n28/02/2027\n\n## Outra seção\n\n01/03/2026\n\n28/02/2027\n'
    doc(tmp_path, 'a.md', text)
    anchor = {'AFO_DATES': {'document': 'a.md', 'section': 'Duração', 'quote': text.split('## Outra')[0]}}
    scorer = SourceAligner(tmp_path, freeze_rules(anchor, tmp_path))
    case = SimpleNamespace(metadata={'evidence_ids': ['AFO_DATES']})
    entries = [{'relative_path': 'a.md', 'excerpt': value} for value in ('01/03/2026', '28/02/2027')]
    out = scorer.score(case, entries)
    assert not out['complete_selected_anchors']
    assert out['pending_anchors'] == ['AFO_DATES']
    a = text.index('## Outra')
    wrong = {'relative_path': 'a.md', 'excerpt': text[a:], 'metadata': {'parent_source_start': a, 'parent_source_end': len(text)}}
    assert not scorer.score(case, [wrong])['complete_selected_anchors']


def test_coordinator_requires_correct_role_document_and_real_heading(tmp_path):
    text = '# Projeto\n\n## Coordenador na Instituição\n\nNome Correto\n\n## Participante\n\nOutra Pessoa\n'
    doc(tmp_path, 'a.md', text); doc(tmp_path, 'b.md', text)
    anchor = {'AFO_NAME': {'document': 'a.md', 'section': 'Projeto', 'quote': '## Coordenador na Instituição\n\nNome Correto'}}
    scorer = SourceAligner(tmp_path, freeze_rules(anchor, tmp_path))
    case = SimpleNamespace(metadata={'evidence_ids': ['AFO_NAME']})
    entry = {'relative_path': 'a.md', 'excerpt': 'Coordenador na Instituição\nNome Correto', 'section_title': 'Coordenador na Instituição'}
    assert scorer.score(case, [entry])['complete_selected_anchors']
    assert not scorer.score(case, [{**entry, 'relative_path': 'b.md'}])['complete_selected_anchors']
    assert not scorer.score(case, [{**entry, 'excerpt': 'Participante\nNome Correto', 'section_title': 'Participante'}])['complete_selected_anchors']
    assert not scorer.score(case, [{**entry, 'excerpt': 'Coordenador na Instituição\nOutra Pessoa'}])['complete_selected_anchors']




def test_escaped_markdown_body_and_repeated_synthetic_heading_have_real_origin(tmp_path):
    text = '# Documento\n\n## Seção\n\nPrimeira frase.\n\nPesquisa P&amp;D sobre algo verificável.\n'
    doc(tmp_path, 'a.md', text)
    anchors = {'A': {'document': 'a.md', 'section': 'Seção', 'quote': 'Pesquisa P&amp;D sobre algo verificável.'}}
    scorer = SourceAligner(tmp_path, freeze_rules(anchors, tmp_path))
    entry = {'relative_path': 'a.md', 'section_title': 'Seção', 'excerpt': 'Seção\nPesquisa P&D sobre algo verificável.'}
    out = scorer.score(SimpleNamespace(metadata={'evidence_ids': ['A']}), [entry])
    assert out['complete_selected_anchors']
    aligned = out['source_alignment'][0]
    assert aligned['status'] == 'verified_body_and_heading'
    assert text[aligned['spans'][0][0]:aligned['spans'][0][1]] == anchors['A']['quote']


