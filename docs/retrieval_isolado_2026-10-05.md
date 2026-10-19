# Retrieval isolado — código atual, 05/10/2026

## Entrega e organização

Dez diretórios de diagnóstico intermediário foram movidos de `results/runs/`
para `results/archive/2026-10-03-controls/`, preservando nomes e conteúdo.
Nenhum resultado foi apagado; os três baselines completos e as comparações
recentes de modelos, contexto e evidências continuam nos caminhos originais.
O README local de resultados registra a correspondência de caminhos.
Não houve redução de tamanho, commit, push ou alteração dos documentos locais.

Experimento concluído: **70 perguntas respondíveis × 2 condições = 140 buscas**,
zero chamadas generativas e nenhuma exceção. As 10 perguntas não respondíveis
não entram no denominador de recall positivo. O conjunto/gabarito não foi alterado.

## Método reproduzível

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --no-sync python -m benchmark.retrieval_isolated \
  --output-dir benchmark/results/runs/NOVA_EXECUCAO_RETRIEVAL
```

- Coleção: todos os 88 documentos do índice, incluindo distratores.
- `collection`: nenhuma restrição documental fornecida.
- `oracle_scope`: documentos obtidos das anotações; controle privilegiado,
  não escopo escolhido pelo planner nem qualidade end-to-end.
- Query: pergunta original, acrescida das mensagens de usuário do histórico
  congelado nos follow-ups. Sem respostas de referência ou reescrita por agente.
- Um round por condição, sem subqueries ou busca dependente multi-hop.
- Dense BGE-M3, sparse, RRF e reranker atuais; nenhuma mudança de ranking,
  chunking, modelo, framework ou índice. Orçamento final: 3.000 tokens BGE.
- Fingerprint: `6c49f49797c1a5cb87118650cfeea80e7f3fc5410c48124bbff673371ab45a8b`.
- FlagEmbedding 1.3.5, faiss-cpu 1.13.2, sentence-transformers 5.3.0,
  CrewAI 1.14.0. Configuração e hashes constam do resultado.
- Runner bloqueia `generate`, `structured`, reconstrução de chunks e gravação
  de novo índice. Sem `prepare` remoto. Apenas modelos locais já disponíveis.

O controle antigo foi atualizado para chamar `select_context()` depois de
`collect()`. Encontrar candidatos não equivale a selecioná-los para geração.

## Resultados principais

As porcentagens abaixo são **cobertura literal**, não acurácia de respostas.

| Métrica | Coleção completa | Escopo oracle |
| --- | ---: | ---: |
| Média do recall das anotações no contexto final | 72,07% | 83,20% |
| Todas as anotações no contexto final | 44/70 (62,86%) | 54/70 (77,14%) |
| Todas as anotações após expandir top-30 reranker para parents | 45/70 | 54/70 |
| Recall de chunks @30 do reranker | 73,50% | 87,75% |
| MRR @30 do reranker | 0,625 | 0,699 |
| nDCG @30 do reranker | 0,616 | 0,731 |
| Mediana da busca/expansão/packing | 5,76 s | 3,58 s |

Recall/nDCG de chunks têm 68 casos elegíveis: dois não possuem chunks alinhados
às anotações. MRR e cobertura das anotações usam 70. Latência não inclui carga
inicial dos modelos nem alinhamento das anotações; não é latência de geração.

### Cobertura completa do contexto por categoria

| Categoria | Coleção completa | Escopo oracle |
| --- | ---: | ---: |
| Factual em um documento | 8/10 | 9/10 |
| Entidades | 6/8 | 6/8 |
| Cross-document | 5/10 | 7/10 |
| Multi-hop, query fixa | 3/10 | 4/10 |
| Listas/agregações | 6/8 | 8/8 |
| Resumos | 3/6 | 4/6 |
| Tabelas de PDFs | 7/8 | 8/8 |
| Follow-up | 6/10 | 8/10 |

Não extrapolar os 3/10 de multi-hop para o fluxo agentic: uma query única não
resolve necessariamente os elos dependentes. Os casos tabulares não validam XLSX.

## Onde há evidência de fragilidade

1. **Escopo faz diferença.** Fornecer documentos corretos eleva cobertura
   completa de 44 para 54 casos. Isso orienta investigar descoberta documental
   e queries; não prova que o planner atual consiga atingir o controle oracle.
2. **Reranker melhora a ordem, não o alcance do pool.** Na coleção completa,
   MRR @30 sobe de 0,498 no RRF para 0,625; nDCG de 0,526 para 0,616.
   Recall @30 permanece igual, pois reordena os mesmos 30 candidatos. Não houve
   perda de cobertura completa do top-30 RRF para o top-30 reranker.
3. **Fusão ajuda modestamente neste controle.** Cobertura completa após expansão
   dos top-30: dense 43, sparse 44, RRF 45, reranker 45 (coleção inteira).
   Não basta melhorar a ordenação dos mesmos candidatos para alcançar evidência
   que não entrou no pool.
4. **Perda demonstrada no packing: L05.** A anotação da comissão foi encontrada
   nos parents do reranker, mas o chunk relevante
   `e56c11dc36caf3fb51770d25` foi cortado por `token_budget`.
   Contexto final: 2.911 tokens BGE, sem cobertura literal completa da comissão.
   Com escopo oracle, a anotação fica completa. É candidato adequado para um
   experimento de orçamento/recomposição, diferente de Q08.
5. **Ainda existem limites das anotações/alinhamento.** JAN24_LDAR e
   REGO_PROGRESSION não se alinham aos children pelo scorer atual, afetando F10,
   E06 e H05. Mesmo percorrendo todos os parents, algumas anotações inteiras
   não recebem cobertura: AFO_DATES, SAAR_NAME, SAAR_DASHBOARD e SAAR_DATES.
   Elas aparecem em sete casos (F02, E01, H03, H06, S01, Q02, Q04).
   Isso exige inspeção de spans/fatos mínimos e da reconstrução estrutural;
   não equivale a provar ausência factual no corpus. Não alterar gabaritos para
   fazer a métrica subir nem apresentar esses casos como todos respondidos errado.

### Controles concretos

| Caso | Coleção completa | Escopo oracle |
| --- | --- | --- |
| F03: Terraform/RACK | Evidências completas | Evidências completas |
| Q08: instituição do presidente da banca | Evidências completas | Evidências completas |
| T04/T05: valores tabulares | Evidências completas | Evidências completas |
| H02: projeto/coordenador | 1/2 anotações | 1/2 anotações |
| H08: cadeia entre atas | Nenhuma anotação completa | Todas completas |
| L05: comissão | Anotação cortada no packing | Anotação completa |

Q08 corrobora a falha posterior de verificação/cobertura vista na geração.
H08 sugere avaliar busca dependente e escopo; não transformar automaticamente
o oracle em comportamento de produção. Recuperar T04/T05 não certifica cálculos.

## Correção auditável do scorer

Depois da execução, a auditoria encontrou cobertura de parents menor que a do
contexto final, o que viola a relação de subconjunto. O alinhamento exigia que
o parent inteiro fosse trecho contíguo da fonte, mas headings reconstruídos
podem impedir isso mesmo quando a citação literal está dentro do parent.

O scorer de expansão passou a usar a mesma função literal do contexto final:
primeiro contenção exata no excerto, depois união de spans na fonte. A cobertura
foi recalculada **offline, sobre os mesmos rankings**, sem repetir busca ou
chamar modelo. Não houve alteração da métrica de contexto final ou dos rankings.
A checagem de monotonicidade passou em ambas as condições.

Resultados em `benchmark/results/runs/retrieval_isolated_2026-10-05/`:

- `retrieval.json`, `summary.json`: dados originais preservados; a métrica antiga
  de expansão de parents foi substituída e não deve ser usada para conclusões.
- `retrieval_scored.json`, `summary_scored.json`: pontuação corrigida, referência
  deste relatório. Mantêm hash do dado bruto, scorer, corpus e ausência de nova busca.
- `code.zip`: snapshot da execução original, sem `.env`/credenciais.
- `scoring_code.zip`: snapshot do scorer corrigido e do script de recálculo.

Recalcular apenas a pontuação:

```sh
uv run --no-sync python -m benchmark.retrieval_rescore \
  --run-dir benchmark/results/runs/retrieval_isolated_2026-10-05
```

## Validação e conclusão

Suíte completa final: **214 testes passaram**, três avisos SWIG existentes.
Inclui seleção das 70 perguntas, packing antes da pontuação e regressão de
parent com heading reconstruído. Nenhum default da aplicação mudou.

O retrieval é funcional, mas **não está demonstrado como suficientemente coeso
para todas as categorias**. Próximos controles: revisar as anotações sem
alinhamento; testar L05 isolando orçamento; avaliar descoberta/subqueries nos
casos multi-documento; medir busca dependente em H08. Manter avaliação semântica
separada e não inferir qualidade de produção deste conjunto diagnóstico conhecido.
