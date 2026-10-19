# Phi-4: orçamento de evidências 3.000 versus 5.000

Experimento concluído em 05/10/2026: seis execuções novas, 33 chamadas
generativas, nenhuma exceção. Mais evidências foram enviadas em F03, mas não
houve ganho de resposta nestes dois casos. Não promover o orçamento maior.

## Método

Comparação com a condição `16384/integrated` do levantamento
`phi4_context_comparison_2026-10-05`. Cumbuco, `phi4:latest`, janela solicitada
16.384, temperatura zero, mesmos limites de saída por papel, mesmo código de
produção e índice congelado. Única diferença na configuração: orçamento de
packing `context_tokens=3000` versus `5000`, medido com tokenizer BGE, não
Phi-4. Não houve alteração de defaults, modelos, ranking, chunking ou índice.

F03 e Q08, três repetições sequenciais cada. Gabaritos não entram nos prompts.
Controle anterior preservado; ordem não randomizada e carga do servidor não
controlada. Não atribuir causalidade de hardware às latências observadas.
O harness tem SHA diferente por acrescentar a opção de orçamento; o SHA do
código de produção e a configuração LLM foram conferidos como idênticos.

O orçamento é um teto, não uma meta de preenchimento. O Flow calcula o custo
do contexto estrutural e seleciona evidências; o payload dos agentes usa o
texto das evidências selecionadas. Portanto, medir tanto o packing BGE quanto
a entrada reportada pelo gerador, sem convertê-los por um fator fixo.

## Resultados

| Caso | Controle 3.000 | Condição 5.000 | Contexto ativo BGE / evidências |
| --- | --- | --- | --- |
| F03: IaC do RACK | 3/3 corretas: Terraform | 3/3 corretas: Terraform | 2.953 / 25 → 3.487 / 30 |
| Q08: instituição do presidente da banca no histórico | 3/3 abstenções indevidas | 3/3 abstenções indevidas | 2.167 / 25 → 2.167 / 25 |

Em F03, resposta idêntica: “A ferramenta de Infrastructure as Code citada no
RACK é o Terraform. [E3]”. Conferido o excerto E3 de `RACK.pdf`: descreve o
provisionamento usando ferramentas de IaC como Terraform. A informação correta
já estava no controle; acrescentar cinco evidências não corrigiu uma falha.

Em Q08, os pares chunk/parent foram idênticos aos do controle nas três
repetições. O teto de 3.000 não era limitante. A claim da instituição PUCRS
recebeu suporte literal válido. Uma claim adicional sobre a presidência recebeu
testemunho parafraseado, rejeitado deterministicamente. A cobertura R1 exige
ambas, torna-se falsa e o reparo repete a citação inválida. A resposta final
é “Não encontrei evidências suficientes para responder.” O conteúdo necessário
foi recuperado: trata-se de falso negativo de verificação/cobertura, não falta
de espaço nem evidência ausente no corpus.

Todas as execuções concluíram um round. A entrada máxima reportada subiu de
7.255 para **8.317 tokens**; em F03, reasoning/answer/verification reportaram
8.317/7.804/8.310 na primeira repetição maior. Há uso real além de 8.192,
sem chegar perto da janela solicitada de 16.384. Não houve sinal de saída no
teto nas 33 chamadas novas. A janela efetiva não é confirmada por um campo
`num_ctx` observado do servidor; continuam disponíveis os parâmetros enviados
e o uso reportado. O digest permaneceu
`ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba`.

| Mediana total por caso | 3.000 | 5.000 |
| --- | ---: | ---: |
| F03 | 160,23 s | 168,61 s |
| Q08 | 281,40 s | 352,24 s |

Q08 não recebeu mais evidências apesar da latência maior. Assim, o custo
adicional não pode ser atribuído integralmente ao orçamento: carga/condições
remotas não foram controladas. Não diagnosticar offload/VRAM por esses números.

## Conclusão e limites

Orçamento maior é funcional e pode ampliar o contexto enviado, mas estes
controles **não demonstram melhoria de qualidade**. F03 já acertava e Q08 não
sofria pressão de packing. Não generalizar para multi-hop ou perguntas cuja
evidência necessária realmente tenha sido cortada por orçamento.

Próximo passo recomendado: corrigir/testar testemunhos literais e cobertura
por requisito em Q08, preservando rejeição de claims sem suporte. Para futuros
experimentos de capacidade, selecionar casos com evidência relevante perdida
especificamente na seleção por orçamento, anotando a recuperação dessa
evidência e a correção final, não só a quantidade de trechos.

A configuração padrão da aplicação permanece intacta: janela 8.192,
orçamento 3.000. Nenhum benchmark completo, correção de grounding, alteração
administrativa do servidor ou reindexação foi realizado nesta etapa.

## Reprodução

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --no-sync python -m benchmark.priority_controls \
  --mode integrated --num-ctx 16384 --context-tokens 5000 \
  --case-id REAL-F03 --case-id REAL-Q08 \
  --output-dir benchmark/results/runs/NOVA_CONDICAO_EVIDENCIAS_5000
```

Resultados operacionais ignorados pelo Git:
`benchmark/results/runs/phi4_evidence_budget_2026-10-05/5000/integrated/`.
Traces incluem prompts, respostas, configuração, identidade disponível,
latências e contexto ativo. Snapshots excluem `.env` e credenciais.

Validação local: 79 testes de controles/providers e três testes do harness
passaram. Três avisos SWIG já existentes. Compilação do harness e
`git diff --check` passaram. A suíte completa não foi reexecutada nesta etapa.
