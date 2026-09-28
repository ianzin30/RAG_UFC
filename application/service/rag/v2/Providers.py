"""All generative transports, model resolution and structured-output repair."""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Protocol
import requests
from pydantic import BaseModel, ValidationError
from .Config import LLMConfig, ModelSelection


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Capabilities:
    structured_output: bool = False
    streaming: bool = False
    temperature: bool = True
    seed: bool = False
    tool_calls: bool = False


class LLMProvider(Protocol):
    capabilities: Capabilities

    def generate(self, prompt: str, schema: dict | None = None) -> str: ...
    def identity(self) -> dict: ...


class OllamaProvider:
    capabilities = Capabilities(structured_output=True, seed=True)

    def __init__(self, selection: ModelSelection, config: LLMConfig, transport=None):
        self.selection, self.config = selection, config
        self.settings = config.providers.get("ollama", {})
        self.base_url = self.settings.get("base_url", "http://localhost:11434").rstrip(
            "/"
        )
        self.transport = transport or requests.Session()
        self.physical_model = None
        self.digest = None
        self.model_capabilities = []

    def _json(self, method, path, **kwargs):
        try:
            response = self.transport.request(
                method,
                self.base_url + path,
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(f"Ollama {path}: {exc}") from exc

    def resolve(self):
        if self.physical_model:
            return
        models = self._json("GET", "/api/tags").get("models", [])
        names = {item.get("name", item.get("model")): item for item in models}
        logical = self.selection.model
        configured = self.settings.get("models", {}).get(logical)
        if configured:
            candidates = [configured] if configured in names else []
        else:
            candidates = [
                name for name in (logical, logical + ":latest") if name in names
            ]
            if not candidates and logical == "qwen3.5":
                candidates = sorted(
                    name
                    for name in names
                    if name.startswith("qwen3.5:") and "cloud" not in name
                )
                if len(candidates) > 1:
                    raise ProviderError(
                        "Configure llm.providers.ollama.models.qwen3.5: multiple local variants available."
                    )
        if not candidates:
            raise ProviderError(
                f"Local model unavailable: {configured or logical}. Install/configure it explicitly."
            )
        self.physical_model = candidates[0]
        self.digest = names[self.physical_model].get("digest")
        self.model_capabilities = names[self.physical_model].get("capabilities", [])
        # ``/api/tags`` does not expose capabilities on every Ollama version.
        # Resolve them from the model manifest so thinking-capable Qwen builds
        # can be instructed not to spend a structured-output budget on hidden
        # chain-of-thought.
        if not self.model_capabilities:
            try:
                manifest = self._json(
                    "POST", "/api/show", json={"name": self.physical_model}
                )
                self.model_capabilities = manifest.get("capabilities", [])
                self.digest = manifest.get("details", {}).get(
                    "digest", self.digest
                )
            except ProviderError:
                # Capabilities are optional; transport/generation failures
                # remain explicit in generate().
                self.model_capabilities = []

    def identity(self):
        return {
            "provider": "ollama",
            "logical_model": self.selection.model,
            "physical_model": self.physical_model,
            "digest": self.digest,
        }

    def generate(self, prompt, schema=None):
        self.resolve()
        payload = {
            "model": self.physical_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": self.config.temperature,
                "num_ctx": self.config.num_ctx,
                "num_predict": self.config.max_output_tokens,
            },
        }
        if "thinking" in self.model_capabilities:
            payload["think"] = False
        if schema:
            payload["format"] = schema
        result = self._json("POST", "/api/generate", json=payload)
        if result.get("done_reason") == "length":
            raise ProviderError(
                "Model output exceeded max_output_tokens; refusing truncated output"
            )
        if (
            not isinstance(result.get("response"), str)
            or not result["response"].strip()
        ):
            raise ProviderError("Ollama returned no response text")
        return result["response"]


class UFCAPIProvider:
    capabilities = Capabilities()

    def __init__(self, selection, config):
        self.selection, self.config = selection, config

    def identity(self):
        return {
            "provider": "ufc",
            "logical_model": self.selection.model,
            "physical_model": self.selection.model,
            "digest": None,
        }

    def generate(self, prompt, schema=None):
        from ...UfcOllama import UFCOllamaClient, DEFAULT_UFC_API_URL

        key = os.getenv("UFC_API_KEY")
        if not key:
            raise ProviderError("UFC_API_KEY is required only for the UFC provider")
        settings = self.config.providers.get("ufc", {})
        return UFCOllamaClient(
            api_key=key,
            model_name=self.selection.model,
            api_url=settings.get("api_url")
            or os.getenv("UFC_API_URL", DEFAULT_UFC_API_URL),
            timeout_seconds=self.config.timeout_seconds,
            generation_options={"temperature": self.config.temperature},
        ).invoke(prompt)


class VLLMProvider:
    """OpenAI-compatible chat transport for a locally tunneled vLLM server."""

    capabilities = Capabilities(structured_output=True)

    def __init__(self, selection: ModelSelection, config: LLMConfig, transport=None):
        self.selection, self.config = selection, config
        settings = config.providers.get("vllm", {})
        self.base_url = (
            os.getenv("VLLM_BASE_URL")
            or settings.get("base_url")
            or "http://127.0.0.1:8000/v1"
        ).rstrip("/")
        self.api_key = os.getenv("VLLM_API_KEY")
        self.transport = transport or requests.Session()
        self.physical_model = None
        self.served_models: list[str] = []

    def _json(self, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            response = self.transport.request(
                method,
                self.base_url + path,
                headers=headers,
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(f"vLLM {path}: {exc}") from exc
        if not isinstance(result, dict):
            raise ProviderError(f"vLLM {path}: expected a JSON object")
        return result

    def resolve(self):
        if self.physical_model is not None:
            return
        result = self._json("GET", "/models")
        entries = result.get("data")
        if not isinstance(entries, list):
            raise ProviderError("vLLM /models: missing data list")
        self.served_models = [
            item["id"]
            for item in entries
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        if self.selection.model not in self.served_models:
            raise ProviderError(
                f"vLLM model {self.selection.model!r} is unavailable; "
                f"served models: {self.served_models}"
            )
        self.physical_model = self.selection.model

    def identity(self):
        return {
            "provider": "vllm",
            "logical_model": self.selection.model,
            "physical_model": self.physical_model,
            "digest": None,
        }

    def generate(self, prompt, schema=None):
        self.resolve()
        payload = {
            "model": self.physical_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
        }
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "rag_response", "schema": schema},
            }
        result = self._json("POST", "/chat/completions", json=payload)
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("vLLM returned no chat completion choices")
        choice = choices[0]
        if choice.get("finish_reason") == "length":
            raise ProviderError(
                "Model output exceeded max_output_tokens; refusing truncated output"
            )
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderError("vLLM returned no chat completion message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("vLLM returned no response text")
        return content


class ProviderRegistry:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.factories = {
            "ollama": OllamaProvider,
            "ufc": UFCAPIProvider,
            "vllm": VLLMProvider,
        }
        self.instances = {}
        self.calls = []
        self.capture_payloads = False

    def resolve(self, role):
        selection = self.config.roles.get(role) or ModelSelection(
            provider=self.config.provider, model=self.config.model
        )
        role_config = self.config.model_copy(
            update={
                "max_output_tokens": self.config.role_max_output_tokens.get(
                    role, self.config.max_output_tokens
                )
            }
        )
        # The same model can serve roles with distinct bounded-output budgets.
        key = (role, selection.provider, selection.model)
        if key not in self.instances:
            factory = self.factories.get(selection.provider)
            if factory is None:
                raise ProviderError(f"Unknown provider: {selection.provider}")
            self.instances[key] = factory(selection, role_config)
        return self.instances[key]

    def generate(self, role, prompt, schema=None):
        provider = self.resolve(role)
        active_config = getattr(
            provider,
            "config",
            self.config.model_copy(
                update={
                    "max_output_tokens": self.config.role_max_output_tokens.get(
                        role, self.config.max_output_tokens
                    )
                }
            ),
        )
        started = time.perf_counter()
        event = {
            "role": role,
            "temperature": active_config.temperature,
            "num_ctx": active_config.num_ctx,
            "max_output_tokens": active_config.max_output_tokens,
        }
        try:
            result = provider.generate(
                prompt, schema if provider.capabilities.structured_output else None
            )
            event["status"] = "ok"
            if self.capture_payloads:
                event.update(prompt=prompt, raw_response=result)
            return result
        except Exception as exc:
            event.update(status="error", error=str(exc))
            raise
        finally:
            event.update(
                provider.identity(), latency_seconds=time.perf_counter() - started
            )
            self.calls.append(event)

    def structured(self, role, prompt, model: type[BaseModel], references=None):
        schema = model.model_json_schema()
        references = references or {}

        def constrain(node):
            if isinstance(node, dict):
                for key, value in node.get("properties", {}).items():
                    if key in references and value.get("type") == "array":
                        value["items"] = {"type": "string", "enum": references[key]}
                for value in node.values():
                    constrain(value)
            elif isinstance(node, list):
                for value in node:
                    constrain(value)

        constrain(schema)

        def validate_references(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if (
                        key in references
                        and isinstance(value, list)
                        and not set(value) <= set(references[key])
                    ):
                        raise ValueError(f"Unknown {key}; allowed: {references[key]}")
                    validate_references(value)
            elif isinstance(node, list):
                for value in node:
                    validate_references(value)

        request = (
            prompt
            + "\nReturn only JSON matching this schema:\n"
            + json.dumps(schema, ensure_ascii=False)
        )
        for attempt in range(2):
            raw = self.generate(role, request, schema)
            self.calls[-1]["structured_attempt"] = attempt + 1
            try:
                text = raw.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = model.model_validate_json(text)
                validate_references(parsed.model_dump())
                return parsed
            except (ValidationError, ValueError) as exc:
                self.calls[-1]["validation_error"] = str(exc)
                if attempt:
                    raise ProviderError(
                        f"Invalid {role} output after bounded repair: {exc}"
                    ) from exc
                request += (
                    "\nYour previous output was invalid. Correct it.\n"
                    + raw
                    + "\nValidation: "
                    + str(exc)
                )
