"""Public RAG facade backed exclusively by the V2 engine.

This is the supported entry point for applications. Research code may use the
modules under ``rag_ufc_core.rag.v2`` directly; those are not a stable API.
"""

import logging
from pathlib import Path

from .settings import DataPaths, EngineSettings
from .rag.v2.Collections import CollectionStore
from .rag.v2.Spreadsheet import SpreadsheetChunker
from .rag.v2.Support import normalize_identifier, tokenize_search_text

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, settings: EngineSettings, paths: DataPaths, collection_name=None,
                 model_name=None, *, engine_factory=None):
        if engine_factory is None:
            from .rag.v2.Engine import RAGEngine as engine_factory
        self.settings = settings
        self.paths = paths
        self.collections_root = Path(paths.collections_root)
        self.index_cache_root = Path(paths.index_cache_root)
        self.collection_name = None
        self.collection_names = []
        self.document_registry = []
        self.document_catalog = []
        self.last_retrieval_focus = None
        self._response_status_callback = None
        self._collection_progress_callback = None
        self.model_name = model_name or settings.llm.model
        self._spreadsheet = SpreadsheetChunker()
        self._v2 = engine_factory(
            self, settings.llm.model_copy(update={"model": self.model_name}), settings.retrieval
        )
        if collection_name:
            self.load_collection(collection_name)

    def load_collection(self, collection_name):
        return self._v2.load_collection(collection_name)

    def check_model_ready(self):
        """Model discovery/tokenizer only: no completion request."""
        checked = {}
        for role in ('planner', 'research', 'reasoning', 'answer', 'verification', 'source_focus'):
            provider = self._v2.providers.resolve(role)
            key = (provider.identity().get('provider'), provider.identity().get('endpoint'), provider.selection.model)
            if key in checked and key[0] == 'spark':
                provider.physical_model = checked[key].physical_model
                provider.tokenizer = checked[key].tokenizer
                provider.served_models = list(checked[key].served_models)
            elif hasattr(provider, 'resolve'):
                provider.resolve()
                checked[key] = provider

    def check_ready(self):
        """Resolve retrieval dependencies without sending a user query."""
        self.check_model_ready()
        if self._v2.retriever is None:
            raise ValueError('Coleção sem índice carregado.')
        encoder = self._v2.encoder
        if hasattr(encoder, 'verify_model_unchanged'):
            encoder.verify_model_unchanged()
        self._v2.retriever.reranker.score('', [])
        return self._v2.load_diagnostics

    def set_model(self, model_name, rebuild_crewai_agents=True):
        # The optional argument remains accepted for existing callers.
        self._v2.set_model(model_name)
        self.model_name = model_name

    def pipeline_identity(self):
        """Effective pipeline identity: settings in use plus the loaded index, if any."""
        from .identity import pipeline_identity
        return pipeline_identity(
            self.settings.with_model(self.model_name),
            index_diagnostics=getattr(self._v2, "load_diagnostics", None),
        )

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
