"""
App configuration - paths, constants, and file type settings.

Defines project paths, the logo image, supported file types for upload,
and collection names.
"""

import base64
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGO_PATH = PROJECT_ROOT / "application" / "assets" / "rag_treino_icon.png"
LOGO_DATA_URI = (
    f"data:image/png;base64,{base64.b64encode(LOGO_PATH.read_bytes()).decode('ascii')}"
    if LOGO_PATH.exists()
    else ""
)

# Collection names
ROOT_COLLECTION_KEY = "__root__"
UPLOAD_COLLECTION_NAME = "uploaded_files"

# Supported file types for upload
UPLOAD_FILE_TYPES = [
    "pdf",
    "docx",
    "pptx",
    "xlsx",
    "csv",
    "md",
    "txt",
    "html",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "tiff",
    "bmp",
]
