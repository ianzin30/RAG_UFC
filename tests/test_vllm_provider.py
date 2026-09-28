import pytest

from application.service.rag.v2.Config import LLMConfig, ModelSelection
from application.service.rag.v2.Providers import (
    OllamaProvider,
    ProviderError,
    ProviderRegistry,
    UFCAPIProvider,
    VLLMProvider,
)


MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class FakeTransport:
    def __init__(self, completion=None, models=None):
        self.calls = []
        self.completion = completion or {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]
        }
        self.models = models if models is not None else [MODEL]

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == "GET":
            return FakeResponse({"data": [{"id": name} for name in self.models]})
        return FakeResponse(self.completion)


def make_provider(transport, **kwargs):
    config = LLMConfig(
        provider="vllm",
        model=MODEL,
        providers={"vllm": {"base_url": "http://127.0.0.1:8000/v1"}},
        temperature=0.2,
        max_output_tokens=47,
        **kwargs,
    )
    return VLLMProvider(ModelSelection(provider="vllm", model=MODEL), config, transport)


def test_vllm_resolution_and_structured_chat_payload(monkeypatch):
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    transport = FakeTransport()
    provider = make_provider(transport)
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
    assert provider.generate("question", schema) == "OK"
    assert [call[0] for call in transport.calls] == ["GET", "POST"]
    assert transport.calls[0][1] == "http://127.0.0.1:8000/v1/models"
    payload = transport.calls[1][2]["json"]
    assert payload == {
        "model": MODEL,
        "messages": [{"role": "user", "content": "question"}],
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 47,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "rag_response", "schema": schema},
        },
    }
    assert provider.identity()["physical_model"] == MODEL
    assert provider.generate("again") == "OK"
    assert [call[0] for call in transport.calls] == ["GET", "POST", "POST"]


def test_vllm_base_url_and_optional_key(monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://other-host:9000/v1/")
    monkeypatch.setenv("VLLM_API_KEY", "test-key")
    transport = FakeTransport()
    provider = make_provider(transport)
    provider.resolve()
    assert transport.calls[0][1] == "http://other-host:9000/v1/models"
    assert transport.calls[0][2]["headers"] == {"Authorization": "Bearer test-key"}


def test_vllm_missing_model_stops_before_generation(monkeypatch):
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    transport = FakeTransport(models=["another-model"])
    provider = make_provider(transport)
    with pytest.raises(ProviderError, match="another-model") as error:
        provider.generate("question")
    assert MODEL in str(error.value)
    assert [call[0] for call in transport.calls] == ["GET"]


@pytest.mark.parametrize(
    "completion, message",
    [
        ({"choices": []}, "choices"),
        ({"choices": [{}]}, "message"),
        ({"choices": [{"message": {"content": ""}}]}, "response text"),
        (
            {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]},
            "truncated",
        ),
    ],
)
def test_vllm_rejects_invalid_or_truncated_completion(completion, message):
    provider = make_provider(FakeTransport(completion=completion))
    with pytest.raises(ProviderError, match=message):
        provider.generate("question")


def test_registry_selects_vllm_and_keeps_existing_providers():
    registry = ProviderRegistry(LLMConfig(provider="vllm", model=MODEL))
    assert isinstance(registry.resolve("answer"), VLLMProvider)
    assert registry.factories["ollama"] is OllamaProvider
    assert registry.factories["ufc"] is UFCAPIProvider
