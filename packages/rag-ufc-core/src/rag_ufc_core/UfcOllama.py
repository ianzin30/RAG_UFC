"""Authenticated UFC/Open WebUI transport; class name retained for compatibility."""

import logging

import requests


DEFAULT_UFC_API_URL = "https://cumbuco.ollama.atlab.ufc.br/api/chat/completions"
logger = logging.getLogger(__name__)


class UFCOllamaClient:
    """Chat completions by default; legacy generate is explicitly opt-in."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        api_url: str = DEFAULT_UFC_API_URL,
        timeout_seconds: int = 420,
        generation_options: dict | None = None,
        api_format: str = "chat",
        transport=None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.generation_options = dict(generation_options or {})
        if api_format not in {"chat", "ollama_generate"}:
            raise ValueError("UFC api_format must be chat or ollama_generate")
        self.api_format = api_format
        self.transport = transport or requests

    def _coerce_prompt(self, prompt_value) -> str:
        if isinstance(prompt_value, str):
            return prompt_value
        if hasattr(prompt_value, "to_string"):
            return prompt_value.to_string()
        return str(prompt_value)

    def invoke(self, prompt_value) -> str:
        return self.invoke_with_metadata(prompt_value)["text"]

    def invoke_with_metadata(self, prompt_value) -> dict:
        prompt = self._coerce_prompt(prompt_value)
        logger.info("Invoking UFC LLM request with model=%s", self.model_name)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model_name, "stream": False}
        if self.api_format == "chat":
            payload["messages"] = [{"role": "user", "content": prompt}]
            payload.update(self.generation_options)
        else:
            payload.update(prompt=prompt, keep_alive="10m")
            payload["options"] = dict(self.generation_options)

        try:
            response = self.transport.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(
                "Timeout while waiting for the UFC LLM response."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise TimeoutError("Could not connect to the UFC LLM endpoint.") from exc
        except requests.exceptions.RequestException as exc:
            raise TimeoutError(
                "Unexpected request error while calling the UFC LLM."
            ) from exc

        if response.status_code != 200:
            hint = ""
            if response.status_code in {401, 403}:
                hint = " Check UFC_API_KEY and account/model API permissions in Open WebUI."
            raise TimeoutError(
                f"UFC LLM request failed with HTTP {response.status_code}.{hint}"
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise TimeoutError("UFC LLM response was not valid JSON.") from exc

        if not isinstance(result, dict):
            raise TimeoutError("UFC LLM response must be a JSON object.")
        if self.api_format == "chat":
            choices = result.get("choices")
            if (
                not isinstance(choices, list)
                or not choices
                or not isinstance(choices[0], dict)
            ):
                raise TimeoutError(
                    "UFC chat response did not contain completion choices."
                )
            choice = choices[0]
            if choice.get("finish_reason") == "length":
                raise TimeoutError(
                    "Model output exceeded max_output_tokens; refusing truncated output"
                )
            if choice.get("finish_reason") == "content_filter":
                raise TimeoutError(
                    "UFC chat completion was blocked by a content filter."
                )
            message = choice.get("message")
            answer = message.get("content") if isinstance(message, dict) else None
        else:
            if result.get("done_reason") == "length":
                raise TimeoutError(
                    "Model output exceeded max_output_tokens; refusing truncated output"
                )
            answer = result.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise TimeoutError("UFC LLM response did not contain response text.")

        usage = result.get("usage") if isinstance(result.get("usage"), dict) else None
        if self.api_format == "ollama_generate":
            usage = {
                "prompt_tokens": result.get("prompt_eval_count"),
                "completion_tokens": result.get("eval_count"),
            }
        sent = {
            key: payload[key]
            for key in ("params", "options", "temperature", "max_tokens")
            if key in payload
        }
        limit = (
            payload.get("params", {}).get("max_tokens")
            or payload.get("max_tokens")
            or payload.get("options", {}).get("num_predict")
        )
        output_tokens = (usage or {}).get("completion_tokens")
        return {
            "text": answer,
            "sent_parameters": sent,
            "usage": usage,
            "reported_model": result.get("model"),
            "finish_reason": (
                choice.get("finish_reason")
                if self.api_format == "chat"
                else result.get("done_reason")
            ),
            "output_at_limit": bool(
                limit and output_tokens is not None and output_tokens >= limit
            ),
        }
