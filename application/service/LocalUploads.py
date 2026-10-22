"""Research-checkout uploads: the core service rooted at the Drive collections root.

Extraction and file layout live in ``rag_ufc_core.LocalUploads``; this module only
supplies the checkout's collections root, as Streamlit expects.
"""

from __future__ import annotations

from rag_ufc_core import LocalUploads as _core
from rag_ufc_core.LocalUploads import (  # noqa: F401 - historical import surface
    PLAIN_TEXT_SUFFIXES,
    SUPPORTED_UPLOAD_SUFFIXES,
    UploadProgressCallback,
    _emit_upload_progress,
    _next_output_path,
)

from .GoogleDrive import GoogleDriveService


class LocalUploadService(_core.LocalUploadService):
    def __init__(self) -> None:
        self.drive_service = GoogleDriveService()
        super().__init__(self.drive_service.collections_root)
