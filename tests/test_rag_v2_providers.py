import pytest
from application.service.rag.v2.Config import LLMConfig, ModelSelection
from application.service.rag.v2.Providers import (
    OllamaProvider,
    ProviderRegistry,
    Capabilities,
    ProviderError,
)
from application.service.rag.v2.Models import ResearchResult


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Transport:
    def __init__(self, names):
        self.names, self.payloads = names, []

    def request(self, method, url, **kwargs):
        self.payloads.append(kwargs)
        return Response(
            {"models": [{"name": n, "digest": "digest"} for n in self.names]}
            if method == "GET"
            else {"response": "ok"}
        )


def test_qwen_logical_name_resolves_only_in_adapter():
    config = LLMConfig(
        model="qwen3.5", providers={"ollama": {"models": {"qwen3.5": "qwen3.5:4b"}}}
    )
    provider = OllamaProvider(
        ModelSelection(model="qwen3.5"), config, Transport(["qwen3.5:4b", "qwen3.5:9b"])
    )
    assert provider.generate("test") == "ok"
    assert provider.identity() == {
        "provider": "ollama",
        "logical_model": "qwen3.5",
        "physical_model": "qwen3.5:4b",
        "digest": "digest",
    }


def test_qwen_ambiguous_or_missing_does_not_fallback():
    for names in (["qwen3.5:4b", "qwen3.5:9b"], ["llama3:8b"]):
        with pytest.raises(ProviderError):
            OllamaProvider(
                ModelSelection(model="qwen3.5"), LLMConfig(), Transport(names)
            ).generate("test")


def test_structured_output_repair_is_bounded_and_instrumented():
    class Fake:
        capabilities = Capabilities()

        def __init__(self, *args):
            self.n = 0

        def identity(self):
            return {
                "provider": "fake",
                "logical_model": "test",
                "physical_model": "test",
            }

        def generate(self, prompt, schema=None):
            self.n += 1
            return "invalid" if self.n == 1 else '{"queries":["next"]}'

    registry = ProviderRegistry(LLMConfig(provider="fake"))
    registry.factories["fake"] = Fake
    assert registry.structured("research", "test", ResearchResult).queries == ["next"]
    assert len(registry.calls) == 2
    assert all(call["provider"] == "fake" for call in registry.calls)


def test_ufc_adapter_uses_same_high_level_contract(monkeypatch):
    from application.service.rag.v2.Providers import UFCAPIProvider
    from application.service import UfcOllama

    calls = []

    class Client:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def invoke(self, prompt):
            return '{"queries":["Atlas"]}'

        def invoke_with_metadata(self, prompt):
            return {
                "text": self.invoke(prompt),
                "usage": None,
                "sent_parameters": None,
                "finish_reason": None,
                "output_at_limit": False,
            }

    monkeypatch.setenv("UFC_API_KEY", "fake-test-key")
    monkeypatch.setattr(UfcOllama, "UFCOllamaClient", Client)
    registry = ProviderRegistry(LLMConfig(provider="ufc", model="future-model"))
    assert registry.structured("research", "query", ResearchResult).queries == ["Atlas"]
    assert calls[0]["model_name"] == "future-model"
    assert registry.calls[0]["provider"] == "ufc"


def test_role_selection_and_structured_retry_exhaustion():
    class Invalid:
        capabilities = Capabilities()

        def __init__(self, selection, config):
            self.model = selection.model

        def identity(self):
            return {"provider": "fake", "logical_model": self.model}

        def generate(self, prompt, schema=None):
            return "not JSON"

    registry = ProviderRegistry(
        LLMConfig(
            provider="fake",
            model="default",
            roles={"verification": ModelSelection(provider="fake", model="verifier")},
        )
    )
    registry.factories["fake"] = Invalid
    with pytest.raises(ProviderError, match="bounded repair"):
        registry.structured("verification", "test", ResearchResult)
    assert len(registry.calls) == 2
    assert all(item["logical_model"] == "verifier" for item in registry.calls)


def test_facade_provider_model_switch_does_not_rebuild_index(monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[1] / "application")
    )
    from service.rag.RagService import RAGService

    monkeypatch.delenv("UFC_API_KEY", raising=False)
    service = RAGService()
    marker = object()
    service._v2.retriever = marker
    service.set_model("qwen3.5")
    assert service._v2.retriever is marker
    assert service._v2.providers.config.model == "qwen3.5"


def test_benchmark_ollama_thinking_sampling_and_failure_usage():
    class ThinkingTransport:
        def __init__(self, length=False):
            self.payload = None; self.length = length
        def request(self, method, url, **kwargs):
            if url.endswith('/api/tags'):
                return Response({'models': [{'name': 'qwen3:4b', 'digest': 'd'}]})
            if url.endswith('/api/show'):
                return Response({'capabilities': ['completion', 'thinking']})
            self.payload = kwargs['json']
            return Response({'model': 'qwen3:4b', 'response': '' if self.length else '{"queries":[]}',
                'thinking': 'hidden analysis', 'prompt_eval_count': 12, 'eval_count': 4096 if self.length else 30,
                'done_reason': 'length' if self.length else 'stop', 'eval_duration': 1000000000})
    config = LLMConfig(model='qwen3:4b', temperature=.6, max_output_tokens=4096,
        providers={'ollama': {'think': True, 'options': {'top_p': .95, 'top_k': 20, 'min_p': 0., 'seed': 42}}})
    for length in (False, True):
        transport = ThinkingTransport(length)
        registry = ProviderRegistry(config); registry.capture_payloads = True
        from application.service.rag.v2.Providers import Capabilities
        provider = registry.resolve('planner'); provider.transport = transport
        provider.capabilities = Capabilities(seed=True)
        if length:
            with pytest.raises(ProviderError, match='exceeded'):
                registry.generate('planner', 'test', schema={'type': 'object'})
        else:
            registry.generate('planner', 'test', schema={'type': 'object'})
        assert transport.payload['think'] is True and 'format' not in transport.payload
        assert transport.payload['options']['seed'] == 42 and transport.payload['options']['top_k'] == 20
        assert registry.calls[-1]['usage']['prompt_tokens'] == 12
        assert registry.calls[-1]['thinking'] == 'hidden analysis'
        assert registry.calls[-1]['server_timings']['eval_duration'] == 1000000000
        assert registry.calls[-1]['output_at_limit'] is length
    app_transport = ThinkingTransport()
    provider = OllamaProvider(ModelSelection(model='qwen3:4b'), LLMConfig(), app_transport)
    provider.generate('app')
    assert app_transport.payload['think'] is False
