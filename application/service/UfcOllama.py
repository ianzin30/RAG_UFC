"""Ollama API client for local text generation.

Provides a wrapper around the Ollama generate endpoint at UFC's internal server,
handling authentication, request/response formatting, and generation options.
"""
import requests


DEFAULT_UFC_API_URL = "http://ollama.atlab.ufc.br:8080/ollama/api/generate"


class UFCOllamaClient:
    """HTTP client for Ollama text generation at UFC's internal Ollama server."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        api_url: str = DEFAULT_UFC_API_URL,
        timeout_seconds: int = 210,
        generation_options: dict | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.generation_options = dict(generation_options or {})

    def _coerce_prompt(self, prompt_value) -> str:
        if isinstance(prompt_value, str):
            return prompt_value
        if hasattr(prompt_value, "to_string"):
            return prompt_value.to_string()
        return str(prompt_value)

    def invoke(self, prompt_value) -> str:
        prompt = self._coerce_prompt(prompt_value)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
        }
        if self.generation_options:
            payload["options"] = dict(self.generation_options)

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise RuntimeError("Timeout while waiting for the UFC LLM response.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError("Could not connect to the UFC LLM endpoint.") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Unexpected request error while calling the UFC LLM: {exc}") from exc

        if response.status_code != 200:
            detail = response.text.strip() or response.reason
            raise RuntimeError(f"UFC LLM request failed with HTTP {response.status_code}: {detail}")

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError("UFC LLM response was not valid JSON.") from exc

        answer = result.get("response")
        if not answer:
            raise RuntimeError("UFC LLM response did not contain a 'response' field.")

        return answer
