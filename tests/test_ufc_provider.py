"""Cumbuco/Open WebUI contracts without credentials or real inference."""

import pytest
import requests

from application.service.UfcOllama import DEFAULT_UFC_API_URL, UFCOllamaClient
from application.service.rag.v2.Config import LLMConfig, ModelSelection
from application.service.rag.v2.Models import ResearchResult
from application.service.rag.v2.Providers import (
    ProviderError,
    ProviderRegistry,
    UFCAPIProvider,
)


def completion(content="OK", finish_reason="stop"):
    return {
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}]
    }


class Response:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class Transport:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.setenv("UFC_API_KEY", "test-only-key")
    monkeypatch.delenv("UFC_API_URL", raising=False)


def provider(transport, **config):
    return UFCAPIProvider(
        ModelSelection(provider="ufc", model="phi4:latest"),
        LLMConfig(**config),
        transport,
    )


def test_chat_contract_and_role_budget():
    transport = Transport(Response(completion()))
    assert provider(transport, max_output_tokens=384).generate("Teste") == "OK"
    url, call = transport.calls[0]
    assert url == DEFAULT_UFC_API_URL
    assert call["headers"]["Authorization"] == "Bearer test-only-key"
    assert call["timeout"] == 420
    assert call["json"] == {
        "model": "phi4:latest",
        "stream": False,
        "messages": [{"role": "user", "content": "Teste"}],
        "temperature": 0,
        "max_tokens": 384,
    }


def test_environment_endpoint_overrides_configuration(monkeypatch):
    monkeypatch.setenv("UFC_API_URL", "https://example.test/api/chat/completions")
    transport = Transport(Response(completion()))
    provider(
        transport,
        providers={"ufc": {"api_url": "https://configured.test/api/chat/completions"}},
    ).generate("test")
    assert transport.calls[0][0] == "https://example.test/api/chat/completions"


def test_configured_endpoint_without_environment():
    transport = Transport(Response(completion()))
    provider(
        transport,
        providers={"ufc": {"api_url": "https://configured.test/api/chat/completions"}},
    ).generate("test")
    assert transport.calls[0][0] == "https://configured.test/api/chat/completions"


def test_missing_key_fails_before_http(monkeypatch):
    monkeypatch.delenv("UFC_API_KEY")
    transport = Transport()
    with pytest.raises(ProviderError, match="UFC_API_KEY"):
        provider(transport).generate("test")
    assert not transport.calls


@pytest.mark.parametrize("status", [401, 403, 502])
def test_http_failures_are_explicit_and_do_not_leak_key(status):
    transport = Transport(Response({}, status))
    with pytest.raises(ProviderError, match=f"HTTP {status}") as error:
        provider(transport).generate("test")
    assert "test-only-key" not in str(error.value)


@pytest.mark.parametrize(
    "result",
    [
        [],
        {},
        {"choices": []},
        {"choices": [None]},
        {"choices": [{"message": None}]},
        completion(""),
        completion(" "),
        completion(123),
        ValueError("not JSON"),
    ],
)
def test_malformed_responses_are_rejected(result):
    with pytest.raises(ProviderError):
        provider(Transport(Response(result))).generate("test")


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_incomplete_or_filtered_output_is_not_accepted(reason):
    with pytest.raises(ProviderError):
        provider(Transport(Response(completion("partial", reason)))).generate("test")


@pytest.mark.parametrize(
    "error",
    [requests.Timeout(), requests.ConnectionError(), requests.RequestException()],
)
def test_transport_failures_are_provider_errors(error):
    with pytest.raises(ProviderError):
        provider(Transport(error)).generate("test")


def test_legacy_generate_requires_explicit_configuration():
    transport = Transport(Response({"response": "legacy"}))
    client = UFCOllamaClient(
        "test-only-key",
        "phi4:latest",
        api_format="ollama_generate",
        api_url="https://example.test/ollama/api/generate",
        transport=transport,
    )
    assert client.invoke("test") == "legacy"
    assert transport.calls[0][1]["json"]["prompt"] == "test"
    assert "messages" not in transport.calls[0][1]["json"]


def test_invalid_api_format_fails_without_http():
    with pytest.raises(ProviderError, match="api_format"):
        provider(Transport(), providers={"ufc": {"api_format": "unknown"}}).generate(
            "test"
        )


def test_cumbuco_structured_repair_and_diagnostics():
    transport = Transport(
        Response(completion("invalid")), Response(completion('{"queries":["Atlas"]}'))
    )
    registry = ProviderRegistry(LLMConfig(provider="ufc", model="phi4:latest"))
    registry.factories["ufc"] = lambda selection, config: UFCAPIProvider(
        selection, config, transport
    )
    assert registry.structured("research", "test", ResearchResult).queries == ["Atlas"]
    assert len(transport.calls) == len(registry.calls) == 2
    assert all(call[1]["json"]["max_tokens"] == 384 for call in transport.calls)
    assert all(
        call["provider"] == "ufc" and call["physical_model"] == "phi4:latest"
        for call in registry.calls
    )
    assert "test-only-key" not in str(registry.calls)


def test_explicit_params_protocol_and_observability_share_production_adapter():
    data = {
        **completion(),
        "usage": {"prompt_tokens": 100, "completion_tokens": 384},
        "model": "phi4:latest",
    }
    transport = Transport(Response(data))
    config = LLMConfig(
        provider="ufc",
        model="phi4:latest",
        providers={"ufc": {"protocol": "openwebui_ollama"}},
    )
    registry = ProviderRegistry(config)
    registry.factories["ufc"] = lambda selection, settings: UFCAPIProvider(
        selection, settings, transport
    )
    assert registry.generate("research", "Teste") == "OK"
    payload = transport.calls[0][1]["json"]
    assert payload["params"] == {"temperature": 0, "max_tokens": 384, "num_ctx": 8192}
    assert "max_tokens" not in payload
    event = registry.calls[0]
    assert event["sent_parameters"] == {"params": payload["params"]}
    assert event["observed"]["usage"]["completion_tokens"] == 384
    assert event["observed"]["finish_reason"] == "stop" and event["output_at_limit"]
    assert event["configured"]["num_ctx"] == 8192
    assert "test-only-key" not in str(event)


def test_missing_usage_stays_unknown_and_invalid_protocol_rejected():
    result = provider(Transport(Response(completion()))).generate_result("test")
    assert result.usage is None and not result.output_at_limit
    with pytest.raises(ProviderError, match="protocol"):
        provider(Transport(), providers={"ufc": {"protocol": "unknown"}}).generate(
            "test"
        )
