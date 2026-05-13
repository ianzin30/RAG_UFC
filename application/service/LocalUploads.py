"""Local file upload ingestion for the shared collections root.

Handles extraction and ingest of files uploaded directly through the UI,
supporting PDFs (pypdf or docling), Office documents, spreadsheets, plain text,
and images. All extracts are saved under data/collections as Markdown.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .GoogleDrive import (
    EXTRACTION_METHOD_DOCLING,
    EXTRACTION_METHOD_PYPDF,
    GoogleDriveService,
    SPREADSHEET_SUFFIXES,
)
from .SpreadsheetMarkdown import extract_spreadsheet_markdown

logger = logging.getLogger("ragufc.storage")

PLAIN_TEXT_SUFFIXES = {".md", ".txt"}
SUPPORTED_UPLOAD_SUFFIXES = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".csv",
    ".md",
    ".txt",
    ".html",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tiff",
    ".bmp",
}

UploadProgressCallback = Callable[[dict[str, object]], None]


def _next_output_path(collection_path: Path, safe_name: str, start_index: int) -> Path:
    index = max(1, start_index)
    while True:
        output_path = collection_path / f"{index:02d}_{safe_name}.md"
        if not output_path.exists():
            return output_path
        index += 1


def _emit_upload_progress(
    progress_callback: UploadProgressCallback | None,
    *,
    status: str,
    processed: int,
    total: int,
    file_name: str | None = None,
    saved: int = 0,
    skipped: int = 0,
    reason: str | None = None,
) -> None:
    if not callable(progress_callback):
        return
    progress_callback(
        {
            "status": status,
            "processed": processed,
            "total": total,
            "file_name": file_name,
            "saved": saved,
            "skipped": skipped,
            "reason": reason,
        }
    )


class LocalUploadService:
    """Extract and ingest uploaded files into the shared collection system."""

    def __init__(self) -> None:
        self.drive_service = GoogleDriveService()
        self.collections_root = self.drive_service.collections_root

    def _decode_text_bytes(self, file_bytes: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="ignore")

    def _extract_uploaded_file_text(self, file_name: str, file_bytes: bytes, extraction_method: str) -> str:
        suffix = Path(file_name).suffix.lower()

        if suffix in PLAIN_TEXT_SUFFIXES:
            return self._decode_text_bytes(file_bytes).strip()

        if suffix in SPREADSHEET_SUFFIXES:
            return extract_spreadsheet_markdown(
                file_bytes=file_bytes,
                suffix=suffix,
                file_name=file_name,
            ).strip()

        if extraction_method == EXTRACTION_METHOD_PYPDF and suffix == ".pdf":
            return self.drive_service._extract_pdf_text_with_pypdf(file_bytes).strip()

        if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
            raise RuntimeError(f"Unsupported uploaded file type: {suffix or 'unknown'}")

        return self.drive_service._extract_file_text_with_docling(file_bytes, suffix).strip()

    def ingest_uploaded_files(
        self,
        uploaded_files,
        collection_name: str = "uploaded_files",
        extraction_method: str = EXTRACTION_METHOD_DOCLING,
        progress_callback: UploadProgressCallback | None = None,
    ) -> dict:
        collection_path = self.collections_root / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        skipped_files = []
        uploaded_files = list(uploaded_files or [])
        total_files = len(uploaded_files)
        next_index = len(list(collection_path.glob("*.md"))) + 1

        _emit_upload_progress(
            progress_callback,
            status="queued",
            processed=0,
            total=total_files,
        )

        for index, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = Path(uploaded_file.name).name
            file_bytes = uploaded_file.getvalue()
            if not file_bytes:
                reason = "empty file"
                skipped_files.append({"name": file_name, "reason": reason})
                _emit_upload_progress(
                    progress_callback,
                    status="skipped",
                    processed=index,
                    total=total_files,
                    file_name=file_name,
                    saved=len(saved_files),
                    skipped=len(skipped_files),
                    reason=reason,
                )
                continue

            _emit_upload_progress(
                progress_callback,
                status="extracting",
                processed=index - 1,
                total=total_files,
                file_name=file_name,
                saved=len(saved_files),
                skipped=len(skipped_files),
            )
            try:
                text = self._extract_uploaded_file_text(file_name, file_bytes, extraction_method)
            except Exception as exc:
                reason = str(exc)
                skipped_files.append({"name": file_name, "reason": reason})
                _emit_upload_progress(
                    progress_callback,
                    status="skipped",
                    processed=index,
                    total=total_files,
                    file_name=file_name,
                    saved=len(saved_files),
                    skipped=len(skipped_files),
                    reason=reason,
                )
                continue

            if not text:
                reason = "no text extracted"
                skipped_files.append({"name": file_name, "reason": reason})
                _emit_upload_progress(
                    progress_callback,
                    status="skipped",
                    processed=index,
                    total=total_files,
                    file_name=file_name,
                    saved=len(saved_files),
                    skipped=len(skipped_files),
                    reason=reason,
                )
                continue

            safe_name = self.drive_service._safe_filename(Path(file_name).stem)
            output_path = _next_output_path(collection_path, safe_name, next_index)
            next_index = int(output_path.name.split("_", 1)[0]) + 1
            output_path.write_text(
                f"# {file_name}\n\nExtraction method: {extraction_method}\n\n{text}\n",
                encoding="utf-8",
            )
            saved_files.append(
                {
                    "name": file_name,
                    "output_path": str(output_path),
                    "extraction_method": extraction_method,
                }
            )
            logger.info("File uploaded - filename=%s collection=%s", file_name, collection_name)
            _emit_upload_progress(
                progress_callback,
                status="saved",
                processed=index,
                total=total_files,
                file_name=file_name,
                saved=len(saved_files),
                skipped=len(skipped_files),
            )

        if not saved_files:
            details = ", ".join(f"{item['name']}: {item['reason']}" for item in skipped_files) or "no supported files"
            _emit_upload_progress(
                progress_callback,
                status="error",
                processed=total_files,
                total=total_files,
                saved=len(saved_files),
                skipped=len(skipped_files),
                reason=details,
            )
            raise RuntimeError(f"No uploaded files could be processed ({details}).")

        _emit_upload_progress(
            progress_callback,
            status="completed",
            processed=total_files,
            total=total_files,
            saved=len(saved_files),
            skipped=len(skipped_files),
        )

        return {
            "collection_name": collection_name,
            "files": saved_files,
            "skipped_files": skipped_files,
        }
