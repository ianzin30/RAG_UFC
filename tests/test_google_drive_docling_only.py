import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_ROOT = PROJECT_ROOT / "application"
for path in (PROJECT_ROOT, APPLICATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from application.service.google_drive_support import extraction as extraction_module
from application.service.google_drive_support.constants import (
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_PYPDF,
    PDF_MIME_TYPE,
)
from application.service.google_drive_support.listing import normalize_extraction_method


def test_google_drive_extraction_method_is_forced_to_docling():
    assert normalize_extraction_method(None) == EXTRACTION_METHOD_DOCLING
    assert normalize_extraction_method(EXTRACTION_METHOD_DOCLING) == EXTRACTION_METHOD_DOCLING
    assert normalize_extraction_method(EXTRACTION_METHOD_PYPDF) == EXTRACTION_METHOD_DOCLING


def test_google_drive_text_extraction_ignores_pypdf_request(monkeypatch):
    monkeypatch.setattr(
        extraction_module,
        "build_docling_file_plan",
        lambda drive_file: SimpleNamespace(mode="download", suffix=".pdf", export_mime_type=None),
    )
    monkeypatch.setattr(extraction_module, "download_drive_file_bytes", lambda service, file_id: b"pdf-bytes")
    monkeypatch.setattr(extraction_module, "extract_file_text_with_docling", lambda owner, file_bytes, suffix: "docling-text")

    def fail_if_called(pdf_bytes):
        raise AssertionError("Google Drive extraction should not call PyPDF.")

    monkeypatch.setattr(extraction_module, "extract_pdf_text_with_pypdf", fail_if_called)

    text = extraction_module.extract_drive_file_text(
        owner=object(),
        service=object(),
        drive_file={"id": "file-1", "name": "AFO.pdf", "mimeType": PDF_MIME_TYPE},
        extraction_method=EXTRACTION_METHOD_PYPDF,
    )

    assert text == "docling-text"
