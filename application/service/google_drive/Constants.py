"""Constants shared by the Google Drive ingestion helpers."""
# Simple: Store Google Drive file types and permission settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"
SUPPORTED_EXTRACTION_METHODS = {
    EXTRACTION_METHOD_PYPDF,
    EXTRACTION_METHOD_DOCLING,
}

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME_TYPE = "application/pdf"
SPREADSHEET_SUFFIXES = {".xlsx", ".csv"}

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
