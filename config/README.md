# Configuração V2

`config/config.toml` é a configuração compartilhada sem segredos. `.env` na raiz é carregado por `RuntimeConfig` para valores locais.

## LLMs

`[llm]` define provider/modelo, temperatura, timeout, orçamento de saída e limites por papel. `[llm.roles.<papel>]` pode selecionar outro provider/modelo. `[llm.providers.<provider>]` configura o transporte.

Providers disponíveis: `ollama`, `ufc`, `vllm`. Não há fallback automático entre famílias de modelos.

- Ollama local: UI expõe somente `phi4:latest` e `qwen3.5`. A tag física Qwen fica em `llm.providers.ollama.models`.
- UFC: requer `UFC_API_KEY`; endpoint pode ser configurado no provider ou em `UFC_API_URL`.
- vLLM: usa o modelo anunciado por `/v1/models`; `VLLM_BASE_URL` sobrescreve a URL configurada e `VLLM_API_KEY` é opcional.

`[llm_models].options` controla opções de modelos servidos pelo provider ativo. Alterar apenas a seleção/modelo não reindexa documentos. Para trocar de provider, ajuste `[llm]` e as opções aplicáveis.

`num_ctx` é enviado ao Ollama. O contexto máximo do vLLM é configurado ao iniciar seu servidor.

## Retrieval

`[rag_v2]` concentra modelos BGE, device, batch, limites parent/child, dense/sparse, RRF, reranker, memória de subconjuntos, hops e contexto. CPU é o default desta instalação.

Não existem tabelas ativas de splitter V1, seletor LLM ou grounding heurístico. `rag_v2.enabled=false` gera erro explícito: somente V2 é suportada.

## Integrações e segredos

Use `config/.env.example` como template. Google Drive requer credenciais OAuth próprias; UI usa cliente Web e URI de retorno compatível com o endereço publicado. Telegram também aceita o fluxo desktop já existente.

Arquivos de credenciais e tokens são ignorados. `GOOGLE_OAUTH_CREDENTIALS_FILE`, `GOOGLE_OAUTH_TOKEN_FILE` e `GOOGLE_OAUTH_REDIRECT_URI` permitem configurar caminhos/retorno. O token é estado local da implantação.

O tema compartilhado está em `.streamlit/config.toml`; outros arquivos locais dessa pasta são ignorados.
