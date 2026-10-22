"""Collection names accepted by ``RAGService.load_collection``.

``uploaded_files`` (and the legacy ``__root__``) designate every Markdown file under
the collections root; other names are subdirectories.
"""

from .rag.v2.Collections import (
    ROOT_COLLECTION_KEY,
    UPLOAD_COLLECTION_NAME,
    format_collection_selection_label,
    normalize_collection_selection,
)

__all__ = ["ROOT_COLLECTION_KEY", "UPLOAD_COLLECTION_NAME", "format_collection_selection_label",
           "normalize_collection_selection"]
