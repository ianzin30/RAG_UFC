import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_ROOT = PROJECT_ROOT / "application"
for path in (PROJECT_ROOT, APPLICATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from application.service.rag_service.cache import (
    build_rag_index_fingerprint,
    build_rag_index_fingerprint_inputs,
)


def build_inputs(*, quantization: str, max_length: int) -> dict:
    return build_rag_index_fingerprint_inputs(
        selected_collections=["google_drive_rag"],
        file_hashes=[{"relative_path": "google_drive_rag/doc.md", "sha256": "abc123"}],
        embedding_model_name="BAAI/bge-m3",
        embedding_quantization=quantization,
        embedding_max_length=max_length,
        splitter_config={
            "chunk_size": 500,
            "chunk_overlap": 100,
            "separators": ["\n\n", "\n", " "],
        },
        cache_version=4,
    )


def test_rag_index_fingerprint_changes_when_embedding_outputs_can_change():
    base = build_rag_index_fingerprint(build_inputs(quantization="none", max_length=1024))
    quantized = build_rag_index_fingerprint(build_inputs(quantization="4bit", max_length=1024))
    longer_context = build_rag_index_fingerprint(build_inputs(quantization="none", max_length=2048))

    assert quantized != base
    assert longer_context != base


def test_rag_index_fingerprint_inputs_do_not_track_batch_size():
    inputs = build_inputs(quantization="4bit", max_length=1024)

    assert "embedding_quantization" in inputs
    assert "embedding_max_length" in inputs
    assert "embedding_batch_size" not in inputs
