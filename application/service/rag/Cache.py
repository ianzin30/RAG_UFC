"""Cache fingerprinting for FAISS indices.

Tracks file hashes, embedding model config, and splitter settings to invalidate
indices when source documents or configuration change, avoiding stale embeddings.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RAG_INDEX_MANIFEST_FILE_NAME = "manifest.json"


def build_file_hash_record(file_path: Path, relative_to: Path) -> dict[str, str]:
    return {
        "relative_path": file_path.relative_to(relative_to).as_posix(),
        "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
    }


def build_rag_index_fingerprint_inputs(
    *,
    selected_collections: list[str],
    file_hashes: list[dict[str, str]],
    embedding_model_name: str,
    embedding_quantization: str,
    embedding_max_length: int,
    splitter_config: dict[str, Any],
    cache_version: int | str,
) -> dict[str, Any]:
    normalized_files = sorted(
        [
            {
                "relative_path": str(item["relative_path"]),
                "sha256": str(item["sha256"]),
            }
            for item in file_hashes
        ],
        key=lambda item: item["relative_path"],
    )
    normalized_splitter = {
        "chunk_size": int(splitter_config.get("chunk_size") or 0),
        "chunk_overlap": int(splitter_config.get("chunk_overlap") or 0),
        "separators": [str(item) for item in (splitter_config.get("separators") or [])],
    }
    return {
        "selected_collections": [str(item) for item in selected_collections],
        "files": normalized_files,
        "embedding_model_name": str(embedding_model_name or ""),
        "embedding_quantization": str(embedding_quantization or ""),
        "embedding_max_length": int(embedding_max_length or 0),
        "splitter": normalized_splitter,
        "cache_version": cache_version,
    }


def build_rag_index_fingerprint(fingerprint_inputs: dict[str, Any]) -> str:
    serialized = json.dumps(
        fingerprint_inputs,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_rag_index_cache_dir(cache_root: Path, fingerprint: str) -> Path:
    return cache_root / fingerprint


def read_rag_index_manifest(cache_dir: Path) -> dict[str, Any] | None:
    manifest_path = cache_dir / RAG_INDEX_MANIFEST_FILE_NAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def write_rag_index_manifest(cache_dir: Path, manifest: dict[str, Any]) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / RAG_INDEX_MANIFEST_FILE_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path
