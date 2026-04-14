"""File discovery helpers for the Google Drive service."""

from __future__ import annotations

from pathlib import Path

from .constants import (
    DOCLING_BINARY_MIME_TYPES,
    DOCLING_EXPORT_MIME_TYPES,
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_PYPDF,
    PDF_MIME_TYPE,
    SUPPORTED_EXTRACTION_METHODS,
)
from .models import DoclingFilePlan, SupportedFileListing


# Este validador fixa o Google Drive em Docling, mesmo se algum chamador pedir outro extrator.
def normalize_extraction_method(extraction_method: str | None) -> str:
    normalized = (extraction_method or EXTRACTION_METHOD_DOCLING).strip().lower()
    if normalized not in SUPPORTED_EXTRACTION_METHODS:
        supported = ", ".join(sorted(SUPPORTED_EXTRACTION_METHODS))
        raise ValueError(f"Método de extração inválido: '{extraction_method}'. Use um destes: {supported}.")
    return EXTRACTION_METHOD_DOCLING


# Esta busca localiza a pasta-alvo pelo nome dentro do Google Drive.
def find_folder(service, folder_name: str):
    query = (
        f"mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{folder_name}' and trashed = false"
    )
    result = service.files().list(q=query, fields="files(id, name)", pageSize=10).execute()
    folders = result.get("files", [])
    return folders[0] if folders else None


# Esta listagem recupera os arquivos filhos da pasta escolhida.
def list_folder_files(service, folder_id: str):
    query = f"'{folder_id}' in parents and trashed = false"
    result = service.files().list(q=query, fields="files(id, name, mimeType)", pageSize=200).execute()
    return result.get("files", [])


# Este plano decide se o arquivo sera baixado ou exportado antes da extracao.
def build_docling_file_plan(drive_file: dict) -> DoclingFilePlan | None:
    mime_type = (drive_file.get("mimeType") or "").lower()
    file_suffix = Path(drive_file.get("name") or "").suffix.lower()

    if mime_type in DOCLING_BINARY_MIME_TYPES:
        return DoclingFilePlan(
            mode="download",
            suffix=file_suffix or DOCLING_BINARY_MIME_TYPES[mime_type],
        )

    if mime_type in DOCLING_EXPORT_MIME_TYPES:
        export_mime_type, export_suffix = DOCLING_EXPORT_MIME_TYPES[mime_type]
        return DoclingFilePlan(
            mode="export",
            export_mime_type=export_mime_type,
            suffix=export_suffix,
        )

    return None


# Esta funcao filtra apenas os arquivos compatíveis com o extrator escolhido.
def list_supported_files(service, folder_name: str, extraction_method: str) -> SupportedFileListing:
    folder = find_folder(service, folder_name)
    if not folder:
        return SupportedFileListing(
            folder_name=folder_name,
            files=[],
            message=f"Pasta '{folder_name}' não encontrada.",
        )

    files = list_folder_files(service, folder["id"])
    if extraction_method == EXTRACTION_METHOD_DOCLING:
        supported_files = [drive_file for drive_file in files if build_docling_file_plan(drive_file)]
    else:
        supported_files = [drive_file for drive_file in files if drive_file.get("mimeType") == PDF_MIME_TYPE]

    return SupportedFileListing(folder_name=folder["name"], files=supported_files)
