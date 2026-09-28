"""Shared non-secret settings and machine-local environment bootstrap."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_FILE = PROJECT_ROOT / "config/config.toml"
_ENV_LOADED = False


@dataclass(frozen=True)
class LLMModelRuntimeOption:
    label: str
    model_name: str


@dataclass(frozen=True)
class AppRuntimeConfig:
    llm_model: str
    llm_provider: str
    llm_model_options: tuple[LLMModelRuntimeOption, ...]

    @property
    def ufc_model_name(self):
        """Deprecated compatibility alias; the model belongs to [llm]."""
        return self.llm_model


def load_project_environment():
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(dotenv_path=ENV_FILE, override=True)
        _ENV_LOADED = True


def _read_config_document():
    load_project_environment()
    if not CONFIG_FILE.exists():
        raise RuntimeError("Missing config/config.toml")
    with CONFIG_FILE.open("rb") as file:
        return tomllib.load(file)


@lru_cache(maxsize=1)
def get_runtime_config():
    from .rag.v2.Config import LLMConfig

    payload = _read_config_document()
    llm = LLMConfig.model_validate(payload["llm"])
    raw_options = payload.get("llm_models", {}).get("options", [])
    if llm.provider == "ollama":
        local_names = ("phi4:latest", "qwen3.5")
        if llm.model not in local_names:
            raise ValueError("Use logical local model phi4:latest or qwen3.5; configure physical tags in provider settings")
        raw_options = [{"model_name": name, "label": name} for name in local_names]
    options, seen = [], set()
    for raw in raw_options:
        name = str(raw.get("model_name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            options.append(LLMModelRuntimeOption(
                label=str(raw.get("label") or name), model_name=name
            ))
    if llm.model not in seen:
        options.insert(0, LLMModelRuntimeOption(llm.model, llm.model))
    return AppRuntimeConfig(llm.model, llm.provider, tuple(options))


def reset_runtime_config_cache():
    get_runtime_config.cache_clear()
