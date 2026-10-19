# Seleção de evidências

Para começar pelas 70 perguntas originais e entender os comandos, consulte
[o guia do benchmark](../benchmark/README.md). Este documento descreve o
protocolo técnico e a matriz suplementar, que exige opções explícitas.

Esta rodada altera somente a seleção do contexto. Gemma denso, BGE-M3 esparso,
BGE-Reranker, índice, históricos, avaliação e consultas ficam congelados.
A aplicação não habilita automaticamente as políticas experimentais.

`EvidenceSelection.py` implementa a lista preliminar de 32 parents, seleção por
MMR (`mmr_parent_v1`) e seleção por suporte documental (`evidence_coverage_v1`).
O Qwen interpreta necessidades livres, examina até oito lotes de quatro parents
e propõe combinações com ligações intermediárias. Cada suporte exige uma citação
literal e proveniência verificável no Markdown. O modelo indica IDs de segmentos
do texto original; o código reconstrói as citações, impedindo alterações de
espaços ou palavras durante a cópia. Prefixos repetidos são separados do corpo,
e somente segmentos alinhados ao Markdown podem ser citados. O parent inteiro
permanece na entrada e no contexto. Referências a outro parent são rejeitadas. Presença textual não garante
correção semântica: essa interpretação é uma estimativa do seletor.
As combinações são escolhidas deterministicamente dentro de 3.000 tokens BGE;
parents não são truncados e textos do LLM não entram nas evidências.

Há no máximo dez chamadas ao seletor: uma de necessidades (1.024 tokens de saída),
oito de suporte e uma de combinações (2.048 tokens cada). A janela real do servidor
é conferida com `/tokenize`, incluindo schema e reserva de saída. Falhas não têm
fallback nem tentativas de reparação. A leitura dos lotes pode parar quando
o modelo estima suporte integral para todas as necessidades e dependências;
a síntese ainda precisa formar uma combinação coerente. Parents não examinados
são registrados e permanecem disponíveis para completar o contexto pelo ranking. A geração de resposta final é bloqueada.

## Reprodução

```sh
VLLM_BASE_URL=http://10.101.53.209:8000/v1 .venv/bin/python -m benchmark.evidence_selection \
  --split development --search-policy all --context-policy all --output-dir benchmark/results/rounds/evidence_selection_2026-10-07_v5/development
VLLM_BASE_URL=http://10.101.53.209:8000/v1 .venv/bin/python -m benchmark.evidence_selection \
  --split regression --search-policy all --context-policy all --output-dir benchmark/results/rounds/evidence_selection_2026-10-07_v5/regression
.venv/bin/python -m benchmark.evidence_selection_oracle \
  --output benchmark/results/rounds/evidence_selection_2026-10-07_v5/minimum_parent_cover.json
.venv/bin/python -m benchmark.evidence_selection_report \
  --root benchmark/results/rounds/evidence_selection_2026-10-07_v5
```

Cada conjunto de buscas (`single` e `directed_v1`) é compartilhado por seis
condições: global/alternância sobre a união inteira; global/alternância sobre a
lista preliminar; MMR e cobertura documental sobre a mesma lista. Os rankings
salvos não são recalculados. `--search-policy` e `--context-policy` permitem
selecionar condições; assinaturas diferentes exigem diretórios diferentes.
A execução é sequencial. O executor paralelo e os parâmetros de partição foram
removidos: o servidor serializa gerações e os ensaios concorrentes produziram
timeouts. Respostas estruturadas são reutilizadas somente para role, prompt e
schema idênticos sob a assinatura completa; não há cache de erros de transporte.
Chamadas lógicas, físicas, acertos de cache e tokens físicos são registrados
separadamente. Protótipos e snapshots permanecem em `results/rounds`; uma
assinatura anterior à limpeza não pode ser retomada com código diferente.

O desenvolvimento reúne os 20 e 60 casos institucionais já examinados.
As 70 perguntas antigas são regressão. O diagnóstico `minimum_parent_cover`
usa explicitamente o gabarito, posições verificadas e otimização inteira para
medir a possibilidade de encaixe de parents completos. Não é utilizado pelos
seletores. A dependência de SciPy já está disponível no ambiente por meio das
dependências científicas; sua versão deve acompanhar o artefato diagnóstico.

O conjunto reservado preparado está em `benchmark/datasets/selection_generalization_v1`.
São 30 perguntas, dez por categoria, em todas as 13 famílias restantes; as 30
pedem campos novos e os fatos aparecem no máximo duas vezes. O primeiro rascunho
automático foi rejeitado por confusão entre projetos. Sua saída original foi
preservada e substituída por curadoria documental explícita em `test/curation.py`.
Posições são reconstruídas a partir do Markdown, sem retrieval. A revisão é do
agente, sem auditoria humana independente; equivalência semântica de fatos entre
documentos exige cautela além da checagem de colisões literais.

## Teste reservado

As 30 perguntas e suas anotações já estão preparadas em
`benchmark/datasets/selection_generalization_v1`. Os geradores automáticos de
rascunhos foram removidos, pois foram substituídos pela curadoria documental.
O compilador e a validação de posições permanecem em `generalization_dataset`.
Os rascunhos e a curadoria existente foram preservados junto ao dataset.
Não é necessário criar ou executar perguntas novas para estudar um seletor
sobre as 70 originais.

Antes da execução, `selection_reserved_execution --mode freeze` exige a passagem
do critério de desenvolvimento e a auditoria. O modo `search` realiza buscas
uma vez, com o planejador direcionado existente e sem geração. O runner de
seleção aceita `--split test --dataset-dir ... --frozen-search-dir ...` e verifica
o congelamento. O conjunto fica marcado como consumido após a avaliação.

Se nenhuma alternativa melhorar pelo menos duas perguntas e ambas as categorias
alvo nos 80 casos, preservando cobertura parcial, limites e no máximo duas
regressões por escopo nas 70 antigas, a decisão é revisar e o teste não é
consumido. Esses mesmos critérios são aplicados às 30 perguntas reservadas;
o vencedor é definido no desenvolvimento. O relatório separa buscas originais
e direcionadas e não afirma transferência para outros tipos de documento.

A assinatura ignora timestamps e IDs de permissão gerados por requisição em
`/models`, mantendo ID, root, parent, janela, revisão/digest quando expostos e
versão do servidor. O endpoint não expõe hash dos pesos Qwen; essa limitação
é registrada, sem afirmar verificação criptográfica dos pesos remotos.
