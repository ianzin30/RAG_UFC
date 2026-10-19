"""Central experiment LLM settings, independent of application model roles."""
from benchmark.core.bootstrap import bootstrap_python_path


def load_planner_input_format():
    bootstrap_python_path()
    from service.RuntimeConfig import _read_config_document
    from service.rag.v2.AdaptiveRetrieval import INPUT_FORMATS
    value = _read_config_document().get('benchmark', {}).get('planner', {}).get('input_format', 'legacy_v1')
    if value not in INPUT_FORMATS:
        raise ValueError('Unknown benchmark planner input format')
    return value


def load_benchmark_llm():
    bootstrap_python_path()
    from service.RuntimeConfig import _read_config_document
    from service.rag.v2.Config import LLMConfig
    document = _read_config_document()
    values = dict(document['benchmark']['llm'])
    tokenizer = values.pop('tokenizer')
    if values.get('provider') not in {'ufc', 'vllm', 'ollama'}:
        raise ValueError('Search experiments support UFC, vLLM or Ollama; no provider fallback')
    overrides = values.pop('providers', {})
    providers = {k: dict(v) for k, v in document['llm']['providers'].items()}
    for name, settings in overrides.items():
        providers[name] = {**providers.get(name, {}), **settings}
    cfg = LLMConfig.model_validate({**values, 'providers': providers,
        'roles': {}, 'role_max_output_tokens': {'planner': values['max_output_tokens']}})
    if cfg.provider == 'ufc' and cfg.providers['ufc'].get('protocol') != 'openwebui_ollama':
        raise ValueError('Cumbuco requires the validated Open WebUI params envelope')
    return cfg, tokenizer
