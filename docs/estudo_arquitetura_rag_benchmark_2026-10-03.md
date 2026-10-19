# Estudo crítico da arquitetura RAG V2

Data: 03/10/2026. Base principal: `real_80_cumbuco_phi4_params_2026-10-03`, com os controles da investigação anterior como evidência complementar.

## Conclusão

A V2 possui uma base determinística aproveitável: FAISS com escopo real, sparse BGE-M3, RRF, reranking, IDs persistidos, cache versionado e traces. O problema dominante está nas decisões semânticas que conectam esses componentes. Uma escolha documental incerta torna-se filtro definitivo; estados contraditórios encerram a investigação; o contexto acumula as primeiras evidências; a verificação aceita citações verdadeiras que não demonstram a relação perguntada.

A arquitetura tem um Flow multi-hop, mas praticamente não exerceu esse comportamento: dos dez casos multi-hop, um falhou no planner e nove encerraram no primeiro round. Em toda a execução, houve apenas uma chamada ao Research Agent. Isso muda a interpretação de “0/10 acertos completos”: não é um experimento que demonstrou fracasso de três hops efetivamente executados.

Recomendo evoluir contratos e políticas do Flow antes de trocar modelo, framework, embeddings ou banco vetorial. Os resultados não justificam essas substituições neste momento.

## Evidência e limites do estudo

Foram lidos código, 80 traces, respostas, gabaritos, catálogos de candidatos, bundle de índice e testes. O hash atual dos arquivos de `application/service` coincide com o hash registrado nessa execução. As verificações desta auditoria foram offline; nenhuma nova chamada generativa ou benchmark foi executado.

A execução usou Phi-4 via Cumbuco, contexto solicitado de 8.192, com o envelope `params` aplicado somente pelo harness. A aplicação de produção ainda usa o adapter anterior. Comparações entre essas duas condições precisam preservar essa identificação.

| Observação | Resultado e interpretação |
| --- | --- |
| Disponibilidade | 70/80 sem exceção, contra 19/80 no baseline. Não equivale a correção. |
| Revisão semântica inicial | 19/70 completas e 6/70 parciais úteis nas perguntas respondíveis; classificação assistida contra fatos obrigatórios, ainda sem revisão humana independente. |
| Controles negativos | 6/10 com abstenção adequada; inclui ambiguidade no conjunto. |
| Escopo documental | Em 36 dos 68 casos respondíveis com plano válido, o escopo não cobre ao menos um documento de referência. Um deles pede clarificação; nos outros 35 o filtro omite a referência. |
| Multi-hop observado | 73 casos chegaram somente ao round 1; um chegou ao round 2; seis ficaram no round 0. Nenhum chegou ao 3. |
| Estado contraditório | 34 casos têm simultaneamente `unanswerable=true` e `requires_additional_retrieval=true`. |
| Planner | Mediana de 7.768 tokens de entrada reportados, janela solicitada de 8.192, orçamento de saída 512. |
| Índice | 88 documentos, 7.280 children, 6.879 parents; todos os children `section_detail`; nenhuma linha com `row_values`. |
| Citações | 84 claims com IDs existentes; esse teste não mede suporte semântico. |

Cobertura de escopo compara os documentos anotados, não todas as fontes alternativas possíveis. Por exemplo, uma ata posterior pode repetir um nome da ata de referência. A contagem não prova que os 36 casos tenham ficado totalmente sem evidência; exemplos como E03 demonstram diretamente o filtro errado. Campos e métricas não observados não foram estimados.

## 1. O planner tem autoridade excessiva sobre a recuperação — prioridade P0

**Evidência observada.** E03 pergunta pela ata de 19/08/2022 e seleciona `03-2022_Ata_de_Reuniao.pdf`. F05 pergunta por 13/07/2022 e seleciona uma ata de junho. H02 precisa descobrir o projeto a partir de Redfish, mas restringe a busca a duas atas sem RACK. E02 inclui `neymar.jpg` junto de RACK. S02 restringe uma pergunta sobre AFO a cinco atas.

**Mecanismo.** `Flow.answer()` aceita os IDs quando pertencem ao catálogo. Não valida se o documento corresponde à data, entidade, tipo ou relação solicitada. A lista vira um escopo fixo antes de todas as buscas. O FAISS executa corretamente o pre-filtering e, justamente por isso, torna impossível recuperar um documento excluído por engano.

O catálogo gerado em `Documents.py` contém apenas ID, nome e caminho. Não há descrição factual do documento, data canônica do evento, entidades ou capacidades tabulares. Nomes muito parecidos de atas aumentam a dificuldade. `Scope` aceita `explicit_single_document` com dois IDs, como confirmado em validação offline. A enumeração de IDs assegura identidade válida, mas não adequação semântica.

**Direção recomendada.** Separar restrição explícita do usuário de hipótese do planner. Resolver referências documentais por um catálogo pesquisável, com aliases, tipo e datas provenientes da fonte. Usar identificadores curtos nos prompts, mapeados aos IDs estáveis por código. Quando a pergunta exige descobrir qual projeto contém um atributo, pesquisar a relação antes de restringir o documento. Permitir revisão controlada do escopo quando faltam fatos, respeitando restrições explícitas do usuário.

**Experimento.** Nos mesmos casos, comparar o resolver atual com resolução documental em duas etapas, mantendo query/ranking/modelo. Medir cobertura das referências, documentos extras, clarificação indevida e custo. E03/F05/H02/E02 são controles obrigatórios. Um catálogo apenas mais curto já foi testado e não resolveu a escolha documental; não basta adotar esse ajuste isolado.

Referências de código: `Documents.py:40`, `Models.py:7`, `Flow.py:345–386`.

## 2. O multi-hop para quando deveria decidir como continuar — prioridade P0

**Evidência observada.** Em 34 casos, o reasoning declara impossibilidade e necessidade de buscar mais ao mesmo tempo. Sete são H02/H03/H04/H07/H08/H09/H10. O Flow encerra todos esses casos no primeiro round. H08 pede explicitamente multi-hop no plano, identifica Pablo e a lacuna sobre sua disciplina, mas para antes de pesquisar essa lacuna.

**Mecanismo.** Os três booleanos `sufficient`, `unanswerable` e `requires_additional_retrieval` são independentes. Em `Flow.py:452`, suficiência ou impossibilidade causam `break` antes de consultar a necessidade de nova busca. O schema aceita essa contradição. A ausência de um fato no top-K acaba tratada como ausência no corpus.

A síntese ocorre mesmo depois de `stop_reason=unanswerable`. Cinco desses casos terminaram como `answered`: C01, C02, H02, S05 e U02. C02 efetivamente responde bem; os demais mostram por que a decisão não deve depender de uma bandeira isolada. `established_facts`, `missing_facts` e `contradictions` não são transmitidos à síntese, que relê o contexto e pode ignorar o diagnóstico anterior.

**Direção recomendada.** Tornar a próxima ação uma decisão validada: responder, recuperar uma lacuna, rever escopo, pedir clarificação ou abster. “Ainda não encontrado” precisa ser diferente de “impossível após as tentativas permitidas”. Manter fatos, lacunas e dependências entre fatos em estado compartilhado, e transmitir esse estado à síntese/verificação. Um fato estabelecido deve manter seus IDs e o vínculo com a necessidade que ele satisfaz.

**Experimento.** Reproduzir estados contraditórios com respostas simuladas e testar a política sem LLM. Depois executar os dez casos H com plano/escopo corretos fornecidos como controle, medindo novas evidências por round. Só comparar dois versus três hops depois de confirmar que o segundo realmente ocorre.

Referências: `Models.py:75`, `Flow.py:202`, `Flow.py:431–478`; `tests/test_rag_v2_flow.py` atualmente exercita um agente simulado cooperativo, sem esse conflito de estado.

## 3. Grounding verifica frases, mas não garante a resposta — prioridade P0

**Evidência observada.** H02 recebe evidência de José Macedo coordenando um projeto de Big Data e aprova uma claim que o vincula à automação via Redfish. L05 confunde presentes na reunião com comissão julgadora. U02 transforma cronograma de preparação para implantação em prova de implantação realizada. C01 aprova o título genérico “Coordenador do Projeto” como resposta a uma pergunta que exige nomes.

**Mecanismo.** A verificação recebe a pergunta original, claims e apenas as evidências citadas por cada claim. Isso ajuda a limitar referências indevidas, mas não informa os fatos obrigatórios, a resolução conversacional, as lacunas já detectadas ou os conflitos com outras evidências. `central_question_supported` é um único booleano sem justificativa estruturada por requisito.

Há duas brechas determinísticas adicionais:

- O reparo semântico só é acionado quando alguma claim não é `SUPPORTED`. Falta de resposta central, com claims verdadeiras mas irrelevantes, não dispara esse reparo.
- Se há qualquer claim aprovada, `central_question_supported=false` produz uma resposta parcial, mesmo que ela não cubra nenhum fato solicitado. C07/C08/L07/Q10 exemplificam parciais sem utilidade para a pergunta.

Nos lotes, o suporte central é agregado por OR: basta um lote dizer “sim”. Isso não demonstra que a união cobre todos os itens exigidos. Não há verificação global final de contradições entre claims. O controle anterior de duas coordenações incompatíveis aprovadas em 3/3 confirma essa lacuna.

**Direção recomendada.** Introduzir requisitos da resposta com IDs e registrar, para cada um, fatos/claims/evidências que o cobrem. Separar suporte textual, pertinência, cobertura, modalidade temporal e consistência global. Reparar também falta de suporte central; entregar parcial somente quando pelo menos um requisito substantivo estiver atendido. Contradições devem permanecer explícitas, com suas fontes, e bloquear uma conclusão definitiva quando não houver critério de resolução.

**Experimento.** Controles com nome correto no cargo errado, proposta versus decisão, previsão versus realização, documento de outra data, evidências contraditórias e fato verdadeiro irrelevante. Medir falsas aprovações e falsas rejeições separadamente; calibrar somente um threshold genérico seria insuficiente.

Referências: `Flow.py:158–245`, `Flow.py:488–530`, `Models.py:109–118`.

## 4. A pergunta e o contexto conversacional perdem informação — prioridade P0

Em Q08, o histórico fala da banca de Algoritmos e Banco de Dados. O planner mantém “De qual instituição é o presidente dela?” sem resolver “dela”, cria a query “presidente da instituição” e o resultado passa a ser o presidente da ASTEF.

Somente o planner recebe o histórico. Reasoning e Answer recebem `resolved_question`; Verification recebe apenas `original_question`, sem histórico nem resolução. Portanto, mesmo uma resolução correta do planner não é conhecida integralmente pelo verificador. A condição de igualdade literal entre original e resolvida também decide se a pergunta resolvida entra como query: uma reescrita legítima pode fazer o retrieval depender exclusivamente das subqueries.

Recomendo um contrato compartilhado com pergunta original, pergunta autossuficiente resolvida, referências conversacionais e fatos pedidos. Validar que entidades, datas e restrições foram preservadas, permitindo esclarecimento quando uma referência realmente não se resolve. O histórico da conversa ajuda a interpretar a pergunta; não deve ser usado como evidência documental de verdade.

Referências: `Flow.py:350`, `Flow.py:177`, `Flow.py:205`, `Flow.py:391–401`, `Flow.py:440`.

## 5. Há perdas demonstradas entre ranking e contexto — prioridade P1

No caso C01, o escopo AFO/RACK está correto. Mesmo assim:

| Evidência | Onde foi encontrada | Onde desapareceu |
| --- | --- | --- |
| Fernando, coordenador do AFO | Dense rank 23 na subquery sobre AFO | RRF rank 33, fora do top-30 enviado ao reranker |
| Paulo, coordenador do RACK | Dense rank 5, RRF 13, reranker 16 em uma das buscas | `document_token_budget` na seleção de contexto |

O reranker não pode recuperar um candidato que não recebeu. RRF está implementado corretamente; o resultado mostra uma limitação da composição de canais e do corte escolhido, não erro da fórmula. Campos curtos aparecem apenas em um canal e podem perder espaço para textos longos presentes nos dois.

`collect()` percorre candidatos e mantém os primeiros parents que cabem. O estado só acumula evidências; queries posteriores não substituem evidências anteriores menos úteis. O orçamento é dividido igualmente entre documentos. Cada query é enviada a cada documento do escopo, inclusive “coordenador do AFO” no RACK. Isso aumenta custo e faz a ordem das queries influenciar a seleção final.

No único round 2 observado, S02, seis queries foram aplicadas a cinco atas: 30 buscas. Houve 689 rejeições por orçamento documental, contagem de eventos que pode repetir candidatos. O Flow parou por `no_new_evidence`, estado que não distingue ausência de novos resultados de impossibilidade de acomodá-los. O escopo já estava errado, portanto não se pode atribuir o fracasso inteiro ao packing.

**Experimentos separados:** queries por campo/relação; candidatos do reranker 30 versus 60 com orçamento final igual; coleta conjunta e reranking entre queries; seleção por fatos cobertos; substituição de contexto quando surge evidência melhor; desempate de documentos pelo escopo efetivamente pedido. Reservar contexto de apoio sem exigir sempre o parent inteiro. Medir cobertura adicional, custo e perda por estágio antes de promover qualquer variante.

Referências: `Retrieval.py:163–184`, `Flow.py:80–144`, `Flow.py:412–430`.

## 6. Parent-child existe, mas a unidade documental é excessivamente fragmentada — prioridade P1

O índice tem 6.879 parents para 7.280 children: quase um parent por child. A mediana do parent é 132 caracteres; em AFO/RACK/SAAR, aproximadamente 86–89. SAAR tem 438 parents. Os nomes dos três coordenadores existem no índice, acompanhados do heading correto; o problema não é uma ausência geral desses nomes na ingestão.

`docling_text()` cria uma “section” por item textual com o último heading visto. `build_document_chunks()` trata cada item como unidade inicial, sem recompor a seção lógica nem preservar uma pilha completa de headings. Há trechos “Coordenador na Instituição\nEmpresa” em RACK/SAAR: o heading continua sobre o item seguinte. O texto enviado ao encoder/reranker não inclui o nome do documento; um campo curto correto perde parte da associação com o projeto, embora essa associação exista nos metadados.

**Hipótese sustentada pela estrutura:** parte da dificuldade em achar relações campo–valor vem da perda de hierarquia e dos muitos fragmentos pouco informativos. Ainda é necessário um experimento para quantificar o ganho de recomposição.

Recomendo agrupar itens pela seção hierárquica, preservando limites de tabelas, cabeçalhos e proveniência; representar pares campo–valor e sua entidade documental; testar um prefixo contextual curto no texto de busca, mantendo o excerto original para citações. `parent_tokens` deve ser um teto, não o critério único para definir unidade semântica. Preservar o tratamento especializado de planilhas.

Referências: `StructuredExtraction.py:36–66`, `Documents.py:52–155`, `Retrieval.py:28`.

## 7. O caminho tabular não atende ao corpus usado — prioridade P0 para cálculos

Todos os 7.280 chunks deste corpus são `section_detail`, sem `row_values`. O agregador determinístico aceita apenas `row_record`. Isso não significa que o suporte a planilhas esteja quebrado; significa que a rota de cálculo não está disponível para as tabelas em PDF deste benchmark.

Em T04, `aggregation=null`; o cálculo fica com o LLM. O primeiro draft acerta 21.120 e a diferença de 80, mas rotula incorretamente a soma como total impresso. A verificação confunde cálculo e observação documental; o reparo passa a afirmar `19.200 + 1.920 = 21.200`. O verificador então aprova essa igualdade e rejeita a diferença correta. Há uma regressão aritmética durante o reparo, não apenas um erro inicial de geração.

O parser `decimal_value()` também interpreta `10.800` como 10,8 quando a string não contém vírgula; o controle anterior demonstrou soma 21,12 para as três parcelas brasileiras. Diferença entre células não existe em `TableOperation`.

Recomendo extrair operandos com célula/linha, tipo, unidade e locale; validar a vinculação aos excertos; calcular por código; distinguir `valor_impresso` de `valor_calculado`; permitir que ambos coexistam quando o documento é inconsistente. Publicar no catálogo a capacidade tabular real e impedir que o planner acione operações indisponíveis. Não converter indiscriminadamente todo PDF em planilha; preservar as tabelas úteis como estrutura adicional.

Referências: `Tables.py:6–60`, `Models.py:29`, `StructuredExtraction.py:55`, `Flow.py:381`.

## 8. O orçamento é local a cada componente, não ao pedido completo — prioridade P1

O planner recebeu mediana de 7.768 tokens reportados para janela de 8.192 e saída máxima de 512. Esse conjunto não deixa a folga esperada; a interpretação exata dos contadores depende do servidor. Vinte chamadas de vários papéis reportaram 8.192 tokens de entrada; isso não prova truncamento por si só.

O packing usa o tokenizer BGE, enquanto geração usa Phi-4. Conta texto dos parents, mas não todo o envelope de mensagens, instruções do CrewAI, JSON, schema, enumerações e saída. O registry adiciona IDs do catálogo ao schema depois de o catálogo já constar do prompt. O reparo acrescenta o output inválido e todo o erro ao mesmo pedido, sem novo cálculo de orçamento.

`ProviderLLM.call()` serializa mensagens em uma string, perdendo os papéis na interface comum. No adapter UFC, geração retorna apenas texto; uso e término ficam disponíveis somente pela instrumentação especial do benchmark. A arquitetura de capabilities existe, mas não fornece ao domínio um resultado comum com parâmetros efetivamente enviados, uso e término.

**Direção:** orçamento por pedido completo e por provider/modelo; reserva de saída e margem; IDs curtos; schemas concisos; reparos compactos conforme o tipo de erro; limite de itens além do limite de tokens. Um envelope comum de mensagens e resultado evita depender de monkeypatch HTTP para observar o contrato. Investigar structured output nativo onde suportado, sem presumir capacidade do endpoint.

O ensaio anterior com papéis preservados não melhorou consistentemente o planner. Essa mudança é um saneamento de contrato a validar, não uma promessa de ganho isolado. O benchmark também não demonstra que contexto maior sozinho resolveria os erros semânticos.

Referências: `Agents.py:25`, `Providers.py:162`, `Providers.py:357–410`, `Config.py:14–57`.

## 9. Cobertura de resumo, observabilidade e custo — prioridade P1/P2

`evidence_batches()` percorre todos os parents do escopo e marca os agrupados como `processed_parents` antes da síntese. Em S01 informa 438 processados, sete lotes e `complete=true`, mas a execução falha na verificação do primeiro lote; as duas chamadas de answer são draft e reparo. Esses 438 itens foram preparados, não todos efetivamente sintetizados.

A lista `state.evidence` recebe os parents de todos os lotes antecipadamente. Portanto, estar no trace como evidência não garante ter sido visto pelo Answer Agent. Em uma execução concluída, a síntese de lotes também não faz redução final orientada aos fatos pedidos: deduplica texto idêntico e concatena claims. Isso permite redundância, omissões e conflito entre lotes.

O gatilho de cobertura depende de strings exatas de intenção. Entre 76 planos válidos, houve 50 `single_fact`, 14 `comparison`, seis `cross_document`, três `entity_lookup`, dois `explicit_multi_document` usados indevidamente como intent e um `document_expansion`. Somente S01 ativou a enumeração estrutural. A taxonomia flexível virou comportamento implicitamente frágil.

Recomendo separar intenção descritiva de capacidades executáveis validadas (`needs_exhaustive_coverage`, relações, cálculo); distinguir candidatos recuperados, evidências selecionadas, lotes preparados, enviados e concluídos; mapear cada trecho à chamada que efetivamente o recebeu; consolidar fatos entre lotes antes da resposta final.

Custos observados: aproximadamente 941s em reranking, 718s nas chamadas do planner e 661s em reasoning. Dense e sparse somados consumiram menos de um segundo nas buscas medidas. Trocar FAISS por outro banco não ataca o custo principal demonstrado. Queries por partição recalculam o embedding da mesma query; reutilização por query é uma otimização simples a medir depois da correção do plano.

O papel `source_focus` consumiu 47 chamadas e 151s. Das 86 fontes citadas, 41 tiveram foco, 34 ficaram indisponíveis e 11 em fallback. Dezesseis chamadas tiveram erro de validação; há citações acima dos 240 caracteres. O orçamento do lote considera tamanho dos excertos, não quantidade de vínculos claim–evidência e saída necessária. Melhorar batching e validar cada seleção independentemente é prioridade inferior à correção da resposta.

Referências: `Coverage.py:6–68`, `Flow.py:248–336`, `Flow.py:482–530`, `Engine.py:253–280`.

## 10. O que manter e o que os testes ainda não demonstram

Manter o pre-filter exato, a semântica sparse, RRF, reranker isolado, cache independente do modelo gerativo, IDs e proveniência, estado tipado, limites de execução, compatibilidade de fontes e os traces. Existem testes úteis de exatidão do FAISS, equivalência sparse com a função oficial, cálculo do RRF, referências inválidas, cache e histórico. Não apareceu evidência para substituir CrewAI; os problemas descritos estão nas políticas e payloads construídos pelo projeto.

Os 158 testes aprovados confirmam contratos exercitados, não correção semântica em produção. O teste de multi-hop usa um agente simulado que devolve os estados esperados; não cobre impossibilidade junto com pedido de busca. O teste de follow-up garante que o histórico chega ao planner, mas não que a referência resolvida chega à verificação. IDs existentes não demonstram relação correta entre pessoa, cargo e data.

Priorizar regressões extraídas dos traces: estado contraditório; escopo com data errada; JSON válido com plano incoerente; nome correto no papel errado; planejamento versus realização; soma e total impresso divergentes; falta de contexto em nova busca; parcial sem fato pedido; lotes preparados que falham antes da síntese.

## Sequência recomendada de investigação e correção

| Ordem | Intervenção | Evidência de aceite |
| --- | --- | --- |
| 1 | Unificar o contrato Cumbuco validado com o runtime e registrar identidade/parâmetros | Mesmo payload e controle de transporte no app e harness; sem alterar geração/retrieval nessa comparação |
| 2 | Validar plano, escopo e referências conversacionais | Redução de escopos que excluem referências; E03/F05/Q08 com alvo correto; nenhuma adição arbitrária como E02 |
| 3 | Corrigir transições multi-hop e orçamento substituível | Estados contraditórios resolvidos; H08 busca a lacuna; diferenciar falta de espaço de falta de novidade |
| 4 | Cobertura por requisitos e verificação global | H02/L05/U02 não aprovados; parciais só com utilidade; conflito oracle explicitado |
| 5 | Operandos/cálculos determinísticos | T04 preserva 21.120, 21.200 e 80; T05 diferença correta; locale validado |
| 6 | Experimentos de representação, pool e packing | C01 acompanha os dois nomes até o contexto; Complete Evidence Recall por estágio, com custo reportado |
| 7 | Resumo por fatos e observabilidade de lotes | Cobertura mede lotes concluídos; requisitos globais atendidos; contradições preservadas |

Cada intervenção precisa de comparação isolada com a condição atual e dos controles negativos. Depois, executar a suíte completa congelada e um conjunto novo separado por família documental. Como estes 80 casos já orientaram a investigação, melhorá-los é evidência de correção nos casos conhecidos, não validação de generalização.

## Rastreabilidade

- [Execução das 80 perguntas](benchmark_cumbuco_phi4_reexecucao_2026-10-03.md).
- [Investigação controlada anterior](investigacao_cumbuco_phi4_2026-10-03.md).
- Resultados brutos: `benchmark/results/runs/real_80_cumbuco_phi4_params_2026-10-03/run.json`.
- Casos detalhados: `traces/REAL-<ID>.json.gz` dentro desse diretório; comparar `diagnostics.query_plan`, `diagnostics.state`, `diagnostics.hops`, `diagnostics.context_selection`, `diagnostics.verification` e `provider_calls`.
- Escopo: comparar os `document_ids` do plano com os documentos de `benchmark/datasets/real/evidence.json`, usando o `candidate_catalog` do mesmo índice; foram considerados 68 casos respondíveis com plano válido, incluindo erros posteriores ao planejamento.
- Multihop: usar `diagnostics.state.current_hop`, não o tamanho de `diagnostics.hops`, pois esta lista tem uma entrada por query/partição.
- Nenhum código de produção, documento, índice ou resultado original foi alterado nesta auditoria.
