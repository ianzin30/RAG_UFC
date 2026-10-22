"""Explicit engine inputs: validated settings and data locations.

Nothing here derives paths from the installed package location or reads a .env
file; hosts (the research checkout, applications) decide where data lives.
"""

from __future__ import annotations

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

    def with_model(self, model: str) -> "EngineSettings":
        return EngineSettings(self.llm.model_copy(update={"model": model}), self.retrieval)
