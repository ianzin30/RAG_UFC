# Simplificação do retrieval: diagnóstico e próxima comparação

15/10/2026. Análise do código e dos artefatos de `agent_interface_qwen36_spark_2026-10-15/run_01`. Não houve inferência, busca nova, promoção à aplicação ou alteração de configuração. O monitor não foi reativado.

## Conclusão

O agente controla a busca, mas não controla diretamente sua leitura nem a composição final. O acervo encontrado cresce; a janela apresentada pode perder evidências. Esse desacoplamento explica por que uma busca útil pode não melhorar o resultado. A quantidade de etapas, isoladamente, não demonstra limitação do modelo.

Há três responsabilidades distintas: encontrar, escolher o que mostrar e decidir continuar. Simplificar significa deixar cada responsabilidade verificável e remover trabalho sem utilidade demonstrada. Eliminar validação, proveniência ou registros reduziria a capacidade de entender as falhas.

O ganho documental líquido sobre A permanece de uma pergunta na coleção. A redução de erros em C/D é real, mas não justifica o custo do ciclo como um todo. O ganho histórico do reranker no top-5 não é uma ablação atual do contexto final. Tampouco se pode atribuir as falsas suficiências apenas à interface: observações incompletas, decisões do modelo e o controlador interagem.

## Auditoria nova: os quatro conjuntos cabem

Foi reutilizado `benchmark.selection.diagnostic.minimum_parent_cover`, que minimiza a soma dos tokens dos parents inteiros sob as restrições de cobertura de `evidence_v2`. O diagnóstico usa as posições documentais do gabarito exclusivamente offline. Não é um seletor utilizável em produção.

| D / collection | Menor soma de tokens BGE | Parents | Posições dos parents na ordem global | Buscas executadas |
|---|---:|---:|---|---:|
| C01 | 24 | 2 | 59, 61 | 3 |
| C02 | 285 | 3 | 32, 33, 67 | 4 |
| C08 | 1.867 | 2 | 1, 5 | 3 |
| L05 | 664 | 1 | 4 | 2 |

São tokens dos textos documentais segundo a contagem congelada, sem acrescentar cabeçalhos de apresentação. Em C01, os dois parents existentes têm 12 tokens cada: são os trechos de função/nome nos documentos corretos. Não houve recorte novo. A identidade documental é parte da regra congelada; esses números não pretendem medir toda a informação necessária para gerar uma resposta ou navegar em um documento sem sua proveniência.

Cada combinação foi reavaliada por `evidence_v2`. Também foram reproduzidos ordem, seleção, tokens e avaliação dos candidatos/contextos das 140 execuções de D. Os arquivos da rodada permaneceram com hashes idênticos.

| Classificação dos pools finais de D | collection | oracle_scope |
|---|---:|---:|
| Contexto completo | 52 | 58 |
| Candidatos completos e combinação viável, mas contexto incompleto | 4 | 2 |
| Cobertura completa não comprovada nos candidatos | 14 | 10 |
| Candidatos completos, mas conjunto mínimo acima de 3.000 | 0 | 0 |

Os dois casos viáveis perdidos em `oracle_scope` são C01 e C02. As colunas repetem as mesmas 70 perguntas; não são 140 perguntas distintas.

A auditoria exclui impossibilidade de orçamento para os quatro casos da coleção. Não distingue causalmente o escore do reranker, a representação child/parent e a política gulosa de encaixe. `token_budget` no trace significa que o parent não coube **depois das escolhas anteriores**, não que nenhuma seleção completa coubesse.

Com estes pools e este avaliador, uma seleção ideal informada pelo gabarito alcançaria 56/70 na coleção. Isso é um teto diagnóstico para replay dos pools finais, não uma previsão de desempenho de uma política real. Os outros 14 casos não podem ser resolvidos apenas rearranjando esses mesmos candidatos segundo o avaliador; pendências de alinhamento continuam separadas. Não foi calculado um orçamento mínimo para evidências ausentes do pool.

Artefatos: [auditoria JSON](analises/viabilidade_interface_D_2026-10-15.json) e [script reproduzível](analises/auditar_viabilidade_interface.py). Execute a partir da raiz com um caminho de saída novo:

```sh
.venv/bin/python docs/analises/auditar_viabilidade_interface.py \
  --output /tmp/viabilidade_interface_D_reproducao.json
```

## Como distinguir as cinco classes

As classes podem coexistir. A tabela é um diagnóstico por etapa, não uma tentativa de atribuir uma causa única a cada pergunta.

| Classe | Evidência observável | Limite da conclusão |
|---|---|---|
| Consulta inadequada ou encerramento cedo | Texto/escopo das consultas, lacunas no contexto no momento da parada, orçamento restante, ação de encerramento | Contexto incompleto não prova que outra consulta funcionaria. Atribuição causal exige intervenção controlada na consulta/parada; por enquanto registrar hipótese e divergência do avaliador. |
| Evidência não recuperada | Cobertura não comprovada no pool acumulado de children e, separadamente, de parents expandidos | Separar falta de recuperação de alinhamento pendente. Um parent pode introduzir evidência fora do child que o recuperou. |
| Recuperada, mas não mostrada/selecionada | Evidência nos parents; avaliação dos textos exatos apresentados ao agente; avaliação do contexto final | Ver um `parent_id` ou uma amostra de seu child não significa ter visto a evidência. Mostrar ao agente e entregar no contexto são medidas diferentes. |
| Evidência não cabe | Candidatos completos e mínimo comprovado de parents inteiros acima de 3.000 | Não basta um descarte `token_budget`. Solver sem solução comprovada significa pendência diagnóstica. |
| Erro operacional | Ação solicitada/efetiva, incidente, recuperação, decisão consumida e contexto preservado | Erro de protocolo não é erro factual. Limite de decisões após ações válidas não é falha de transporte. |

Registrar também julgamento de suficiência: declaração do agente versus cobertura do contexto exato na parada. Uma declaração falsa pode coexistir com falha de seleção. O avaliador offline não deve retornar suas anotações ao agente.

Para cada decisão, a linha de auditoria deve conter: consulta e escopo; candidatos adicionados; evidências verificadas no pool, no texto mostrado e no contexto; parents que entraram/saíram; tokens usados; descarte por posição/encaixe; ação; orçamento restante; incidente; tempo e origem física/histórica/cache. Informações de avaliação devem ficar em um artefato separado das entradas do controlador.

## Próxima comparação controlada: somente a ordenação entre buscas

**Pergunta experimental:** o reranking global acrescenta qualidade suficiente à seleção para justificar seu custo, quando o reranking local é mantido?

**Hipótese:** alternar os resultados locais de consultas complementares pode preservar evidências úteis que recebem escore baixo contra a pergunta original. É uma hipótese; alternância também pode dar espaço a consultas ruins e consumir orçamento com parents grandes.

| Elemento | Controle G | Tratamento L |
|---|---|---|
| Busca inicial e buscas complementares | Trajetórias salvas de D | Exatamente as mesmas no replay |
| Reranking local | Preservado | Preservado |
| Ordem de seleção | União reranqueada contra consulta original, como em D | Alternância determinística das listas locais |
| Parents, deduplicação, encaixe | Parents inteiros, seleção gulosa, 3.000 tokens BGE | Iguais |
| Agente, feedback, instruções e limites | Congelados | Iguais; não executados novamente no replay |

Definição de L, fixada antes de medir: em cada busca, converter os children locais em uma lista de parents pela primeira ocorrência; percorrer Q0, Q1, Q2, Q3 nessa ordem, tomando um parent ainda não emitido de cada lista por volta; remover duplicatas; aplicar o mesmo `pack_order`. Lista vazia é ignorada. Parent que não cabe é descartado e a seleção continua, como hoje. Não comparar numericamente escores locais de consultas diferentes. Não criar reservas por documento, quotas por categoria, preferências por entidades ou truncamento.

A função `round_robin` já existe em `EvidenceSelection.py`; isso reduz a necessidade de inventar outra política. Sua existência e experimentos antigos não substituem esta comparação sobre as trajetórias atuais. Não aplicar o shortlist de 32 parents nem MMR nesta rodada.

### Etapa 1 — replay diagnóstico, ainda não executado

1. Reproduzir G antes de medir L: mesmos IDs, ordem, tokens, avaliações e hashes de entrada. A auditoria acima já reproduziu o estado final; o replay deverá reproduzir também todos os estados intermediários.
2. Aplicar G e L em cada pool acumulado após busca bem-sucedida. Erros sem busca mantêm o estado. A primeira busca deve ser idêntica entre políticas.
3. Manter consultas, número de buscas e paradas históricos como dados fixos. Não reaproveitar decisões históricas como se tivessem sido tomadas sobre a observação alternativa.
4. Medir todas as 70 perguntas da coleção; repetir separadamente em `oracle_scope`. C01/C02/C08/L05 são diagnósticos, não o conjunto de otimização.
5. Reportar ganhos e regressões pareados por pergunta e evidência, completude final, cobertura parcial, cobertura intermediária e evidências que entraram/saíram. Preservar `evidence_v2` e `literal_v1`, sem corrigir regras para favorecer uma política.

Em D, 55/70 perguntas da coleção fizeram apenas a busca inicial; uma política que só muda a combinação entre buscas deve deixá-las idênticas no replay. Apenas 15 tiveram buscas complementares. Isso limita o alcance desta intervenção e oferece uma verificação de implementação.

Não medir novas falsas suficiências ou novos erros do agente no replay: as decisões não foram geradas novamente. Pode-se mostrar a incompatibilidade entre uma declaração histórica e um contexto alternativo, identificada como contrafactual, sem apresentá-la como desempenho observado do agente L.

### Critério de passagem proposto

Tratar esta rodada como investigação conservadora: levar L ao ciclo completo somente se preservar pelo menos as 52 perguntas completas de G na coleção, não perder evidências já cobertas por pergunta e não apresentar regressão no controle documental. Ganhos devem ser listados, não escondidos no saldo. Esse critério prioriza qualidade e pode rejeitar uma alternativa mais barata com perdas; não é teste de equivalência estatística nem promoção automática.

Não escolher várias políticas e parâmetros com base nos quatro casos. Se L falhar, registrar o resultado e formular a próxima hipótese em outro protocolo. Se passar, o replay habilita uma comparação do ciclo completo; não comprova o resultado dela.

### Etapa 2 — ciclo completo, condicionado à análise do replay

Executar G versus L com as mesmas 70 perguntas, configuração congelada e limites. Depois que a observação divergir, obter decisões reais do modelo para cada condição. Reutilizar somente requisições integralmente idênticas e assinadas. Avaliar cobertura final, ganhos/perdas, buscas, decisões, falsas suficiências, incidentes e custos reais. A continuará sendo uma referência histórica de benefício líquido sobre a busca original; não é um terceiro fator experimental.

Amostras adicionais precisam seguir uma regra definida: manter prioridade da última busca e os mesmos limites de seis children/dois por documento. Onde hoje há fallback pela ordem global, usar a ordem da política em teste e registrar essa consequência. No ciclo completo, a estimativa será do efeito da política de ordenação sobre seleção **e observação**, com suas decisões subsequentes; não do reranker isolado de todo o restante.

Se houver empate de qualidade com custo menor, a conclusão possível é eficiência neste conjunto. Não alegar generalização ou prova de equivalência a partir das mesmas perguntas já examinadas.

## Custo e reprodutibilidade

Os 581,47 segundos de reranking global pertencem ao trabalho físico novo conjunto de C/D. Não são automaticamente economia de D, nem estimativa de aceleração total. No replay, relatar tempo de CPU do replay e operações que a política exigiria/dispensaria; a redução de duração precisa ser medida no ciclo completo, porque as consultas podem mudar.

O código também reavalia chunks antigos contra a mesma consulta original. Há uma otimização independente: cache do escore global por consulta exata, texto do chunk, identidade/revisão do reranker, tokenizer e parâmetros de processamento. Na busca inicial, escores locais só são reutilizáveis quando a entrada é realmente idêntica. Validar ordenação e contexto sob possíveis diferenças numéricas de batching. Essa otimização preserva a intenção da política G e não resolve por si só as perdas de seleção. Não introduzi-la silenciosamente só em um braço da comparação; medi-la em experimento de eficiência separado.

Salvar manifesto com hashes do código real (o checkout contém mudanças ainda não commitadas), corpus, índice, perguntas, histórico, regras, modelos/tokenizers, prompts, schemas, política, desempates e todos os limites. Registrar versões de runtime/servidor e limitações de identificação dos pesos. Seed 42 e temperatura zero são controles; replay de respostas salvas e repetição de inferência são garantias diferentes.

Retomada exige assinatura idêntica. Uma chamada marcada como iniciada sem resultado conhecido bloqueia repetição automática. Salvar início/fim e resultado atomicamente. Distinguir custo físico novo, demanda lógica por condição, reaproveitamento entre condições e custo histórico. Separar o tempo de recuperação densa/esparsa, reranking local, global, seleção, agente, avaliação e persistência. Não somar fases sobrepostas como se fossem tempo total.

## O que investigar depois, conforme o resultado

Se os candidatos continuarem incompletos, investigar consulta/parada e recuperação. Se a evidência estiver nos candidatos mas fora das observações, testar leitura sob demanda em experimento próprio. Se a combinação não couber em outros pools, testar granularidade ou orçamento separadamente. Se houver contexto incompleto e encerramento como suficiente, testar julgamento de parada sem misturá-lo à seleção.

Memória externa com proveniência pode manter o acervo recuperado enquanto a janela muda, mas fixar permanentemente tudo que já entrou no contexto pode reter ruído. Verificador adicional e seleção semântica pelo LLM também acrescentam custo e novas falhas. Nenhuma dessas mudanças faz parte da próxima comparação.
