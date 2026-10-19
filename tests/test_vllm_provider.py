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
    settings = kwargs.pop('provider_settings', {'base_url': 'http://127.0.0.1:8000/v1'})
    config = LLMConfig(
        provider="vllm",
        model=MODEL,
        providers={"vllm": settings},
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


@pytest.mark.parametrize('thinking', [True, False, None])
def test_optional_thinking_and_sampling_payload(thinking):
    options = dict(top_p=0.9, top_k=20, min_p=0.0, seed=42,
                   presence_penalty=0.2, frequency_penalty=-0.2,
                   repetition_penalty=1.1, stop=['END'])
    settings = {'options': options}
    if thinking is not None:
        settings['enable_thinking'] = thinking
    transport = FakeTransport()
    provider = make_provider(transport, provider_settings=settings)
    provider.generate('question')
    payload = transport.calls[-1][2]['json']
    assert all(payload[key] == value for key, value in options.items())
    assert 'num_ctx' not in payload
    assert payload.get('chat_template_kwargs') == (
        None if thinking is None else {'enable_thinking': thinking})
    assert provider.last_generation.sent_parameters == {k: v for k, v in payload.items() if k != 'messages'}
    assert provider.chat_template_kwargs() == payload.get('chat_template_kwargs', {})


def test_absent_sampling_options_are_not_sent():
    provider = make_provider(FakeTransport())
    assert set(provider.build_payload('x')) == {'model', 'messages', 'stream', 'temperature', 'max_tokens'}


@pytest.mark.parametrize('settings', [
    {'enable_thinking': 'false'}, {'enable_thinking': 1}, {'unknown': 1},
    {'options': {'top_p': 0.0}}, {'options': {'top_p': 1.1}},
    {'options': {'top_k': 0}}, {'options': {'top_k': 2.5}},
    {'options': {'seed': True}}, {'options': {'seed': '42'}},
    {'options': {'min_p': -0.1}}, {'options': {'presence_penalty': 3.0}},
    {'options': {'frequency_penalty': -3.0}}, {'options': {'repetition_penalty': 0.0}},
    {'options': {'repetition_penalty': float('inf')}},
    {'options': {'stop': []}}, {'options': {'stop': ['']}},
    {'options': {'temperature': 0.0}}, {'options': {'unknown': 1}},
])
def test_invalid_vllm_settings_fail_before_transport(settings):
    from pydantic import ValidationError
    transport = FakeTransport()
    with pytest.raises(ValidationError):
        make_provider(transport, provider_settings=settings)
    assert not transport.calls


@pytest.mark.parametrize('field', ['reasoning', 'reasoning_content'])
@pytest.mark.parametrize('bad_output', [None, 'empty', 'length'])
def test_response_diagnostics_survive_empty_and_truncated_outputs(field, bad_output):
    content = '' if bad_output == 'empty' else 'FINAL'
    response = {'model': MODEL, 'usage': {'prompt_tokens': 12, 'completion_tokens': 47},
                'choices': [{'message': {'content': content, field: 'PRIVATE'},
                             'finish_reason': 'length' if bad_output == 'length' else 'stop'}]}
    provider = make_provider(FakeTransport(completion=response))
    if bad_output:
        with pytest.raises(ProviderError):
            provider.generate('x')
    else:
        assert provider.generate('x') == 'FINAL'
    recorded = provider.last_generation
    assert recorded.thinking == 'PRIVATE' and recorded.text == content
    assert recorded.reported_model == MODEL and recorded.output_at_limit
    assert recorded.usage == response['usage']
    assert recorded.sent_parameters['max_tokens'] == 47


@pytest.mark.parametrize('exception', ['timeout', 'connection', 'http'])
def test_transport_failure_is_explicit_and_never_retried(exception):
    import requests
    class BrokenTransport(FakeTransport):
        def request(self, method, url, **kwargs):
            if method == 'GET':
                return super().request(method, url, **kwargs)
            self.calls.append((method, url, kwargs))
            errors = {'timeout': requests.Timeout, 'connection': requests.ConnectionError,
                      'http': requests.HTTPError}
            raise errors[exception]('synthetic failure')
    transport = BrokenTransport()
    provider = make_provider(transport)
    with pytest.raises(ProviderError, match='synthetic failure'):
        provider.generate('x')
    assert len(transport.calls) == 2
    assert provider.last_generation.sent_parameters['model'] == MODEL


def test_registry_records_reasoning_and_usage_on_failed_generation():
    registry = ProviderRegistry(LLMConfig(provider='vllm', model=MODEL))
    provider = registry.resolve('planner')
    provider.transport = FakeTransport(completion={'model': MODEL, 'usage': {'completion_tokens': 512},
        'choices': [{'message': {'content': '', 'reasoning': 'PRIVATE'}, 'finish_reason': 'length'}]})
    registry.capture_payloads = True
    with pytest.raises(ProviderError):
        registry.generate('planner', 'question')
    event = registry.calls[-1]
    assert event['status'] == 'error' and event['thinking'] == 'PRIVATE'
    assert event['usage']['completion_tokens'] == 512
    assert event['finish_reason'] == 'length' and event['output_at_limit']
    assert event['raw_response'] == '' and event['reported_model'] == MODEL
    assert event['observed']['model'] == MODEL and event['observed']['usage'] == event['usage']


def test_reported_model_mismatch_fails_with_diagnostics():
    provider = make_provider(FakeTransport(completion={'model': 'unexpected',
        'choices': [{'message': {'content': 'OK'}, 'finish_reason': 'stop'}]}))
    with pytest.raises(ProviderError, match='different model'):
        provider.generate('x')
    assert provider.last_generation.reported_model == 'unexpected'
