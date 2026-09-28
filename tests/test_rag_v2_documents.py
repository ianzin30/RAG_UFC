from pathlib import Path
from types import SimpleNamespace
from application.service.rag.v2.Documents import build_document_chunks
from application.service.rag.v2.Config import V2Config


class Tokenizer:
    def __call__(self, text, **kwargs):
        import re

        return {
            "offset_mapping": [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
        }


def test_same_document_names_have_distinct_ids_and_explicit_parents(tmp_path):
    documents = []
    for collection in ("a", "b"):
        path = tmp_path / collection / "same.md"
        documents.append(
            SimpleNamespace(
                page_content="# Same\n## Section\nRepeated text. Repeated text.",
                metadata={"source": str(path)},
            )
        )
    result = build_document_chunks(
        documents, tmp_path, Tokenizer(), V2Config(), lambda *args: []
    )
    chunks, parents, catalog = result
    assert len({chunk.document_id for chunk in chunks}) == 2
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(chunk.text in parents[chunk.parent_id] for chunk in chunks)
    assert result == build_document_chunks(
        documents, tmp_path, Tokenizer(), V2Config(), lambda *args: []
    )


def test_structural_sidecar_cannot_silently_desynchronize(tmp_path):
    import pytest
    from application.service.StructuredExtraction import (
        ExtractedText,
        write_structure_sidecar,
    )

    path = tmp_path / "doc.md"
    path.write_text("hello")
    extracted = ExtractedText(
        "hello", [{"title": "T", "text": "hello", "provenance": [{"page_no": 2}]}]
    )
    write_structure_sidecar(path, extracted)
    document = SimpleNamespace(page_content="hello", metadata={"source": str(path)})
    chunks, _, _ = build_document_chunks(
        [document], tmp_path, Tokenizer(), V2Config(), lambda *args: []
    )
    assert chunks[0].provenance == [{"page_no": 2}]
    document.page_content = "changed"
    with pytest.raises(ValueError, match="Stale"):
        build_document_chunks(
            [document], tmp_path, Tokenizer(), V2Config(), lambda *args: []
        )
