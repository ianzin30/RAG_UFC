# Planejamento semântico e generalização institucional

`semantic_decomposition_v1` é experimental. Após a busca original, o Qwen
configurado recebe somente pergunta, histórico, IDs/nomes do catálogo e até
seis children (até dois por documento). Ele descreve necessidades em texto
livre e propõe até três consultas. Não recebe categoria, respostas esperadas,
IDs de evidência, aliases de projetos ou datas derivadas do resolvedor.

Uma referência documental precisa de uma citação literal da pergunta/histórico
ou de um child da amostra pertencente ao documento escolhido. Essa verificação
comprova a origem da referência, não sua correção semântica. Referências sem
suporte abrem a busca à coleção; IDs desconhecidos fazem o planejamento falhar.
No controle oracle, a coleção continua limitada ao escopo diagnóstico fornecido.

A chamada usa saída estruturada, temperatura zero, até 1.024 tokens de saída
reservados e uma tentativa. O endpoint `/tokenize` do próprio servidor conta
exatamente a entrada com o template de chat. A amostra é reduzida até caber na
janela informada pelo servidor (12.288 tokens nesta rodada). Pergunta, histórico e catálogo não são truncados.
As respostas finais ficam bloqueadas; só o registro de planejamento do
experimento pode chamar o modelo. Os planos não viram evidência documental.

## Dados e congelamento

O inventário separa famílias por texto idêntico, datas de reunião demonstradas
na origem ou alta similaridade textual. Famílias que incluem os 16 documentos
das anotações antigas são excluídas. O manifesto seleciona primeiro 14 famílias
para desenvolvimento e as próximas 40 para teste, entre fontes com pelo menos
6.500 caracteres, antes de observar resultados de recuperação.

Há 20 perguntas de desenvolvimento (6 multi-hop, 6 cruzamento e 8 controles),
60 de teste (20 de cada grupo) e as 70 antigas para regressão. Anotações usam
posições únicas do Markdown e requisitos explícitos de evidence_v2, sem
exceções por ID/campo. Fatos com spans sobrepostos podem aparecer em até duas
perguntas. A revisão semântica da pergunta, resposta e ligação é feita pelo
agente responsável e registrada em source_audit.json; não equivale a revisão
humana independente. Rascunhos assistidos inválidos são preservados e rejeitados.

Após concluir o desenvolvimento, congelar código, prompt, configuração,
identidades, limites e critérios. O teste só pode ser preparado depois desse
marco. Modificar código ou prompt invalida a reserva. Código congelado deve
continuar igual durante as três divisões da execução final.

## Execução

A URL da VPN serve o Qwen previsto; o override abaixo pertence ao experimento.
A configuração padrão da aplicação não é alterada.

```sh
VLLM_BASE_URL=http://10.101.53.209:8000/v1 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
.venv/bin/python -m benchmark.semantic_retrieval \
  --dataset-dir benchmark/datasets/generalization_v1 --split development \
  --output-dir benchmark/results/rounds/semantic_generalization_2026-10-07/development
```

As opções são `--search-policy`, `--context-policy`, `--max-searches`,
`--dataset-dir`, `--split`, `--rules` e `--inference-seed`. Para regressão, usar
`--dataset-dir benchmark/datasets/real --split regression` e opcionalmente
`--reuse-regression-controls`. A opção `--control-seed-root` permite reutilizar
os controles de uma execução da mesma divisão. O reuso confere o código dos
componentes de recuperação, além da identidade de corpus, índice,
vetores, modelos, configuração, dados e avaliação; sua proveniência é assinada.
Somente referência e directed_v1 são reutilizados. Os planos
semânticos e as buscas novas são calculados. Latências históricas/reuso não são
comparáveis a execução fria; trabalho compartilhado não deve ser somado.

```sh
.venv/bin/python -m benchmark.semantic_retrieval_report \
  --run-root benchmark/results/rounds/semantic_generalization_2026-10-07 \
  --freeze-development
```

Depois da curadoria e auditoria do teste, executar `--split test` em seu próprio
diretório. O runner confere o congelamento. A execução registra falhas como
observações falhas com contexto vazio e zero crédito; não substitui pelo
baseline, não repete a chamada malformada e continua a avaliar os outros casos.
Uma execução com erros não atende aos critérios de candidatura.

## Comparações e decisão

Cinco condições: busca original, directed_v1/alternância, volume ampliado,
semântica/global e semântica/alternância. Volume usa 30 vezes a quantidade de
consultas planejadas, com custo do planejamento separado. As seleções semânticas
compartilham exatamente plano, consultas, candidatos e pontuações. Parents
inteiros continuam limitados a 3.000 tokens, sem truncamento.

Candidatura exige pelo menos três completas líquidas adicionais no teste contra
directed_v1, ganho nas duas categorias-alvo, cobertura parcial agregada sem
redução em ambos os escopos, até duas perdas de casos antigos antes completos
por escopo, ganhos documentais e sucesso integral dentro dos limites.
O relatório inclui métricas por campo/família/fato, diferenças, falhas por etapa,
mediana/p95, pares de reranker, tokens do planejador e bootstrap pareado por
componentes que compartilham famílias ou fatos. Intervalo incluindo zero não
comprova superioridade estatística. Modelo vLLM identificado por ID e metadados
estáveis de serviço; o servidor não fornece digest dos pesos.

## Ajustes feitos exclusivamente no desenvolvimento

A primeira execução foi preservada em `development_v1`. Ela mostrou consultas
para fatos não pedidos e uma referência documental inválida. A revisão do
prompt acrescentou orientações gerais de economia e exemplos sintéticos de
outro assunto, sem regras por pergunta, projeto ou cargo. O schema agora limita
os IDs aos itens do catálogo. Um preflight separado revelou que o catálogo e
esse enum não cabiam no limite local de 8.192 tokens; a conferência passou a
usar os 12.288 tokens de janela informados pelo servidor, com a mesma reserva
de 1.024 tokens de saída. Essas revisões antecedem o congelamento e a elaboração
do teste reservado. Execuções interrompidas continuam em diretórios próprios.

## Curadoria e execução do teste

O teste foi curado após o congelamento. Há 40 famílias: as primeiras 20 apoiam
20 ligações indiretas e 20 controles com fatos distintos; as outras 20 apoiam
20 cruzamentos. Os cruzamentos usam dois ciclos de sete documentos financeiros
e um de seis documentos sobre pessoal/ensino; cada fato aparece duas vezes.
Essa organização resulta em dependência entre perguntas, contabilizada pelo
bootstrap em componentes documentais conectados. `test/curation.py` preserva a
curadoria e `pre_evaluation_manifest.json` assina os arquivos antes da busca.
Todos os 60 pedidos finais estão fora dos quatro campos legados, embora
algumas ligações intermediárias envolvam pessoas em funções administrativas.

Regressão e teste executam em processos separados, com arquivos e caches próprios,
a partir do mesmo código congelado. Parte dessas execuções ocorre simultaneamente.
Consequentemente, latências são observações deste ambiente compartilhado (CPU e
servidor Qwen), com possível concorrência, e não estimativas de execução fria
isolada em produção. Quantidades de consultas, pares e tokens são registradas
separadamente; as duas seleções semânticas continuam compartilhando trabalho.

## Resultado executado em 7 de outubro de 2026

Na coleção, directed_v1 completou 48/60 perguntas inéditas e a semântica com alternância 44/60. Houve dois ganhos e seis regressões. No conjunto antigo, as completas passaram de 64/70 para 49/70, com 15 perdas de casos antes completos. Os critérios de candidatura não foram atendidos; a política permanece experimental.

No teste, todas as 60 perguntas tinham cobertura documental completa na união de candidatos da busca original, sem limite de montagem de contexto. As perdas aconteceram ao levar as evidências ao contexto final. Isso favorece investigar seleção e orçamento de contexto antes de aumentar novamente as buscas. Cobertura ilimitada na união não demonstra que todas as exigências cabem simultaneamente nos 3.000 tokens com parents inteiros: uma próxima auditoria deve separar escolha de parents e restrição de tamanho.

Foram registradas 1500 observações, 299 chamadas únicas ao planejador e nenhuma geração de resposta final. Uma conexão interrompida antes do planejamento de REAL-L02 no escopo correto produziu três observações com falha (volume e as duas seleções semânticas), preservadas com zero crédito; não houve repetição ou fallback. O teste não teve falhas técnicas. Integridade e limites passaram; sucesso técnico integral não passou. Os 45 testes automatizados passaram, os 280 controles históricos foram reproduzidos e o replay confirmou os parents de todas as 1.497 observações sem falha.

| Condição no teste | Coleção | Escopo correto |
|---|---:|---:|
| reference | 48/60 | 57/60 |
| directed | 48/60 | 57/60 |
| volume | 48/60 | 57/60 |
| semantic_global | 48/60 | 57/60 |
| semantic_round_robin | 44/60 | 54/60 |

O relatório e os artefatos ficam em `benchmark/results/rounds/semantic_generalization_2026-10-07/`. A configuração padrão foi preservada. Os dados de teste já examinados passam a ser material de regressão/desenvolvimento; uma revisão do prompt ou código exige outro teste reservado. Todos os documentos selecionados para os conjuntos novos são atas, com curadoria do agente e sem auditoria humana independente.

Depois de concluir as três divisões, executar o módulo de relatório sem `--freeze-development`. As conferências adicionais desta rodada são `validate_round.py`, `control_identity_audit.py`, `packing_latency_replay.py`, `shared_fact_sensitivity.py` e `supplement_report.py`, preservadas no diretório da rodada. O suplemento deve ser executado uma vez após regenerar o relatório principal; `finalize_documentation.py` acrescenta a síntese. Nenhuma dessas análises executa novas buscas ou chamadas ao Qwen.
