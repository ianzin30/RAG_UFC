import json
from pathlib import Path

from application.service.google_drive import Ingestion, Listing
from application.service.google_drive.Models import SupportedFileListing


def _drive_file(
    file_id: str,
    name: str,
    *,
    modified_time: str = "2026-05-12T12:00:00.000Z",
    checksum: str = "checksum",
    size: str = "123",
) -> dict:
    return {
        "id": file_id,
        "name": name,
        "mimeType": "application/pdf",
        "modifiedTime": modified_time,
        "md5Checksum": checksum,
        "size": size,
    }


def _patch_listing(monkeypatch, files: list[dict]) -> None:
    monkeypatch.setattr(
        Ingestion,
        "list_supported_files",
        lambda service, folder_name, extraction_method: SupportedFileListing(
            folder_name="rag",
            files=files,
        ),
    )


def _manifest_path(collection_path: Path) -> Path:
    return collection_path / Ingestion.DRIVE_IMPORT_MANIFEST_FILE


def test_incremental_import_skips_unchanged_manifest_entry(monkeypatch, tmp_path):
    drive_file = _drive_file("file-1", "Ata.pdf")
    signature = Ingestion._source_signature(drive_file, "docling")
    collection_path = tmp_path / "collections" / "google_drive_rag"
    collection_path.mkdir(parents=True)
    output_path = collection_path / "01_Ata.md"
    output_path.write_text("# Ata.pdf\n\ncached", encoding="utf-8")
    _manifest_path(collection_path).write_text(
        json.dumps(
            {
                "version": Ingestion.DRIVE_IMPORT_CACHE_VERSION,
                "files": {
                    "file-1": {
                        "source_signature": signature,
                        "output_file": "01_Ata.md",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    _patch_listing(monkeypatch, [drive_file])
    monkeypatch.setattr(
        Ingestion,
        "extract_drive_file_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unchanged file should not extract")),
    )

    progress = []
    result = Ingestion.ingest_folder_to_collection(
        owner=object(),
        service=object(),
        collections_root=tmp_path / "collections",
        folder_name="rag",
        collection_name="google_drive_rag",
        extraction_method="docling",
        progress_callback=progress.append,
    ).to_dict()

    assert output_path.read_text(encoding="utf-8") == "# Ata.pdf\n\ncached"
    assert result["processed_count"] == 0
    assert result["cached_count"] == 1
    assert result["files"][0]["status"] == "cached"
    assert progress[-1]["status"] == "completed"
    assert progress[-1]["cached"] == 1


def test_incremental_import_bootstraps_existing_markdown_without_manifest(monkeypatch, tmp_path):
    drive_file = _drive_file("file-1", "Ata.pdf")
    collection_path = tmp_path / "collections" / "google_drive_rag"
    collection_path.mkdir(parents=True)
    output_path = collection_path / "57_Ata.md"
    output_path.write_text("# Ata.pdf\n\ncached", encoding="utf-8")
    _patch_listing(monkeypatch, [drive_file])
    monkeypatch.setattr(
        Ingestion,
        "extract_drive_file_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("bootstrapped file should not extract")),
    )

    result = Ingestion.ingest_folder_to_collection(
        owner=object(),
        service=object(),
        collections_root=tmp_path / "collections",
        folder_name="rag",
        collection_name="google_drive_rag",
        extraction_method="docling",
    ).to_dict()

    manifest = json.loads(_manifest_path(collection_path).read_text(encoding="utf-8"))
    assert result["processed_count"] == 0
    assert result["cached_count"] == 1
    assert result["files"][0]["output_file"] == "57_Ata.md"
    assert manifest["files"]["file-1"]["output_file"] == "57_Ata.md"


def test_incremental_import_changed_file_overwrites_stable_output(monkeypatch, tmp_path):
    drive_file = _drive_file("file-1", "Ata.pdf", checksum="new-checksum")
    collection_path = tmp_path / "collections" / "google_drive_rag"
    collection_path.mkdir(parents=True)
    output_path = collection_path / "01_Ata.md"
    output_path.write_text("# Ata.pdf\n\nold", encoding="utf-8")
    _manifest_path(collection_path).write_text(
        json.dumps({"files": {"file-1": {"source_signature": "old", "output_file": "01_Ata.md"}}}),
        encoding="utf-8",
    )
    _patch_listing(monkeypatch, [drive_file])
    monkeypatch.setattr(Ingestion, "extract_drive_file_text", lambda *args, **kwargs: "new extracted text")

    result = Ingestion.ingest_folder_to_collection(
        owner=object(),
        service=object(),
        collections_root=tmp_path / "collections",
        folder_name="rag",
        collection_name="google_drive_rag",
        extraction_method="docling",
    ).to_dict()

    assert result["processed_count"] == 1
    assert result["changed_count"] == 1
    assert result["files"][0]["status"] == "changed"
    assert "new extracted text" in output_path.read_text(encoding="utf-8")


def test_incremental_import_new_file_gets_next_available_output(monkeypatch, tmp_path):
    drive_file = _drive_file("file-2", "Novo.pdf")
    collection_path = tmp_path / "collections" / "google_drive_rag"
    collection_path.mkdir(parents=True)
    (collection_path / "01_Ata.md").write_text("# Ata\n\ncached", encoding="utf-8")
    _manifest_path(collection_path).write_text(json.dumps({"files": {}}), encoding="utf-8")
    _patch_listing(monkeypatch, [drive_file])
    monkeypatch.setattr(Ingestion, "extract_drive_file_text", lambda *args, **kwargs: "new text")

    result = Ingestion.ingest_folder_to_collection(
        owner=object(),
        service=object(),
        collections_root=tmp_path / "collections",
        folder_name="rag",
        collection_name="google_drive_rag",
        extraction_method="docling",
    ).to_dict()

    assert result["new_count"] == 1
    assert result["files"][0]["output_file"] == "02_Novo.md"
    assert (collection_path / "02_Novo.md").exists()


def test_incremental_import_deletes_manifest_entries_removed_from_drive(monkeypatch, tmp_path):
    drive_file = _drive_file("file-1", "Ata.pdf")
    signature = Ingestion._source_signature(drive_file, "docling")
    collection_path = tmp_path / "collections" / "google_drive_rag"
    collection_path.mkdir(parents=True)
    (collection_path / "01_Ata.md").write_text("# Ata\n\ncached", encoding="utf-8")
    stale_path = collection_path / "02_Removido.md"
    stale_path.write_text("# Removido\n\nold", encoding="utf-8")
    _manifest_path(collection_path).write_text(
        json.dumps(
            {
                "files": {
                    "file-1": {"source_signature": signature, "output_file": "01_Ata.md"},
                    "file-2": {"source_signature": "old", "output_file": "02_Removido.md"},
                }
            }
        ),
        encoding="utf-8",
    )
    _patch_listing(monkeypatch, [drive_file])
    monkeypatch.setattr(
        Ingestion,
        "extract_drive_file_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unchanged file should not extract")),
    )

    result = Ingestion.ingest_folder_to_collection(
        owner=object(),
        service=object(),
        collections_root=tmp_path / "collections",
        folder_name="rag",
        collection_name="google_drive_rag",
        extraction_method="docling",
    ).to_dict()

    manifest = json.loads(_manifest_path(collection_path).read_text(encoding="utf-8"))
    assert result["deleted_count"] == 1
    assert not stale_path.exists()
    assert "file-2" not in manifest["files"]


def test_list_folder_files_requests_change_metadata():
    captured = {}

    class FakeRequest:
        def execute(self):
            return {"files": []}

    class FakeFiles:
        def list(self, **kwargs):
            captured.update(kwargs)
            return FakeRequest()

    class FakeService:
        def files(self):
            return FakeFiles()

    Listing.list_folder_files(FakeService(), "folder-id")

    assert "modifiedTime" in captured["fields"]
    assert "md5Checksum" in captured["fields"]
    assert "size" in captured["fields"]
