"""Typed payloads used inside the Google Drive service."""
# Simple: Data structures for Google Drive file information

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoogleDrivePaths:
    credentials_file: Path
    web_credentials_file: Path
    collections_root: Path
    token_file: Path
    redirect_uri: str


@dataclass(frozen=True)
class DoclingFilePlan:
    mode: str
    suffix: str
    export_mime_type: str | None = None


@dataclass(frozen=True)
class SupportedFileListing:
    folder_name: str
    files: list[dict]
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "folder_name": self.folder_name,
            "files": self.files,
            "message": self.message,
        }


@dataclass(frozen=True)
class SavedDriveFile:
    id: str
    name: str
    mime_type: str | None
    extraction_method: str
    output_file: str | None = None
    status: str = "processed"
    source_signature: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "extraction_method": self.extraction_method,
            "output_file": self.output_file,
            "status": self.status,
            "source_signature": self.source_signature,
        }


@dataclass(frozen=True)
class CollectionIngestResult:
    collection_name: str
    folder_name: str
    extraction_method: str
    files: list[SavedDriveFile]
    checked_count: int = 0
    total_count: int = 0
    processed_count: int = 0
    cached_count: int = 0
    new_count: int = 0
    changed_count: int = 0
    deleted_count: int = 0

    def to_dict(self) -> dict:
        return {
            "collection_name": self.collection_name,
            "folder_name": self.folder_name,
            "extraction_method": self.extraction_method,
            "files": [item.to_dict() for item in self.files],
            "checked_count": self.checked_count,
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "cached_count": self.cached_count,
            "new_count": self.new_count,
            "changed_count": self.changed_count,
            "deleted_count": self.deleted_count,
        }
