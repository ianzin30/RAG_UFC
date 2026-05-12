"""Collection writing helpers for the Google Drive service."""
# Simple: Download Drive folders and save changed files locally

from __future__ import annotations

from collections import defaultdict, deque
from contextlib import suppress
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Callable

from .Constants import EXTRACTION_METHOD_DOCLING
from .Extraction import extract_drive_file_text, safe_filename
from .Listing import list_supported_files, normalize_extraction_method
from .Models import CollectionIngestResult, SavedDriveFile

ProgressCallback = Callable[[dict[str, object]], None]

DRIVE_IMPORT_MANIFEST_FILE = ".google_drive_manifest.json"
DRIVE_IMPORT_CACHE_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    processed: int,
    total: int,
    status: str,
    file_name: str | None = None,
    checked: int | None = None,
    cached: int | None = None,
    changed: int | None = None,
    new: int | None = None,
    deleted: int | None = None,
    to_process: int | None = None,
) -> None:
    if not callable(progress_callback):
        return
    payload: dict[str, object] = {
        "processed": processed,
        "total": total,
        "status": status,
        "file_name": file_name,
    }
    for key, value in {
        "checked": checked,
        "cached": cached,
        "changed": changed,
        "new": new,
        "deleted": deleted,
        "to_process": to_process,
    }.items():
        if value is not None:
            payload[key] = value
    progress_callback(payload)


def _manifest_path(collection_path: Path) -> Path:
    return collection_path / DRIVE_IMPORT_MANIFEST_FILE


def _read_manifest(collection_path: Path) -> tuple[dict, bool]:
    path = _manifest_path(collection_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"files": {}}, False
    except (OSError, json.JSONDecodeError):
        return {"files": {}}, False
    if not isinstance(payload, dict):
        return {"files": {}}, False
    if not isinstance(payload.get("files"), dict):
        payload["files"] = {}
    return payload, True


def _write_manifest(collection_path: Path, manifest: dict) -> None:
    path = _manifest_path(collection_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _source_signature(drive_file: dict, extraction_method: str) -> str:
    payload = {
        "cache_version": DRIVE_IMPORT_CACHE_VERSION,
        "extraction_method": extraction_method,
        "id": str(drive_file.get("id") or ""),
        "name": str(drive_file.get("name") or ""),
        "mimeType": str(drive_file.get("mimeType") or ""),
        "modifiedTime": str(drive_file.get("modifiedTime") or ""),
        "md5Checksum": str(drive_file.get("md5Checksum") or ""),
        "size": str(drive_file.get("size") or ""),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _manifest_entry(
    drive_file: dict,
    *,
    extraction_method: str,
    output_file: str,
    source_signature: str,
) -> dict[str, object]:
    return {
        "id": str(drive_file.get("id") or ""),
        "name": str(drive_file.get("name") or ""),
        "mime_type": drive_file.get("mimeType"),
        "modified_time": drive_file.get("modifiedTime"),
        "md5_checksum": drive_file.get("md5Checksum"),
        "size": drive_file.get("size"),
        "extraction_method": extraction_method,
        "source_signature": source_signature,
        "output_file": output_file,
        "updated_at": _now_iso(),
    }


def _saved_drive_file(
    drive_file: dict,
    *,
    extraction_method: str,
    output_file: str,
    status: str,
    source_signature: str,
) -> SavedDriveFile:
    return SavedDriveFile(
        id=str(drive_file.get("id") or ""),
        name=str(drive_file.get("name") or "arquivo"),
        mime_type=drive_file.get("mimeType"),
        extraction_method=extraction_method,
        output_file=output_file,
        status=status,
        source_signature=source_signature,
    )


def _safe_output_stem(output_file: str) -> str:
    stem = Path(output_file).stem
    match = re.match(r"^\d+[_\- ]+(?P<name>.+)$", stem)
    return match.group("name") if match else stem


def _existing_markdown_by_safe_name(collection_path: Path) -> dict[str, deque[str]]:
    matches: dict[str, deque[str]] = defaultdict(deque)
    for markdown_file in sorted(collection_path.glob("*.md"), key=lambda item: item.name.lower()):
        matches[_safe_output_stem(markdown_file.name)].append(markdown_file.name)
    return matches


def _bootstrap_manifest_from_markdown(
    *,
    collection_path: Path,
    drive_files: list[dict],
    collection_name: str,
    folder_name: str,
    extraction_method: str,
) -> dict:
    existing_by_safe_name = _existing_markdown_by_safe_name(collection_path)
    files: dict[str, dict] = {}
    for drive_file in drive_files:
        file_id = str(drive_file.get("id") or "")
        if not file_id:
            continue
        safe_name = safe_filename(Path(str(drive_file.get("name") or "arquivo")).stem)
        existing_outputs = existing_by_safe_name.get(safe_name)
        if not existing_outputs:
            continue
        output_file = existing_outputs.popleft()
        signature = _source_signature(drive_file, extraction_method)
        files[file_id] = _manifest_entry(
            drive_file,
            extraction_method=extraction_method,
            output_file=output_file,
            source_signature=signature,
        )
    return {
        "version": DRIVE_IMPORT_CACHE_VERSION,
        "collection_name": collection_name,
        "folder_name": folder_name,
        "extraction_method": extraction_method,
        "files": files,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _allocate_output_file(collection_path: Path, safe_name: str, used_output_files: set[str]) -> str:
    used_prefixes = {
        match.group("prefix")
        for output_file in used_output_files
        if (match := re.match(r"^(?P<prefix>\d+)_", output_file))
    }
    for index in range(1, 10000):
        prefix = f"{index:02d}"
        if prefix in used_prefixes:
            continue
        output_file = f"{index:02d}_{safe_name}.md"
        if output_file in used_output_files:
            continue
        if (collection_path / output_file).exists():
            used_output_files.add(output_file)
            used_prefixes.add(prefix)
            continue
        used_output_files.add(output_file)
        used_prefixes.add(prefix)
        return output_file
    raise RuntimeError("Nao foi possivel escolher um nome local para o arquivo importado.")


def _delete_stale_files(
    *,
    collection_path: Path,
    manifest_files: dict,
    current_file_ids: set[str],
) -> int:
    deleted = 0
    for file_id, entry in list(manifest_files.items()):
        if file_id in current_file_ids:
            continue
        output_file = str(entry.get("output_file") or "")
        if output_file:
            with suppress(OSError):
                (collection_path / Path(output_file).name).unlink()
        manifest_files.pop(file_id, None)
        deleted += 1
    return deleted


def _initial_used_output_files(collection_path: Path, manifest_files: dict) -> set[str]:
    used = {path.name for path in collection_path.glob("*.md")}
    for entry in manifest_files.values():
        output_file = str(entry.get("output_file") or "").strip()
        if output_file:
            used.add(Path(output_file).name)
    return used


# Esta etapa completa baixa a pasta do Drive e grava somente arquivos novos/alterados.
def ingest_folder_to_collection(
    owner,
    service,
    collections_root: Path,
    folder_name: str,
    collection_name: str,
    extraction_method: str,
    progress_callback: ProgressCallback | None = None,
) -> CollectionIngestResult:
    normalized_method = normalize_extraction_method(extraction_method)
    listing = list_supported_files(service, folder_name, normalized_method)
    if listing.message:
        raise RuntimeError(listing.message)

    if not listing.files:
        raise RuntimeError(f"Nenhum arquivo compativel com Docling encontrado na pasta '{folder_name}'.")

    collection_path = collections_root / collection_name
    collection_path.mkdir(parents=True, exist_ok=True)

    manifest, has_manifest = _read_manifest(collection_path)
    if not has_manifest:
        manifest = _bootstrap_manifest_from_markdown(
            collection_path=collection_path,
            drive_files=listing.files,
            collection_name=collection_name,
            folder_name=listing.folder_name,
            extraction_method=normalized_method,
        )
    manifest_files = manifest.setdefault("files", {})
    if not isinstance(manifest_files, dict):
        manifest_files = {}
        manifest["files"] = manifest_files

    current_file_ids = {str(drive_file.get("id") or "") for drive_file in listing.files if drive_file.get("id")}
    deleted_count = _delete_stale_files(
        collection_path=collection_path,
        manifest_files=manifest_files,
        current_file_ids=current_file_ids,
    )
    used_output_files = _initial_used_output_files(collection_path, manifest_files)

    saved_files: list[SavedDriveFile] = []
    to_process: list[tuple[dict, str, str, str, str]] = []
    total_files = len(listing.files)
    checked_count = 0
    cached_count = 0
    new_count = 0
    changed_count = 0

    _emit_progress(
        progress_callback,
        processed=0,
        total=total_files,
        status="checking",
        checked=0,
        cached=0,
        changed=0,
        new=0,
        deleted=deleted_count,
        to_process=0,
    )

    for drive_file in listing.files:
        checked_count += 1
        file_id = str(drive_file.get("id") or "")
        file_name = str(drive_file.get("name") or "arquivo")
        signature = _source_signature(drive_file, normalized_method)
        entry = manifest_files.get(file_id) if file_id else None
        output_file = str(entry.get("output_file") or "").strip() if isinstance(entry, dict) else ""
        output_file = Path(output_file).name if output_file else ""
        output_exists = bool(output_file and (collection_path / output_file).exists())

        if isinstance(entry, dict) and entry.get("source_signature") == signature and output_exists:
            cached_count += 1
            saved_files.append(
                _saved_drive_file(
                    drive_file,
                    extraction_method=normalized_method,
                    output_file=output_file,
                    status="cached",
                    source_signature=signature,
                )
            )
            _emit_progress(
                progress_callback,
                processed=0,
                total=total_files,
                status="cached",
                file_name=file_name,
                checked=checked_count,
                cached=cached_count,
                changed=changed_count,
                new=new_count,
                deleted=deleted_count,
                to_process=len(to_process),
            )
            continue

        if output_file:
            used_output_files.add(output_file)
        else:
            safe_name = safe_filename(Path(file_name).stem)
            output_file = _allocate_output_file(collection_path, safe_name, used_output_files)

        import_status = "changed" if isinstance(entry, dict) else "new"
        if import_status == "changed":
            changed_count += 1
        else:
            new_count += 1
        to_process.append((drive_file, output_file, signature, import_status, file_name))
        _emit_progress(
            progress_callback,
            processed=0,
            total=total_files,
            status="queued",
            file_name=file_name,
            checked=checked_count,
            cached=cached_count,
            changed=changed_count,
            new=new_count,
            deleted=deleted_count,
            to_process=len(to_process),
        )

    processed_count = 0
    process_total = len(to_process)
    for drive_file, output_file, signature, import_status, file_name in to_process:
        _emit_progress(
            progress_callback,
            processed=processed_count,
            total=total_files,
            status="processing",
            file_name=file_name,
            checked=checked_count,
            cached=cached_count,
            changed=changed_count,
            new=new_count,
            deleted=deleted_count,
            to_process=process_total,
        )
        text = extract_drive_file_text(owner, service, drive_file, normalized_method).strip()
        if text:
            output_path = collection_path / output_file
            output_path.write_text(
                f"# {drive_file['name']}\n\nExtraction method: {normalized_method}\n\n{text}\n",
                encoding="utf-8",
            )
            file_id = str(drive_file.get("id") or "")
            manifest_files[file_id] = _manifest_entry(
                drive_file,
                extraction_method=normalized_method,
                output_file=output_file,
                source_signature=signature,
            )
            saved_files.append(
                _saved_drive_file(
                    drive_file,
                    extraction_method=normalized_method,
                    output_file=output_file,
                    status=import_status,
                    source_signature=signature,
                )
            )
            processed_count += 1
        _emit_progress(
            progress_callback,
            processed=processed_count,
            total=total_files,
            status="processed",
            file_name=file_name,
            checked=checked_count,
            cached=cached_count,
            changed=changed_count,
            new=new_count,
            deleted=deleted_count,
            to_process=process_total,
        )

    if not saved_files:
        raise RuntimeError("Arquivos compativeis encontrados, mas nenhum conteudo pode ser extraido com Docling.")

    manifest.update(
        {
            "version": DRIVE_IMPORT_CACHE_VERSION,
            "collection_name": collection_name,
            "folder_name": listing.folder_name,
            "extraction_method": normalized_method,
            "updated_at": _now_iso(),
        }
    )
    _write_manifest(collection_path, manifest)
    _emit_progress(
        progress_callback,
        processed=processed_count,
        total=total_files,
        status="completed",
        checked=checked_count,
        cached=cached_count,
        changed=changed_count,
        new=new_count,
        deleted=deleted_count,
        to_process=process_total,
    )

    return CollectionIngestResult(
        collection_name=collection_name,
        folder_name=listing.folder_name,
        extraction_method=normalized_method,
        files=saved_files,
        checked_count=checked_count,
        total_count=total_files,
        processed_count=processed_count,
        cached_count=cached_count,
        new_count=new_count,
        changed_count=changed_count,
        deleted_count=deleted_count,
    )
