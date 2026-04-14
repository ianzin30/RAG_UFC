"""Download and text extraction helpers for the Google Drive service."""

from __future__ import annotations

import re
import tempfile
from io import BytesIO
from pathlib import Path

from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

try:
    from ..spreadsheet_markdown import extract_spreadsheet_markdown
except ImportError:
    from spreadsheet_markdown import extract_spreadsheet_markdown

from .constants import EXTRACTION_METHOD_DOCLING, SPREADSHEET_SUFFIXES
from .listing import build_docling_file_plan


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


# Este caminho usa a camada textual do PDF quando o extrator escolhido e pypdf.
def extract_pdf_text_with_pypdf(pdf_bytes: bytes) -> str:
    buffer = BytesIO(pdf_bytes)
    reader = PdfReader(buffer)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


# Este cache evita recriar o conversor do Docling a cada arquivo.
def get_docling_converter(owner):
    if owner._docling_converter is None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Docling não está instalado. Adicione 'docling' às dependências do projeto."
            ) from exc
        owner._docling_converter = DocumentConverter()
    return owner._docling_converter


# Esta etapa envia um arquivo temporario para o Docling e devolve markdown limpo.
def extract_file_text_with_docling(owner, file_bytes: bytes, suffix: str) -> str:
    converter = get_docling_converter(owner)
    with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as temp_file:
        temp_file.write(file_bytes)
        temp_file.flush()
        temp_path = Path(temp_file.name)

    try:
        result = converter.convert(str(temp_path))
        return result.document.export_to_markdown().strip()
    finally:
        temp_path.unlink(missing_ok=True)


# Este fluxo escolhe entre planilha, Docling e pypdf conforme o arquivo e o metodo ativos.
def extract_drive_file_text(owner, service, drive_file: dict, extraction_method: str) -> str:
    if extraction_method == EXTRACTION_METHOD_DOCLING:
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

    pdf_bytes = download_drive_file_bytes(service, drive_file["id"])
    return extract_pdf_text_with_pypdf(pdf_bytes)


# Este helper sanitiza o nome do arquivo para virar nome de markdown local.
def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "document"
