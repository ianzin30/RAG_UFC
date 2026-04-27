from application.service.RuntimeConfig import (
    _normalize_embedding_device,
    _normalize_embedding_quantization,
)


def test_embedding_device_defaults_to_cpu_when_blank() -> None:
    assert _normalize_embedding_device("") == "cpu"


def test_embedding_device_accepts_gpu_alias() -> None:
    assert _normalize_embedding_device("gpu") == "cuda"


def test_embedding_device_accepts_mps() -> None:
    assert _normalize_embedding_device("mps") == "mps"


def test_embedding_quantization_defaults_to_none_when_blank() -> None:
    assert _normalize_embedding_quantization("") == "none"


def test_embedding_quantization_accepts_int8() -> None:
    assert _normalize_embedding_quantization("int8") == "int8"
