"""Explicit engine inputs: validated settings and data locations.

Nothing here derives paths from the installed package location or reads a .env
file; hosts (the research checkout, applications) decide where data lives.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import tomllib

from .rag.v2.Config import LLMConfig, V2Config, load_settings


@dataclass(frozen=True)
class DataPaths:
    collections_root: Path
    index_cache_root: Path

    @classmethod
    def under(cls, data_root) -> "DataPaths":
        """The conventional layout: ``<data>/collections`` and ``<data>/cache/rag_v2``."""
        data_root = Path(data_root)
        return cls(data_root / "collections", data_root / "cache" / "rag_v2")


@dataclass(frozen=True)
class EngineSettings:
    llm: LLMConfig
    retrieval: V2Config

    @classmethod
    def from_document(cls, document: dict) -> "EngineSettings":
        """``document`` has the shape of config.toml: ``[llm]`` and ``[rag_v2]``."""
        llm, retrieval = load_settings(document)
        return cls(llm, retrieval)

    @classmethod
    def from_toml(cls, path) -> "EngineSettings":
        with Path(path).open("rb") as stream:
            return cls.from_document(tomllib.load(stream))

    @classmethod
    def from_release(cls, deployment: dict | None = None, *, overrides: dict | None = None,
                     manifest: dict | None = None) -> "EngineSettings":
        """The pipeline approved in this release's RELEASE.json, completed for a deployment.

        ``deployment`` (``{"llm": {...}, "retrieval": {...}}``) may only set operational
        fields: endpoints, credential variable names, timeouts, device and batch sizes.
        ``overrides`` deliberately changes the pipeline; ``check_adoption`` then reports
        the divergence instead of presenting it as the approved pipeline.
        """
        from .release import release_manifest

        approved = deepcopy((manifest or release_manifest())["pipeline"]["pipeline_config"])
        deployment = deepcopy(deployment or {})
        _require_operational(deployment)
        overrides = deepcopy(overrides or {})
        llm = _merge(_merge(approved["llm"], deployment.get("llm", {})), overrides.get("llm", {}))
        retrieval = _merge(_merge(approved["retrieval"], deployment.get("retrieval", {})),
                           overrides.get("retrieval", {}))
        return cls.from_document({"llm": llm, "rag_v2": retrieval})

    def with_model(self, model: str) -> "EngineSettings":
        return EngineSettings(self.llm.model_copy(update={"model": model}), self.retrieval)


def _merge(base: dict, extra: dict) -> dict:
    result = dict(base)
    for key, value in extra.items():
        result[key] = _merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def _require_operational(deployment: dict) -> None:
    from .identity import OPERATIONAL_LLM_FIELDS, OPERATIONAL_PROVIDER_FIELDS, OPERATIONAL_RETRIEVAL_FIELDS

    unknown = set(deployment) - {"llm", "retrieval"}
    llm = deployment.get("llm", {})
    unknown |= {f"llm.{key}" for key in set(llm) - OPERATIONAL_LLM_FIELDS - {"providers"}}
    for name, options in llm.get("providers", {}).items():
        unknown |= {f"llm.providers.{name}.{key}" for key in set(options) - OPERATIONAL_PROVIDER_FIELDS}
    unknown |= {f"retrieval.{key}" for key in set(deployment.get("retrieval", {})) - OPERATIONAL_RETRIEVAL_FIELDS}
    if unknown:
        raise ValueError(
            "Deployment settings may not change the pipeline; use overrides for: " + ", ".join(sorted(unknown))
        )
