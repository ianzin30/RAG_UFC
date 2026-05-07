"""Local file upload ingestion — per-user scoped.

Handles extraction and ingest of files uploaded directly through the UI,
supporting PDFs (pypdf or docling), Office documents, spreadsheets, plain text,
and images. All extracts are saved to the user's collection directory as Markdown.
"""
import logging
from pathlib import Path

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


class LocalUploadService:
    """Extract and ingest uploaded files into the collection system.

    Accepts an optional *user_context*. When provided, files are stored under
    data/users/{uid}/collections/{collection_name}/ and metadata is recorded in
    MongoDB. When user_context is None (dev mode / auth disabled), falls back to
    the legacy global collections root.
    """

    def __init__(self, user_context=None) -> None:
        self.drive_service = GoogleDriveService()
        self._user_context = user_context
        self.collections_root = self._resolve_collections_root()

    def _resolve_collections_root(self) -> Path:
        if self._user_context is not None:
            from .storage.UserStoragePaths import collections_root_for
            return collections_root_for(self._user_context.user_id)
        return self.drive_service.collections_root

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
            return extract_spreadsheet_markdown(file_bytes=file_bytes, suffix=suffix, file_name=file_name).strip()

        if extraction_method == EXTRACTION_METHOD_PYPDF and suffix == ".pdf":
            return self.drive_service._extract_pdf_text_with_pypdf(file_bytes).strip()

        if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
            raise RuntimeError(f"Unsupported uploaded file type: {suffix or 'unknown'}")

        return self.drive_service._extract_file_text_with_docling(file_bytes, suffix).strip()

    def _record_file_in_mongo(self, *, filename: str, storage_path: str, collection_name: str) -> None:
        if self._user_context is None:
            return
        try:
            from .storage.MongoClientProvider import get_db
            from .storage.UserFileRepository import record_file
            db = get_db()
            record_file(
                db,
                user_id=self._user_context.user_id,
                filename=filename,
                original_filename=filename,
                storage_path=storage_path,
                collection_name=collection_name,
                status="indexed",
            )
        except Exception as exc:
            logger.warning("Failed to record file in MongoDB: %s", exc)

    def _mark_collection_deleted_in_mongo(self, collection_name: str) -> None:
        if self._user_context is None:
            return
        try:
            from .storage.MongoClientProvider import get_db
            from .storage.UserFileRepository import mark_collection_deleted
            mark_collection_deleted(get_db(), self._user_context.user_id, collection_name)
        except Exception as exc:
            logger.warning("Failed to mark collection deleted in MongoDB: %s", exc)

    def ingest_uploaded_files(
        self,
        uploaded_files,
        collection_name: str = "uploaded_files",
        extraction_method: str = EXTRACTION_METHOD_DOCLING,
    ) -> dict:
        collection_path = self.collections_root / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)

        # Mark all existing files in this collection as deleted before overwriting
        self._mark_collection_deleted_in_mongo(collection_name)
        for old_file in collection_path.glob("*.md"):
            old_file.unlink()

        saved_files = []
        skipped_files = []

        uid_label = self._user_context.user_id if self._user_context else "anon"

        for index, uploaded_file in enumerate(uploaded_files, start=1):
            file_name = Path(uploaded_file.name).name
            file_bytes = uploaded_file.getvalue()
            if not file_bytes:
                skipped_files.append({"name": file_name, "reason": "empty file"})
                continue

            try:
                text = self._extract_uploaded_file_text(file_name, file_bytes, extraction_method)
            except Exception as exc:
                skipped_files.append({"name": file_name, "reason": str(exc)})
                continue

            if not text:
                skipped_files.append({"name": file_name, "reason": "no text extracted"})
                continue

            safe_name = self.drive_service._safe_filename(Path(file_name).stem)
            output_path = collection_path / f"{index:02d}_{safe_name}.md"
            output_path.write_text(
                f"# {file_name}\n\nExtraction method: {extraction_method}\n\n{text}\n",
                encoding="utf-8",
            )
            self._record_file_in_mongo(
                filename=f"{index:02d}_{safe_name}.md",
                storage_path=str(output_path),
                collection_name=collection_name,
            )
            saved_files.append(
                {
                    "name": file_name,
                    "output_path": str(output_path),
                    "extraction_method": extraction_method,
                }
            )
            logger.info(
                "File uploaded — uid=%s filename=%s collection=%s",
                uid_label,
                file_name,
                collection_name,
            )

        if not saved_files:
            details = ", ".join(f"{item['name']}: {item['reason']}" for item in skipped_files) or "no supported files"
            raise RuntimeError(f"No uploaded files could be processed ({details}).")

        return {
            "collection_name": collection_name,
            "files": saved_files,
            "skipped_files": skipped_files,
        }
