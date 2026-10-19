# Estado intermediário: organização dos commits — 19/10/2026

Branch local: `codex/desenvolvimento-intermediario-spark`. Base: `f9f7707` (`main`). Esta etapa organiza o trabalho existente; não promove o controlador experimental nem envia alterações ao GitHub.

Os 323 caminhos do diff inicial foram distribuídos em 19 commits por responsabilidade e dependência. Este documento constitui o vigésimo commit. Todos os arquivos preexistentes foram conferidos por SHA-256 após a divisão: conteúdo e remoções preservados. Nenhuma alteração funcional foi acrescentada para fabricar a separação.

## Mapa dos commits

| # | Commit | Responsabilidade | Caminhos |
|---|---|---|---|
| 1 | `7191e57` | feat(llm): add reusable OpenAI-compatible Spark client | 6 |
| 2 | `95623ab` | feat(providers): validate sampling and preserve generation metadata | 9 |
| 3 | `89c7b9f` | feat(rag): enforce question contracts and grounded answer verification | 11 |
| 4 | `e51bc46` | feat(retrieval): support Gemma embeddings and structural chunk diagnostics | 8 |
| 5 | `b7c6950` | refactor(benchmark): extract shared artifacts and evidence evaluators | 15 |
| 6 | `99b3273` | feat(selection): add deterministic parent ordering and packing | 2 |
| 7 | `294708e` | feat(retrieval): add bounded experimental investigation policies | 5 |
| 8 | `6ba6af8` | test(benchmark): version evidence datasets and reserved splits | 48 |
| 9 | `00c04e5` | feat(benchmark): add saved-evidence selection diagnostics | 6 |
| 10 | `9fa5503` | feat(benchmark): consolidate search studies and reproducible replays | 33 |
| 11 | `130ea44` | fix(sources): validate citations and restrict document preview paths | 2 |
| 12 | `1c75fbd` | fix(chat): persist turns atomically across sessions | 6 |
| 13 | `0129dc5` | feat(streamlit): connect test chat to the centralized Spark profile | 15 |
| 14 | `5b5ff58` | docs(research): preserve retrieval investigations and experiment protocols | 20 |
| 15 | `f59e85b` | docs(benchmark): archive retrieval reports and diagnostic evidence | 24 |
| 16 | `447d7c2` | docs(audit): preserve the original Streamlit audit evidence | 26 |
| 17 | `770af75` | docs(chat): archive Spark validation and composer screenshots | 44 |
| 18 | `73b2d00` | docs: document current chat setup and benchmark commands | 6 |
| 19 | `4cef8b9` | chore(tooling): track project design skills and provenance | 37 |

## Por que alguns grupos ficaram maiores

Configuração e providers compartilham os tipos de sampling, a resolução do ambiente e os metadados de geração. Contratos de pergunta, cálculo e verificação compartilham o estado do fluxo RAG. Persistência, operações e estado do chat usam a mesma API transacional. Separar esses arquivos sem alterar a implementação criaria versões intermediárias incompatíveis.

O commit do runner reúne os estudos de busca, a substituição do runner anterior e seus testes. Os estudos importam o runtime, os helpers do runner e as ferramentas de seleção; há imports locais entre esses módulos. Não foram reescritos só para reduzir o tamanho de um commit. Os relatórios e as ferramentas de design foram separados dos commits funcionais.

## Validação

A suíte do estado final passou: **482 testes, 3 desmarcados**, em 21,28 segundos. Essa execução não inclui novas submissões à Spark. Os três testes históricos dependem das referências congeladas anteriores; a mudança de código/configuração não foi contornada nem teve suas assinaturas relaxadas.

Comando usado:

```sh
.venv/bin/python -m pytest tests -q --tb=short \
  --deselect=tests/test_global_order_replay.py::test_real_offline_replay_is_reproducible_and_resumes_only_same_signature \
  --deselect=tests/test_document_budget_replay.py::test_real_experiment_is_offline_reproducible_and_keeps_current_window \
  --deselect=tests/test_document_budget_cycle.py::test_real_preflight_has_no_transport_and_checks_both_budgets
```

Além disso, checkpoints selecionados foram exportados do índice/commit para diretórios temporários separados, sem os arquivos ainda não versionados da pasta de trabalho. As suítes abaixo passaram sobre essas cópias. Não se afirma que toda a suíte completa foi executada em cada commit intermediário.

| Commit | Testes no checkpoint isolado |
|---|---|
| `7191e57` | 24 passed in 0.39s |
| `95623ab` | 74 passed, 3 warnings in 0.79s |
| `89c7b9f` | 55 passed in 1.92s |
| `e51bc46` | 18 passed, 3 warnings in 3.76s |
| `99b3273` | 19 passed in 0.08s |
| `294708e` | 16 passed in 0.11s |
| `130ea44` | 4 passed in 0.19s |
| `1c75fbd` | 18 passed in 0.81s |
| `0129dc5` | 56 passed, 1 deselected, 7 warnings in 8.31s |

No checkpoint da interface, o teste `frozen_reference` foi desmarcado porque a cópia isolada não contém `benchmark/results/`. Ele passou na suíte final executada na pasta original. Os demais três testes históricos permanecem fora do aceite informado acima.

A conferência dos candidatos incluiu os arquivos adicionados/modificados e 155 entradas dos arquivos ZIP. Não foram encontradas correspondências com as credenciais configuradas no `.env`, nem os padrões específicos de credenciais inspecionados. Essa conferência não equivale a certificar todos os dados ou a auditar o histórico Git inteiro. O `.env` permanece ignorado e não versionado.

Alguns arquivos novos de benchmark já tinham linhas em branco extras no final; esses avisos de whitespace foram preservados para manter o conteúdo e os hashes existentes.

## O que este checkpoint oferece e o que permanece local

- Aplicação: RAG V2, Spark/Qwen3.6, janela local de 16.384 tokens e 6.000 tokens documentais; controlador experimental continua separado.
- Chat: fontes, histórico transacional, uma execução por submissão e compositor abaixo das respostas.
- Git inclui código, dependências declaradas, configurações públicas, datasets de avaliação, relatórios e evidências de auditoria.
- `.env`, histórico de uso, corpus, caches/índices, ambientes Python e `benchmark/results/` continuam fora do Git, conforme as regras existentes. Um clone não reproduz automaticamente os resultados nem contém toda a infraestrutura para hospedagem.
- A hospedagem exige configurar credenciais, acesso à Spark, coleção/índice e serviços de recuperação. O pipeline ativo depende do Ollama/EmbeddingGemma e dos recursos BGE descritos na configuração.
- Documentos e arquivos arquivados retratam configurações e código de outras datas. A seção histórica de recuperação em `config/README.md` ainda menciona 3.000 tokens; o valor ativo é 6.000 em `config/config.toml`, também descrito em `docs/chat_spark.md`. Esta divisão não revisa todas as inconsistências da documentação antiga.

## Publicação posterior

Nenhum push foi executado nesta etapa. Para publicar a branch quando desejado:

```sh
git push -u origin codex/desenvolvimento-intermediario-spark
```

A branch `main` permanece na base original. Esse checkpoint é para desenvolvimento e testes, não uma certificação de qualidade das respostas ou de prontidão para produção.
