"""Atomic index bundles, independently versioned from generation settings."""

import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
from zipfile import BadZipFile
import numpy as np
from .Models import Chunk

logger = logging.getLogger(__name__)
FORMAT_VERSION = 3


def fingerprint(files, settings):
    payload = {
        "version": FORMAT_VERSION,
        "files": sorted(files, key=lambda item: item["relative_path"]),
        "settings": settings,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def load_bundle(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"]))
            vectors = data["vectors"].copy()
            if meta["version"] != FORMAT_VERSION:
                raise ValueError("index format mismatch")
            chunks = [Chunk.model_validate(item) for item in meta["chunks"]]
            if len(vectors) != len(chunks) or len(meta["sparse"]) != len(chunks):
                raise ValueError("index alignment mismatch")
            checksum = hashlib.sha256(vectors.tobytes()).hexdigest()
            if checksum != meta["vectors_sha256"]:
                raise ValueError("dense checksum mismatch")
            if any(chunk.parent_id not in meta["parents"] for chunk in chunks):
                raise ValueError("missing parent")
            if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
                raise ValueError("duplicate chunk IDs")
            if any(
                not isinstance(row, dict)
                or any(not np.isfinite(weight) or weight < 0 for weight in row.values())
                for row in meta["sparse"]
            ):
                raise ValueError("invalid sparse weights")
            return chunks, meta["parents"], meta["catalog"], vectors, meta["sparse"]
    except (ValueError, KeyError, OSError, BadZipFile, TypeError) as exc:
        logger.warning("Rebuilding incompatible/corrupt V2 bundle %s: %s", path, exc)
        return None


def save_bundle(path, chunks, parents, catalog, vectors, sparse):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    vectors = np.asarray(vectors, dtype="float32")
    meta = {
        "version": FORMAT_VERSION,
        "chunks": [chunk.model_dump() for chunk in chunks],
        "parents": parents,
        "catalog": catalog,
        "sparse": sparse,
        "vectors_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, suffix=".npz", delete=False
        ) as stream:
            temporary = stream.name
            np.savez_compressed(
                stream, vectors=vectors, metadata=json.dumps(meta, ensure_ascii=False)
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()
