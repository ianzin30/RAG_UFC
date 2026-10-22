"""Download and text extraction helpers for the Google Drive service."""
# Simple: Extract readable text from downloaded Drive files

from __future__ import annotations

from io import BytesIO

from googleapiclient.http import MediaIoBaseDownload

# Extraction itself is core-owned so every ingestion source writes the same corpus.
from rag_ufc_core.DocumentExtraction import (  # noqa: F401 - re-exported for GoogleDriveService
    extract_file_text_with_docling,
    extract_pdf_text_with_pypdf,
    get_docling_converter,
    safe_filename,
)

from ..SpreadsheetMarkdown import extract_spreadsheet_markdown
from .Constants import EXTRACTION_METHOD_DOCLING, SPREADSHEET_SUFFIXES
from .Listing import build_docling_file_plan


# Este helper baixa o conteudo bruto de uma request do Drive para bytes em memoria.
def download_request_bytes(request) -> bytes:
    buffer = BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer.read()


# Esta chamada baixa arquivos binarios comuns do Drive.
def download_drive_file_bytes(service, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id)
    return download_request_bytes(request)


# Esta chamada exporta arquivos nativos do Google Workspace para um formato tratavel.
def export_google_workspace_file_bytes(service, file_id: str, export_mime_type: str) -> bytes:
    request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    return download_request_bytes(request)


# Este fluxo do Google Drive usa Docling em todos os arquivos suportados.
def extract_drive_file_text(owner, service, drive_file: dict, extraction_method: str) -> str:
    _ = extraction_method
    plan = build_docling_file_plan(drive_file)
    if not plan:
        raise RuntimeError(f"Tipo de arquivo não suportado pelo Docling: {drive_file.get('mimeType')}")

    if plan.mode == "export":
        file_bytes = export_google_workspace_file_bytes(service, drive_file["id"], plan.export_mime_type)
    else:
        file_bytes = download_drive_file_bytes(service, drive_file["id"])

    if plan.suffix in SPREADSHEET_SUFFIXES:
        try:
            spreadsheet_text = extract_spreadsheet_markdown(
                file_bytes=file_bytes,
                suffix=plan.suffix,
                file_name=drive_file.get("name") or "spreadsheet",
            ).strip()
            if spreadsheet_text:
                return spreadsheet_text
        except Exception:
            pass

    return extract_file_text_with_docling(owner, file_bytes, plan.suffix)
