# Estudo comparativo de retrieval e próxima iteração

Data: 05/10/2026. Base: duas execuções completas, com 70 perguntas respondíveis em coleção completa e escopo correto fornecido. Este estudo usa os artefatos salvos; não executa novas buscas, embeddings, reranking ou geração.

## Decisão recomendada

O foco principal da próxima iteração deve ser **preservar a relação entre documento, seção e fato nos trechos recuperáveis**, acompanhado de uma auditoria do avaliador. A troca dos embeddings densos trouxe um ganho real no indicador registrado, mas deixou quase intacto o problema de recuperar relações como projeto → coordenador.

Antes de reindexar, há um controle barato e útil: passar toda a união das duas buscas ao reranker, em vez de cortar essa união em 30 candidatos. Esse controle separa o efeito do modelo do efeito da competição por vagas no ranking.

Aumentar a janela de contexto e substituir novamente o modelo de embeddings ficam em prioridade menor, diante dos limites observados abaixo.

## 1. O que a comparação demonstra

O experimento substituiu BGE-M3 denso por EmbeddingGemma denso. Os chunks, parents, catálogo, pesos esparsos BGE-M3, perguntas, históricos, escopos, reranker e orçamento de contexto foram preservados. A auditoria confirmou igualdade dos rankings e scores esparsos nas 140 avaliações pareadas. Foram conferidos os hashes dos datasets, fontes anotadas e bundles de índice.

| Categoria | Total | Falhas BGE-M3 | Falhas EmbeddingGemma |
|---|---:|---:|---:|
| Multi-hop | 10 | 7 | 6 |
| Cruzamento de documentos | 10 | 5 | 5 |
| Resumos | 6 | 3 | 3 |
| Continuação de conversa | 10 | 4 | 4 |
| Localização de entidades | 8 | 2 | 2 |
| Listas e agregações | 8 | 2 | 1 |
| Factual em documento único | 10 | 2 | 1 |
| Tabelas | 8 | 1 | 0 |
| **Total** | **70** | **26** | **22** |

O número de casos completos passou de 44/70 para 48/70: aumento de 5,7 pontos percentuais. A média, por pergunta, da fração de evidências cobertas passou de 72,1% para 76,9%.

Quatro casos passaram de incompletos para completos: `REAL-F01`, `REAL-H08`, `REAL-L03` e `REAL-T06`. Nenhum caso antes completo se tornou incompleto.

**Essa ausência de regressão vale para o indicador binário de completude.** Houve uma regressão parcial em `REAL-S03`: a cobertura caiu de 6/7 para 5/7 evidências, com perda de `RACK_CORE`. O caso já falhava nos dois modelos, por isso essa piora não aparece na tabela de contagem de falhas. `REAL-C08`, por outro lado, ganhou `SEP20_CHAIR`, mas continuou incompleto. A próxima avaliação deve acompanhar as duas métricas.

Os resultados pertencem a este corpus e a esta composição híbrida. As perguntas compartilham documentos e evidências; quatro casos recuperados não constituem quatro observações independentes de qualidade geral do modelo.

## 2. Onde o sistema perde cobertura

A união contém até 60 chunks: até 30 da busca densa e até 30 da esparsa, descontadas as duplicatas. O RRF combina as posições e escolhe os 30 que seguem para o reranker. As contagens abaixo usam a cobertura dos parents correspondentes, sem tratá-los como o contexto final.

| Etapa: perguntas com todas as evidências cobertas | BGE-M3 | EmbeddingGemma |
|---|---:|---:|
| Todos os parents do índice, conforme o avaliador literal | 63/70 | 63/70 |
| União completa dos candidatos densos e esparsos | 49/70 | 50/70 |
| 30 candidatos após o corte do RRF | 45/70 | 49/70 |
| Contexto final com orçamento de 3.000 tokens | 44/70 | 48/70 |

No Gemma, as 22 falhas podem ser classificadas pelo primeiro obstáculo observado, sem contar a mesma pergunta duas vezes:

| Primeiro obstáculo observado | Casos | Interpretação |
|---|---:|---|
| Cobertura literal não alinhável nem com todos os parents | 7 | Mistura problemas de representação e do avaliador; exige auditoria |
| Evidência necessária ausente da união das duas buscas | 13 | A etapa inicial não oferece cobertura completa ao restante do pipeline |
| União completa, mas perda no corte para 30 candidatos | 1 | `REAL-S03` |
| Candidatos completos, mas perda na seleção final | 1 | `REAL-L05` |
| **Total** | **22** | |

Assim, **20 das 22 falhas já têm um obstáculo antes do corte final de candidatos e da montagem do contexto**. Essa classificação não atribui uma causa única a cada pergunta: um caso pode também perder outras evidências em etapas posteriores. O arquivo de diagnóstico registra cada evidência separadamente.

### O ganho do Gemma inclui um efeito de ordenação

Três dos quatro casos recuperados (`H08`, `L03`, `T06`) **já tinham cobertura completa na união inicial do BGE**, mas perdiam evidências no corte para 30 candidatos. O Gemma mudou a ordenação e a composição do conjunto admitido ao reranker. Apenas `F01`, entre esses quatro casos, não tinha cobertura completa na união do BGE.

Portanto, não devemos interpretar todos os quatro ganhos como evidências que o BGE era incapaz de encontrar. Uma parte relevante do ganho passa pela fusão e pelo limite de candidatos.

O reranker atual melhora a ordem dos candidatos que recebe: no Gemma, a cobertura completa nos cinco primeiros passa de 34 casos após RRF para 43 após reranking. Isso não prova que ele seja ótimo, mas não aponta sua substituição como primeira prioridade.

## 3. O problema estrutural mais recorrente

Onze das 22 perguntas incompletas do Gemma dependem de uma das anotações `AFO_NAME`, `RACK_NAME` ou `SAAR_NAME`. Os seis multi-hop que continuam falhando são `H01`–`H06`; todos dependem dessas relações entre projeto e coordenador.

A inspeção do índice mostra, por exemplo, dois blocos distintos:

```text
Projeto
AFO - Automation of Federation Onboarding II
```

```text
Coordenador na Instituição
Fernando Antonio Mota Trinta
```

O segundo bloco contém nome e função, mas o texto usado para busca não carrega a identidade do projeto. O índice possui `relative_path`, `document_id` e outros metadados; a busca densa, a esparsa e o reranker usam o texto do chunk. A identidade documental armazenada em metadados não é automaticamente incorporada à representação que esses modelos comparam.

| Documento | Parents | Mediana de palavras por parent | Parents com menos de 30 palavras |
|---|---:|---:|---:|
| AFO | 503 | 14 | 407 |
| RACK | 415 | 14 | 322 |
| SAAR | 438 | 13 | 354 |
| **Total dos três** | **1.356** | — | **1.083 (79,9%)** |

O parâmetro `parent_tokens=1536` é um limite máximo, não uma garantia de agrupamento. `StructuredExtraction.docling_text()` produz uma seção para cada item textual do extrator; `Documents.build_document_chunks()` trata cada seção do sidecar separadamente. Ele pode dividir uma seção grande, mas não reúne esses itens pequenos em um parent que preserve a relação entre os campos.

Esse mecanismo oferece uma hipótese concreta para o próximo experimento: melhorar a representação das relações locais pode ter mais alcance que outra troca de encoder. Ainda é uma hipótese causal a testar, não uma promessa de recuperar os onze casos.

## 4. O avaliador precisa de uma auditoria antes de novos rankings de qualidade

Quatro anotações não recebem cobertura integral quando todos os parents são oferecidos ao avaliador atual:

- `AFO_DATES` e `SAAR_DATES`: rótulos e valores foram separados e recebem cabeçalhos repetidos.
- `SAAR_DASHBOARD`: a frase foi fragmentada em blocos, inclusive entre páginas.
- `SAAR_NAME`: o cabeçalho original com o título do projeto não foi preservado como aquele trecho no índice; o nome do coordenador existe.

Elas afetam sete perguntas: `F02`, `E01`, `H03`, `H06`, `S01`, `Q02` e `Q04`. Isso estabelece um teto de 63/70 casos completos **para a combinação atual de índice e avaliador**, independentemente do encoder.

Uma sondagem diagnóstica que permite alinhar o corpo do parent sem o cabeçalho repetido encontra cobertura textual para as duas anotações de datas e a de dashboard. Isso demonstra uma limitação do alinhamento atual. **Não adotamos essa sondagem como nova métrica:** textos e datas repetidos podem casar com várias posições, e a solução deve respeitar a proveniência e a seção correta.

Há um contraexemplo especialmente útil: com Gemma, `REAL-E01` já entrega “Lincoln Souza Rocha” e a identificação do projeto SAAR em trechos do documento correto. A anotação literal continua incompleta. No BGE, o nome não estava no contexto final. Portanto, a tabela binária esconde um ganho de recuperação nesse caso. É necessário revisar o suporte da relação; não basta aceitar qualquer ocorrência do nome.

A auditoria deve produzir uma versão explícita de avaliação por fatos mínimos e relações, com trechos/proveniência associados, mantendo a métrica literal antiga para rastreabilidade. As duas execuções devem ser repontuadas sob a mesma versão. Não comparar uma pontuação nova diretamente com os antigos 44/70 e 48/70 como se a definição fosse idêntica.

## 5. Controles que ajudam a descartar prioridades fracas

### Mais contexto: ganho pequeno nos candidatos atuais

Foi reproduzida a seleção real `collect()` → `select_context()` usando os candidatos e scores salvos. A execução de 3.000 tokens reproduziu exatamente os chunks selecionados e os acertos por evidência nas 140 perguntas/execuções da condição coleção completa. Não houve novas buscas nem inferência.

| Orçamento em tokens do tokenizer BGE | BGE: casos completos | Gemma: casos completos |
|---|---:|---:|
| 3.000 | 44 | 48 |
| 4.500 | 45 | 49 |
| 6.000 | 44 | 49 |
| 12.000 | 45 | 49 |

O único caso que se torna completo é `L05`. No BGE, o ganho não é monotônico: a seleção gulosa admite blocos maiores ao ampliar o orçamento e pode deslocar um bloco posterior. Não ocorreu regressão em relação aos casos completos no orçamento original, mas `L05` volta a ficar incompleto em 6.000.

Este é um controle de seleção de evidências, não um teste de janela do gerador. Aumentar o contexto não recupera evidências que não chegaram aos candidatos.

### Escopo correto: ajuda, mas não elimina o problema

Com os documentos corretos fornecidos, o Gemma passa de 48 para 55 casos completos. São recuperados `C07`, `C08`, `L05`, `S03`, `S04`, `Q01` e `Q10`; nenhum caso completo regride. Os seis multi-hop `H01`–`H06` continuam incompletos.

Isso justifica estudar resolução de escopo e decomposição de consulta mais adiante. O controle recebe informação do gabarito, então seus ganhos não devem ser apresentados como capacidade automática existente.

## 6. Próxima rodada proposta

### Etapa 0 — validar a medição

Revisar as quatro anotações não alinháveis, `E01` e a regressão parcial de `S03`. Conferir texto original, trechos selecionados e proveniência. Manter as relações de entidade/cargo/projeto como requisito. Definir uma versão de scoring que distinga evidência ausente, relação incompleta e fragmentação/formatação da anotação. Repontuar as duas execuções existentes antes de novos comparativos sob essa definição.

### Experimento de controle — remover o corte antecipado para 30

**Hipótese:** o corte do RRF descarta evidência útil que o reranker poderia selecionar.

- Manter `search_k=30` por canal e os rankings já obtidos.
- Comparar `rerank_k=30` com a união inteira, de até 60 candidatos.
- Reranquear essa união com o mesmo modelo e manter o contexto em 3.000 tokens.
- Fazer o controle tanto para BGE quanto para Gemma.
- Casos sentinela: `H08`, `L03`, `S03`, `T06`; avaliar também todas as 70 perguntas.

O envelope observado permite cobertura pré-contexto de 49 casos no BGE e 50 no Gemma. Isso é um limite de disponibilidade da união salva, não previsão do resultado após reranking e seleção. Medir latência adicional e regressões parciais. Esse teste não exige reindexação e esclarece quanto do ganho atribuído ao encoder pode ser obtido ajustando os candidatos.

### Experimento principal — contexto documental e blocos relacionados

**Hipótese:** trechos curtos perdem relevância e relações por não carregarem a identidade do documento e por serem separados de campos vizinhos.

Usar Gemma como referência experimental e variar um fator por braço:

| Braço | Alteração | O que fica fixo |
|---|---|---|
| R0 | Configuração atual | Referência |
| R1 | Acrescentar identidade documental e caminho de seção ao texto usado para retrieval | Mesmas fronteiras de chunks e parents; mesmos modelos, consulta e orçamento |
| R2 | Agrupar blocos adjacentes da mesma seção e preservar cabeçalhos sem corpo | Mesmos modelos, protocolo de consulta e orçamento; sem acrescentar o enriquecimento de R1 |
| R3, posterior | Combinar R1 e R2, se os controles mostrarem benefício | Mesmos critérios de avaliação |

Em R1, o texto de retrieval deve ser explicitamente separado do excerto original usado como evidência. Documentar sua aplicação nos canais denso/esparso e no reranker. A identidade deve vir do próprio documento, nunca das respostas esperadas. Aplicar a regra a todo o corpus, não apenas aos três projetos conhecidos.

Em R2, o agrupamento deve respeitar seção, ordem de leitura, proveniência e limites de tamanho. Campo e valor, projeto e coordenador, e frases partidas entre páginas são casos sentinela. Não concatenar blocos arbitrários nem atravessar documentos. “Parent maior” deve significar uma unidade documental coerente, não apenas mais tokens.

Casos sentinela: `E01`, `E02`, `C01`, `H01`–`H06`, `Q01`, `Q10`; os quatro ganhos atuais (`F01`, `H08`, `L03`, `T06`) devem ser preservados. Os sentinelas orientam inspeção, mas o julgamento usa o conjunto completo e a versão de scoring congelada após a auditoria.

### Experimento posterior — consultas em etapas

Se a representação estiver adequada e as cadeias continuarem incompletas, comparar a consulta original com uma segunda busca baseada somente em entidades encontradas na primeira. Por exemplo: localizar o projeto pela pista técnica e então buscar seu coordenador. Medir separadamente recuperação de cada ligação, cadeia completa e custo. Esse protocolo muda a estratégia de retrieval e deve ter seu próprio baseline; não misturá-lo à avaliação atual de uma única rodada.

BM25 pode ser outro experimento futuro para substituir a parte esparsa. Os resultados atuais não medem essa troca e não a sustentam como principal correção das falhas observadas.

## 7. Critérios de decisão

- Publicar completude por categoria, cobertura parcial e IDs que melhoram ou pioram. Inspecionar ganhos concentrados na mesma evidência, para não confundir repetição com generalização.
- Manter corpus, perguntas, versão de scoring e parâmetros não investigados congelados em cada comparação.
- Exigir proveniência correta: nome certo de outro projeto ou cargo não é sucesso.
- Registrar contagem de candidatos, tamanho do contexto, latência e custo de reindexação; a comparação anterior de CPU BGE e GPU Ollama não é um benchmark de hardware equivalente.
- Julgar a hipótese também na etapa que ela pretende corrigir: cobertura da união para R1/R2; perdas do corte para o controle de reranking; cobertura de cada ligação para consultas em etapas.
- As 70 perguntas já foram observadas. Uma alegação de generalização exigirá perguntas novas e independentes, não apenas ajustes até acertar este conjunto.

## Artefatos e reprodução

- Baseline: `benchmark/results/runs/retrieval_isolated_2026-10-05_fresh/`.
- Gemma: `benchmark/results/runs/embeddinggemma_dense_2026-10-05/`.
- Diagnóstico: `benchmark/results/studies/comparacao_retrieval_2026-10-05/study.json`.
- Casos e causas: `benchmark/results/studies/comparacao_retrieval_2026-10-05/case_diagnosis.csv`.
- Auditoria de alinhamento: `benchmark/results/studies/comparacao_retrieval_2026-10-05/annotation_alignment_audit.json`.
- Replay de contexto: `benchmark/results/studies/comparacao_retrieval_2026-10-05/context_replay.json`.

```sh
.venv/bin/python -m benchmark.retrieval_comparison_study \
  --baseline-dir benchmark/results/runs/retrieval_isolated_2026-10-05_fresh \
  --candidate-dir benchmark/results/runs/embeddinggemma_dense_2026-10-05 \
  --output-dir benchmark/results/studies/comparacao_retrieval_2026-10-05

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m benchmark.retrieval_context_replay \
  --run-dir benchmark/results/runs/retrieval_isolated_2026-10-05_fresh \
  --run-dir benchmark/results/runs/embeddinggemma_dense_2026-10-05 \
  --output benchmark/results/studies/comparacao_retrieval_2026-10-05/context_replay.json
```

Pontos de código para a próxima iteração: `application/service/StructuredExtraction.py` (`docling_text`), `application/service/rag/v2/Documents.py` (`build_document_chunks`), `application/service/rag/v2/Retrieval.py` (`HybridRetriever.search`), `benchmark/real_suite.py` (`anchor_coverage`) e `application/service/rag/v2/Flow.py` (`select_context`). Nenhuma dessas rotinas foi alterada por este estudo.
