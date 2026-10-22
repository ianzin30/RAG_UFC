"""Reusable RAG core shared by the RAG-UFC research repository and applications.

Stable API: ``RAGService``, ``EngineSettings``, ``DataPaths``, ``pipeline_identity``,
``release_manifest`` and ``check_adoption``. Modules under ``rag_ufc_core.rag.v2``
are implementation details that research protocols may use directly.
"""

__version__ = "1.0.0"

__all__ = [
    "DataPaths",
    "EngineSettings",
    "RAGService",
    "__version__",
    "check_adoption",
    "pipeline_identity",
    "release_manifest",
]

_EXPORTS = {
    "DataPaths": "settings",
    "EngineSettings": "settings",
    "RAGService": "facade",
    "pipeline_identity": "identity",
    "release_manifest": "release",
    "check_adoption": "release",
}


def __getattr__(name):
    # Lazy: importing the package must not load models, CrewAI or FAISS.
    if name in _EXPORTS:
        from importlib import import_module
        return getattr(import_module(f"{__name__}.{_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
