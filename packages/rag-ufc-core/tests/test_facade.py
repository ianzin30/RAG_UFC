"""The facade works from injected settings and paths, with no research checkout."""
from pathlib import Path

import pytest

from rag_ufc_core import DataPaths, RAGService, pipeline_identity
from rag_ufc_core.LocalUploads import LocalUploadService
from rag_ufc_core.rag.v2.Engine import RAGEngine
from rag_ufc_core.secret_source import read_secret, use_secret_source

from conftest import HashEncoder


class PreparedEngine(RAGEngine):
    """The real engine with a deterministic encoder instead of BGE/Ollama."""

    def __init__(self, facade, llm_config, config):
        super().__init__(facade, llm_config, config)
        self.encoder = HashEncoder()


def test_collection_index_is_built_and_cached_under_the_injected_paths(settings, corpus):
    paths = DataPaths.under(corpus)
    events = []
    service = RAGService(settings, paths, engine_factory=PreparedEngine)
    service.set_collection_progress_callback(events.append)
    service.load_collection(["uploaded_files", "uploaded_files", " "])
    assert service.collection_names == ["uploaded_files"]
    assert service.collection_name == "Uploaded files"
    cached = list(paths.index_cache_root.glob("*.npz"))
    assert len(cached) == 1 and cached[0].stem == service._v2.load_diagnostics["fingerprint"]
    assert {e["event"] for e in events} >= {"collection_load_started", "collection_cache_written"}
    assert {entry["document_name"] for entry in service.document_catalog} == {"regimento.pdf", "calendario.pdf"}

    again = RAGService(settings, paths, engine_factory=PreparedEngine)
    again.load_collection("uploaded_files")
    assert again._v2.load_diagnostics["cache_hit"] is True
    assert all(Path(c.source).is_relative_to(paths.collections_root) for c in again._v2.retriever.chunks)

    identity = again.pipeline_identity()
    assert identity["index"]["index_fingerprint"] == again._v2.load_diagnostics["fingerprint"]
    assert identity["pipeline_signature"] == pipeline_identity(settings)["pipeline_signature"]


def test_model_switch_keeps_the_loaded_index(settings, corpus):
    service = RAGService(settings, DataPaths.under(corpus), engine_factory=PreparedEngine)
    service.load_collection("uploaded_files")
    retriever = service._v2.retriever
    service.set_model("other/model")
    assert service._v2.retriever is retriever
    assert service.pipeline_identity()["models"]["generation"]["model"] == "other/model"


def test_unknown_collection_and_empty_selection_fail_clearly(settings, corpus):
    service = RAGService(settings, DataPaths.under(corpus), engine_factory=PreparedEngine)
    with pytest.raises(ValueError, match="No collection selected"):
        service.load_collection([])
    with pytest.raises(ValueError, match="not found"):
        service.load_collection("missing")


def test_secret_source_is_explicit_and_replaceable(monkeypatch):
    monkeypatch.setenv("CORE_TEST_SECRET", " from-env ")
    assert read_secret("CORE_TEST_SECRET") == "from-env"
    use_secret_source({"CORE_TEST_SECRET": "from-host"}.get)
    try:
        assert read_secret("CORE_TEST_SECRET") == "from-host"
        assert read_secret("MISSING") == ""
    finally:
        use_secret_source(None)


def test_uploads_write_the_markdown_corpus_under_the_given_root(tmp_path):
    class Upload:
        def __init__(self, name, data):
            self.name, self._data = name, data

        def getvalue(self):
            return self._data

    progress = []
    service = LocalUploadService(tmp_path / "collections")
    result = service.ingest_uploaded_files(
        [Upload("notas aula.txt", "Prova em 10/03.".encode()), Upload("vazio.txt", b"")],
        progress_callback=progress.append,
    )
    saved = Path(result["files"][0]["output_path"])
    assert saved == tmp_path / "collections" / "uploaded_files" / "01_notas_aula.md"
    assert saved.read_text(encoding="utf-8") == "# notas aula.txt\n\nExtraction method: docling\n\nProva em 10/03.\n"
    assert result["skipped_files"] == [{"name": "vazio.txt", "reason": "empty file"}]
    assert [p["status"] for p in progress] == ["queued", "extracting", "saved", "skipped", "completed"]
