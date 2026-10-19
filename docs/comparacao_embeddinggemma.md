# Comparação de retrieval: BGE-M3 e EmbeddingGemma

O adaptador `application/service/rag/v2/OllamaEmbeddings.py` permite usar
EmbeddingGemma na busca densa via `/api/embed` da Ollama. A busca esparsa e o
tokenizer de chunking continuam usando BGE-M3; o reranker continua sendo
`BAAI/bge-reranker-v2-m3`.

Essa composição permite mudar os embeddings densos sem mudar simultaneamente
chunking, vocabulário esparso, fusão, reranking e seleção de contexto.

## Experimento controlado

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m benchmark.embedding_comparison \
  --baseline-dir benchmark/results/runs/retrieval_isolated_2026-10-05_fresh \
  --output-dir benchmark/results/runs/embeddinggemma_dense_2026-10-05
```

O runner reutiliza os chunks, parents, catálogo e pesos esparsos do índice BGE
congelado. Só recalcula os vetores densos e grava outro bundle, com fingerprint
que inclui o hash do bundle original, a identidade do modelo Ollama e os
formatos de entrada. Não altera o bundle original nem a configuração ativa.

O EmbeddingGemma instalado é identificado por seu digest, sua quantização e a
versão da Ollama. São usados 768 componentes e os prefixos recomendados:

- Pergunta: `task: search result | query: `.
- Documento: `title: none | text: `.

O truncamento automático está desativado. Erros HTTP, dimensão incorreta,
valores não finitos, vetores nulos ou mudança do digest não recebem fallback.

Referências: [formatos de entrada do Google](https://ai.google.dev/gemma/docs/embeddinggemma/model_card#prompt-instructions)
e [API de embeddings da Ollama](https://docs.ollama.com/api/embed).

São executadas as mesmas 70 perguntas respondíveis, com os mesmos históricos,
em coleção completa e escopo correto fornecido: 140 avaliações. O gerador e a
reconstrução de chunks ficam bloqueados. O orçamento de contexto permanece
igual ao baseline. Ao final, o runner verifica que as perguntas, os escopos e os
rankings esparsos são idênticos aos do baseline.

## Resultados

No diretório informado em `--output-dir`:

- `index_build.json`: identidade e status da construção do índice separado.
- `retrieval.json`: rankings e cobertura de evidências por pergunta/condição.
- `summary.json`: métricas agregadas por etapa e categoria.
- `comparison.json` e `comparison.md`: falhas por categoria nos dois modelos,
  IDs que melhoraram e IDs que regrediram.
- `code.zip`: snapshot do código e da configuração da execução.

Para gerar também o relatório individual da condição EmbeddingGemma:

```sh
.venv/bin/python -m benchmark.category_report \
  --run-dir benchmark/results/runs/embeddinggemma_dense_2026-10-05
```

Falha significa cobertura literal incompleta das evidências anotadas no contexto
final. Não significa necessariamente resposta errada; evidências equivalentes
não anotadas e diferenças de representação estrutural precisam de revisão.
O estudo não mede geração de respostas nem busca multi-hop em rodadas dependentes.
As latências locais não são uma comparação de hardware equivalente: o BGE usa
CPU nesta configuração e a Ollama pode usar GPU.

## Uso na aplicação

Em 2026-10-06, a configuração da aplicação passou a usar EmbeddingGemma denso
com BGE-M3 esparso e a união completa de candidatos, após a rodada controlada.
Estas chaves estão ativas na seção `[rag_v2]` de `config/config.toml`:

```toml
embedding_provider = "ollama"
embedding_ollama_model = "embeddinggemma:latest"
embedding_ollama_base_url = "http://localhost:11434"
embedding_timeout_seconds = 120
chunking_strategy = "legacy"
search_k = 30
rerank_k = 60
context_tokens = 3000
```

`embedding_model` continua identificando o encoder BGE responsável pelos pesos
esparsos e pelo tokenizer. A aplicação cria um cache distinto quando o provider
ou a identidade do modelo muda. O bundle experimental do runner permanece
separado do cache criado pela aplicação.

Com 30 resultados por canal, o limite de 60 permite que toda a união deduplicada
seja avaliada pelo reranker. O reagrupamento experimental não foi ativado.
Reinicie a aplicação para que os serviços recarreguem a configuração.
