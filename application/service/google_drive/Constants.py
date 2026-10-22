"""Constants shared by the Google Drive ingestion helpers."""
# Simple: Store Google Drive file types and permission settings

from rag_ufc_core.DocumentExtraction import (  # noqa: F401 - one definition for all sources
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_PYPDF,
    SPREADSHEET_SUFFIXES,
    SUPPORTED_EXTRACTION_METHODS,
)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME_TYPE = "application/pdf"

DOCLING_BINARY_MIME_TYPES = {
    PDF_MIME_TYPE: ".pdf",
    DOCX_MIME_TYPE: ".docx",
    PPTX_MIME_TYPE: ".pptx",
    XLSX_MIME_TYPE: ".xlsx",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
}

DOCLING_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": (DOCX_MIME_TYPE, ".docx"),
    "application/vnd.google-apps.spreadsheet": (XLSX_MIME_TYPE, ".xlsx"),
    "application/vnd.google-apps.presentation": (PPTX_MIME_TYPE, ".pptx"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}
