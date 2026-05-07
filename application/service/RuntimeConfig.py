"""Shared runtime configuration for the application.

This module centralizes two config sources:
- the project-root `.env` for secrets and machine-specific credentials
- `config/config.toml` for non-secret runtime tuning
"""
# Simple: Load and manage settings from configuration files

from __future__ import annotations

try:
    import tomllib
except ImportError:
    import tomli as tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_FILE = PROJECT_ROOT / "config" / "config.toml"

_ENV_LOADED = False


@dataclass(frozen=True)
class EmbeddingRuntimeConfig:
    model_name: str
    device: str
    quantization: str
    batch_size: int
    max_length: int


@dataclass(frozen=True)
class SplitterRuntimeConfig:
    chunk_size: int
    chunk_overlap: int
    separators: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalRuntimeConfig:
    base_search_k: int
    base_fetch_k: int
    base_lambda_mult: float
    lexical_limit: int
    candidate_pool_limit: int
    llm_selection_limit: int
    llm_selector_enabled: bool


@dataclass(frozen=True)
class RagRuntimeConfig:
    agent_mode: str
    strict_grounding: bool
    min_evidence_score: float


@dataclass(frozen=True)
class GenerationRuntimeConfig:
    temperature: float
    top_p: float
    repeat_penalty: float
    seed: int | None
    num_ctx: int | None


@dataclass(frozen=True)
class LLMModelRuntimeOption:
    label: str
    model_name: str


@dataclass(frozen=True)
class AppRuntimeConfig:
    ufc_model_name: str
    embedding: EmbeddingRuntimeConfig
    splitter: SplitterRuntimeConfig
    retrieval: RetrievalRuntimeConfig
    rag: RagRuntimeConfig
    generation: GenerationRuntimeConfig
    llm_model_options: tuple[LLMModelRuntimeOption, ...] = ()


def load_project_environment() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    _ENV_LOADED = True


def _read_config_document() -> dict[str, Any]:
    load_project_environment()
    if not CONFIG_FILE.exists():
        raise RuntimeError(
            "Missing config/config.toml. Create it and use it for runtime tuning such as model, "
            "embedding device, batch size, and context length."
        )

    with CONFIG_FILE.open("rb") as config_file:
        payload = tomllib.load(config_file)
    if not isinstance(payload, dict):
        raise RuntimeError("Invalid config/config.toml: expected a TOML document with tables.")
    return payload


def _require_table(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Missing or invalid [{key}] table in config/config.toml.")
    return value


def _get_optional_table(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _require_str(table: dict[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Missing {label} in config/config.toml.")
    return value.strip()


def _get_optional_str(table: dict[str, Any], key: str, default: str) -> str:
    value = table.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _require_positive_int(table: dict[str, Any], key: str, label: str) -> int:
    value = table.get(key)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid {label} in config/config.toml: expected a positive integer.") from exc
    if parsed <= 0:
        raise RuntimeError(f"Invalid {label} in config/config.toml: expected a positive integer.")
    return parsed


def _get_positive_int(table: dict[str, Any], key: str, default: int) -> int:
    value = table.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _get_optional_int(table: dict[str, Any], key: str) -> int | None:
    value = table.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_float(table: dict[str, Any], key: str, default: float) -> float:
    value = table.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_string_list(table: dict[str, Any], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = table.get(key)
    if not isinstance(value, list):
        return default
    normalized_items = [str(item) for item in value]
    return tuple(normalized_items) if normalized_items else default


def _normalize_embedding_device(device: str) -> str:
    normalized = (device or "cpu").strip().lower()
    if normalized == "gpu":
        return "cuda"
    if normalized in {"cuda", "cpu", "mps"}:
        return normalized
    raise RuntimeError(f"Unsupported embedding device '{device}'. Use 'cuda', 'mps', or 'cpu'.")


def _normalize_embedding_quantization(quantization: str) -> str:
    normalized = (quantization or "none").strip().lower()
    if not normalized:
        return "none"
    if normalized in {"none", "4bit", "int8"}:
        return normalized
    raise RuntimeError(
        f"Unsupported embedding quantization '{quantization}'. Use 'none', '4bit', or 'int8'."
    )


def _get_llm_model_options(table: dict[str, Any], default_model_name: str) -> tuple[LLMModelRuntimeOption, ...]:
    raw_options = table.get("options")
    options: list[LLMModelRuntimeOption] = []
    seen_models: set[str] = set()

    if isinstance(raw_options, list):
        for raw_option in raw_options:
            if not isinstance(raw_option, dict):
                continue
            model_name = str(raw_option.get("model_name") or "").strip()
            if not model_name or model_name in seen_models:
                continue
            label = str(raw_option.get("label") or "").strip() or model_name
            seen_models.add(model_name)
            options.append(LLMModelRuntimeOption(label=label, model_name=model_name))

    if default_model_name and default_model_name not in seen_models:
        options.insert(0, LLMModelRuntimeOption(label=default_model_name, model_name=default_model_name))

    return tuple(options)


@lru_cache(maxsize=1)
def get_runtime_config() -> AppRuntimeConfig:
    payload = _read_config_document()
    model_table = _require_table(payload, "model")
    llm_models_table = _get_optional_table(payload, "llm_models")
    embeddings_table = _require_table(payload, "embeddings")
    splitter_table = _get_optional_table(payload, "splitter")
    retrieval_table = _get_optional_table(payload, "retrieval")
    rag_table = _require_table(payload, "rag")
    generation_table = _get_optional_table(payload, "generation")

    default_model_name = _require_str(model_table, "ufc_model_name", "model.ufc_model_name")

    return AppRuntimeConfig(
        ufc_model_name=default_model_name,
        llm_model_options=_get_llm_model_options(llm_models_table, default_model_name),
        embedding=EmbeddingRuntimeConfig(
            model_name=_require_str(embeddings_table, "model_name", "embeddings.model_name"),
            device=_normalize_embedding_device(
                _get_optional_str(embeddings_table, "device", "cpu")
            ),
            quantization=_normalize_embedding_quantization(
                _get_optional_str(embeddings_table, "quantization", "none")
            ),
            batch_size=_require_positive_int(
                embeddings_table, "batch_size", "embeddings.batch_size"
            ),
            max_length=_require_positive_int(
                embeddings_table, "max_length", "embeddings.max_length"
            ),
        ),
        splitter=SplitterRuntimeConfig(
            chunk_size=_get_positive_int(splitter_table, "chunk_size", 500),
            chunk_overlap=_get_positive_int(splitter_table, "chunk_overlap", 100),
            separators=_get_string_list(
                splitter_table,
                "separators",
                ("\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""),
            ),
        ),
        retrieval=RetrievalRuntimeConfig(
            base_search_k=_get_positive_int(retrieval_table, "base_search_k", 6),
            base_fetch_k=_get_positive_int(retrieval_table, "base_fetch_k", 30),
            base_lambda_mult=_get_float(retrieval_table, "base_lambda_mult", 0.2),
            lexical_limit=_get_positive_int(retrieval_table, "lexical_limit", 12),
            candidate_pool_limit=_get_positive_int(retrieval_table, "candidate_pool_limit", 30),
            llm_selection_limit=_get_positive_int(retrieval_table, "llm_selection_limit", 8),
            llm_selector_enabled=_coerce_bool(
                retrieval_table.get("llm_selector_enabled"),
                default=True,
            ),
        ),
        rag=RagRuntimeConfig(
            agent_mode=_get_optional_str(rag_table, "agent_mode", "crewai").lower() or "crewai",
            strict_grounding=_coerce_bool(
                rag_table.get("strict_grounding"),
                default=True,
            ),
            min_evidence_score=max(0.0, _get_float(rag_table, "min_evidence_score", 0.22)),
        ),
        generation=GenerationRuntimeConfig(
            temperature=max(0.0, _get_float(generation_table, "temperature", 0.0)),
            top_p=max(0.0, min(1.0, _get_float(generation_table, "top_p", 0.9))),
            repeat_penalty=max(0.0, _get_float(generation_table, "repeat_penalty", 1.05)),
            seed=_get_optional_int(generation_table, "seed"),
            num_ctx=_get_optional_int(generation_table, "num_ctx"),
        ),
    )


def reset_runtime_config_cache() -> None:
    get_runtime_config.cache_clear()


__all__ = [
    "AppRuntimeConfig",
    "CONFIG_FILE",
    "ENV_FILE",
    "EmbeddingRuntimeConfig",
    "GenerationRuntimeConfig",
    "LLMModelRuntimeOption",
    "PROJECT_ROOT",
    "RagRuntimeConfig",
    "RetrievalRuntimeConfig",
    "SplitterRuntimeConfig",
    "get_runtime_config",
    "load_project_environment",
    "reset_runtime_config_cache",
]
