"""Shared non-secret settings and machine-local environment bootstrap."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib
import os
import json
import hashlib
from copy import deepcopy
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_FILE = PROJECT_ROOT / "config/config.toml"
_ENV_LOADED = False


class RuntimeConfigurationError(ValueError):
    pass


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
        for name, value in dotenv_values(ENV_FILE, interpolate=False).items():
            if value is not None and name not in {"LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"}:
                os.environ.setdefault(name, value)
        _ENV_LOADED = True


def _read_config_document():
    load_project_environment()
    if not CONFIG_FILE.exists():
        raise RuntimeError("Missing config/config.toml")
    with CONFIG_FILE.open("rb") as file:
        return tomllib.load(file)


def checkout_settings_document():
    """config/config.toml with [llm] resolved for this process: the core's default document."""
    raw = _read_config_document()
    return {**raw, "llm": resolve_application_llm(raw["llm"])}


@lru_cache(maxsize=1)
def get_runtime_config():
    from .rag.v2.Config import LLMConfig

    payload = _read_config_document()
    llm = LLMConfig.model_validate(resolve_application_llm(payload["llm"]))
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
    get_chat_config.cache_clear()


def read_secret(name):
    value = os.environ.get(name, dotenv_values(ENV_FILE, interpolate=False).get(name))
    return str(value or '').strip()


def resolve_application_llm(raw):
    """Process > TOML > defaults; legacy dotenv values may only agree with TOML."""
    result = deepcopy(raw)
    if result.get('provider') != 'spark':
        return result
    file_values = dotenv_values(ENV_FILE, interpolate=False)
    provider = result.setdefault('providers', {}).setdefault('spark', {})
    for variable, container, key, default in (
        ('LLM_BASE_URL', provider, 'base_url', 'https://spark.ollama.atlab.ufc.br/api'),
        ('LLM_MODEL', result, 'model', 'nvidia/Qwen3.6-35B-A3B-NVFP4'),
    ):
        configured = str(container.get(key, default)).rstrip('/')
        legacy = str(file_values.get(variable) or '').strip().rstrip('/')
        if variable not in os.environ and legacy and legacy != configured:
            raise RuntimeConfigurationError(f'{variable} no .env diverge do config/config.toml. Migre o valor para o TOML ou defina um override explícito no processo.')
        container[key] = os.environ.get(variable, configured).strip().rstrip('/')
    return result


@lru_cache(maxsize=1)
def get_chat_config():
    from pydantic import BaseModel, Field, ConfigDict
    class ChatConfig(BaseModel):
        model_config = ConfigDict(extra='forbid')
        history_messages: int = Field(default=6, ge=0, le=100)
        max_sessions: int = Field(default=6, ge=1)
        title_max_chars: int = Field(default=34, ge=8)
        excerpt_chars: int = Field(default=900, ge=1)
        default_title: str = 'Nova conversa'
        history_path: str = 'data/local_chat_sessions.json'
    values = dict(_read_config_document().get('streamlit', {}).get('chat', {}))
    if os.getenv('RAG_CHAT_HISTORY_PATH'): values['history_path'] = os.environ['RAG_CHAT_HISTORY_PATH']
    return ChatConfig.model_validate(values)


def application_profile():
    from .rag.v2.Config import load_settings
    llm, retrieval = load_settings()
    # application/ holds symlinks to moved core modules; the package tree covers the rest.
    files = sorted((PROJECT_ROOT / 'application').rglob('*.py')) + [PROJECT_ROOT / 'llm_client.py']
    files += sorted((PROJECT_ROOT / 'packages/rag-ufc-core/src').rglob('*.py'))
    implementation = hashlib.sha256(b''.join(str(p.relative_to(PROJECT_ROOT)).encode() + p.read_bytes() for p in files)).hexdigest()
    public = {'llm': llm.model_dump(), 'retrieval': retrieval.model_dump(), 'implementation_fingerprint': implementation}
    public['fingerprint'] = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
    return public
