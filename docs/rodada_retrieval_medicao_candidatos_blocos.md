# Rodada de medição, candidatos e blocos contínuos

O runner desta rodada é `benchmark/retrieval_round.py`. Ele separa a repontuação,
o controle da união completa e a reindexação estrutural. Todos os modos bloqueiam
`ProviderRegistry.generate` e `structured`; uma tentativa de geração interrompe
o benchmark. A configuração persistida da aplicação não é modificada.

## Definições congeladas

- `literal_v1`: função original `benchmark.real_suite.anchor_coverage`, sem
  alteração. A auditoria exige reprodução exata dos créditos de ambos os runs.
- `evidence_v2`: requisitos no arquivo congelado `evidence_v2_rules.json` com
  hashes dos documentos, spans originais e associação explícita de função/nome
  e rótulo/valor. Espaços, marcadores de títulos e escape de entidades HTML são
  normalizados mantendo um mapa de posições no Markdown original.

O coordenador precisa aparecer com sua função na posição original do documento
correto. O título do projeto não precisa aparecer novamente: a identidade do
documento já é uma condição obrigatória. Datas iguais fora da seção auditada
não cobrem o requisito. O dashboard exige todos os caracteres factuais do
enunciado, permitindo a união de fragmentos com origem demonstrada.

Para bundles antigos, o alinhamento usa correspondência única do corpo ou
limites de posição comprovados pela ordem e proveniência do sidecar. Um título
repetido artificialmente só recebe crédito se o título original correspondente
for demonstrado. Ocorrências sem posição inequívoca recebem zero crédito e
geram pendência. Os overrides anteriores foram conferidos no Markdown e estão
registrados na auditoria como ponto de partida, sem substituir o gabarito.

## Reprodução

Executar a partir da raiz, com os modelos locais já disponíveis:

```sh
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4
export VECLIB_MAXIMUM_THREADS=4
ROUND=benchmark/results/rounds/medicao_candidatos_blocos_2026-10-05
BGE=benchmark/results/runs/retrieval_isolated_2026-10-05_fresh
GEMMA=benchmark/results/runs/embeddinggemma_dense_2026-10-05
.venv/bin/python -m benchmark.retrieval_round --mode audit --output-dir "$ROUND/rescore"
RULES="$ROUND/rescore/evidence_v2_rules.json"
.venv/bin/python -m benchmark.retrieval_round --mode candidates --baseline-dir "$BGE" --output-dir "$ROUND/candidates_bge" --rules "$RULES"
.venv/bin/python -m benchmark.retrieval_round --mode candidates --baseline-dir "$GEMMA" --output-dir "$ROUND/candidates_gemma" --rules "$RULES"
.venv/bin/python -m benchmark.retrieval_round --mode structure --baseline-dir "$GEMMA" --output-dir "$ROUND/markdown_blocks_gemma" --rules "$RULES" --chunking-strategy markdown_blocks_v1
.venv/bin/python -m benchmark.retrieval_origin_audit --rules "$RULES" --output "$ROUND/rescore/child_parent_source_positions.json" --run-dir "$BGE" --run-dir "$GEMMA" --run-dir "$ROUND/markdown_blocks_gemma"
.venv/bin/python -m benchmark.retrieval_round --mode report --output-dir "$ROUND/comparison" --rules "$RULES" --run-dir "$ROUND/rescore/retrieval_isolated_2026-10-05_fresh" --run-dir "$ROUND/rescore/embeddinggemma_dense_2026-10-05" --run-dir "$ROUND/candidates_bge" --run-dir "$ROUND/candidates_gemma" --run-dir "$ROUND/markdown_blocks_gemma"
```

As duas versões são publicadas; `--evaluation-version` seleciona a versão usada
na decisão. Cada diretório só retoma uma assinatura idêntica, que inclui código,
modelos, versões, regras, corpus, datasets e índice original. Se qualquer um
desses campos mudar, utilizar um novo diretório. Os lotes de embedding da
variante estrutural também são retomáveis sob a mesma assinatura.

## Intervenções independentes

O controle de candidatos não instancia encoder ou busca: reconstrói a RRF a
partir dos dois rankings salvos, confere igualdade e reranqueia toda a união
deduplicada. Os scores dos 30 candidatos originais são conferidos contra a
referência, com tolerância de 0,001 para arredondamento em lotes com padding
diferente. O contexto usa a seleção existente e 3.000 tokens.

`markdown_blocks_v1` lê o Markdown original, associa títulos consecutivos ao
conteúdo seguinte e agrupa blocos adjacentes até 1.536 tokens BGE. Os children
têm até 384 tokens, sem sobreposição. Tanto os parents quanto os children são
substrings exatas, incluindo espaços entre blocos, e carregam os offsets em
`Chunk.metadata`. Blocos grandes são divididos por offsets e os limites são
conferidos após a tokenização de cada substring. Não há prefixos artificiais.
Planilhas conservam a estratégia especializada existente.

A estratégia padrão continua `legacy` e conserva exatamente a fórmula anterior
do fingerprint. A estratégia experimental tem fingerprint separado, incluindo
hash da implementação. Bundles antigos não precisam de offsets para carregar.
Gemma é o canal denso e BGE-M3 fornece os pesos esparsos e o tokenizer. O corte
antes do reranker é de 30 na variante estrutural, mesmo que a união completa
apresente ganhos.

## Artefatos e decisão

`comparison/report.md` e `comparison/comparison.json` publicam completude e
cobertura parcial por categoria e escopo, cobertura por etapa, candidatos
efetivos, ganhos e perdas por evidência, sentinelas e latências. `block_sizes.json`
registra tamanhos por documento. `documental_gain_support.json` associa os
ganhos aos requisitos e posições originais. Os JSONs por pergunta mantêm as
pendências de alinhamento.

A auditoria de origem inclui o teto de cobertura do índice completo e os
offsets de children e parents dos documentos anotados. A nova estratégia
também armazena os offsets de todos os documentos no próprio bundle.

A candidatura exige aumento de completude na coleção, ausência de perda de
casos completos nos dois escopos e cobertura parcial agregada sem redução.
Uma melhora concentrada em uma evidência pode atingir várias perguntas, mas
não demonstra generalização. As latências do controle incluem só reranking e
seleção; as demais incluem busca e precisam ser interpretadas separadamente.

## Resultado desta rodada

Sob `evidence_v2`, a união completa elevou BGE de 45 para 49 perguntas completas
na coleção e Gemma de 49 para 51, sem regressões de completude nos dois escopos
e sem redução da cobertura parcial agregada. Ambas são **candidatas à adoção**.

O reagrupamento reduziu Gemma de 49 para 40 perguntas completas: 9 ganhos e
18 perdas. A cobertura parcial caiu de 78,30% para 68,71%; 34 das 37 ocorrências
de perda de evidência aconteceram na seleção de contexto. A decisão é **revisar**
o tamanho e a expansão dos parents, mantendo a continuidade documental.

A versão final da proveniência foi armazenada em `markdown_blocks_gemma_verified`.
O run medido em `markdown_blocks_gemma` continua intacto. A atualização conferiu
identidade de todos os IDs, textos, posições, parents, catálogos, vetores e pesos
esparsos; reutilizou os scores e preservou as métricas. A assinatura registra os
hashes e a prova. Para reproduzir essa atualização específica dos artefatos:

```sh
.venv/bin/python -m benchmark.retrieval_provenance_refresh --run-dir "$ROUND/markdown_blocks_gemma" --output-dir "$ROUND/markdown_blocks_gemma_verified"
```

Ao conferir os resultados salvos desta rodada, usar o diretório `verified` como
quinto `--run-dir` do relatório e também na auditoria de origem. O runner atual
já incorpora a proveniência corrigida para novas execuções, que precisam de
diretórios novos quando a assinatura do código mudar.
