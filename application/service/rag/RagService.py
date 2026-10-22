"""Research-checkout RAG facade: the core facade bound to config/config.toml and data/.

The behavior lives in ``rag_ufc_core.facade.RAGService``; this class only supplies
the checkout's settings and data locations, as Streamlit, Telegram and benchmarks
expect from ``RAGService(collection_name, model_name)``.
"""

from rag_ufc_core.facade import RAGService as _CoreRAGService
from rag_ufc_core.settings import DataPaths, EngineSettings

from ..RuntimeConfig import PROJECT_ROOT, get_runtime_config
from .v2.Config import load_settings
from .v2.Engine import RAGEngine


class RAGService(_CoreRAGService):
    def __init__(self, collection_name=None, model_name=None):
        llm_config, config = load_settings()
        self.runtime_config = get_runtime_config()
        self.project_root = PROJECT_ROOT
        super().__init__(
            EngineSettings(llm_config, config),
            DataPaths.under(PROJECT_ROOT / "data"),
            collection_name,
            model_name,
            # Looked up here so tests can replace the engine on this module.
            engine_factory=RAGEngine,
        )
