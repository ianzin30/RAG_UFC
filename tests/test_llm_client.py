"""Real SDK serialization and SSE handling against an in-memory HTTP transport."""
import json

import httpx
import pytest

import check_llm
import llm_client
from llm_client import (DEFAULT_MODEL, EmptyContentError, LLMAuthenticationError,
                        LLMClient, LLMConfigurationError, LLMConnectionError, LLMError, LLMSettings)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def env_file(tmp_path):
    path = tmp_path / '.env'
    path.write_text('LLM_BASE_URL=https://spark.example.test/api\nLLM_API_KEY=test-only-secret\nLLM_MODEL=' + DEFAULT_MODEL + '\n')
    return path


def make_client(env_file, handler, **kwargs):
    return LLMClient(env_path=env_file, http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def response(content='pong', **message):
    return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 0,
        'model': DEFAULT_MODEL, 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': content, **message}}]})


def test_empty_key_stops_before_sdk_or_network(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('LLM_API_KEY=\n')
    monkeypatch.setattr(llm_client, 'OpenAI', lambda **_: pytest.fail('SDK initialized without key'))
    with pytest.raises(LLMConfigurationError, match='^Preencha LLM_API_KEY no .env$'):
        LLMClient(env_path=env)


def test_environment_precedence_and_secret_not_in_repr(env_file, monkeypatch):
    settings = LLMSettings.from_env(env_file)
    assert settings.api_key == 'test-only-secret'
    assert 'test-only-secret' not in repr(settings)
    assert 'LLM_API_KEY' not in llm_client.os.environ
    monkeypatch.setenv('LLM_MODEL', 'environment-model')
    assert LLMSettings.from_env(env_file).model == 'environment-model'


def test_chat_serializes_standard_and_extra_parameters_without_v1(env_file):
    requests = []
    def handler(request):
        requests.append(request)
        return response(reasoning='private reasoning never returned')
    with make_client(env_file, handler) as client:
        text = client.chat([{'role': 'user', 'content': 'test'}], temperature=0, top_p=.9,
                           max_tokens=128, seed=42, stop=['END'],
                           extra_body={'top_k': 20, 'chat_template_kwargs': {'enable_thinking': False}})
    assert text == 'pong'
    request = requests[0]
    assert str(request.url) == 'https://spark.example.test/api/chat/completions'
    assert request.headers['Authorization'] == 'Bearer test-only-secret'
    body = json.loads(request.content)
    assert body['model'] == DEFAULT_MODEL and body['stream'] is False
    assert body['top_k'] == 20 and 'extra_body' not in body
    assert body['chat_template_kwargs'] == {'enable_thinking': False}
    assert {k: body[k] for k in ('temperature', 'top_p', 'max_tokens', 'seed', 'stop')} == {
        'temperature': 0, 'top_p': .9, 'max_tokens': 128, 'seed': 42, 'stop': ['END']}
    assert request.extensions['timeout']['read'] == 420.0


def test_defaults_preserve_server_reasoning_and_allow_other_models(env_file):
    bodies = []
    def handler(request):
        bodies.append(json.loads(request.content))
        return response()
    with make_client(env_file, handler) as client:
        client.chat([], model='openai/gpt-oss-20b')
    assert bodies[0]['model'] == 'openai/gpt-oss-20b'
    assert bodies[0]['temperature'] == 0 and bodies[0]['max_tokens'] >= 2048
    assert 'chat_template_kwargs' not in bodies[0] and 'reasoning_effort' not in bodies[0]


def test_models_returns_ids_only(env_file):
    def handler(request):
        assert str(request.url) == 'https://spark.example.test/api/models'
        return httpx.Response(200, json={'object': 'list', 'data': [
            {'id': DEFAULT_MODEL, 'object': 'model', 'owned_by': 'lab', 'created': 0}]})
    with make_client(env_file, handler) as client:
        assert client.list_models() == [DEFAULT_MODEL]


@pytest.mark.parametrize('content', [None, '', '  '])
def test_reasoning_without_final_content_is_an_explicit_error(env_file, content):
    with make_client(env_file, lambda _: response(content, reasoning='private')) as client:
        with pytest.raises(EmptyContentError, match='Resposta final vazia'):
            client.chat([])


@pytest.mark.parametrize('status', [429, 500, 503])
def test_only_retryable_http_errors_back_off(env_file, monkeypatch, status):
    calls, waits = [], []
    monkeypatch.setattr(llm_client.time, 'sleep', waits.append)
    def handler(request):
        calls.append(request)
        return response() if len(calls) == 3 else httpx.Response(status, json={'error': 'temporary'})
    with make_client(env_file, handler) as client:
        assert client.chat([]) == 'pong'
    assert len(calls) == 3 and waits == [1., 2.]


@pytest.mark.parametrize('status', [400, 401, 403, 404])
def test_non_retryable_errors_are_clear_and_do_not_leak_server_body(env_file, monkeypatch, status):
    calls = []
    monkeypatch.setattr(llm_client.time, 'sleep', lambda _: pytest.fail('Nonretryable HTTP error retried'))
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={'error': 'echo test-only-secret and sensitive prompt'})
    with make_client(env_file, handler) as client:
        with pytest.raises(LLMError) as error:
            client.chat([])
    assert len(calls) == 1
    assert str(status) in str(error.value)
    assert 'test-only-secret' not in str(error.value) and 'sensitive prompt' not in str(error.value)
    if status in (401, 403):
        assert isinstance(error.value, LLMAuthenticationError) and 'Open WebUI' in str(error.value)


def test_retry_exhaustion_is_bounded(env_file, monkeypatch):
    calls, waits = [], []
    monkeypatch.setattr(llm_client.time, 'sleep', waits.append)
    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={'error': 'busy'})
    with make_client(env_file, handler) as client:
        with pytest.raises(LLMError, match='503'):
            client.chat([])
    assert len(calls) == 3 and waits == [1., 2.]


@pytest.mark.parametrize('error_type', [httpx.ConnectError, httpx.ReadTimeout])
def test_connection_and_unknown_timeout_outcomes_are_not_retried(env_file, error_type):
    calls = []
    def handler(request):
        calls.append(request)
        raise error_type('sensitive raw error', request=request)
    with make_client(env_file, handler) as client:
        with pytest.raises(LLMConnectionError) as error:
            client.chat([])
    assert len(calls) == 1 and 'sensitive' not in str(error.value)
    if error_type is httpx.ConnectError:
        assert 'VPN' in str(error.value)


def events(*deltas):
    return ''.join('data: ' + json.dumps({'id': 'test', 'object': 'chat.completion.chunk', 'created': 0,
        'model': DEFAULT_MODEL, 'choices': [{'index': 0, 'delta': d, 'finish_reason': None}]}) + '\n\n'
        for d in deltas) + 'data: [DONE]\n\n'


def test_stream_yields_final_content_only_and_closes(env_file):
    responses = []
    def handler(request):
        assert json.loads(request.content)['stream'] is True
        r = httpx.Response(200, text=events({'reasoning': 'private'}, {'content': 'po'}, {'content': 'ng'}),
                           headers={'content-type': 'text/event-stream'})
        responses.append(r)
        return r
    with make_client(env_file, handler) as client:
        assert list(client.stream_chat([])) == ['po', 'ng']
    assert responses[0].is_closed


def test_reasoning_only_stream_is_an_explicit_error(env_file):
    with make_client(env_file, lambda _: httpx.Response(200, text=events({'reasoning': 'private'}),
                     headers={'content-type': 'text/event-stream'})) as client:
        with pytest.raises(EmptyContentError, match='sem resposta final'):
            list(client.stream_chat([]))


def test_interrupted_stream_is_not_restarted(env_file):
    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self):
            yield events({'content': 'partial'}).split('data: [DONE]')[0].encode()
            raise httpx.ReadError('sensitive raw error')
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=BrokenStream(), headers={'content-type': 'text/event-stream'})
    with make_client(env_file, handler) as client:
        stream = client.stream_chat([])
        assert next(stream) == 'partial'
        with pytest.raises(LLMConnectionError, match='VPN'):
            next(stream)
    assert len(calls) == 1


def test_provider_parameters_must_be_in_extra_body(env_file):
    with make_client(env_file, lambda _: pytest.fail('Invalid parameters sent')) as client:
        with pytest.raises(LLMConfigurationError, match='extra_body'):
            client.chat([], top_k=20)


def test_check_script_validates_all_three_sequentially_without_reasoning_effort(monkeypatch, capsys):
    active, calls = [], []
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def list_models(self): return list(check_llm.MODELS)
        def chat(self, messages, model=None, **params):
            assert not active
            active.append(model)
            calls.append((model, params))
            assert messages == [{'role': 'user', 'content': 'Responda apenas: pong'}]
            active.pop()
            return 'pong'
    monkeypatch.setattr(check_llm, 'LLMClient', FakeClient)
    assert check_llm.main() == 0
    assert [m for m, _ in calls] == list(check_llm.MODELS)
    assert calls[0][1]['extra_body'] == {'chat_template_kwargs': {'enable_thinking': False}}
    assert all('extra_body' not in p and 'reasoning_effort' not in p for _, p in calls[1:])
    assert capsys.readouterr().out.count('| pong |') == 3


def test_check_script_missing_key_prints_only_actionable_message(monkeypatch, capsys):
    def missing(): raise LLMConfigurationError('Preencha LLM_API_KEY no .env')
    monkeypatch.setattr(check_llm, 'LLMClient', missing)
    assert check_llm.main() == 1
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err == 'Preencha LLM_API_KEY no .env\n'
