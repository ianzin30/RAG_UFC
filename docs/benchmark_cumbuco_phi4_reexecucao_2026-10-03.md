# Reexecução das 80 perguntas — Cumbuco / Phi-4

## Condição congelada

Execução sequencial em 03/10/2026, das 08h45 às 09h40 (Fortaleza), sem respostas de referência nos prompts. O baseline de 02/10 permanece intacto.

- Provider: UFC/Cumbuco, modelo `phi4:latest`, serviço Open WebUI `0.8.10`.
- Digest informado: `ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba`.
- Override **somente no harness**: envio de temperatura, limite de saída por papel e contexto de 8.192 em `params`, conforme contrato validado na investigação. Nenhuma promoção para o provider de produção.
- Demais prompts, planner, retrieval, agentes e verificação mantidos. Esta condição não representa a execução sem override do Streamlit.
- Código de produção: `f9f7707d5bdcd05d73929964dacaf7225f65a015` como HEAD, com alterações locais existentes identificadas pelo hash de conteúdo em `run.json`; não é um checkout limpo desse commit.
- Mesmo índice do baseline, reutilizado em cache: `6c49f49797c1a5cb87118650cfeea80e7f3fc5410c48124bbff673371ab45a8b`. Sem reindexação.

```bash
.venv/bin/python -m benchmark.real_suite \
  --provider ufc --model phi4:latest \
  --ufc-chat-envelope openwebui_params \
  --output-dir benchmark/results/runs/real_80_cumbuco_phi4_params_2026-10-03
```

## Resultados determinísticos

| Métrica | Baseline 02/10 | Transporte validado 03/10 |
| --- | ---: | ---: |
| Perguntas executadas | 80 | 80 |
| Execuções sem exceção | 19 | 70 |
| Exceções de pipeline | 61 | 10 |
| Chamadas de geração | 240 | 374 |
| Tempo acumulado das perguntas | 51min48s | 54min22s |

A rodada completa durou aproximadamente 55 minutos. Latência por pergunta: p50 **36,77s**, p95 **68,64s**, incluindo erros. As 374 chamadas HTTP retornaram 200: sucesso HTTP não equivale a resposta válida ou correta.

Estados internos: 30 `answered`, 29 `abstained`, 9 `partial`, 2 `clarification_required`, 10 erros. Erros: quatro no planner, três no reasoning, dois na verification e um na answer.

Todos os envios registraram contexto solicitado de 8.192. Vinte chamadas reportaram 8.192 tokens de entrada e 29 atingiram o limite de saída solicitado. Esses contadores sinalizam pressão de orçamento, mas não provam, isoladamente, truncamento da entrada. Os casos de JSON incompleto têm a saída e o erro preservados no trace.

As 84 claims entregues têm referências não vazias e IDs existentes em `cited_sources`. Isso verifica **integridade estrutural**, não suporte semântico.

A métrica literal original pôde ser calculada em 62 casos com resposta/trace bem-sucedido e evidências anotadas: 20 tiveram todas as âncoras selecionadas; recall macro literal selecionado 35,48%, citado 31,45%. É um subconjunto condicionado ao sucesso de execução, não Recall@K de todos os 80 casos. Âncoras extensas podem penalizar respostas corretas; as anotações originais não foram alteradas.

## Revisão assistida contra os fatos obrigatórios

Esta é uma **classificação preliminar auditável das saídas**, não um score determinístico nem avaliação humana independente. O estado interno do RAG não foi usado como prova de acerto. O gabarito e os fatos obrigatórios permanecem congelados.

| Categoria | Casos | Completos | Parciais úteis | Comportamento negativo correto |
| --- | ---: | ---: | ---: | ---: |
| Factual single-document | 10 | 5 | 0 | — |
| Entity lookup | 8 | 2 | 1 | — |
| Cross-document | 10 | 2 | 0 | — |
| Multi-hop | 10 | 0 | 2 | — |
| List/aggregation | 8 | 4 | 0 | — |
| Summary | 6 | 0 | 2 | — |
| Spreadsheet/table (PDF) | 8 | 4 | 1 | — |
| Follow-up | 10 | 2 | 0 | — |
| Unanswerable/ambiguous | 10 | — | — | 6 |

Entre 70 perguntas respondíveis: **19 completas (27,14%)**, **6 parciais úteis (8,57%)**. Completas: F01, F02, F03, F04, F09, E01, E08, C02, C03, L01, L02, L03, L04, T01, T02, T03, T08, Q03, Q04 (todos com prefixo `REAL-`).

Parciais úteis: E05, H06, H08, S03, S06, T07. A classificação estrita exige os fatos congelados: E05 omite PUCRS; H06 omite a identificação de Lincoln; H08 omite disciplina/ajuda; S03 não nomeia os três módulos existentes; S06 omite remuneração, unanimidade e seleção de substituto; T07 omite a marcação explícita dos dois itens. Algumas dessas respostas atendem boa parte da pergunta; não foram promovidas a completas por impressão de qualidade.

Controles negativos corretos: U03, U04, U05, U06, U07 e U09. U01 e U10 tiveram erro; U08 pediu clarificação indevida; U02 inventou uma conclusão factual a partir de previsão.

Demais resultados: 14 respostas incorretas/fora do alvo, 23 abstenções indevidas em perguntas respondíveis, duas clarificações indevidas e dez erros. T08 respondeu integralmente apesar do rótulo interno `partial`; C01 e outros falharam apesar de `answered`.

## Falhas prioritárias preservadas nos traces

1. **Pertinência e escopo:** C01/Q01/Q10 trazem atribuições genéricas em vez de nomes; C07/C08 usam atas de outras datas; Q08 troca presidente da banca por presidente da ASTEF; S05 muda de assunto.
2. **Falsas aprovações:** H02 atribui a coordenação do RACK a José Macedo; L05 confunde presentes com comissão; U02 apresenta datas planejadas como entrada efetiva em produção.
3. **Aritmética:** T04 afirma `19.200 + 1.920 = 21.200`, sem detectar que o correto é 21.120 e a diferença do total impresso é 80. A resposta parcial é incorreta, não útil.
4. **Estruturado:** JSON incompleto e reparo ineficaz ainda impedem dez casos; o transporte corrigido não resolve sozinho a concisão dos agentes e a pressão do catálogo/schema.
5. **Multi-hop:** nenhum acerto completo estrito. H06/H08 recuperam apenas parte da relação necessária. Mais hops, isoladamente, não demonstraram solução.

O transporte validado reduziu drasticamente as exceções e permitiu respostas corretas que não existiam no baseline. Porém, esta rodada altera conjuntamente o encaminhamento dos parâmetros antes ignorados: contexto, limite de saída e temperatura. Não permite atribuir todo o efeito ao aumento de contexto, nem declarar qualidade de produção ou superioridade entre modelos. O conjunto já foi usado no diagnóstico e não é teste cego.

## Artefatos e validação

Resultados, respostas, gabaritos, logs e traces completos: `benchmark/results/runs/real_80_cumbuco_phi4_params_2026-10-03/`. O `run.json` bruto conserva `review_status=pending`; esta revisão complementar não sobrescreve observações originais. Resultados operacionais permanecem ignorados pelo Git.

Teste novo: isolamento do override, orçamento por papel, envelope `params` e digest; contrato de produção preservado. Suíte completa: **158 passed**, três avisos SWIG, em 9,00s.

Próximo passo recomendado: implementar, mediante aprovação, as correções já propostas para transporte de produção, catálogo/plano fiel, verificação de pertinência e contradições e cálculo determinístico. Esta execução não aplicou essas correções automaticamente.
