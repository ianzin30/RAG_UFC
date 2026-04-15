"""Shared runtime configuration for the application.

This module centralizes two config sources:
- the project-root `.env` for secrets and machine-specific credentials
- `config/config.toml` for non-secret runtime tuning
"""

from __future__ import annotations

import tomllib
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
    focused_search_k: int
    focused_fetch_k: int
    focused_lambda_mult: float
    lexical_limit: int
    coverage_limit: int
    context_default_limit: int
    context_diverse_limit: int
    context_summary_limit: int


@dataclass(frozen=True)
class AggregationRuntimeConfig:
    topics_limit: int
    names_limit: int
    list_extraction_names_limit: int
    dates_limit: int
    money_values_limit: int
    fact_lines_limit: int
    key_points_limit: int


@dataclass(frozen=True)
class RagRuntimeConfig:
    agent_mode: str
    strict_grounding: bool
    min_evidence_score: float


@dataclass(frozen=True)
class AppRuntimeConfig:
    ufc_model_name: str
    embedding: EmbeddingRuntimeConfig
    splitter: SplitterRuntimeConfig
    retrieval: RetrievalRuntimeConfig
    aggregation: AggregationRuntimeConfig
    rag: RagRuntimeConfig


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
    normalized = (device or "cuda").strip().lower()
    if normalized == "gpu":
        return "cuda"
    if normalized in {"cuda", "cpu"}:
        return normalized
    raise RuntimeError(f"Unsupported embedding device '{device}'. Use 'cuda' or 'cpu'.")


def _normalize_embedding_quantization(quantization: str) -> str:
    normalized = (quantization or "none").strip().lower()
    if not normalized:
        return "none"
    if normalized in {"none", "4bit"}:
        return normalized
    raise RuntimeError(
        f"Unsupported embedding quantization '{quantization}'. Use 'none' or '4bit'."
    )


@lru_cache(maxsize=1)
def get_runtime_config() -> AppRuntimeConfig:
    payload = _read_config_document()
    model_table = _require_table(payload, "model")
    embeddings_table = _require_table(payload, "embeddings")
    splitter_table = _get_optional_table(payload, "splitter")
    retrieval_table = _get_optional_table(payload, "retrieval")
    aggregation_table = _get_optional_table(payload, "aggregation")
    rag_table = _require_table(payload, "rag")

    return AppRuntimeConfig(
        ufc_model_name=_require_str(model_table, "ufc_model_name", "model.ufc_model_name"),
        embedding=EmbeddingRuntimeConfig(
            model_name=_require_str(embeddings_table, "model_name", "embeddings.model_name"),
            device=_normalize_embedding_device(
                _get_optional_str(embeddings_table, "device", "cuda")
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
            focused_search_k=_get_positive_int(retrieval_table, "focused_search_k", 6),
            focused_fetch_k=_get_positive_int(retrieval_table, "focused_fetch_k", 100),
            focused_lambda_mult=_get_float(retrieval_table, "focused_lambda_mult", 0.2),
            lexical_limit=_get_positive_int(retrieval_table, "lexical_limit", 12),
            coverage_limit=_get_positive_int(retrieval_table, "coverage_limit", 10),
            context_default_limit=_get_positive_int(retrieval_table, "context_default_limit", 6),
            context_diverse_limit=_get_positive_int(retrieval_table, "context_diverse_limit", 8),
            context_summary_limit=_get_positive_int(retrieval_table, "context_summary_limit", 6),
        ),
        aggregation=AggregationRuntimeConfig(
            topics_limit=_get_positive_int(aggregation_table, "topics_limit", 10),
            names_limit=_get_positive_int(aggregation_table, "names_limit", 24),
            list_extraction_names_limit=_get_positive_int(
                aggregation_table, "list_extraction_names_limit", 80
            ),
            dates_limit=_get_positive_int(aggregation_table, "dates_limit", 12),
            money_values_limit=_get_positive_int(aggregation_table, "money_values_limit", 12),
            fact_lines_limit=_get_positive_int(aggregation_table, "fact_lines_limit", 14),
            key_points_limit=_get_positive_int(aggregation_table, "key_points_limit", 10),
        ),
        rag=RagRuntimeConfig(
            agent_mode=_get_optional_str(rag_table, "agent_mode", "crewai").lower() or "crewai",
            strict_grounding=_coerce_bool(
                rag_table.get("strict_grounding"),
                default=True,
            ),
            min_evidence_score=max(0.0, _get_float(rag_table, "min_evidence_score", 0.22)),
        ),
    )


def reset_runtime_config_cache() -> None:
    get_runtime_config.cache_clear()


__all__ = [
    "AppRuntimeConfig",
    "AggregationRuntimeConfig",
    "CONFIG_FILE",
    "ENV_FILE",
    "EmbeddingRuntimeConfig",
    "PROJECT_ROOT",
    "RagRuntimeConfig",
    "RetrievalRuntimeConfig",
    "SplitterRuntimeConfig",
    "get_runtime_config",
    "load_project_environment",
    "reset_runtime_config_cache",
]
