import pytest
from langchain_core.documents import Document
from application.service.rag.v2.Collections import CollectionStore
from application.service.rag.v2.Spreadsheet import SpreadsheetChunker
from application.service.rag.v2.Documents import build_document_chunks
from application.service.rag.v2.Config import V2Config
from tests.test_rag_v2_documents import Tokenizer


def test_collection_loading_deduplicated_hashes_and_utf8(tmp_path):
    path = tmp_path / "a" / "same.md"
    path.parent.mkdir()
    path.write_text("# Ata\nSão Paulo\n", encoding="utf-8")
    store = CollectionStore(tmp_path)
    hashes = store.enumerate(["a", "__root__"])
    assert len(hashes) == 1
    assert hashes[0]["relative_path"] == "a/same.md"
    document = store.load(["a"])[0]
    assert document.page_content == "# Ata\nSão Paulo\n"
    assert document.metadata["collection_name"] == "a"
    path.write_text("changed", encoding="utf-8")
    assert hashes != store.enumerate(["a"])


def test_missing_and_empty_collection_fail_explicitly(tmp_path):
    store = CollectionStore(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        store.load(["missing"])
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="No documents"):
        store.enumerate(["empty"])


def test_spreadsheet_preserves_specialized_chunks_and_stable_ids(tmp_path):
    text = """# Pessoas
Document Type: spreadsheet
Descrição da planilha
## Sheet: Equipe
Column profiles:
- Nome: texto
People index:
- Person: João Silva | Role: Professor | Sheet: Equipe | Row: 2
Row records:
- Spreadsheet file pessoas.xlsx | Sheet Equipe | Row 2: Nome=João Silva | Cargo=Professor
"""
    doc = Document(page_content=text, metadata={
        "source": str(tmp_path / "pessoas.md"), "document_name": "Pessoas"
    })
    builder = SpreadsheetChunker()._build_spreadsheet_chunks
    items = builder(doc, "")
    assert [item.metadata["chunk_kind"] for item in items] == [
        "summary", "column_profile", "people_index", "row_record"
    ]
    row = items[-1]
    assert row.metadata["row_number"] == 2
    assert row.metadata["row_values"] == {"Nome": "João Silva", "Cargo": "Professor"}
    assert items[-2].metadata["entity_name"] == "João Silva"
    args = ([doc], tmp_path, Tokenizer(), V2Config(), builder)
    first = build_document_chunks(*args)
    assert first == build_document_chunks(*args)
    assert len({item.chunk_id for item in first[0]}) == len(first[0])
    assert {item.chunk_kind for item in first[0]} == {
        "summary", "column_profile", "people_index", "row_record"
    }


def test_facade_contracts_and_callbacks_without_model(monkeypatch):
    import importlib
    facade = importlib.import_module("application.service.rag.RagService")

    class Engine:
        def __init__(self, owner, llm, config):
            self.owner = owner
            self.retriever = object()

        def load_collection(self, selection):
            return selection

        def set_model(self, model):
            self.model = model

        def ask(self, question, history=None, diagnostics=False):
            return {"answer_text": question, "diagnostics_enabled": diagnostics}

    monkeypatch.setattr(facade, "RAGEngine", Engine)
    service = facade.RAGService()
    marker = service._v2.retriever
    assert service.load_collection(["a", "b"]) == ["a", "b"]
    assert service.ask_question("test") == "test"
    assert service.ask_question_with_diagnostics("test")["diagnostics_enabled"]
    service.set_model("qwen3.5")
    assert service._v2.retriever is marker
    events = []
    service.set_collection_progress_callback(events.append)
    service._emit_collection_progress("ready", total=1)
    service.set_response_status_callback(events.append)
    service._emit_response_status("answer", "Pronto")
    assert events[0] == {"event": "ready", "total": 1}
    assert events[1]["stage"] == "answer"
    service.set_response_status_callback(lambda event: 1 / 0)
    service._emit_response_status("answer", "Pronto")  # Callback errors are isolated.
