# Auditoria do benchmark real — Cumbuco / Phi-4

Data: 02/10/2026. Escopo: execução `real_80_cumbuco_phi4_2026-10-02`, seus 80 traces e implementação atual. Auditoria offline; nenhuma nova inferência ou alteração do pipeline foi realizada nesta etapa.

## 1. Conclusão executiva

Esta configuração não está apta a responder o corpus avaliado. O resultado não demonstra, isoladamente, incapacidade do Phi-4 nem baixa qualidade dos embeddings: falhas anteriores à recuperação impedem essa conclusão.

Há três bloqueadores prioritários: contrato efetivo de contexto/geração não confirmado; planner que troca a pergunta por outra sem rejeição pelo domínio; verificação que permite entregar conteúdo irrelevante e, em um caso comprovado, afirmações não sustentadas pelas citações.

### Resultado observado

| Resultado | Quantidade |
|---|---:|
| Perguntas | 80 |
| Exceções | 61 (76,25%) |
| Respostas marcadas como parciais | 13 |
| Abstenções | 6 |
| Respostas completas corretas na revisão das saídas contra o gabarito | 0 |
| Perguntas que chegaram ao retrieval | 24 |
| Chamadas generativas HTTP | 240, todas HTTP 200 |
| Soma das latências por pergunta | 3.108 s, aproximadamente 51min48s |

As seis abstenções ocorreram em perguntas respondíveis. O caso U10 exigia esclarecimento e recebeu uma resposta parcial irrelevante. Os demais nove casos de impossibilidade falharam com exceção. Portanto, não há acerto de abstenção demonstrado nesta execução. HTTP 200 não significa resposta RAG correta.

| Categoria | Total | Exceções | Parcial | Abstenção |
|---|---:|---:|---:|---:|
| Factual em um documento | 10 | 6 | 2 | 2 |
| Entidades | 8 | 7 | 1 | 0 |
| Entre documentos | 10 | 5 | 3 | 2 |
| Multi-hop | 10 | 8 | 1 | 1 |
| Lista/agregação | 8 | 5 | 2 | 1 |
| Resumo | 6 | 6 | 0 | 0 |
| Tabela | 8 | 7 | 1 | 0 |
| Sem resposta/escopo insuficiente | 10 | 9 | 1 | 0 |
| Conversacional | 10 | 8 | 2 | 0 |

Erros: 33 por ausência de linhas tabulares no escopo; 22 por saída inválida do planner após reparo; três do reasoning; dois da verificação; um da resposta. Dos 56 casos sem retrieval, 55 falharam e um se absteve por escopo insuficiente.

## 2. Achados demonstrados e hipóteses

### P0 — Contrato remoto e orçamento de contexto

**Observação:** 199/240 chamadas reportaram exatamente 4.096 tokens de entrada; 55 produziram mais tokens de saída que o `max_tokens` solicitado. Todas as 104 chamadas de planner reportaram 4.096 tokens. O teste separado com `options.num_ctx=8192` também reportou 4.096 e excedeu o limite solicitado de saída.

**Código:** em `Providers.py`, `UFCAPIProvider` envia `temperature` e `max_tokens` na interface chat, mas não envia `num_ctx`; esse parâmetro só é encaminhado no formato legado. A instrumentação registra a configuração solicitada, que não comprova sua aplicação pelo servidor.

**Pressão de prompt:** os primeiros prompts F01–F03 possuem cerca de 21 mil caracteres. A pergunta aparece aproximadamente na posição 1.494, seguida por mais de 19 mil caracteres. Catálogo e enumeração de IDs no schema repetem informação. O reparo concatena resposta inválida e erro ao mesmo prompt, ampliando-o. O adapter CrewAI serializa mensagens em texto; o cliente remoto as transporta dentro de uma mensagem de usuário, sem preservar seus papéis originais como mensagens separadas.

**Hipótese:** truncamento, template ou interpretação de parâmetros do serviço contribui para a perda de instruções. Não foi demonstrado qual trecho é descartado, nem se o contador remoto reflete fielmente a entrada. Não é correto concluir que o modelo Phi-4 tenha limite intrínseco de 4.096 tokens. O probe com texto repetitivo é sinal de diagnóstico, não uma avaliação suficiente da janela efetiva.

**Melhoria:** distinguir parâmetros solicitados, enviados e observados; medir orçamento do prompt completo com tokenizer do gerador, incluindo schema, histórico, evidências e reserva de saída. Confirmar o contrato da versão implantada antes de alterar o payload.

### P0 — O planner perde a pergunta e o pipeline aceita

Exemplos dos traces:

| Caso | Pergunta original | Reescrita aceita |
|---|---|---|
| F03 | Ferramenta IaC do RACK; gabarito Terraform | Ano de fundação de uma empresa |
| F04 | Três dimensões do SAAR | Replicação de DNA |
| C01 | Coordenadores de AFO e RACK | Diretores da Pfizer e datas de nascimento |
| Q07 | Data/horário da prova e divulgação das notas | Ano de lançamento do iPhone |
| U10 | Projeto não especificado; precisa esclarecer | CEO da Microsoft |

`Flow.py` aceita `resolved_question` após validação estrutural e de IDs, sem verificar preservação da intenção. A lógica `original_matches_resolved` deixa a formulação original de fora justamente quando a reescrita difere. Reasoning e synthesis seguem essa nova pergunta; a verificação recebe a original, criando um fluxo internamente inconsistente.

**Melhoria:** manter a pergunta original imutável como objetivo de todas as etapas; reescritas e subqueries devem ser auxiliares. Validar coerência entre intenção, escopo, entidades e plano. Não resolver isso proibindo toda reescrita: follow-ups precisam de resolução contextual legítima. Catálogo compacto e schema menos redundante devem ser experimentados separadamente dessa proteção semântica.

### P0 — Suporte factual não equivale a responder; verificador também erra

Todas as 13 respostas parciais terminaram com `central_question_supported=false`. Mesmo assim, `Flow.py` entrega claims marcadas `SUPPORTED`, precedidas apenas por aviso de parcialidade. Uma frase verdadeira mas desconectada não é uma resposta parcial útil.

F03 entrega descrição do AFO em vez de Terraform. Q07 entrega uma pergunta sobre assinatura eletrônica como se fosse uma claim factual. Em L08 há problema adicional: a resposta atribui a Creto Vidal centros de pesquisa, bolsas e premiações. E6 trata de discussão administrativa e automatização de secretarias; E1 é rodapé de autenticidade. Esses excertos não sustentam as afirmações entregues. Logo, existe falso positivo de suporte, não só irrelevância.

O reparo é disparado por claims rejeitadas; a ausência de suporte à pergunta central, sozinha, não o dispara. Nas sínteses em lotes, combinar `central_question_supported` por OR também não comprova cobertura conjunta de todos os requisitos.

**Melhoria:** avaliar separadamente suporte de cada afirmação, pertinência à pergunta e cobertura dos fatos pedidos. Só apresentar uma resposta parcial quando ela responder a um subconjunto identificável desses fatos. Caso contrário, reparar uma vez e abster. Não confiar exclusivamente na autoavaliação do mesmo gerador: criar controles negativos e revisão independente.

### P1 — Agregação acionada sem capacidade documental

O catálogo desta execução contém 7.280 chunks, todos `section_detail`; nenhum `row_record`. Mesmo assim, 33 perguntas acionaram `aggregate()` antes do retrieval e falharam com `No structured table rows in requested scope`. Algumas eram factuais, não tabulares, como F01.

**Melhoria:** validar intenção e capacidade do escopo antes de executar operações tipadas. Ausência de estrutura não pode causar exceção indiscriminada. Expor ao planner capacidades reais; preservar o caminho especializado de planilhas e evoluir separadamente a representação de tabelas extraídas de PDFs. Para contas, validar operandos, unidades, proveniência e operação disponível — não transformar todo pedido numérico em agregação.

### P1 — Multi-hop e seleção de contexto precisam de avaliação isolada

Riscos identificados no código, cuja contribuição quantitativa ainda não foi isolada:

- Evidências são acumuladas até o orçamento, sem recomposição que substitua contexto inicial pouco útil. Um novo hop pode não acrescentar evidência porque o orçamento acabou; isso não equivale a ausência de novos resultados.
- Recupera-se child, mas a geração recebe parent; parents grandes podem consumir boa parte do orçamento de 3.000 tokens, contado com tokenizer de embeddings.
- A divisão rígida do orçamento por documento pode excluir parents que não caibam, mesmo relevantes.
- Expansão para parent e metadados podem diluir o trecho que recebeu bom score no reranker.
- Pergunta reescrita incorretamente contamina todos os hops seguintes.

**Melhoria:** distinguir motivos de descarte e parada; medir cobertura por hop; experimentar montagem por trechos/parents e recomposição orientada aos fatos faltantes. Não aumentar hops antes de corrigir o objetivo da pesquisa.

### P2 — Observabilidade e custos

Nos erros, `Engine.ask()` conserva diagnostics e chamadas, mas não serializa integralmente plano, estado e evidências parciais. Isso limita métricas em 61 casos.

O foco de fontes consumiu 18 chamadas e aproximadamente 75 segundos mesmo sem respostas úteis. Deve continuar posterior à aprovação substantiva da resposta. O índice dense faz busca e ordenação do conjunto permitido completo para desempate estável: há custo potencial de escala, mas ele não explica os erros semânticos desta execução.

Preservar os pontos positivos: pre-filtering exato, canais separados, RRF, reranker independente, IDs estáveis, cache documental independente do gerador e traces por etapa. Não há evidência aqui para substituir FAISS ou CrewAI.

## 3. O que este benchmark permite concluir

Nas 18 saídas sem exceção com âncoras aplicáveis, a cobertura literal selecionada e citada foi zero; U10 não possui âncora aplicável. Isso mede o contexto final produzido por consultas orientadas pelo planner, não Recall@K do retriever com a pergunta correta. Nos erros, métricas ausentes não devem ser convertidas arbitrariamente em zero de retrieval.

O conjunto tem 80 perguntas em nove categorias, mas famílias de casos compartilham documentos e fatos. Não são 80 observações independentes de produção. O gabarito ainda merece revisão humana independente. Os casos tabulares são de documentos/PDFs e não certificam regressão de planilhas reais.

O runner faz avaliação literal conservadora, não nota semântica automática. Usa basename para identificar documento nas âncoras: precisa identidade completa para futuros homônimos entre coleções. Os relatórios brutos ainda dizem `review_pending`; esta auditoria acrescenta revisão qualitativa, sem alterar os resultados originais ou fingir que ela é uma métrica automática.

A execução anterior com vLLM teve outra configuração e revisão incompleta; não permite afirmar superioridade entre modelos. Também não é válido extrapolar os quatro casos experimentais anteriores para estes 80.

## 4. Experimentos recomendados, em ordem

| Etapa | Controle e intervenção | Medidas e critério de decisão |
|---|---|---|
| 1. Contrato remoto | Prompt curto de controle; textos naturais longos com marcadores no início/meio/fim; variar apenas parâmetros documentados da versão implantada e limites de saída. Repetir pequenas amostras. | Tokens enviados/observados, finish reason, preservação dos marcadores, truncamento, latência. Só avançar quando houver configuração efetiva reproduzível; respeitar a capacidade do servidor. |
| 2. Planner | Mesmas perguntas e modelo; comparar prompt atual com catálogo compacto, mensagens estruturadas e schema reduzido, uma mudança por vez. | JSON válido, fidelidade à pergunta, intenção e escopo corretos, acionamento tabular indevido. Incluir follow-ups legítimos e ambiguidades. |
| 3. Retrieval isolado | Perguntas fixas sem planner; comparar escopo correto fornecido pelo gabarito com coleção completa. | Recall@1/5/10/30, MRR, nDCG e Complete Evidence Recall em dense, sparse, RRF, reranker e contexto final. Localizar a etapa de perda antes de trocar modelos ou chunking. |
| 4. Síntese/verificação | Pergunta original e evidências corretas fornecidas como controle; adicionar evidências irrelevantes e contraditórias em braços separados. | Correção por fatos, pertinência, suporte/cobertura de citações, falsas aceitações e abstenções. Controles negativos não podem passar como respostas parciais úteis. |
| 5. Tabelas e multi-hop | Casos controlados com estrutura e sem estrutura; variantes de orçamento/recomposição; dois versus três hops. | Exatidão de operandos/cálculos, cobertura completa, ganho por hop, descarte por orçamento, parada finita e custo. |
| 6. End-to-end | Congelar configuração e executar novamente o conjunto, após os controles anteriores. | Acerto completo e parcial útil separados de disponibilidade; erros, abstenção correta, latência p50/p95 e custo por resposta correta. |

Separar desenvolvimento e teste por família documental para evitar vazamento entre perguntas quase equivalentes. Como estes 80 casos já foram examinados para diagnóstico, reservar novos casos cegos para confirmação final. Registrar versão do serviço remoto, identidade/digest do modelo quando disponível, parâmetros efetivos, corpus/index fingerprint e revisão do código. Não ajustar várias variáveis ao mesmo tempo nem prometer percentuais de melhoria antes da medição.

## 5. Referências locais

- Resultados: `benchmark/results/runs/real_80_cumbuco_phi4_2026-10-02/run.json`.
- Saídas/gabaritos: `report.md` no mesmo diretório; traces comprimidos em `traces/`.
- Contexto: `context_probe.md` no mesmo diretório.
- Planejamento, packing, síntese e verificação: `application/service/rag/v2/Flow.py`.
- Transporte e structured outputs: `application/service/rag/v2/Providers.py`, `application/service/UfcOllama.py` e adapter CrewAI em V2.
- Recuperação e estrutura: `Dense.py`, `Retrieval.py`, `Documents.py`, `Tables.py`, `Coverage.py`, dentro de V2.
- Instrumentação: `application/service/rag/v2/Engine.py` e `benchmark/real_suite.py`.

Os artefatos operacionais de resultados permanecem locais/ignorados pelo Git. Este documento não contém credenciais e não modifica o baseline.
