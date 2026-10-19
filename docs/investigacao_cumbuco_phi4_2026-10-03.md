# Investigação controlada — Cumbuco / Phi-4

Data: 03/10/2026. Baseline preservado: `real_80_cumbuco_phi4_2026-10-02`. Resultados desta investigação: `benchmark/results/runs/investigation_cumbuco_phi4_2026-10-03/`.

## Conclusão

A integração enviava parâmetros num formato que o Open WebUI não aplicava como esperado para Ollama. O envelope `params` permitiu demonstrar contexto acima de 4.096 e limites de saída efetivos. Isso resolveu a troca completa de assunto nos planos interpretáveis deste experimento, mas permanecem erros de escopo, ambiguidade e verificação de contradições. Ainda não há configuração aprovada para uma nova rodada end-to-end.

Foram realizadas 288 chamadas generativas sequenciais: 48 controles de transporte, 216 de planner e 24 de síntese/verificação. Retrieval e aritmética não fizeram chamadas generativas. Nenhuma variante foi promovida ao provider de produção. A única alteração no runtime é a preservação de plano, estado e evidências parciais nos diagnostics de erro.

## 1. Preparação e identidade

Selecionados previamente 18 casos, dois por categoria: F01/F03, E03/E05, C01/C09, H03/H07, L07/L08, S01/S06, T04/T05, U03/U10 e Q01/Q07. As citações e adjacências foram verificadas nos documentos locais; as contas foram conferidas com aritmética decimal. Nenhuma resposta do gabarito foi corrigida. Esta revisão é do autor da investigação, não validação humana independente.

O serviço informa Open WebUI **0.8.10**. `/api/models` identifica `phi4:latest`, formato GGUF, 14,7B parâmetros, quantização **Q4_K_M**, digest `ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba`. Identidade observada na preparação; a API de geração não devolve digest por chamada.

Configuração, código, seleção, dataset e índice estão registrados nos artefatos. O fingerprint documental é o mesmo do baseline: `6c49f49797c1a5cb87118650cfeea80e7f3fc5410c48124bbff673371ab45a8b`. O gerador não recebeu gabaritos no planner ou no retrieval; no experimento oracle recebeu somente as evidências, explicitamente como controle.

## 2. Transporte e contexto — controle passou

A fonte oficial da versão implantada mostra que `apply_params_to_form_data` lê `params` e, para modelos Ollama, escreve esse conteúdo em `options`. Por isso, enviar `options` diretamente nesse caminho não garante que ele seja mantido. A conversão também trata o limite de geração de maneira diferente conforme sua posição no payload. Referências: [middleware 0.8.10](https://github.com/open-webui/open-webui/blob/v0.8.10/backend/open_webui/utils/middleware.py) e [conversão de payload 0.8.10](https://github.com/open-webui/open-webui/blob/v0.8.10/backend/open_webui/utils/payload.py).

O primeiro canário curto continha `CONTROLE_OK` mas recebeu comentários extras: o critério estrito falhou e foi conservado. Um controle adicional com instrução de sistema explícita passou **6/6**, sem alterar modelo. Esse segundo teste muda a instrução; não deve ser apresentado como correção isolada de transporte do primeiro.

Com textos naturais e todos os demais parâmetros fixos:

| Entrada longa | Contexto solicitado | Tokens de entrada reportados | Três marcadores recuperados |
|---|---|---:|---:|
| Mesmo texto | Padrão | 4.096 | 0/3 repetições |
| Mesmo texto | 8.192 em `params` | 5.146 | 3/3 repetições |

Controles deliberadamente longos pararam em **64, 64, 64** e **128, 128, 128** tokens conforme o limite enviado em `params`. Apesar do corte, o servidor retornou `finish_reason=stop`. Esse campo, sozinho, não comprova saída completa.

Está demonstrada uma configuração efetiva e reproduzível para os tamanhos testados. Não foi medida a janela máxima intrínseca do modelo. No planner, entradas de aproximadamente 7.700 tokens também foram reportadas pelo servidor. A mudança conjunta de contexto/temperatura no transporte do planner não permite atribuir toda diferença em relação ao baseline exclusivamente ao aumento de contexto.

## 3. Planner — controle não passou

Quatro condições cumulativas, três repetições por pergunta, usando o transporte validado e saída de 512 tokens. Cada comparação adjacente altera um componente: catálogo, enumerações do schema, depois papéis das mensagens. Os experimentos são single-shot: o reparo de JSON foi desativado somente nesta comparação para isolar o efeito do prompt.

| Condição | JSON válido | IDs de escopo exatamente iguais à referência | Escopo cobrindo a referência | Agregação sem linhas disponíveis |
|---|---:|---:|---:|---:|
| Prompt atual | 51/54 | 27/54 | 30/54 | 0 |
| Catálogo compacto | 54/54 | 30/54 | 33/54 | 2 |
| Schema reduzido | 48/54 | 30/54 | 33/54 | 0 |
| Papéis preservados | 51/54 | 27/54 | 27/54 | 3 |

“Escopo exato” compara o conjunto de documentos com a referência; consistência entre cardinalidade e `scope.kind` é medida à parte. “Cobertura” admite coleção inteira ou documentos adicionais. Esses indicadores não equivalem a correção completa do plano.

Não houve troca de assunto nos planos parseados revisados. Entretanto, todas as variantes perderam a parte de L07 sobre pessoas distintas. E03 selecionou março de 2022 em vez de agosto de 2022. H03 selecionou atas que não contêm a resposta, em vez de pesquisar a relação antes de restringir o escopo. U10 foi truncado em três condições e virou pesquisa multi-documento na quarta; nenhuma pediu a clarificação correta.

O catálogo compacto reduziu a entrada e melhorou validade sintática, mas removeu `relative_path` e não resolveu a seleção documental. A evidência não justifica adotá-lo automaticamente. Mesmo com temperatura zero houve pequenas diferenças entre repetições, inclusive acionamento de agregação.

## 4. Retrieval isolado — concluído

Executadas 16 perguntas respondíveis em duas condições: coleção completa e escopo de referência fornecido pelo gabarito. Queries são perguntas originais; follow-ups incluem as falas anteriores do usuário. Não houve reescrita por agente.

São registrados Recall@1/5/10/30, MRR, nDCG, Evidence Recall e Complete Evidence Recall por canal, fusão, reranker e contexto. Relevância de child usa sobreposição exata de trecho anotado, com mínimo explícito de caracteres; cobertura completa exige todo o fato anotado. Não há juiz LLM.

As âncoras originais dos coordenadores também incluíam títulos em outras seções. Acrescentamos uma avaliação suplementar com o campo/nome pedido, preservando a avaliação original e o gabarito. Essas novas âncoras foram conferidas contra a fonte, e o índice completo consegue cobri-las.

| Condição | Contextos com todas as evidências | Recall médio de evidências no contexto |
|---|---:|---:|
| Coleção inteira | **10/16** | **68,30%** |
| Escopo correto fornecido | **12/16** | **81,70%** |

As falhas remanescentes localizam problemas diferentes:

- F01/Q01: o escopo correto recupera o coordenador; na coleção inteira ele não entra no contexto.
- C01: a query de comparação não recupera os dois nomes mesmo no escopo correto; a busca privilegia descrições dos projetos.
- C09: modalidades das duas reuniões continuam ausentes no contexto, apesar de existirem no índice.
- H03: a integração ETL é encontrada, mas falta o coordenador.
- S01: parte da evidência desaparece na fusão/top-N; outra parte chega ao reranker e é descartada por orçamento na montagem final.

Esses resultados medem recuperação em controles, não acerto da geração nem melhoria de produção. O conjunto é pequeno e contém famílias correlacionadas.

## 5. Síntese e verificação — interrompidas por controle negativo

Usados `AgentTeam`, validação/reparo do registry e `RAGFlow.synthesize/verify` reais. O adapter experimental fornece o envelope validado de transporte. Não houve planner, retrieval ou foco de fontes nesse ramo.

O primeiro caso foi F01, com quatro condições, três repetições cada:

| Evidência fornecida | Resultado |
|---|---|
| Correta | Nome correto e claim aprovada em 3/3 |
| Irrelevante | Nenhuma claim aprovada em 3/3 |
| Vazia | Nenhuma claim aprovada em 3/3 |
| Duas fontes incompatíveis | Duas afirmações mutuamente contraditórias aprovadas em 3/3 |

No controle artificial de conflito, uma fonte atribui AFO II a Fernando e a outra atribui o mesmo projeto a Carlos, negando Fernando. Ambas têm rótulo neutro e nenhuma precedência temporal ou de autoridade. O answer produz as duas atribuições definitivas; o verifier classifica ambas `SUPPORTED` e marca `central_question_supported=true`, sem apontar conflito.

A revisão das saídas confirma a falha detectada pelo sentinel. A verificação individual contra cada excerto não garante coerência do conjunto de claims. O ramo parou após essas três repetições; as outras 17 perguntas e a comparação de dois/três hops com recomposição não foram executadas após esse gate. O acerto 3/3 com evidência correta refere-se somente a F01.

## 6. Tabelas — controles determinísticos

As parcelas 10.800 + 8.400 + 1.920 somam 21.120 horas; o documento imprime 21.200. O gabarito preserva a discrepância de 80. A diferença monetária março–abril foi conferida: R$ 6.150,04.

O agregador somou corretamente inteiros tipados e moeda brasileira com vírgula decimal. Strings `10.800`, `8.400`, `1.920`, entretanto, foram interpretadas como decimais e produziram **21,12**, não 21.120. Isso demonstra ambiguidade de formato no parser; não demonstra erro em planilhas já tipadas.

PDF textual sem `row_record` continua gerando exceção no agregador. A operação de diferença entre duas células também não existe no contrato atual de agregação. Portanto, planner e cálculo devem validar capacidades e formatos antes de executar.

## 7. Proposta concreta para a próxima implementação

1. **Adapter Cumbuco:** declarar o formato Open WebUI/Ollama explicitamente e enviar limites/contexto/temperatura em `params`, com testes de payload. Registrar solicitados/enviados/observados e sinalizar teto de saída atingido, sem tratar `stop` como garantia de completude. Preservar adapters de outros serviços.
2. **Objetivo e escopo:** manter pergunta original, resolução contextual e fatos pedidos disponíveis em reasoning, answer e verification. Usar referências documentais curtas no prompt, mapeadas deterministicamente para IDs estáveis; manter nomes/datas/proveniência úteis no catálogo. Quando o catálogo não permitir identificar o documento, pesquisar primeiro com escopo aberto em vez de escolher IDs arbitrários. Validar cardinalidade e pedidos de agregação. Testar ambiguidades sem listar toda a coleção como resposta.
3. **Grounding:** verificar suporte, pertinência, cobertura dos fatos e contradições entre claims/evidências. Fornecer também o contexto relevante de conflito ao verifier. Reparar uma vez quando faltar suporte central; entregar parcial somente para fatos pedidos efetivamente cobertos. O conflito F01 vira teste de regressão obrigatório.
4. **Retrieval/contexto:** experimentar queries por campo estrutural e decomposição de comparação nos casos perdidos; medir pools maiores antes do reranker para S01; medir recomposição do orçamento por fatos faltantes. Cada alteração tem braço de controle e não aumenta hops automaticamente.
5. **Tabelas:** normalizar valores com tipo e locale explícitos, preservar cabeçalhos/unidades e validar a capacidade do escopo. Contratos de cálculo devem explicitar operandos e proveniência. Acrescentar diferença controlada somente onde os operandos estiverem disponíveis.

Depois dessas correções aprovadas, repetir primeiro os controles que falharam e completar os ramos suspensos. Só então congelar a configuração, repetir as 80 perguntas e criar confirmação cega por famílias documentais adicionais. A rodada completa não foi executada nesta investigação.

## Reprodução e artefatos

Validação local: **157 testes passaram**, com três avisos de depreciação SWIG já existentes, usando `uv run --no-sync --with pytest==8.3.5 python -m pytest -q`. Compilação dos módulos novos e entrada CLI também passaram. Foram adicionados sete testes para seleção balanceada, métricas/deduplicação, cobertura completa, isolamento de homônimos, variantes de prompt, checkpoints e estado parcial em erros.

O uso dos CLIs está em `docs/benchmarking.md`. Seleção, controles e âncoras suplementares ficam em `benchmark/datasets/real/diagnostic_*.json`. `benchmark.investigation` executa os modos isolados; `benchmark.investigation_review` reavalia offline; `benchmark.investigation_tables` executa aritmética/capacidades.

No diretório da execução: `prepare.json`, `transport.json`, `transport_validation.json`, `planner.json`, `planner_scope_review.json`, `retrieval.json`, `retrieval_atomic_review.json`, `oracle.json`, `tables.json` e `semantic_review.json`. Todos os payloads estão sem cabeçalhos de autenticação; resultados permanecem ignorados pelo Git. Baseline e seus documentos/caches foram preservados.
