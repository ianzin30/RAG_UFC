# Por que faltou evidência? Análise das 14 perguntas

**Há problemas em mais de uma etapa. Os 14 casos são incompletos pela métrica congelada; não são 14 falhas semânticas comprovadas.** Esta análise usa somente o índice e os registros existentes, sem modelo, buscas ou rerankings novos.

## O que foi comprovado

- Todas as passagens anotadas faltantes existem nas representações de blocos do índice. Não se constatou perda total desses trechos na ingestão. Isso não significa que sejam fáceis de recuperar.
- Em 13 casos, as consultas executadas não acumularam todas as passagens anotadas. A ausência já aparece no conjunto anterior ao reranking local. Os 25 conjuntos locais conferidos conservaram os mesmos candidatos após esse reranking.
- Em C02, os três objetivos foram encontrados, mas o de RACK ficou fora da seleção principal. O agente o recebeu em uma amostra extra. A combinação necessária tem 285 tokens e cabia no limite.
- Oito casos pararam após a busca inicial. Onze escolheram finish_sufficient sem todas as passagens anotadas no contexto. São contagens sobrepostas, não uma divisão de culpa.
- Em C07 e H03 há uma contradição direta: a justificativa reconhece a informação faltante e a ação declara suficiência.
- Há fontes alternativas relevantes em E02, C01, H04, Q02 e Q10. Não recalculamos completude com outro critério. S04 e H02 também precisam de cautela semântica sobre inferência da decisão e ligação entre pessoa, projeto e período.

## Um problema geral de representação

Os blocos de coordenação têm 10–12 tokens e contêm apenas o rótulo e o nome, sem o nome do projeto no próprio texto. Datas e seus rótulos ficaram separados em quatro blocos de 8–11 tokens por projeto. O dashboard SAAR está dividido em dois blocos. Essa fragmentação é observável; seu efeito causal precisa de comparação própria.

Existem consultas históricas já executadas que recuperaram cada uma das 11 âncoras distintas faltantes. Em C01 há consultas com o mesmo texto e filtro no documento correto que recuperaram os coordenadores. Isso prova recuperabilidade para essas entradas salvas, não que o agente escolheria esses filtros nem que uma regra de filtro resolveria todos os casos.

## Os 14 casos

| Caso | Buscas com a original | Encerramento | Diagnóstico |
|---|---:|---|---|
| E02 | 1 | finish_sufficient | Fontes alternativas |
| C01 | 3 | finish_sufficient | Consulta e fontes alternativas |
| C02 | 3 | finish_incomplete | Seleção comprovada |
| C07 | 1 | finish_sufficient | Encerramento contraditório |
| C09 | 1 | finish_sufficient | Interpretação da pergunta |
| H01 | 1 | finish_incomplete | Investigação interrompida |
| H02 | 3 | finish_sufficient | Ligação entre projeto e pessoa |
| H03 | 1 | finish_sufficient | Encerramento contraditório |
| H04 | 1 | finish_sufficient | Fontes alternativas |
| H05 | 3 | finish_incomplete | Consulta mistura duas etapas |
| S01 | 1 | finish_sufficient | Cobertura de vários itens |
| S04 | 1 | finish_sufficient | Continuação de trecho não recuperada |
| Q02 | 2 | finish_sufficient | Fontes alternativas e fragmentação |
| Q10 | 3 | finish_sufficient | Consulta e fontes alternativas |

### E02

Quem é o coordenador na instituição do projeto Rack Build Deployment Validation and Provisioning II?

O agente encerrou na busca inicial. A ata de novembro/2025 associa o projeto RACK II à coordenação de Paulo Rego; a métrica exige o campo do plano RACK.

Revisar equivalência da fonte alternativa antes de chamar isso de falha semântica. Não mudar a nota congelada.

Passagens anotadas faltantes: RACK_NAME.

Consultas executadas:
- Q0: Quem é o coordenador na instituição do projeto Rack Build Deployment Validation and Provisioning II? [coleção inteira]

### C01

Compare os coordenadores dos projetos AFO e RACK.

As buscas por coordenadores foram abertas, sem filtro de documento. Os dois campos anotados não vieram; atas no contexto ligam AFO a Fernando Trinta e RACK a Paulo Rego.

Buscas históricas com o mesmo texto e filtro do projeto recuperaram os campos. Há também suporte alternativo nas atas a auditar.

Passagens anotadas faltantes: AFO_NAME, RACK_NAME.

Consultas executadas:
- Q0: Compare os coordenadores dos projetos AFO e RACK. [coleção inteira]
- Q1: coordenador projeto AFO [coleção inteira]
- Q2: coordenador projeto RACK [coleção inteira]

### C02

Qual é a diferença de objeto entre AFO II, RACK II e SAAR II nos respectivos planos de trabalho?

Todos os objetivos foram recuperados. O de RACK ficou fora do contexto principal, embora aparecesse em amostra adicional mostrada ao agente.

O bloco RACK de 126 tokens chegou à posição 60, quando restavam 34 tokens. A combinação anotada requer 285 tokens. O agente não escolhe diretamente os blocos finais; não atribuir a perda somente à consulta ou somente ao reranker.

Passagens anotadas faltantes: RACK_OBJECTIVE.

Consultas executadas:
- Q0: Qual é a diferença de objeto entre AFO II, RACK II e SAAR II nos respectivos planos de trabalho? [coleção inteira]
- Q1: RACK II objetivo escopo plano de trabalho [coleção inteira]
- Q2: RACK II objetivo escopo plano de trabalho [filtro documental]

### C07

Como João Paulo do Vale Madeiro é identificado na chefia nas aberturas das atas de 13/07/2022 e 29/01/2024?

Após apenas a busca inicial, a justificativa afirma que falta a ata de 13/07/2022, mas a ação é finish_sufficient.

Erro de decisão observável independentemente da nota: a justificativa contradiz a ação. A ata e o trecho existem no índice.

Passagens anotadas faltantes: JULY22_CHAIR.

Consultas executadas:
- Q0: Como João Paulo do Vale Madeiro é identificado na chefia nas aberturas das atas de 13/07/2022 e 29/01/2024? [coleção inteira]

### C09

As extraordinárias de 13/07/2022 e 21/06/2024 ocorreram na mesma modalidade?

Encerrou após a busca inicial, tratando “Extraordinária” como modalidade. A comparação anotada é videoconferência versus reunião híbrida.

Não foram recuperadas as duas aberturas anotadas. Há pendência de alinhamento para JULY22_CHAIR; não tratá-la como ausência física comprovada.

Passagens anotadas faltantes: JULY22_CHAIR, JUNE24_CHAIR.

Consultas executadas:
- Q0: As extraordinárias de 13/07/2022 e 21/06/2024 ocorreram na mesma modalidade? [coleção inteira]

### H01

Qual é o nome do coordenador do projeto que prevê geração de token OAuth?

Reconheceu que faltava o nome do coordenador e encerrou incompleta sem fazer busca complementar.

Ainda havia três buscas disponíveis. O campo de AFO existe no índice e já foi recuperado por outras consultas salvas; isso não é uma execução contrafactual do agente.

Passagens anotadas faltantes: AFO_NAME.

Consultas executadas:
- Q0: Qual é o nome do coordenador do projeto que prevê geração de token OAuth? [coleção inteira]

### H02

Quem coordena o projeto cujo ciclo anterior automatizou a configuração de firmware via Redfish?

Fez duas buscas abertas, cada vez mais longas, ainda misturando o elo Redfish com o nome do coordenador. Encerrou suficiente sem o campo anotado.

A justificativa cita uma amostra para a coordenação; amostras não fazem parte do contexto final. Auditar a ligação e o período das outras atas antes de concluir suficiência semântica.

Passagens anotadas faltantes: RACK_NAME.

Consultas executadas:
- Q0: Quem coordena o projeto cujo ciclo anterior automatizou a configuração de firmware via Redfish? [coleção inteira]
- Q1: coordenador projeto Redfish firmware Redfish [coleção inteira]
- Q2: coordenador projeto Rack Build Deployment Validation and Provisioning Redfish [coleção inteira]

### H03

Quem é o coordenador do projeto que prevê expandir seu ETL para Unity, PowerScale e PowerFlex?

A justificativa diz explicitamente que falta o nome do coordenador de SAAR; mesmo assim a ação é finish_sufficient, sem busca adicional.

O nome está num bloco curto no índice. Outras consultas salvas o recuperam. A contradição entre justificativa e ação é comprovada.

Passagens anotadas faltantes: SAAR_NAME.

Consultas executadas:
- Q0: Quem é o coordenador do projeto que prevê expandir seu ETL para Unity, PowerScale e PowerFlex? [coleção inteira]

### H04

Qual função no PET o coordenador do AFO declarou ter assumido na ata de 19/08/2022, e para que pediu colaboração?

Encerrou na busca inicial. O contexto contém a declaração sobre o PET e outra ata que liga AFO a Fernando Trinta, mas não o campo AFO_NAME do plano.

Auditar a equivalência dessa ligação entre documentos; ausência da passagem anotada não prova ausência de toda evidência válida.

Passagens anotadas faltantes: AFO_NAME.

Consultas executadas:
- Q0: Qual função no PET o coordenador do AFO declarou ter assumido na ata de 19/08/2022, e para que pediu colaboração? [coleção inteira]

### H05

De qual classe para qual classe era a progressão do coordenador do RACK relatada em 19/08/2022, e quem apresentou o parecer?

Uma decisão inválida foi corrigida, consumindo uma das quatro decisões. Depois buscou progressão e coordenação juntas, inclusive dentro do plano RACK.

O trecho da progressão foi encontrado; o elo coordenador↔RACK não foi comprovado pela âncora. Não separar a identificação da pessoa da busca de sua progressão pode prejudicar a recuperação.

Passagens anotadas faltantes: RACK_NAME.

Consultas executadas:
- Q0: De qual classe para qual classe era a progressão do coordenador do RACK relatada em 19/08/2022, e quem apresentou o parecer? [coleção inteira]
- Q1: progressão funcional coordenador RACK 19/08/2022 [filtro documental]
- Q2: coordenador RACK progressão funcional classe [filtro documental]

### S01

Resuma as melhorias e novas funcionalidades previstas para o SAAR.

Encerrou suficiente na busca inicial, faltando DevOps e o dashboard completos segundo as anotações.

O índice contém ambos; o dashboard está dividido entre dois blocos. O caso mistura recuperação de itens distribuídos e julgamento de suficiência do resumo.

Passagens anotadas faltantes: SAAR_DEVOPS, SAAR_DASHBOARD.

Consultas executadas:
- Q0: Resuma as melhorias e novas funcionalidades previstas para o SAAR. [coleção inteira]

### S04

Resuma a preocupação com a carga didática do novo curso de Ciência de Dados e a decisão final sobre CK0211 na extraordinária de 13/07/2022.

Recuperou discussão e votos, mas não o parágrafo final anotado com a decisão. Encerrou suficiente na busca inicial.

O parágrafo de encerramento está em outro bloco de 155 tokens do mesmo documento. Discussão e votação podem sustentar parte da conclusão; equivalência semântica exige revisão.

Passagens anotadas faltantes: JULY22_DECISION.

Consultas executadas:
- Q0: Resuma a preocupação com a carga didática do novo curso de Ciência de Dados e a decisão final sobre CK0211 na extraordinária de 13/07/2022. [coleção inteira]

### Q02

E o SAAR tem o mesmo período previsto?

O agente buscou mais uma vez no SAAR e encerrou suficiente. A ata de novembro/2025 traz os períodos de AFO II e SAAR II, mas a métrica exige rótulos e datas dos planos.

Nos planos, início, rótulos e término ficaram em quatro blocos por projeto, de 8–11 tokens. A falha da âncora não prova erro nas datas alternativas.

Passagens anotadas faltantes: AFO_DATES, SAAR_DATES.

Consultas executadas:
- Q0: Qual é a duração prevista do AFO II? E o SAAR tem o mesmo período previsto? [coleção inteira]
- Q1: período vigência SAAR II 2026 2027 [filtro documental]

### Q10

Quem coordena esse último na instituição?

Fez busca aberta e depois filtrada no RACK; o campo anotado não veio. O contexto possui atas que associam RACK a Paulo Rego.

A busca usou o nome longo do projeto, enquanto consultas históricas mais focadas no coordenador recuperaram o campo. Revisar também a evidência alternativa e sua edição/período.

Passagens anotadas faltantes: RACK_NAME.

Consultas executadas:
- Q0: Vamos falar sobre o AFO. Agora mude para o RACK. Quem coordena esse último na instituição? [coleção inteira]
- Q1: coordenador projeto Rack Infrastructure Deployment Validation and Provisioning [coleção inteira]
- Q2: coordenador projeto Rack Infrastructure Deployment Validation and Provisioning [filtro documental]

## Como interpretar a responsabilidade

Para os 13 casos, comprovamos uma falha de cobertura da recuperação **com aquelas consultas e filtros**. Ainda não isolamos quanto veio da consulta, da representação dos trechos ou do ranking dos canais denso/esparso. O reranker local não excluiu candidatos nesses casos; não poderia recuperar um bloco que nunca entrou na união. Isso não é uma ablação nem prova que o reranker seja dispensável.

O agente contribuiu com paradas sem buscas complementares, consultas que misturam etapas e duas ações contraditórias à própria justificativa. Em parte dos casos, contudo, ele encontrou fontes alternativas plausíveis que a métrica não reconhece. Portanto, o número 11 não pode ser lido automaticamente como 11 decisões semanticamente erradas.

## Próxima investigação recomendada

Primeiro auditar a aceitação de evidências equivalentes com uma regra geral, mantendo evidence_v2 e literal_v1 históricos intactos. Se uma nova avaliação for criada, ela deve ser versionada e aplicada às 70 perguntas e aos dois braços, sem corrigir somente as reprovadas.

Depois separar testes de representação dos blocos e de decisão do agente, um fator por comparação. Os dados atuais justificam estudar blocos que preservem relações rótulo–valor e projeto–pessoa, além de encerramentos coerentes. Não justificam simplesmente desligar o reranker ou criar regras específicas para perguntas.

Arquivos: audit.json (índice, buscas e observações), supplement.json (consultas históricas já executadas), findings.json (interpretação explícita) e preservation.json. As notas e os históricos da rodada original permanecem inalterados.

Trechos alternativos já selecionados, preservados para revisão manual: alternative_sources.json.
