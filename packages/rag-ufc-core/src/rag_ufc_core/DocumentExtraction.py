"""Document-to-Markdown extraction shared by uploads and other ingestion sources.

The Markdown written here is the searchable corpus: changing it changes index
fingerprints and therefore belongs to a core release, not to an application.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import tempfile

EXTRACTION_METHOD_PYPDF = "pypdf"
EXTRACTION_METHOD_DOCLING = "docling"
SUPPORTED_EXTRACTION_METHODS = {EXTRACTION_METHOD_PYPDF, EXTRACTION_METHOD_DOCLING}
SPREADSHEET_SUFFIXES = {".xlsx", ".csv"}


def extract_pdf_text_with_pypdf(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader
    from .StructuredExtraction import ExtractedText

    reader = PdfReader(BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return ExtractedText("\n\n".join(page.strip() for page in pages if page.strip()), [{"title": "", "text": text, "provenance": [{"page_no": index}]} for index, text in enumerate(pages, 1) if text.strip()])


def get_docling_converter(owner):
    """Cache the converter on ``owner._docling_converter``; creating one is expensive."""
    if owner._docling_converter is None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Docling não está instalado. Adicione 'docling' às dependências do projeto."
            ) from exc
        owner._docling_converter = DocumentConverter()
    return owner._docling_converter


def extract_file_text_with_docling(owner, file_bytes: bytes, suffix: str) -> str:
    converter = get_docling_converter(owner)
    with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as temp_file:
        temp_file.write(file_bytes)
        temp_file.flush()
        temp_path = Path(temp_file.name)

    try:
        result = converter.convert(str(temp_path))
        from .StructuredExtraction import docling_text
        return docling_text(result.document)
    finally:
        temp_path.unlink(missing_ok=True)


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "document"
