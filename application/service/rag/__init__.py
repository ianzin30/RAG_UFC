# Simple: Public search system interface

__all__ = ["RAGService"]


def __getattr__(name: str):
    if name == "RAGService":
        from .RagService import RAGService

        return RAGService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
