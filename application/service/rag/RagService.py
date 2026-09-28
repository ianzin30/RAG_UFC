"""Public RAG facade backed exclusively by the V2 engine."""

import logging
from pathlib import Path

from ..RuntimeConfig import get_runtime_config
from .v2.Config import load_settings
from .v2.Engine import RAGEngine
from .v2.Collections import CollectionStore
from .v2.Spreadsheet import SpreadsheetChunker
from .v2.Support import normalize_identifier, tokenize_search_text

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, collection_name=None, model_name=None):
        llm_config, config = load_settings()
        self.runtime_config = get_runtime_config()
        self.project_root = Path(__file__).resolve().parents[3]
        self.collections_root = self.project_root / "data/collections"
        self.collection_name = None
        self.collection_names = []
        self.document_registry = []
        self.document_catalog = []
        self.last_retrieval_focus = None
        self._response_status_callback = None
        self._collection_progress_callback = None
        self.model_name = model_name or llm_config.model
        self._spreadsheet = SpreadsheetChunker()
        self._v2 = RAGEngine(
            self, llm_config.model_copy(update={"model": self.model_name}), config
        )
        if collection_name:
            self.load_collection(collection_name)

    def load_collection(self, collection_name):
        return self._v2.load_collection(collection_name)

    def set_model(self, model_name, rebuild_crewai_agents=True):
        # The optional argument remains accepted for existing callers.
        self._v2.set_model(model_name)
        self.model_name = model_name

    def ask_question_with_trace(self, question, chat_history=None):
        return self._v2.ask(question, chat_history)

    def ask_question_with_diagnostics(self, question, chat_history=None):
        return self._v2.ask(question, chat_history, diagnostics=True)

    def ask_question(self, question, chat_history=None):
        return str(self.ask_question_with_trace(question, chat_history).get("answer_text", "")).strip()

    def set_response_status_callback(self, callback):
        self._response_status_callback = callback if callable(callback) else None

    def set_collection_progress_callback(self, callback):
        self._collection_progress_callback = callback if callable(callback) else None

    def _emit_response_status(self, stage, message, *, mode=None, agent=None):
        self._emit(self._response_status_callback, {
            "stage": stage, "message": message, "mode": mode, "agent": agent,
        })

    def _emit_collection_progress(self, event, **payload):
        callback = self._collection_progress_callback or getattr(
            self, "_benchmark_progress_callback", None
        )
        self._emit(callback, {"event": event, **payload})

    @staticmethod
    def _emit(callback, payload):
        if callable(callback):
            try:
                callback(payload)
            except Exception:
                logger.debug("Progress callback failed", exc_info=True)

    def _enumerate_collection_markdown_files(self, names):
        return CollectionStore(self.collections_root).enumerate(names)

    def _load_collection_documents(self, names):
        return CollectionStore(self.collections_root).load(names)

    def _build_spreadsheet_chunks(self, document, header):
        return self._spreadsheet._build_spreadsheet_chunks(document, header)

    # Compatibility helpers used by deterministic benchmark consumers.
    _normalize_identifier = staticmethod(normalize_identifier)
    _tokenize_search_text = staticmethod(tokenize_search_text)

    def _get_vector_store_documents(self):
        from langchain_core.documents import Document
        if self._v2.retriever is None:
            return []
        return [
            Document(page_content=chunk.text, metadata={
                **chunk.model_dump(), "candidate_id": chunk.chunk_id
            })
            for chunk in self._v2.retriever.chunks
        ]

    @staticmethod
    def _get_retrieval_candidate_id(doc):
        return doc.metadata["chunk_id"]

    def _build_retrieval_candidate_payload(self, doc):
        metadata = doc.metadata
        source = str(metadata.get("source") or "")
        text = doc.page_content
        return {
            **metadata,
            "candidate_id": self._get_retrieval_candidate_id(doc),
            "document_name": metadata.get("document_name") or "documento",
            "source": source,
            "source_name": Path(source).name if source else None,
            "text": text,
            "excerpt": " ".join(text.split())[:240],
            "entity_names": metadata.get("entity_names") or [],
            "date_values": metadata.get("date_values") or [],
            "money_values": metadata.get("money_values") or [],
            "labeled_facts": metadata.get("labeled_facts") or [],
        }
