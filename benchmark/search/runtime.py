"""Verified frozen retrieval and explicit LLM transport; no answer generation."""
import json
import os
from functools import lru_cache
from pathlib import Path
import requests
from transformers import AutoTokenizer

from benchmark.core.artifacts import read_json
from benchmark.core.bootstrap import PROJECT_ROOT, bootstrap_python_path
from benchmark.core.config import load_benchmark_llm
from benchmark.core.reproducibility import CORPUS, sha
from benchmark.selection.run import read_inputs, digest


def load_reference(context_tokenizer='BAAI/bge-m3'):
    bootstrap_python_path()
    from service.rag.v2.Cache import load_bundle
    from service.rag.v2.Config import load_settings
    part, cases, anchors, directory, rules, frozen = next(read_inputs())
    source = frozen['reference']; sig = source['signature']
    if len(cases) != 70 or len(source['results']) != 140:
        raise ValueError('Expected exactly the original 70 answerable questions and both scopes')
    if sha(directory / 'questions.json') != sig['dataset_sha256'] or sha(directory / 'evidence.json') != sig['evidence_sha256'] or sha(rules) != sig['rules_sha256']:
        raise ValueError('Frozen dataset or evaluation changed')
    index = PROJECT_ROOT / 'data/cache/rag_v2' / (sig['index_fingerprint'] + '.npz')
    if sha(index) != sig['index_verification']['active_index_sha256']:
        raise ValueError('Frozen index changed')
    for name, expected in sig['corpus_sha256'].items():
        if sha(CORPUS / name) != expected:
            raise ValueError('Frozen source changed: ' + name)
    _, config = load_settings()
    if config.model_dump() != sig['rag_config']:
        raise ValueError('Retrieval settings changed from frozen reference')
    if (config.search_k, config.rerank_k, config.context_tokens) != (30, 60, 3000):
        raise ValueError('Experiment requires 30 per channel, full union and 3000-token context')
    chunks, parents, catalog, vectors, weights = load_bundle(index)
    rows = {r['key']: r for r in source['results']}
    expected = {f'{c.id}:{s}' for c in cases for s in ('collection', 'oracle_scope')}
    if set(rows) != expected or any(r['status'] != 'ok' for r in rows.values()):
        raise ValueError('Original retrieval is incomplete or contains failures')
    for row in rows.values():
        diag = row['diagnostics']['searches'][0]['diagnostics']
        counts = diag['candidate_counts']
        if counts['union'] != counts['reranked'] or counts['dense'] > 30 or counts['sparse'] > 30:
            raise ValueError('Reference did not rerank full candidate union')
        for item in diag['stages']['reranker']:
            if chunks[item['position']].chunk_id != item['chunk_id']:
                raise ValueError('Frozen ranking references another index')
    tokenizer = AutoTokenizer.from_pretrained(context_tokenizer, local_files_only=True)
    @lru_cache(None)
    def tokens(text):
        return len(tokenizer.encode(text, add_special_tokens=False))
    return {'cases': cases, 'anchors': anchors, 'directory': directory, 'rules_path': rules,
            'source': source, 'rows': rows, 'index': index, 'chunks': chunks, 'parents': parents,
            'catalog': catalog, 'vectors': vectors, 'weights': weights, 'config': config, 'tokens': tokens}


def llm_setup():
    bootstrap_python_path()
    from service.rag.v2.Providers import ProviderRegistry
    cfg, tokenizer_name = load_benchmark_llm()
    if cfg.provider == 'vllm':
        return vllm_setup(cfg, tokenizer_name)
    if cfg.provider == 'ollama':
        return ollama_setup(cfg, tokenizer_name)
    key = os.getenv('UFC_API_KEY')
    if not key:
        raise ValueError('UFC_API_KEY is not configured')
    endpoint = os.getenv('UFC_API_URL') or cfg.providers['ufc']['api_url']
    base = endpoint.rsplit('/api/chat/completions', 1)[0]
    session = requests.Session()
    session.headers.update(Authorization='Bearer ' + key)
    response = session.get(base + '/api/models', timeout=30); response.raise_for_status()
    if cfg.model not in {m['id'] for m in response.json()['data']}:
        raise ValueError('Configured model is not available to this Cumbuco account')
    tags = session.get(base + '/ollama/api/tags', timeout=30); tags.raise_for_status()
    tag = next((m for m in tags.json()['models'] if m['name'] == cfg.model), None)
    if tag is None:
        raise ValueError('Model identity cannot be verified')
    show = session.post(base + '/ollama/api/show', json={'model': cfg.model}, timeout=30); show.raise_for_status()
    details = show.json()
    contexts = [v for k, v in details.get('model_info', {}).items() if k.endswith('.context_length')]
    capacity = max(contexts) if contexts else None
    if capacity and cfg.num_ctx > capacity:
        raise ValueError('Requested context exceeds model capacity')
    # Downloads tokenizer metadata only, never model weights.
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    @lru_cache(None)
    def raw_count(prompt):
        return len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
            tokenize=True, add_generation_prompt=True))
    margin = 512
    def count(prompt):
        return raw_count(prompt) + margin
    registry = ProviderRegistry(cfg); registry.capture_payloads = True
    info = {'provider': cfg.provider, 'model': cfg.model, 'digest': tag.get('digest'),
            'endpoint': endpoint, 'temperature': cfg.temperature, 'num_ctx': cfg.num_ctx,
            'max_output_tokens': cfg.max_output_tokens, 'timeout_seconds': cfg.timeout_seconds,
            'reported_model_capacity': capacity, 'tokenizer': tokenizer_name,
            'reported_model_details': details.get('details'),
            'reported_model_parameters': details.get('parameters'),
            'reported_model_capabilities': details.get('capabilities'),
            'reported_server_template_sha256': digest(details.get('template')),
            'tokenizer_digest': digest(tokenizer.get_vocab()), 'input_safety_margin': margin,
            'input_count_method': 'local model chat template plus 512-token safety margin',
            'identity_limits': 'remote digest reported by Cumbuco, not independent verification of remote weights',
            'context_limits': 'requested num_ctx; server application inferred from transport and reported usage'}
    return registry, count, raw_count, info, session, base


def vllm_setup(cfg, tokenizer_name):
    from service.rag.v2.Providers import ProviderRegistry, Capabilities
    base = (os.getenv('VLLM_BASE_URL') or cfg.providers['vllm']['base_url']).rstrip('/')
    session = requests.Session()
    if os.getenv('VLLM_API_KEY'):
        session.headers.update(Authorization='Bearer ' + os.environ['VLLM_API_KEY'])
    try:
        response = session.get(base + '/models', timeout=30)
    except requests.ConnectionError as exc:
        raise ValueError('vLLM API unavailable; verify the existing tunnel or server. No automatic reconnection.') from exc
    response.raise_for_status()
    model = next((m for m in response.json().get('data', []) if m['id'] == cfg.model), None)
    if model is None:
        raise ValueError('Configured model is not available at the vLLM endpoint')
    capacity = model.get('max_model_len')
    if not isinstance(capacity, int) or capacity <= 0:
        raise ValueError('vLLM must report its served context window')
    if cfg.num_ctx > capacity:
        raise ValueError(f'Requested context {cfg.num_ctx} exceeds served vLLM context {capacity}')
    if cfg.max_output_tokens + 512 >= cfg.num_ctx:
        raise ValueError('Output reserve and 512-token safety margin leave no input budget')
    registry = ProviderRegistry(cfg)
    registry.capture_payloads = True
    provider = registry.resolve('planner')
    # Keep the experiment's message-schema/local-validation contract. Adding
    # server constrained decoding would be a separate intervention.
    provider.capabilities = Capabilities()
    try:
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        template = tokenizer.get_chat_template()
        if not isinstance(template, str) or not template:
            raise ValueError('Tokenizer has no chat template')
        template_kwargs = provider.chat_template_kwargs()
        if template_kwargs and 'enable_thinking' not in template:
            raise ValueError('Tokenizer template does not support configured enable_thinking')
        # Exercise template rendering before any measured calls; never substitute
        # a tokenizer or silently ignore an explicitly configured thinking mode.
        tokenizer.apply_chat_template(provider.build_payload('budget check')['messages'],
            tokenize=True, add_generation_prompt=True, **template_kwargs)
    except Exception as exc:
        raise ValueError(f'Cannot prepare configured vLLM tokenizer/template {tokenizer_name!r}: {exc}') from exc
    @lru_cache(None)
    def raw_count(prompt):
        payload = provider.build_payload(prompt)
        return len(tokenizer.apply_chat_template(payload['messages'],
            tokenize=True, add_generation_prompt=True, **payload.get('chat_template_kwargs', {})))
    margin = 512
    def count(prompt):
        return raw_count(prompt) + margin
    wire = provider.build_payload('')
    info = {'provider': cfg.provider, 'model': cfg.model, 'digest': None,
            'endpoint': base + '/chat/completions', 'temperature': cfg.temperature,
            'num_ctx': cfg.num_ctx, 'max_output_tokens': cfg.max_output_tokens,
            'timeout_seconds': cfg.timeout_seconds, 'reported_model_capacity': capacity,
            'thinking': provider.settings.enable_thinking,
            'sampling': provider.settings.options.model_dump(exclude_none=True),
            'request_parameters': {k: v for k, v in wire.items() if k != 'messages'},
            'reported_model_details': stable_served_metadata(model), 'served_model_metadata_sha256': digest(stable_served_metadata(model)),
            'model_identity_method': 'reported metadata excluding request-generated created and permission fields; no weights attestation',
            'tokenizer': tokenizer_name, 'tokenizer_digest': digest(tokenizer.get_vocab()),
            'tokenizer_template_sha256': digest(template),
            'tokenizer_revision': getattr(tokenizer, 'init_kwargs', {}).get('_commit_hash'),
            'input_safety_margin': margin, 'input_count_method': 'shared request messages and thinking template options plus 512-token safety margin',
            'structured_output_mode': 'schema in user message; local validation; no server response_format',
            'identity_limits': 'served ID/metadata verified; weights digest unavailable',
            'context_limits': 'server max_model_len; client cannot enlarge server context'}
    return registry, count, raw_count, info, session, base


def stable_served_metadata(model):
    # vLLM creates new permission IDs and timestamps on /models requests.
    # They do not identify weights or a server restart. Keep all other fields.
    return {k: v for k, v in model.items() if k not in ('created', 'permission')}


def ollama_setup(cfg, tokenizer_name):
    from service.rag.v2.Providers import ProviderRegistry, Capabilities
    settings = cfg.providers['ollama']
    base = settings['base_url'].rstrip('/')
    session = requests.Session()
    tags = session.get(base + '/api/tags', timeout=30); tags.raise_for_status()
    tag = next((m for m in tags.json()['models'] if m['name'] == cfg.model), None)
    if tag is None:
        raise ValueError('Install the configured local model explicitly before running')
    expected = settings.get('expected_digest')
    if not expected or tag.get('digest') != expected:
        raise ValueError('Local model digest must match benchmark.llm.providers.ollama.expected_digest')
    show = session.post(base + '/api/show', json={'model': cfg.model}, timeout=30); show.raise_for_status()
    details = show.json()
    capacity = max((v for k, v in details.get('model_info', {}).items() if k.endswith('.context_length')), default=0)
    if capacity < cfg.num_ctx:
        raise ValueError('Requested context exceeds reported local model capacity')
    if settings.get('think') is True and 'thinking' not in details.get('capabilities', []):
        raise ValueError('Local model cannot enable requested thinking mode')
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    @lru_cache(None)
    def raw_count(prompt):
        return len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
            tokenize=True, add_generation_prompt=True, enable_thinking=settings.get('think', False)))
    def count(prompt):
        return raw_count(prompt) + 512
    version = session.get(base + '/api/version', timeout=30); version.raise_for_status()
    registry = ProviderRegistry(cfg); registry.capture_payloads = True
    provider = registry.resolve('planner'); provider.resolve()
    provider.capabilities = Capabilities(seed=True)  # schema in prompt, no /api/generate format
    info = {'provider': 'ollama', 'model': cfg.model, 'digest': tag['digest'], 'endpoint': base + '/api/generate',
        'temperature': cfg.temperature, 'num_ctx': cfg.num_ctx, 'max_output_tokens': cfg.max_output_tokens,
        'timeout_seconds': cfg.timeout_seconds, 'thinking': settings.get('think'), 'sampling': settings.get('options', {}),
        'reported_model_capacity': capacity, 'reported_model_details': details.get('details'),
        'reported_model_parameters': details.get('parameters'), 'reported_model_capabilities': details.get('capabilities'),
        'reported_server_template_sha256': digest(details.get('template')), 'server_version': version.json(),
        'tokenizer': tokenizer_name, 'tokenizer_digest': digest(tokenizer.get_vocab()), 'input_safety_margin': 512,
        'input_count_method': 'Qwen chat template with explicit thinking, checked against server usage, plus 512 margin',
        'structured_output_mode': 'schema in prompt; local validation; no server format',
        'context_limits': 'requested window; verify actual residency via /api/ps after synthetic generation'}
    return registry, count, raw_count, info, session, base


def verify_remote_identity(model, session, base):
    if model['provider'] == 'vllm':
        response = session.get(base + '/models', timeout=30)
        response.raise_for_status()
        current = next((m for m in response.json().get('data', []) if m['id'] == model['model']), None)
        if current is None or digest(stable_served_metadata(current)) != model['served_model_metadata_sha256']:
            raise ValueError('Served vLLM model metadata changed during execution')
    else:
        route = '/api/tags' if model['provider'] == 'ollama' else '/ollama/api/tags'
        response = session.get(base + route, timeout=30)
        response.raise_for_status()
        current = next((m for m in response.json()['models'] if m['name'] == model['model']), None)
        if current is None or current['digest'] != model['digest']:
            raise ValueError('Remote model digest changed during execution')
        if model['provider'] == 'ollama':
            show = session.post(base + '/api/show', json={'model': model['model']}, timeout=30)
            show.raise_for_status()
            if digest(show.json().get('template')) != model['reported_server_template_sha256']:
                raise ValueError('Local model template changed during execution')
            version = session.get(base + '/api/version', timeout=30); version.raise_for_status()
            if version.json() != model['server_version']:
                raise ValueError('Local Ollama server version changed during execution')


def build_retriever(reference):
    from service.rag.v2.Retrieval import create_encoder, HybridRetriever, BGEReranker
    from transformers import AutoConfig
    reranker_config = AutoConfig.from_pretrained(reference['config'].reranker_model, local_files_only=True)
    if reranker_config._commit_hash != reference['source']['signature']['reranker']['revision']:
        raise ValueError('Reranker revision differs from frozen reference')
    encoder = create_encoder(reference['config'])
    if encoder.identity != reference['source']['signature']['encoder']:
        raise ValueError('Query encoder identity differs from frozen reference')
    reranker = BGEReranker(reference['config'])
    retriever = HybridRetriever(reference['chunks'], reference['vectors'], reference['weights'],
        encoder, reranker, reference['config'], reference['source']['signature']['index_fingerprint'])
    return retriever


def verify_generation_event(model, event):
    """Verify the wire contract, not just configured values."""
    if model['provider'] == 'vllm':
        if event.get('sent_parameters') != model['request_parameters']:
            raise ValueError('Actual vLLM sampling/thinking/schema payload differs from frozen configuration')
        if event.get('reported_model') != model['model']:
            raise ValueError('Generation model identity differs from frozen vLLM configuration')
        return
    if model['provider'] != 'ollama':
        return
    sent = event.get('sent_parameters') or {}
    expected = {'temperature': model['temperature'], 'num_ctx': model['num_ctx'],
                'num_predict': model['max_output_tokens'], **model['sampling']}
    if sent.get('think') != model['thinking'] or sent.get('options') != expected or sent.get('format') is not None:
        raise ValueError('Actual Ollama thinking/sampling/schema payload differs from frozen configuration')
    if event.get('reported_model') != model['model'] or event.get('digest') != model['digest']:
        raise ValueError('Generation model identity differs from frozen configuration')
