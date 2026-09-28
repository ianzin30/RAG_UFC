"""Runtime LLM model options for the app selector."""

from __future__ import annotations

from dataclasses import dataclass

from .RuntimeConfig import get_runtime_config


@dataclass(frozen=True)
class LLMModelOption:
    label: str
    model_name: str


def get_default_llm_model_name() -> str:
    return str(get_runtime_config().llm_model).strip()


def build_llm_model_options(default_model_name: str | None = None) -> tuple[LLMModelOption, ...]:
    runtime_config = get_runtime_config()
    default_model = str(default_model_name or runtime_config.llm_model).strip()
    if not default_model:
        raise RuntimeError("Missing default LLM model name.")

    configured_options = [
        LLMModelOption(
            label=str(option.label or "").strip() or str(option.model_name),
            model_name=str(option.model_name or "").strip(),
        )
        for option in list(getattr(runtime_config, "llm_model_options", ()) or ())
    ]
    if not configured_options:
        configured_options = [LLMModelOption(label=default_model, model_name=default_model)]

    options: list[LLMModelOption] = []
    seen_models: set[str] = set()
    for option in configured_options:
        if not option.model_name or option.model_name in seen_models:
            continue
        seen_models.add(option.model_name)
        options.append(option)

    if default_model not in seen_models:
        options.insert(0, LLMModelOption(label=default_model, model_name=default_model))
    return tuple(options)


def get_llm_model_names(default_model_name: str | None = None) -> tuple[str, ...]:
    return tuple(option.model_name for option in build_llm_model_options(default_model_name))


def get_llm_model_labels(default_model_name: str | None = None) -> dict[str, str]:
    return {option.model_name: option.label for option in build_llm_model_options(default_model_name)}


def coerce_llm_model_name(model_name: str | None, default_model_name: str | None = None) -> str:
    default_model = str(default_model_name or get_default_llm_model_name()).strip()
    normalized_model = str(model_name or "").strip()
    allowed_models = set(get_llm_model_names(default_model))
    return normalized_model if normalized_model in allowed_models else default_model
