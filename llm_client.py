"""Small OpenAI SDK client for the laboratory Spark API.

No prompts, credentials, reasoning, raw responses or server error bodies are logged.
Only HTTP 429 and 5xx are retried; connection/timeouts and interrupted streams are
never replayed automatically, because their remote generation outcome is unknown.
"""
from collections.abc import Iterator
from dataclasses import dataclass, field
import os
from pathlib import Path
import time

from dotenv import dotenv_values
import httpx
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, OpenAI

DEFAULT_BASE_URL = 'https://spark.ollama.atlab.ufc.br/api'
DEFAULT_MODEL = 'nvidia/Qwen3.6-35B-A3B-NVFP4'
DEFAULT_ENV = Path(__file__).resolve().parent / '.env'


class LLMError(RuntimeError):
    """Safe error message, with no raw request or response data."""


class LLMConfigurationError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


class LLMConnectionError(LLMError):
    pass


class EmptyContentError(LLMError):
    pass


@dataclass(frozen=True)
class LLMSettings:
    base_url: str
    api_key: str = field(repr=False)
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls, env_path=DEFAULT_ENV):
        # Explicit process variables take precedence; reading .env does not mutate
        # the process environment or import credentials from other integrations.
        values = dotenv_values(env_path, interpolate=False)
        def read(name, default=''):
            return (os.environ.get(name, values.get(name)) or default).strip()
        key = read('LLM_API_KEY')
        if not key:
            raise LLMConfigurationError('Preencha LLM_API_KEY no .env')
        return cls(read('LLM_BASE_URL', DEFAULT_BASE_URL), key, read('LLM_MODEL', DEFAULT_MODEL))


def public_error(exc):
    """Never expose SDK error text: gateways can echo headers and prompt bodies."""
    if isinstance(exc, APIStatusError):
        if exc.status_code in (401, 403):
            return LLMAuthenticationError(
                f'HTTP {exc.status_code}: chave inválida, sem permissão ou chaves de API '
                'desligadas no Open WebUI. Verifique sua chave e a configuração com o administrador.')
        return LLMError(f'A API da Spark devolveu HTTP {exc.status_code}.')
    if isinstance(exc, (APITimeoutError, httpx.TimeoutException)):
        return LLMConnectionError(
            'Tempo limite da API da Spark excedido. O resultado remoto é desconhecido; '
            'a chamada não será repetida automaticamente.')
    if isinstance(exc, (APIConnectionError, httpx.TransportError)):
        return LLMConnectionError(
            'Não foi possível conectar à API da Spark. Verifique se a VPN do laboratório está ligada. '
            'A chamada não será repetida automaticamente.')
    return LLMError('Resposta inválida ou erro da API da Spark; os dados da requisição foram omitidos.')


class LLMClient:
    def __init__(self, *, env_path=DEFAULT_ENV, timeout=420.0, max_retries=2,
                 retry_base_seconds=1.0, http_client=None, settings=None):
        self.settings = settings or LLMSettings.from_env(env_path)
        if not isinstance(max_retries, int) or not 0 <= max_retries <= 3:
            raise LLMConfigurationError('max_retries deve estar entre 0 e 3.')
        if timeout <= 0 or retry_base_seconds < 0:
            raise LLMConfigurationError('Timeout deve ser positivo e a espera de retry não pode ser negativa.')
        self._max_retries = max_retries
        self._retry_base = retry_base_seconds
        # Own retry policy avoids the SDK default retries of unknown connection
        # outcomes. There is only one retry layer and no model/endpoint fallback.
        self._sdk = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key,
                           timeout=timeout, max_retries=0, http_client=http_client)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._sdk.close()

    def _request(self, callback):
        self.last_request_attempts = 0
        for attempt in range(self._max_retries + 1):
            self.last_request_attempts += 1
            try:
                return callback()
            except APIStatusError as exc:
                if (exc.status_code == 429 or 500 <= exc.status_code < 600) and attempt < self._max_retries:
                    time.sleep(self._retry_base * 2 ** attempt)
                    continue
                raise public_error(exc) from None
            except APIError as exc:
                raise public_error(exc) from None

    def list_models(self):
        """Return model IDs only; do not print or return transport metadata."""
        page = self._request(self._sdk.models.list)
        return [model.id for model in page.data]

    def _params(self, messages, model, params):
        if 'stream' in params:
            raise LLMConfigurationError('Use chat para texto completo ou stream_chat para streaming.')
        for name in ('top_k', 'min_p', 'repetition_penalty', 'chat_template_kwargs'):
            if name in params:
                raise LLMConfigurationError(f'Passe {name} dentro de extra_body.')
        return {'messages': list(messages), 'model': model or self.settings.model,
                'temperature': 0, 'max_tokens': 2048, **params}

    def chat(self, messages, model=None, **params):
        """Return final message.content only. Server reasoning defaults are preserved.

        For Qwen3.6 extraction/classification/summaries, pass
        extra_body={'chat_template_kwargs': {'enable_thinking': False}}.
        Standard parameters (top_p, seed, stop, max_tokens) pass through unchanged.
        """
        return self.chat_with_metadata(messages, model=model, **params)['text']

    def chat_with_metadata(self, messages, model=None, **params):
        """Public completion boundary; excludes prompts, headers and private reasoning."""
        arguments = self._params(messages, model, params)
        response = self._request(lambda: self._sdk.chat.completions.create(**arguments, stream=False))
        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice else None
        if not isinstance(content, str) or not content.strip():
            raise EmptyContentError('Resposta final vazia em message.content. Confira thinking e max_tokens.')
        if choice.finish_reason == 'length':
            raise LLMError('A saída atingiu max_tokens; resposta truncada recusada.')
        return {'text': content, 'model': response.model, 'finish_reason': choice.finish_reason,
                'usage': response.usage.model_dump() if response.usage else None,
                'transport_attempts': self.last_request_attempts}

    def stream_chat(self, messages, model=None, **params) -> Iterator[str]:
        """Yield only delta.content; reasoning is ignored. Never restart an SSE stream."""
        arguments = self._params(messages, model, params)
        stream = self._request(lambda: self._sdk.chat.completions.create(**arguments, stream=True))
        has_text = False
        try:
            for chunk in stream:
                for choice in chunk.choices:
                    text = choice.delta.content
                    if isinstance(text, str) and text:
                        has_text = has_text or bool(text.strip())
                        yield text
        except (APIError, httpx.HTTPError) as exc:
            raise public_error(exc) from None
        finally:
            stream.close()
        if not has_text:
            raise EmptyContentError(
                'Streaming terminou sem resposta final em delta.content. '
                'Aumente max_tokens ou desligue thinking no Qwen3.6.')


def chat(messages, model=None, **params):
    with LLMClient() as client:
        return client.chat(messages, model=model, **params)


def stream_chat(messages, model=None, **params):
    with LLMClient() as client:
        yield from client.stream_chat(messages, model=model, **params)
