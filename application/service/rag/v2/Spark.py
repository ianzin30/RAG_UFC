"""Application Spark provider. No dependency on experimental runners."""
from functools import lru_cache

from .Config import SparkSettings
from .Providers import VLLMProvider, ProviderError, GenerationResult, Capabilities


@lru_cache(maxsize=4)
def load_tokenizer(name):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    try:
        directory = snapshot_download(name, local_files_only=True)
        return AutoTokenizer.from_pretrained(directory, local_files_only=True)
    except Exception:
        raise ProviderError('Tokenizer Qwen indisponível no cache local. Instale os arquivos do tokenizer antes de iniciar o chat.') from None


class InputBudgetError(ProviderError):
    code = 'input_budget_exceeded'
    @property
    def public_message(self):
        return str(self)


class SparkProvider(VLLMProvider):
    # JSON instructions + local Pydantic/reference validation. Do not assume the
    # gateway implements server-side schema grammars, especially empty enums.
    capabilities = Capabilities(structured_output=False, seed=True)

    def __init__(self, selection, config, *, client=None, tokenizer=None):
        from llm_client import LLMClient, LLMSettings
        from ...RuntimeConfig import read_secret
        self.selection, self.config = selection, config
        self.settings = SparkSettings.model_validate(config.providers.get('spark', {}))
        self.base_url = self.settings.base_url.rstrip('/')
        self.physical_model = None
        self.served_models = []
        self.tokenizer = tokenizer
        key = read_secret(self.settings.api_key_env) if client is None else 'injected'
        if not key:
            raise ProviderError('Preencha LLM_API_KEY no .env')
        self.client = client or LLMClient(settings=LLMSettings(self.base_url, key, selection.model),
                                          timeout=config.timeout_seconds, max_retries=2)

    def identity(self):
        return {'provider': 'spark', 'logical_model': self.selection.model,
                'physical_model': self.physical_model, 'digest': None,
                'endpoint': self.base_url + '/chat/completions'}

    def resolve(self):
        if self.physical_model is not None:
            return
        self.served_models = self.client.list_models()
        if self.selection.model not in self.served_models:
            raise ProviderError('O modelo configurado não está disponível na Spark. Confira o perfil da aplicação.')
        self.tokenizer = self.tokenizer or load_tokenizer(self.settings.tokenizer)
        self.physical_model = self.selection.model

    def generate(self, prompt, schema=None):
        return self.generate_result(prompt, schema).text

    def generate_result(self, prompt, schema=None):
        self.resolve()
        if schema is not None:
            import json
            prompt += '\nReturn only JSON matching this schema:\n' + json.dumps(schema, ensure_ascii=False)
        payload = self.build_payload(prompt, None)
        messages = payload.pop('messages')
        payload.pop('stream')
        # The exact chat template is counted before every request, including JSON repair.
        count = len(self.tokenizer.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=True, **self.chat_template_kwargs()))
        self.last_generation = GenerationResult(text='', identity=self.identity(), sent_parameters=dict(payload),
            server_timings={'transport_attempts': 0, 'input_tokens_checked': count})
        if count + self.config.max_output_tokens + self.settings.input_margin > self.config.num_ctx:
            raise InputBudgetError(f'Entrada excede a janela local: {count} + {self.config.max_output_tokens} de saída + {self.settings.input_margin} de margem > {self.config.num_ctx}. Esta chamada ao modelo não foi enviada.')
        standard = {k: v for k, v in payload.items() if k in {'model', 'temperature', 'top_p', 'max_tokens', 'seed', 'stop', 'presence_penalty', 'frequency_penalty', 'response_format'}}
        extra = {k: v for k, v in payload.items() if k not in standard}
        try:
            completion = self.client.chat_with_metadata(messages, **standard, extra_body=extra)
        finally:
            self.last_generation.server_timings['transport_attempts'] = getattr(self.client, 'last_request_attempts', 0)
        if completion.get('model') and completion['model'] != self.physical_model:
            raise ProviderError('A Spark informou um modelo diferente do configurado.')
        result = self.last_generation
        result.text = completion['text']
        result.usage = completion.get('usage')
        result.reported_model = completion.get('model')
        result.finish_reason = completion.get('finish_reason')
        result.output_at_limit = result.finish_reason == 'length'
        result.server_timings = {'transport_attempts': completion.get('transport_attempts', 1), 'input_tokens_checked': count}
        return result
