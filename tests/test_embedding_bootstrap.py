from pathlib import Path
from types import SimpleNamespace

from application.service.rag.parts.Bootstrap import (
    CPU_INT8_INVALID_MARKER_FILE_NAME,
    RAGServiceBootstrapMixin,
    _EMBEDDING_INSTANCE_CACHE,
)


def test_build_embedding_settings_uses_cpu_int8_onnx_model(monkeypatch) -> None:
    harness = object.__new__(RAGServiceBootstrapMixin)
    harness.embedding_batch_size = 2
    harness.embedding_quantization = "int8"
    harness.embedding_device = "cpu"
    harness.embedding_model_name = "BAAI/bge-m3"
    fake_model_path = Path("/tmp/embedding-model")
    monkeypatch.setattr(
        harness,
        "_ensure_cpu_int8_embedding_model",
        lambda: (fake_model_path, "onnx/model_qint8_arm64.onnx"),
    )

    model_name, model_kwargs, encode_kwargs = harness._build_embedding_settings()

    assert model_name == str(fake_model_path)
    assert model_kwargs == {
        "backend": "onnx",
        "model_kwargs": {
            "provider": "CPUExecutionProvider",
            "file_name": "onnx/model_qint8_arm64.onnx",
        },
    }
    assert encode_kwargs == {"batch_size": 2}


def test_build_embedding_settings_falls_back_when_cpu_int8_export_fails(monkeypatch) -> None:
    harness = object.__new__(RAGServiceBootstrapMixin)
    harness.embedding_batch_size = 2
    harness.embedding_quantization = "int8"
    harness.embedding_device = "cpu"
    harness.embedding_model_name = "BAAI/bge-m3"

    def fail_export():
        raise RuntimeError("onnx export failed")

    monkeypatch.setattr(harness, "_ensure_cpu_int8_embedding_model", fail_export)

    model_name, model_kwargs, encode_kwargs = harness._build_embedding_settings()

    assert model_name == "BAAI/bge-m3"
    assert model_kwargs == {"device": "cpu"}
    assert encode_kwargs == {"batch_size": 2}
    assert harness.embedding_quantization == "none"


def test_build_huggingface_embeddings_falls_back_when_cpu_int8_load_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _EMBEDDING_INSTANCE_CACHE.clear()
    harness = object.__new__(RAGServiceBootstrapMixin)
    harness.embedding_batch_size = 2
    harness.embedding_quantization = "int8"
    harness.embedding_device = "cpu"
    harness.embedding_model_name = "BAAI/bge-m3"
    harness.embedding_max_length = 1024
    harness.embedding_model_cache_root = tmp_path
    created_models: list[tuple[str, dict, dict]] = []
    fake_int8_path = Path("/tmp/embedding-model")
    monkeypatch.setattr(
        harness,
        "_ensure_cpu_int8_embedding_model",
        lambda: (fake_int8_path, "onnx/model_qint8_arm64.onnx"),
    )

    class FakeEmbeddings:
        def __init__(self, *, model_name, model_kwargs, encode_kwargs):
            created_models.append((model_name, model_kwargs, encode_kwargs))
            if model_name == str(fake_int8_path):
                raise RuntimeError("invalid onnx cache")
            self._client = SimpleNamespace(max_seq_length=None)

    monkeypatch.setattr(
        "application.service.rag.parts.Bootstrap.HuggingFaceEmbeddings",
        FakeEmbeddings,
    )

    embeddings = harness._build_huggingface_embeddings()

    assert created_models == [
        (
            str(fake_int8_path),
            {
                "backend": "onnx",
                "model_kwargs": {
                    "provider": "CPUExecutionProvider",
                    "file_name": "onnx/model_qint8_arm64.onnx",
                },
            },
            {"batch_size": 2},
        ),
        ("BAAI/bge-m3", {"device": "cpu"}, {"batch_size": 2}),
    ]
    assert harness.embedding_quantization == "none"
    assert embeddings._client.max_seq_length == 1024


def test_cpu_int8_invalid_marker_skips_reloading_bad_onnx_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = object.__new__(RAGServiceBootstrapMixin)
    harness.embedding_model_name = "BAAI/bge-m3"
    harness.embedding_model_cache_root = tmp_path
    monkeypatch.setattr("application.service.rag.parts.Bootstrap.platform.machine", lambda: "arm64")
    marker_path = (
        tmp_path
        / "BAAI--bge-m3"
        / "onnx-int8-arm64"
        / CPU_INT8_INVALID_MARKER_FILE_NAME
    )
    marker_path.parent.mkdir(parents=True)
    marker_path.write_text("invalid", encoding="utf-8")

    try:
        harness._ensure_cpu_int8_embedding_model()
    except RuntimeError as exc:
        assert "disabled after a previous ONNX load failure" in str(exc)
    else:
        raise AssertionError("Expected invalid int8 marker to skip ONNX loading.")


def test_huggingface_embeddings_are_reused_in_process(monkeypatch) -> None:
    _EMBEDDING_INSTANCE_CACHE.clear()
    harness = object.__new__(RAGServiceBootstrapMixin)
    harness.embedding_batch_size = 2
    harness.embedding_quantization = "none"
    harness.embedding_device = "cpu"
    harness.embedding_model_name = "BAAI/bge-m3"
    harness.embedding_max_length = 1024
    created_models: list[str] = []

    class FakeEmbeddings:
        def __init__(self, *, model_name, model_kwargs, encode_kwargs):
            created_models.append(model_name)
            self._client = SimpleNamespace(max_seq_length=None)

    monkeypatch.setattr(
        "application.service.rag.parts.Bootstrap.HuggingFaceEmbeddings",
        FakeEmbeddings,
    )

    first_embeddings = harness._build_huggingface_embeddings()
    second_embeddings = harness._build_huggingface_embeddings()

    assert first_embeddings is second_embeddings
    assert created_models == ["BAAI/bge-m3"]


def test_resolve_cpu_int8_quantization_target_uses_arm64(monkeypatch) -> None:
    harness = object.__new__(RAGServiceBootstrapMixin)
    monkeypatch.setattr("application.service.rag.parts.Bootstrap.platform.machine", lambda: "arm64")

    assert harness._resolve_cpu_int8_quantization_target() == "arm64"
