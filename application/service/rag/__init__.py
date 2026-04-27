"""RAG service public interface.

Lazy-loads RAGService to avoid circular imports and keep startup time low.
"""

__all__ = ["RAGService"]


def __getattr__(name: str):
    if name == "RAGService":
        from .RagService import RAGService

        return RAGService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
