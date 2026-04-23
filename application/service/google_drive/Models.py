"""Typed payloads used inside the Google Drive service."""
# Simple: Data structures for Google Drive file information

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoogleDrivePaths:
    credentials_file: Path
    collections_root: Path


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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "extraction_method": self.extraction_method,
        }


@dataclass(frozen=True)
class CollectionIngestResult:
    collection_name: str
    folder_name: str
    extraction_method: str
    files: list[SavedDriveFile]

    def to_dict(self) -> dict:
        return {
            "collection_name": self.collection_name,
            "folder_name": self.folder_name,
            "extraction_method": self.extraction_method,
            "files": [item.to_dict() for item in self.files],
        }
