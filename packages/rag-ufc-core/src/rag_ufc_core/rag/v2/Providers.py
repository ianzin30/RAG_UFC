"""All generative transports, model resolution and structured-output repair."""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Protocol
import requests
from pydantic import BaseModel, ValidationError
from .Config import LLMConfig, ModelSelection, VLLMSettings


class ProviderError(RuntimeError):
    pass


def render_structured_request(prompt, model, references=None, *, compact_json=False):
    """Single source for the schema-bearing message counted and transmitted."""
    schema = model.model_json_schema()
    references = references or {}

    def constrain(node):
        if isinstance(node, dict):
            for key, value in node.get("properties", {}).items():
                if key in references:
                    if value.get("type") == "array":
                        value["items"] = {"type": "string", "enum": references[key]}
                    elif value.get("type") == "string":
                        value["enum"] = references[key]
            for value in node.values():
                constrain(value)
        elif isinstance(node, list):
            for value in node:
                constrain(value)

    constrain(schema)
    options = {"separators": (",", ":")} if compact_json else {}
    request = prompt + "\nReturn only JSON matching this schema:\n" + json.dumps(
        schema, ensure_ascii=False, **options)
    return request, schema


@dataclass
class GenerationResult:
    text: str
    identity: dict = field(default_factory=dict)
    sent_parameters: dict | None = None
    usage: dict | None = None
    finish_reason: str | None = None
    output_at_limit: bool = False
    reported_model: str | None = None
    server_timings: dict | None = None
    thinking: str | None = None


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
                self.digest = manifest.get("details", {}).get("digest", self.digest)
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
        self.last_generation = None
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
            payload["think"] = self.settings.get("think", False)
        elif self.settings.get("think") is True:
            raise ProviderError("Configured thinking mode is unsupported by this model")
        options = self.settings.get("options", {})
        if set(options) - {"top_p", "top_k", "min_p", "seed", "repeat_penalty"}:
            raise ProviderError("Unknown Ollama sampling option")
        payload["options"].update(options)
        if schema:
            payload["format"] = schema
        result = self._json("POST", "/api/generate", json=payload)
        self.last_generation = GenerationResult(
            text=result.get("response", ""),
            identity=self.identity(),
            sent_parameters={"options": payload["options"], "think": payload.get("think"),
                             "keep_alive": payload["keep_alive"], "format": payload.get("format")},
            usage={
                "prompt_tokens": result.get("prompt_eval_count"),
                "completion_tokens": result.get("eval_count"),
            },
            finish_reason=result.get("done_reason"),
            output_at_limit=(result.get("eval_count") or 0)
            >= self.config.max_output_tokens,
            reported_model=result.get("model"),
            server_timings={key: result.get(key) for key in
                ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration")},
            thinking=result.get("thinking"),
        )
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

    def generate_result(self, prompt, schema=None):
        self.generate(prompt, schema)
        return self.last_generation


class UFCAPIProvider:
    capabilities = Capabilities()

    def __init__(self, selection, config, transport=None):
        self.selection, self.config = selection, config
        self.transport = transport

    def identity(self):
        observed = (
            self.config.providers.get("ufc", {})
            .get("model_identities", {})
            .get(self.selection.model, {})
        )
        return {
            "provider": "ufc",
            "logical_model": self.selection.model,
            "physical_model": observed.get("model") or self.selection.model,
            "digest": observed.get("digest"),
        }

    def generate(self, prompt, schema=None):
        return self.generate_result(prompt, schema).text

    def generate_result(self, prompt, schema=None):
        from ...UfcOllama import UFCOllamaClient, DEFAULT_UFC_API_URL

        key = os.getenv("UFC_API_KEY")
        if not key:
            raise ProviderError("UFC_API_KEY is required only for the UFC provider")
        settings = self.config.providers.get("ufc", {})
        api_format = settings.get("api_format", "chat")
        options = {"temperature": self.config.temperature}
        if api_format == "chat":
            options["max_tokens"] = self.config.max_output_tokens
            protocol = settings.get("protocol", "openai_chat")
            if protocol not in {"openai_chat", "openwebui_ollama"}:
                raise ProviderError(
                    "Unknown UFC chat protocol; configure openai_chat or openwebui_ollama"
                )
            if protocol == "openwebui_ollama":
                options = {"params": {**options, "num_ctx": self.config.num_ctx}}
        else:
            options.update(
                num_predict=self.config.max_output_tokens, num_ctx=self.config.num_ctx
            )
        try:
            client = UFCOllamaClient(
                api_key=key,
                model_name=self.selection.model,
                api_url=os.getenv("UFC_API_URL")
                or settings.get("api_url")
                or DEFAULT_UFC_API_URL,
                timeout_seconds=self.config.timeout_seconds,
                generation_options=options,
                api_format=api_format,
                transport=self.transport,
            )
            return GenerationResult(
                **client.invoke_with_metadata(prompt), identity=self.identity()
            )
        except (TimeoutError, ValueError) as exc:
            raise ProviderError(str(exc)) from exc


class VLLMProvider:
    """OpenAI-compatible chat transport for a locally tunneled vLLM server."""

    capabilities = Capabilities(structured_output=True, seed=True)

    def __init__(self, selection: ModelSelection, config: LLMConfig, transport=None):
        self.selection, self.config = selection, config
        self.settings = VLLMSettings.model_validate(config.providers.get("vllm", {}))
        self.base_url = (
            os.getenv("VLLM_BASE_URL")
            or self.settings.base_url
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
            hint = " Verify the existing tunnel or server; no automatic reconnection." if isinstance(exc, requests.ConnectionError) else ""
            raise ProviderError(f"vLLM {path}: {exc}.{hint}") from exc
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
            "endpoint": self.base_url + "/chat/completions",
        }

    def chat_template_kwargs(self):
        """Used by both the HTTP payload and benchmark token accounting."""
        value = self.settings.enable_thinking
        return {} if value is None else {"enable_thinking": value}

    def build_payload(self, prompt, schema=None):
        """Pure request construction: never performs resolution or generation."""
        payload = {
            "model": self.physical_model or self.selection.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            **self.settings.options.model_dump(exclude_none=True),
        }
        template_kwargs = self.chat_template_kwargs()
        if template_kwargs:
            payload["chat_template_kwargs"] = template_kwargs
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "rag_response", "schema": schema},
            }
        return payload

    def generate(self, prompt, schema=None):
        self.resolve()
        payload = self.build_payload(prompt, schema)
        # Preserve attempted settings on transport failures as well as bad outputs.
        self.last_generation = GenerationResult(
            text="", identity=self.identity(),
            sent_parameters={k: v for k, v in payload.items() if k != "messages"},
        )
        result = self._json("POST", "/chat/completions", json=payload)
        self.last_generation.usage = result.get("usage")
        self.last_generation.reported_model = result.get("model")
        choices = result.get("choices")
        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(choices[0], dict)
        ):
            raise ProviderError("vLLM returned no chat completion choices")
        choice = choices[0]
        self.last_generation.finish_reason = choice.get("finish_reason")
        usage = result.get("usage") or {}
        self.last_generation.output_at_limit = choice.get("finish_reason") == "length" or (
            usage.get("completion_tokens") or 0) >= self.config.max_output_tokens
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderError("vLLM returned no chat completion message")
        content = message.get("content")
        self.last_generation.text = content if isinstance(content, str) else ""
        self.last_generation.thinking = message.get("reasoning") or message.get("reasoning_content")
        if choice.get("finish_reason") == "length":
            raise ProviderError(
                "Model output exceeded max_output_tokens; refusing truncated output"
            )
        if result.get("model") is not None and result["model"] != self.physical_model:
            raise ProviderError("vLLM returned a different model than configured")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("vLLM returned no response text")
        return content

    def generate_result(self, prompt, schema=None):
        self.generate(prompt, schema)
        return self.last_generation


class ProviderRegistry:
    def __init__(self, config: LLMConfig):
        self.config = config
        from .Spark import SparkProvider
        self.factories = {
            "spark": SparkProvider,
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
        if hasattr(provider, 'last_generation'):
            provider.last_generation = None
        event = {
            "role": role,
            "temperature": active_config.temperature,
            "num_ctx": active_config.num_ctx,
            "max_output_tokens": active_config.max_output_tokens,
            "configured": {
                "temperature": active_config.temperature,
                "num_ctx": active_config.num_ctx,
                "max_output_tokens": active_config.max_output_tokens,
            },
            "sent_parameters": None,
            "observed": {"usage": None, "finish_reason": None, "model": None},
        }
        try:
            completion = (
                provider.generate_result
                if hasattr(provider, "generate_result")
                else provider.generate
            )(prompt, schema if provider.capabilities.structured_output else None)
            if isinstance(completion, GenerationResult):
                result = completion.text
                event.update(
                    {
                        key: value
                        for key, value in asdict(completion).items()
                        if key not in {"text", "identity"}
                    }
                )
                event["observed"] = {
                    "usage": completion.usage,
                    "finish_reason": completion.finish_reason,
                    "model": completion.reported_model,
                    "num_ctx": None,
                }
                prompt_tokens = (completion.usage or {}).get("prompt_tokens")
                event["input_at_requested_context_limit"] = (
                    isinstance(prompt_tokens, (int, float))
                    and prompt_tokens >= active_config.num_ctx
                )
            else:
                result = completion
                event.update(
                    sent_parameters=None,
                    observed={"usage": None, "finish_reason": None},
                )
            event["configured"] = {
                "temperature": active_config.temperature,
                "num_ctx": active_config.num_ctx,
                "max_output_tokens": active_config.max_output_tokens,
            }
            event["status"] = "ok"
            if self.capture_payloads:
                event.update(prompt=prompt, raw_response=result)
            return result
        except Exception as exc:
            completion = getattr(provider, "last_generation", None)
            if isinstance(completion, GenerationResult):
                event.update({key: value for key, value in asdict(completion).items()
                              if key not in {"text", "identity"}})
                event["observed"] = {
                    "usage": completion.usage,
                    "finish_reason": completion.finish_reason,
                    "model": completion.reported_model,
                    "num_ctx": None,
                }
                if self.capture_payloads:
                    event.update(prompt=prompt, raw_response=completion.text)
            event.update(status="error", error=str(exc))
            raise
        finally:
            event.update(
                provider.identity(), latency_seconds=time.perf_counter() - started
            )
            self.calls.append(event)

    def structured(self, role, prompt, model: type[BaseModel], references=None, *, max_attempts=2, compact_json=False,
                   acceptance_model: type[BaseModel] | None = None):
        if max_attempts not in (1, 2):
            raise ValueError("Structured output permits one or two attempts")
        references = references or {}
        request, schema = render_structured_request(prompt, model, references, compact_json=compact_json)

        def validate_references(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if (
                        key in references
                        and isinstance(value, list)
                        and not set(value) <= set(references[key])
                    ):
                        raise ValueError(
                            f"Unknown {key}; use only IDs from the supplied data"
                        )
                    if (
                        key in references
                        and isinstance(value, str)
                        and value not in references[key]
                    ):
                        raise ValueError(
                            f"Unknown {key}; use only IDs from the supplied data"
                        )
                    validate_references(value)
            elif isinstance(node, list):
                for value in node:
                    validate_references(value)

        for attempt in range(max_attempts):
            raw = self.generate(role, request, schema)
            self.calls[-1]["structured_attempt"] = attempt + 1
            try:
                text = raw.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0]
                # The model-facing schema remains frozen when an experiment
                # changes only local acceptance. Application callers use model.
                parsed = (acceptance_model or model).model_validate_json(text)
                validate_references(parsed.model_dump())
                return parsed
            except (ValidationError, ValueError) as exc:
                self.calls[-1]["validation_error"] = str(exc)
                if attempt == max_attempts - 1:
                    raise ProviderError(
                        f"Invalid {role} output after bounded repair: {exc}"
                    ) from exc
                errors = (
                    exc.errors(
                        include_url=False, include_input=False, include_context=False
                    )
                    if isinstance(exc, ValidationError)
                    else [{"msg": str(exc)}]
                )
                request = (
                    prompt
                    + "\nReturn only concise JSON matching this schema:\n"
                    + json.dumps(schema, ensure_ascii=False)
                    + "\nThe previous attempt was invalid. Correct these fields; do not explain:\n"
                    + json.dumps(errors[:4], ensure_ascii=False)
                )
