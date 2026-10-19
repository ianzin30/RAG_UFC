# Avaliação V2

O ponto de entrada para o estudo atual de retrieval e seleção nas 70 perguntas
originais é o [guia do benchmark](../benchmark/README.md). Os comandos abaixo
também incluem estudos históricos de geração, que têm objetivos separados.

Testes unitários usam fakes e fixtures controladas:

```sh
uv sync --frozen
uv run python -m pytest -q
```

Runners abaixo são ferramentas explícitas de avaliação: alguns carregam modelos BGE e os modos de geração consomem inferência. A limpeza do repositório não os executa.

## Runners mantidos

```sh
# Retrieval sintético com queries fixas, sem generator
uv run python -m benchmark.v2 --output benchmark/results/v2_retrieval.json

# Geração sintética: provider/modelo da configuração por default
uv run python -m benchmark.v2 --generate

# Override explícito de desenvolvimento
uv run python -m benchmark.v2 --generate --provider ollama --model phi4:latest

# Corpus real previamente carregado
uv run python -m benchmark.real_corpus --collection uploaded_files
uv run python -m benchmark.real_generation --collection uploaded_files

# Conjunto ampliado (80 perguntas), produção atual, checkpoints por pergunta
uv run python -m benchmark.real_suite --output-dir benchmark/results/runs/real_80
# Retomar somente com os mesmos dados, configuração e código de produção
uv run python -m benchmark.real_suite --output-dir benchmark/results/runs/real_80 --resume

# Estudo de perguntas anotadas e relatório
uv run python -m benchmark.run --questions benchmark/questions.json
```

As perguntas do estudo ficam em JSON; veja `benchmark/questions.json` para o contrato. Anotações de corpus real são puladas quando os documentos exigidos estão ausentes. Documentos operacionais não são publicados junto do repositório.

## Conjunto real ampliado

O pacote [`benchmark/datasets/real`](../benchmark/datasets/real/README.md) reúne
80 perguntas com gabaritos, 77 trechos de referência e fingerprints do corpus
textual. São nove categorias, incluindo 10 casos multi-hop e 10 conversacionais.
O [gabarito legível](../benchmark/datasets/real/gabarito.md) permite revisão manual.

O runner `real_suite` usa a configuração de produção e continua após falhas por
pergunta, salvando respostas, identidade/configuração do provider, respostas HTTP,
traces e logs comprimidos. Não transmite os gabaritos aos agentes. A conferência
literal de trechos é conservadora e não substitui revisão da correção da resposta
ou suporte semântico das claims. Essa revisão é registrada separadamente.

Os runners curtos mantêm seus casos anteriores. Consulte o protocolo e os limites
de independência no README do pacote antes de usar os dados para medir qualidade.
A criação das anotações incluiu apenas conferência documental e estrutural; a
execução de geração é uma etapa posterior, com resultados locais em `results/`.

## Métricas e diagnostics

O runner sintético separa retrieval fixo de geração/agentes e calcula Recall@K, MRR, nDCG, Evidence Recall e Complete Evidence Recall. O corpus real usa anotações documentais: seu Complete Evidence Recall mede documentos necessários, não prova todas as relações internas.

Geração registra acerto determinístico por termos/abstenção, claims, citações e chamadas de providers. Os julgamentos semânticos suplementares nunca sobrescrevem métricas determinísticas. Presença de IDs de citação não equivale, sozinha, a prova de suporte semântico.

Relatórios incluem configuração e diagnostics disponíveis. Resultados de Phi-4, Qwen local e vLLM são específicos de seus modelos. Fixtures sintéticas não demonstram qualidade em produção.

Resultados ficam em `benchmark/results/`, ignorado por Git. Não publique traces ou documentos privados inadvertidamente.

## Histórico

Runners V1 e grid baseado no splitter antigo foram aposentados. Resultados históricos locais foram preservados; para consultar a implementação antiga, use o histórico Git anterior à limpeza. A árvore V2 anterior à limpeza ainda não tinha sido commitada, portanto não se deve atribuir todos os seus resultados a um commit existente.

Não há promessa de reproduzir o baseline V1 a partir da instalação V2 atual. Os testes e runners preservados avaliam a implementação ativa.
## Investigação controlada do Cumbuco

O harness `benchmark.investigation` isola transporte, planejamento, retrieval e
síntese/verificação. Usa `ufc / phi4:latest` por seleção da execução; não muda o
provider ativo da aplicação. A seleção versionada contém 18 casos, dois por
categoria, e controles artificiais ficam identificados separadamente do corpus.

Exemplo, a partir da raiz (use um diretório novo para cada versão do experimento):

```bash
.venv/bin/python -m benchmark.investigation --mode prepare --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation --mode transport --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation --mode transport_validation --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation --mode retrieval --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation_review --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation --mode planner --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation --mode oracle --output-dir benchmark/results/runs/minha_investigacao
.venv/bin/python -m benchmark.investigation_tables --output-dir benchmark/results/runs/minha_investigacao
```

Execute modos generativos sequencialmente. `prepare` exige o corpus local e a
chave já configurada em `.env`; não mostra a chave. Os controles de transporte
distinguem parâmetros configurados, enviados e observados. A validação adicional
mede limites com uma resposta deliberadamente longa e conserva os controles
iniciais mesmo quando falham. Planner/oracle exigem o gate de transporte.

Retrieval não faz chamadas generativas. O escopo fornecido pelo gabarito é um
controle explícito, não uma previsão do planner. São registradas métricas em
dense, sparse, RRF, reranker e contexto. A revisão offline acrescenta âncoras de
fatos mínimos para coordenadores; mantém as âncoras literais originais e não
altera respostas do gabarito. Essas métricas não são correção de resposta.

Oracle usa `AgentTeam` e `RAGFlow.synthesize/verify`, com reparos limitados
existentes, fornecendo os excertos corretos/negativos diretamente. Não é uma
execução end-to-end. Um controle de conflito com três repetições pode interromper
o ramo e exige revisão explícita da saída. JSON válido não constitui aprovação
semântica. O benchmark de 80 perguntas só deve ser repetido após os gates e as
correções de produção correspondentes.

Resultados usam checkpoints com fingerprints; uma execução modificada não pode
retomar silenciosamente um checkpoint incompatível. Payloads e respostas ficam
somente no diretório ignorado de resultados, sem cabeçalhos de autenticação.

## Controles das correções prioritárias

`benchmark/datasets/real/priority_controls.json` congela os 25 casos aprovados;
não modifica as 80 perguntas nem seus gabaritos. O modo negativo acrescenta Q10
como sentinela fora da matriz de pontuação, para reproduzir a falha de identidade.

```sh
uv run --no-sync python -m benchmark.priority_controls --mode transport --output-dir benchmark/results/runs/controle_transporte
uv run --no-sync python -m benchmark.priority_controls --mode planner --output-dir benchmark/results/runs/controle_planner
uv run --no-sync python -m benchmark.priority_controls --mode negative --output-dir benchmark/results/runs/controle_negativos
uv run --no-sync python -m benchmark.priority_controls --mode oracle --output-dir benchmark/results/runs/controle_oracle
```

São três repetições sequenciais, usando o adapter de produção, Phi-4 e contexto
solicitado 8192, sem override histórico. `--case-id` restringe aos controles
pertinentes de uma etapa. Planner usa exatamente `RAGFlow.plan_question`.
Oracle fornece evidências anotadas explicitamente; negativos reapresentam as
claims falsas e evidências do controle de 03/10, sem fornecer gabarito.

Cada condição guarda configuração, SHA do código/harness/dataset, fingerprint,
identidade disponível, payloads e um snapshot de código sem `.env`. Erros não
contam como abstenções corretas. Aprovação falsa ou erro bloqueia o ramo após
suas três repetições; outros ramos independentes podem continuar. O modo
`integrated` existe para os controles aprovados, mas não promove automaticamente
o verificador nem dispara os 80 casos. Revisão semântica continua necessária.

Não confundir contenção literal, cobertura de entidades e suporte semântico.
Uma citação perfeitamente literal pode afirmar algo sobre o projeto errado.
O relatório desta entrega está em `docs/correcoes_prioritarias_rag_v2.md`.

## Experimentos de janela do gerador

O harness `benchmark.priority_controls` aceita `--num-ctx 8192` (controle
histórico, default) e `--num-ctx 16384` (condição explícita). A opção altera
somente a configuração de geração do experimento: provider/modelo continuam
Cumbuco/Phi-4, budgets de saída por papel e `rag_v2.context_tokens` não mudam.
Usar um diretório novo por condição, preservando os três repeats e snapshots.
Não interpretar uma janela maior como aumento automático das evidências enviadas.
Resultados de 05/10/2026: `docs/phi4_contexto_8192_16384_2026-10-05.md`.

## Experimentos do orçamento de evidências

`--context-tokens {3000,5000}` controla somente o packing das evidências,
contado pelo tokenizer BGE. O default continua 3.000. Não altera o índice,
os parâmetros de busca, os limites de saída ou a janela do gerador.
Para isolar esta variável, comparar condições com o mesmo `--num-ctx 16384`.
O harness aplica o orçamento ao Flow real após carregar e conferir o índice
congelado. Usar diretórios distintos; a configuração da aplicação não é editada.

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --no-sync python -m benchmark.priority_controls \
  --mode integrated --num-ctx 16384 --context-tokens 5000 \
  --case-id REAL-F03 --case-id REAL-Q08 \
  --output-dir benchmark/results/runs/NOVA_CONDICAO_EVIDENCIAS_5000
```

## Retrieval isolado atualizado

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --no-sync python -m benchmark.retrieval_isolated \
  --output-dir benchmark/results/runs/retrieval_isolated_2026-10-05
```

Avalia as 70 perguntas respondíveis, sem planner ou gerador, em duas condições:
coleção completa e escopo correto fornecido pelas anotações (controle oracle,
não resultado de resolução automática). Usa a pergunta original; em follow-ups,
acrescenta somente mensagens de usuário do histórico congelado. É um round
por condição: não mede busca multi-hop dependente nem geração de subqueries.

O runner usa o índice congelado, proíbe reconstrução e chamadas generativas,
confere literalmente as anotações no corpus e registra versões/configuração.
Mede Recall/MRR/nDCG e cobertura completa literal em K=1/5/10/30 nos rankings;
separa expansão para parents e contexto final. Após `collect()`, chama
`select_context()`, tal como o Flow atual. `summary.json` resume `retrieval.json`.

Na execução de 05/10, a auditoria corrigiu a pontuação de expansão para parents
offline: usar `retrieval_scored.json` e `summary_scored.json`, preservando os
originais. `benchmark.retrieval_rescore --run-dir ...` reproduz a correção sem
refazer buscas. O runner atual já incorpora o scorer corrigido. Relatório:
`docs/retrieval_isolado_2026-10-05.md`.

Recall de chunks usa sobreposição textual como relevância binária; denominadores
sem chunks alinhados são explicitamente reportados. Cobertura de uma anotação
inteira pode ser mais exigente que o fato mínimo necessário, e evidências
alternativas não anotadas não recebem crédito. Não chamar essas métricas de
acurácia da resposta ou suporte semântico.

Diagnósticos intermediários de 03/10 foram agrupados em
`benchmark/results/archive/2026-10-03-controls/`, preservando nomes e conteúdo.
Baselines completos e comparações recentes continuam em `results/runs/`.

## Retrieval da configuração aplicada: Gemma e união completa

Após a adoção em `config/config.toml`, executar buscas novas com a configuração
da aplicação, sem reutilizar rankings salvos:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python -m benchmark.retrieval_active \
  --output-dir benchmark/results/runs/embeddinggemma_union_active_2026-10-06
```

O runner exige a mesma identidade do Gemma, corpus e estrutura da rodada
congelada, e confere todos os chunks, parents, catálogo, vetores e pesos
esparsos antes de reutilizar o índice. Salva o bundle equivalente sob o
fingerprint calculado pela aplicação, preservando os caches históricos.
Consulta e ordena novamente as 70 perguntas nos dois escopos (140 buscas),
com 30 candidatos por canal, toda a união no reranker e contexto de 3.000
tokens. Chamadas ao gerador e reconstrução de chunks ficam bloqueadas.

`retrieval.json` preserva a medição; `retrieval_scored.json` acrescenta
`literal_v1` e o `evidence_v2` congelado. `summary.json` inclui cobertura por
categoria e etapa, inclusive a união completa. `comparison.json` e `report.md`
comparam com Gemma/corte 30 e com a união da rodada anterior. A assinatura
inclui configuração, modelos, corpus, versões, código, índice e regras;
retomadas com assinatura diferente são recusadas. Use outro diretório para
uma nova execução independente.

## Buscas direcionadas por campo e documento

O runner `benchmark.directed_retrieval` compara referência, controle de volume,
buscas direcionadas com seleção global e as mesmas buscas com alternância
de contexto. A rodada preserva modelos, índice, avaliadores e 3.000 tokens;
permite até quatro consultas e bloqueia o gerador. Políticas e métodos de
reprodução estão em `docs/rodada_buscas_direcionadas.md`.

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python -m benchmark.directed_retrieval \
  --output-dir benchmark/results/rounds/directed_retrieval_2026-10-06_v3 \
  --search-policy all --context-policy all --max-searches 4
```

## Planejamento semântico e generalização

O runner `python -m benchmark.semantic_retrieval` aceita dataset/divisão, política de busca/contexto e limite de consultas, sem depender de 70 perguntas. A política experimental `semantic_decomposition_v1` usa uma chamada estruturada do Qwen após a busca original; compara seleção global e alternância com os mesmos planos e candidatos. Veja [protocolo, comandos e resultados](rodada_planejamento_semantico.md).

A rodada de 7/10/2026 terminou com decisão **revisar**, sem promoção à aplicação: 48/60 completas para directed_v1 contra 44/60 para semântica/alternância na coleção, e 15 regressões de casos antigos. As avaliações, modelos e código foram congelados antes do teste.
