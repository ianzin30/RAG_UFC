# Configuração V2

`config/config.toml` é a configuração compartilhada sem segredos. `.env` na raiz é carregado por `RuntimeConfig` para valores locais.

## LLMs

`[llm]` define provider/modelo, temperatura, timeout, orçamento de saída e limites por papel. `[llm.roles.<papel>]` pode selecionar outro provider/modelo. `[llm.providers.<provider>]` configura o transporte.

Providers disponíveis: `ollama`, `ufc`, `vllm`. Não há fallback automático entre famílias de modelos.

- Ollama local: UI expõe somente `phi4:latest` e `qwen3.5`. A tag física Qwen fica em `llm.providers.ollama.models`.
- UFC/Cumbuco: Open WebUI via `POST /api/chat/completions`, com `messages`, `stream=false` e resposta em `choices[0].message.content`. Requer `UFC_API_KEY`; `UFC_API_URL` tem precedência sobre `llm.providers.ufc.api_url`.
- vLLM: usa o modelo anunciado por `/v1/models`; `VLLM_BASE_URL` sobrescreve a URL configurada e `VLLM_API_KEY` é opcional.

`[llm_models].options` controla opções de modelos servidos pelo provider ativo. Alterar apenas a seleção/modelo não reindexa documentos. Para trocar de provider, ajuste `[llm]` e as opções aplicáveis.

`num_ctx` é enviado ao Ollama e ao Cumbuco quando o protocolo `openwebui_ollama` estiver selecionado. O contexto máximo do vLLM é configurado ao iniciar seu servidor.

### Usar Cumbuco no Streamlit/Telegram

Na `.env` da raiz, preencha `UFC_API_KEY` com uma chave da sua conta Open WebUI (Configurações > Conta). Se a opção estiver desabilitada, solicite acesso ao administrador. Não copie cookies de sessão nem versione a chave. O endpoint padrão é `https://cumbuco.ollama.atlab.ufc.br/api/chat/completions`.

Em `config/config.toml`, substitua somente `provider` e `model` em `[llm]`, mantendo os demais limites:

```toml
[llm]
provider = "ufc"
model = "phi4:latest"
```

Substitua também `[llm_models].options` pelas opções realmente disponíveis no Cumbuco, por exemplo:

```toml
[llm_models]
options = [{ label = "Phi-4 (Cumbuco)", model_name = "phi4:latest" }]
```

Reinicie a aplicação para recarregar configuração e serviços. Isso não muda retrieval/índices, nem exige reindexação. Providers específicos em `[llm.roles]`, se houver, continuam prevalecendo para seus papéis.

Teste uma geração isolada, sem trocar o provider padrão nem executar benchmark:

```sh
uv run --no-sync python scripts/check_ufc.py --model phi4:latest
```

O script envia uma única chamada não-streaming. Sem chave, falha antes do HTTP. `401/403` indica autenticação/permissão; `502` indica falha do gateway. Os testes automatizados usam mocks; uma resposta real do navegador não valida a chave da aplicação.

O adapter não presume JSON schema nativo: usa parsing/validação e reparo limitado compartilhados. O protocolo precisa ser explícito:

```toml
[llm.providers.ufc]
api_format = "chat"
protocol = "openwebui_ollama"
```

Nesse protocolo envia `params = {temperature, max_tokens, num_ctx}`. Para outro serviço OpenAI-compatible, `protocol = "openai_chat"` mantém temperatura/limite na raiz e não inventa controle de contexto. Não envia IDs de chats, cookies ou estado do navegador e não há fallback automático.

Os diagnostics separam `configured`, `sent_parameters` e `observed`. `observed.num_ctx = null` significa que o serviço não comprovou a janela efetiva; uso reportado não equivale a medir truncamento. `output_at_limit` sinaliza saída no limite mesmo com término `stop`. Contagens BGE de contexto são aproximações do tokenizer dos embeddings, não do gerador.

Para uma implantação antiga que ainda usa `/ollama/api/generate`, configure explicitamente `llm.providers.ufc.api_format = "ollama_generate"` e sua URL antiga. O padrão agora é `"chat"`. Documentação do contrato: [API Open WebUI](https://docs.openwebui.com/reference/api-endpoints/).

## Retrieval

`[rag_v2]` concentra modelos BGE, device, batch, limites parent/child, dense/sparse, RRF, reranker, memória de subconjuntos, hops e contexto. CPU é o default desta instalação.

A configuração ativa usa EmbeddingGemma na busca densa via Ollama local,
BGE-M3 na busca esparsa e BGE-Reranker na ordenação. Com `search_k = 30` e
`rerank_k = 60`, toda a união deduplicada das duas buscas chega ao reranker
(até 60 trechos). Se aumentar `search_k`, ajuste `rerank_k` para pelo menos
duas vezes esse valor para continuar avaliando a união completa.
O chunking permanece `legacy` e o contexto permanece em 3.000 tokens.

Ollama precisa estar disponível em `http://localhost:11434`, com
`embeddinggemma:latest` instalado. Reinicie a aplicação para recarregar os
serviços. A troca do encoder usa um cache separado; coleções sem cache dessa
configuração serão indexadas ao serem carregadas. Os índices anteriores são
preservados.

Não existem tabelas ativas de splitter V1, seletor LLM ou grounding heurístico. `rag_v2.enabled=false` gera erro explícito: somente V2 é suportada.

## Integrações e segredos

Use `config/.env.example` como template. Google Drive requer credenciais OAuth próprias; UI usa cliente Web e URI de retorno compatível com o endereço publicado. Telegram também aceita o fluxo desktop já existente.

Arquivos de credenciais e tokens são ignorados. `GOOGLE_OAUTH_CREDENTIALS_FILE`, `GOOGLE_OAUTH_TOKEN_FILE` e `GOOGLE_OAUTH_REDIRECT_URI` permitem configurar caminhos/retorno. O token é estado local da implantação.

O tema compartilhado está em `.streamlit/config.toml`; outros arquivos locais dessa pasta são ignorados.

## Interface LLM do benchmark

`[benchmark.llm]` seleciona o modelo usado por `python -m benchmark search`,
independentemente do `[llm]` da aplicação. A interface está configurada para
vLLM na DGX Spark, com `nvidia/Qwen3.6-35B-A3B-NVFP4` e URL
`http://localhost:8000/v1`. Isso não inicia nem aprova um experimento.

`[benchmark.llm.providers.vllm]` define `base_url` e `enable_thinking`.
`[benchmark.llm.providers.vllm.options]` aceita `top_p`, `top_k`, `min_p`, `seed`,
`presence_penalty`, `frequency_penalty`, `repetition_penalty` e `stop`.
Somente opções presentes são enviadas; chaves desconhecidas e valores inválidos
falham explicitamente. `enable_thinking = true/false` liga/desliga reasoning;
ausência usa o padrão do template do servidor. A contagem local usa o mesmo modo.

Temperatura, saída máxima, tokenizer, orçamento local e timeout pertencem a
`[benchmark.llm]`. A saída inclui reasoning e resposta final. No vLLM, `num_ctx`
limita o orçamento do cliente (entrada + saída + margem de 512 tokens), sem
alterar o contexto máximo do servidor. Os 3.000 tokens de evidência em
`[rag_v2].context_tokens` são independentes e contados pelo tokenizer BGE.

`VLLM_BASE_URL` tem precedência nos dois fluxos; `VLLM_API_KEY` é opcional.
A URL efetiva e os parâmetros enviados são registrados sem cabeçalhos de
autenticação. Modelos ausentes, API indisponível ou tokenizer incompatível
bloqueiam a preparação; não há troca automática de modelo, tokenizer ou provedor,
nem abertura de túnel. Preparar o tokenizer pode baixar seus arquivos de metadados,
mas não pesos do modelo.

O benchmark valida JSON localmente. O reasoning retornado é diagnóstico separado:
não entra no contexto documental ou na próxima observação. Erros preservam os
dados retornados de uso, término e parâmetros. Não é possível afirmar a
identidade dos pesos ou parâmetros internos do servidor apenas pela API.

A rodada local Qwen3 4B foi interrompida. Seus parâmetros históricos continuam nas
assinaturas e snapshots salvos; a configuração atual não pode retomar aquela
rodada. Veja [interface e estudos do benchmark](../benchmark/README.md) para o
exemplo completo. Novas chamadas de geração ficam para o próximo plano.

A geração do benchmark foi congelada no perfil
`qwen36_spark_greedy_no_thinking_v1`: temperatura 0, reasoning desligado,
janela local 16.384, saída máxima 4.096 e margem 512. As penalidades são
explicitamente neutras. Houve uma chamada sintética pelo adaptador e auditoria
de tokenização; ainda não houve uma nova rodada de qualidade.
Veja a [base auditada](../docs/qwen36_generation_base_2026-10-13.md). Mudanças
exigem outro perfil e diretório, sem reescrever os snapshots históricos.

## Chat com a Spark

O perfil da aplicação agora usa `[llm.providers.spark]`. As opções operacionais ficam em `[streamlit.*]`, com launcher `.venv/bin/python run_streamlit.py`. Veja [configuração e recuperação do chat](../docs/chat_spark.md). O benchmark mantém seu perfil próprio; assinaturas antigas continuam exigindo os snapshots originais.
