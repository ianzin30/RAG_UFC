# RAG UFC

Aplicação Streamlit com RAG V2, ingestão local/Google Drive, scraping e Telegram.

## Executar

Python 3.11 e [uv](https://docs.astral.sh/uv/) são necessários.

```sh
uv sync --frozen --no-dev
uv run --no-sync streamlit run application/app.py
```

A configuração sem segredos está em `config/config.toml`. Para credenciais de integrações, copie `config/.env.example` para `.env` e preencha somente o necessário. vLLM sem autenticação não exige API key.

O provider `ufc` também suporta o Cumbuco/Open WebUI via `/api/chat/completions`, com `UFC_API_KEY`. Veja [como ativar e testar](config/README.md#usar-cumbuco-no-streamlittelegram). vLLM permanece o padrão; Ollama local continua disponível.

O primeiro carregamento de uma coleção baixa os modelos BGE de embedding/reranking, se ainda não estiverem no cache externo do Hugging Face. Documentos e índices são criados em `data/` e não acompanham o clone.

## Teste de conexão e resposta dos modelos da Spark

O cliente reutilizável `llm_client.py` acessa a API OpenAI-compatible do Open WebUI
em `https://spark.ollama.atlab.ufc.br/api`, usando o SDK `openai`.
O modelo prioritário é `nvidia/Qwen3.6-35B-A3B-NVFP4`.
A `.env.example` da raiz contém as três variáveis `LLM_BASE_URL`, `LLM_API_KEY`
e `LLM_MODEL`. Preencha somente sua chave em `.env`; esse arquivo é ignorado pelo
Git. Variáveis exportadas no ambiente têm precedência sobre `.env`.

```sh
uv sync --frozen
.venv/bin/python check_llm.py
```

O teste lista somente os IDs anunciados e envia “Responda apenas: pong” aos três
modelos, um de cada vez, imprimindo resposta e duração. Usa temperatura zero e
seed 42. No Qwen3.6, desliga thinking para esse teste; no gpt-oss usa o padrão do
servidor, sem enviar `reasoning_effort`. Chave vazia interrompe antes do HTTP com
`Preencha LLM_API_KEY no .env`. HTTP 401/403 exige verificar chave/permissão ou se
as chaves de API foram desligadas no Open WebUI. Falha de conexão orienta verificar
a VPN do laboratório.

Uso em código, sem registrar prompts ou raciocínio:

```python
from llm_client import chat, stream_chat

messages = [{"role": "user", "content": "Responda apenas: pong"}]
params = {
    "temperature": 0,
    "top_p": 0.9,
    "seed": 42,
    "max_tokens": 128,
    "extra_body": {
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    },
}
print(chat(messages, **params))
for piece in stream_chat(messages, **params):
    print(piece, end="", flush=True)
```

`chat` devolve apenas `message.content`; `stream_chat` entrega apenas fragmentos
de `delta.content` pelo streaming do SDK
([documentação oficial](https://developers.openai.com/api/docs/guides/streaming-responses)).
Para várias chamadas, reutilize `with LLMClient() as client`.
Sem `extra_body`, o padrão de reasoning do servidor é preservado. Use pelo menos
2.048 tokens de saída quando mantiver o raciocínio ligado; resposta final vazia
gera erro explícito, inclusive em streaming. `enable_thinking` só foi validado
previamente pelo laboratório no Qwen3.6; não é enviado aos outros modelos.

O timeout é de 420 segundos. Somente HTTP 429 e 5xx têm até duas novas tentativas,
com esperas de 1 e 2 segundos. Timeout, falha de conexão e interrupção de streaming
não são repetidos automaticamente. O cliente não registra chave, prompts,
raciocínio ou corpos de erro do servidor.

Esse cliente pode ser usado pelos próximos testes; não altera automaticamente o
provider da aplicação ou a configuração congelada do benchmark. A configuração
de outras integrações continua documentada em `config/README.md` e
`config/.env.example`.

## Arquitetura e instalação na VM

- [Estrutura e implantação](docs/README.md)
- [Pipeline V2](docs/pipeline.md)
- [Configuração](config/README.md)
- [Avaliação](docs/benchmarking.md)
- [Precisão e evidências](docs/document_retrieval_precision.md)

## Desenvolvimento

```sh
uv sync --frozen
uv run python -m pytest -q
```

O repositório mantém testes, fixtures e ferramentas V2. O pipeline V1 foi aposentado; resultados históricos locais não são apagados.

## Testar o chat com a Spark

Execute `.venv/bin/python run_streamlit.py`. Veja [configuração, recuperação do histórico e testes](docs/chat_spark.md). O Streamlit mantém o RAG V2, com janela local de 16.384 tokens e contexto documental de 6.000 tokens, sem integração do controlador experimental.
