# Buscas direcionadas para multi-hop e cruzamento de documentos

As políticas desta rodada são experimentais e não alteram `config/config.toml`.
O módulo `application/service/rag/v2/DirectedRetrieval.py` contém o planejamento
determinístico, a união com proveniência por consulta e a seleção por alternância.
Ele não importa datasets, perguntas ou gabaritos do benchmark.

## Reprodução

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python -m benchmark.directed_retrieval \
  --output-dir benchmark/results/rounds/directed_retrieval_2026-10-06_v3 \
  --inference-seed benchmark/results/rounds/directed_retrieval_2026-10-06_v2/inference_cache.json \
  --search-policy all --context-policy all --max-searches 4
```

O runner carrega e verifica o mesmo índice Gemma da configuração aplicada.
Ele bloqueia geração, reconstrução de chunks e criação de embeddings de
documentos. Mantém 70 perguntas nos dois escopos, históricos congelados e
3.000 tokens de contexto. A avaliação principal é `evidence_v2`, com as regras
da rodada anterior; `literal_v1` também é registrada.

As opções de busca são `single`, `budget_matched`, `directed_v1` e `all`.
As opções de contexto são `global_score`, `query_round_robin_v1` e `all`.
A alternância exige buscas direcionadas. O limite permitido é de uma a quatro
consultas; esta rodada usa quatro. Uma execução de condições individuais
deve usar seu próprio diretório, pois a seleção de condições integra a assinatura.

## Condições

1. **Referência:** pergunta original, 30 candidatos por canal, união completa e
   seleção atual. Seus rankings e hits precisam reproduzir o benchmark aplicado.
2. **Controle de volume:** pergunta original, `search_k = 30 × N`, sendo `N`
   o número de consultas planejadas usando o resultado da referência.
   Reranqueia a união inteira, com até `60 × N` candidatos.
3. **Direcionadas/global:** consulta original e até três consultas curtas,
   uma por campo e documento. Mantém rankings locais e reranqueia a união
   deduplicada pela pergunta original. Seleciona pelo score global.
4. **Direcionadas/alternância:** reutiliza exatamente as buscas e os scores
   da condição anterior. Alterna queries, selecionando parents por ranking local.

Nenhum score local é comparado diretamente com score de outra consulta. Parents
repetidos contam uma vez; parents que não cabem são descartados integralmente,
sem truncamento. A alternância continua até esgotar as listas.

O planejamento reconhece os campos coordenador, objetivo/objeto/escopo, chefia
e modalidade. Referências explícitas por projeto/data precedem documentos
descobertos no ranking original. A compatibilidade exige cabeçalhos do campo
ou metadados de reunião derivados do próprio documento. Referências ambíguas
são registradas e não escolhem arbitrariamente uma fonte.

## Reuso, medição e retomada

`inference_cache.json` armazena vetores/pesos de perguntas e scores de pares
query/texto idênticos, sob a assinatura completa. A busca inicial é compartilhada
entre condições; consultas sem auxiliares reutilizam a referência. Novas buscas
densas/esparsas são calculadas. Não se copiam buscas direcionadas do estudo anterior.
O reranking da referência é calculado preservando os mesmos batches e a ordem
do benchmark anterior, inclusive textos repetidos: deduplicar esses textos pode
alterar empates numéricos por arredondamento. O controle precisa reproduzir os
rankings e hits históricos.

`--inference-seed CAMINHO` permite reutilizar um cache imutável de entradas
idênticas de outra execução. Encoder, reranker, versões, configuração e índice
devem ser iguais; caminho e SHA do seed entram na nova assinatura. Isso cria
uma execução nova, sem copiar observações anteriores. Retomar o diretório
existente continua exigindo sua assinatura completa idêntica.

As latências mediana/p95 descrevem esta execução com cache compartilhado;
não são tempos de uma implantação sem cache. Os resultados registram consultas,
pares lógicos, pares novos e encodings novos por observação. Trabalho compartilhado
atribuído a várias condições não deve ser somado entre elas.

Assinaturas incluem corpus, índice, modelos/revisões, configuração, código,
políticas, parâmetros e regras. Retomadas diferentes são recusadas. Checkpoints
são atômicos; erros ficam em `errors.json`, sem substituição pelo baseline.

## Artefatos e decisão

Cada condição possui `retrieval.json` e `summary.json`. O diretório da rodada
contém `code.zip`, assinatura, verificação de índice, comparativo, relatório,
suporte documental dos ganhos, auditoria de C09 e os casos sentinela.

Uma candidata precisa alcançar ao menos 53/70 completas na coleção, melhorar
multi-hop e cruzamento de documentos, preservar todos os casos completos nos
dois escopos, não reduzir a cobertura parcial agregada, comprovar documentalmente
os ganhos e executar todas as consultas dentro do limite.

Ganhos em H01–H06 são identificados como concentrados nas três relações de
coordenador compartilhadas. A rodada não demonstra generalização para perguntas
novas nem avalia a geração da resposta. Não promove automaticamente uma política.

## Resultado da rodada concluída

As quatro condições concluíram 70 perguntas nos dois escopos (560 observações),
com 48 testes aprovados e zero chamadas ao gerador. Sob `evidence_v2` congelado:

| Condição | Coleção completas | Escopo correto completas | Decisão |
|---|---:|---:|---|
| Referência | 51/70 | 58/70 | referência |
| Controle de volume | 55/70 | 60/70 | revisar |
| Direcionadas/global | 56/70 | 62/70 | revisar |
| Direcionadas/alternância | 64/70 | 67/70 | adotar como candidata |

A alternância não perdeu nenhuma evidência nem caso completo nos dois escopos.
Na coleção, multi-hop passou de 4/10 a 10/10 completas e cruzamento de 5/10 a
9/10. A cobertura parcial agregada passou de 80,82% a 93,91%. Os seis ganhos
H01–H06 compartilham três fatos de coordenadores; não demonstram generalização.
C09 passou com as posições originais comprovadas, sem mudar os requisitos.
C08 permanece incompleta na coleção: a evidência está na união, mas seu parent
não cabe após os primeiros trechos selecionados. As outras políticas perderam
E01 e precisam de revisão antes de qualquer adoção.

O [relatório completo](../benchmark/results/rounds/directed_retrieval_2026-10-06_v3/report.md)
registra categorias, sentinelas, ganhos/perdas por evidência, latência com cache,
consultas, pares de reranker, auditoria documental e falhas por etapa.
`validation.json` confere hashes, integralidade dos parents, limite de contexto,
identidade das buscas entre as seleções e reprodução exata da referência.
A política candidata continua experimental; esta rodada não alterou os padrões
da aplicação.
