"""Collection writing helpers for the Google Drive service."""

from __future__ import annotations

from pathlib import Path

from .constants import EXTRACTION_METHOD_DOCLING
from .extraction import extract_drive_file_text, safe_filename
from .listing import list_supported_files, normalize_extraction_method
from .models import CollectionIngestResult, SavedDriveFile


# Esta etapa completa baixa a pasta do Drive e grava a colecao local em markdown usando Docling.
def ingest_folder_to_collection(
    owner,
    service,
    collections_root: Path,
    folder_name: str,
    collection_name: str,
    extraction_method: str,
) -> CollectionIngestResult:
    normalized_method = normalize_extraction_method(extraction_method)
    listing = list_supported_files(service, folder_name, normalized_method)
    if listing.message:
        raise RuntimeError(listing.message)

    if not listing.files:
        raise RuntimeError(f"Nenhum arquivo compatível com Docling encontrado na pasta '{folder_name}'.")

    collection_path = collections_root / collection_name
    collection_path.mkdir(parents=True, exist_ok=True)
    for old_file in collection_path.glob("*.md"):
        old_file.unlink()

    saved_files: list[SavedDriveFile] = []
    for index, drive_file in enumerate(listing.files, start=1):
        text = extract_drive_file_text(owner, service, drive_file, normalized_method).strip()
        if not text:
            continue

        safe_name = safe_filename(Path(drive_file["name"]).stem)
        output_path = collection_path / f"{index:02d}_{safe_name}.md"
        output_path.write_text(
            f"# {drive_file['name']}\n\nExtraction method: {normalized_method}\n\n{text}\n",
            encoding="utf-8",
        )
        saved_files.append(
            SavedDriveFile(
                id=drive_file["id"],
                name=drive_file["name"],
                mime_type=drive_file.get("mimeType"),
                extraction_method=normalized_method,
            )
        )

    if not saved_files:
        raise RuntimeError("Arquivos compatíveis encontrados, mas nenhum conteúdo pôde ser extraído com Docling.")

    return CollectionIngestResult(
        collection_name=collection_name,
        folder_name=listing.folder_name,
        extraction_method=normalized_method,
        files=saved_files,
    )
