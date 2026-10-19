# Perguntas reais — versão 1.0.0

Conjunto de **80 questões com gabarito**, elaborado em 01/10/2026 a partir dos
documentos textuais de `uploaded_files`. Nenhuma questão deste conjunto foi
executada contra o RAG nesta tarefa. A autoria e a conferência textual foram
feitas pelo assistente; a revisão semântica independente ainda está pendente.

## Distribuição definida antes da avaliação

| Categoria principal | Quantidade | O que avalia |
| --- | ---: | --- |
| Factual em documento único | 10 | Nomes, datas, valores e distinção entre proposta e decisão |
| Localização de entidades | 8 | Pessoas, funções e entidades técnicas sem confundir papéis |
| Cruzamento de documentos | 10 | Comparações, mudanças temporais e agregação entre fontes |
| Multi-hop | 10 | Identificar uma entidade por uma pista e consultar outro fato ligado a ela |
| Listas e agregações | 8 | Completude, papéis, contagens e valores associados corretamente |
| Resumos | 6 | Cobertura dos pontos essenciais e preservação de modalidade e temporalidade |
| Tabelas | 8 | Cabeçalhos, células vazias, aritmética e inconsistências documentais |
| Insuficiência de evidência/escopo | 10 | 9 abstenções e 1 pedido de esclarecimento |
| Continuação de conversa | 10 | Referências, troca de assunto e cálculos após contexto anterior |
| **Total** | **80** | **29 normais e 51 críticos** |

São 72 questões novas e 8 casos retomados ou reformulados das suítes reais
anteriores de retrieval/geração, identificados por `metadata.legacy_case`.
As quatro perguntas de geração já usadas nos experimentos estão entre essas oito.
O arquivo antigo `benchmark/questions.json`, voltado à coleção `google_drive_rag`,
continua separado; seus identificadores e caminhos não foram presumidos como
equivalentes aos desta coleção.

Foram anotados **77 trechos de 16 documentos**. O corpus de busca congelado contém
**88 arquivos Markdown**: os demais também importam como possíveis distratores.
Não se deve avaliar apenas sobre os 16 documentos com respostas. Há atas de
2020–2026, os planos AFO/RACK/SAAR e uma extração textual mínima de imagem.

As 8 questões tabulares usam tabelas reais extraídas dos PDFs. Elas **não validam
o caminho de ingestão de planilhas XLSX**. Não foi criado um caso de planilha real
sem um arquivo correspondente. A questão sobre `neymar.jpg` avalia o limite do
conteúdo textual disponível; nenhuma capacidade visual é pressuposta.

## Arquivos

- `questions.json`: perguntas, respostas esperadas e rubricas, no formato aceito
  pelo loader `benchmark.questions.load_questions`.
- `gabarito.md`: leitura humana das mesmas perguntas e respostas.
- `evidence.json`: catálogo dos trechos de suporte, com arquivo e localização
  textual. Os títulos descritivos de localização não são necessariamente headings
  originais da ata. As citações são literais, admitindo só normalização de espaços.
- `manifest.json`: hashes SHA-256 dos 88 documentos e das duas anotações JSON.
- `validate.py`: conferência local de anotações, sem retrieval, modelo ou rede.

Os arquivos do corpus permanecem em `data/`, ignorados pelo Git. Este conjunto
contém pequenos excertos, nomes e valores retirados desses documentos para
permitir auditoria dos gabaritos; não contém os documentos integrais.

## Como interpretar o gabarito

`expected_answer` é uma resposta de referência, não uma exigência de reprodução
literal. `required_facts` define o conteúdo necessário; `critical_errors` explicita
confusões particularmente importantes. Aceitar paráfrases, variações de acento nos
nomes, abreviações inequívocas e representações equivalentes de datas e moeda.
Não aceitar inversão de papel, projeto, data, sinal ou unidade. Valores monetários
exigem precisão de centavos; cálculos anotados usam decimal exato.

`evidence_ids` lista unidades de suporte necessárias. Uma unidade é um trecho
documental de referência, não um chunk de uma versão particular do índice. Isso
permite mudar o chunking sem trocar o gabarito. Evidências equivalentes em outras
passagens podem ser aceitas após revisão, registrando a alternativa e versionando
a anotação. Não exigir o mesmo texto superficial se a relação estiver sustentada.

Nos casos sem resposta, `evidence_ids` fica vazio. `context_evidence_ids` aponta
passagens próximas que ajudam a explicar a insuficiência, **sem fingir que são
evidência do dado ausente**. `absence_scope` limita a conclusão ao documento ou
corpus textual consultado. Ausência de informação não prova inexistência do fato
no mundo. REAL-U10 pede esclarecimento de escopo, e não uma abstenção factual.

Nos follow-ups, usar exatamente `metadata.history` como prefixo independente de
cada questão. Não usar uma resposta gerada por um caso anterior como histórico,
pois isso mudaria o teste e propagaria erros. O histórico não é fonte documental
para certificação de uma claim: conferir também os trechos indicados.

## Multi-hop e completude da evidência

As dez questões têm uma cadeia anotada em `reasoning_steps`:

- H01–H03: ligação entre característica técnica, projeto e coordenador em seções
  distintas de um mesmo plano.
- H04–H10: ligação dependente entre dois documentos; H08 exige também resolver
  quem é o chefe titular e quem apenas presidia a reunião em seu exercício.

Não confundir multi-hop lógico com número de chamadas: um único retrieval pode
encontrar todas as evidências. O gabarito exige a cadeia completa, não um número
mínimo de rounds de execução. Uma comparação de dois nomes conhecidos já na
pergunta pertence à categoria cross-document, não é contada como multi-hop aqui.

Para H01, citar apenas o nome de Fernando não basta: é necessário sustentar tanto
OAuth → AFO quanto AFO → Fernando. O mesmo princípio vale para as demais cadeias.

## Protocolo para uma avaliação futura

1. Conferir os hashes e registrar versão do código, configuração, corpus, provider,
   modelo lógico, modelo efetivo e parâmetros antes de gerar respostas.
2. Executar cada pergunta isoladamente, com seu histórico fixo quando aplicável.
   Nunca enviar `expected_answer`, rubricas ou evidências de referência aos agentes.
3. Separar recuperação de evidências, correção da resposta, completude da cadeia,
   suporte de citações, abstenção/esclarecimento e latência. Uma resposta pode ter
   o nome certo e a citação incompleta; isso precisa aparecer nos resultados.
4. Para questões respondíveis, registrar fatos corretos/obrigatórios e acerto
   completo. Acerto completo exige todos os fatos, sem erro crítico ou informação
   factual material sem suporte. Resumos admitem redações distintas, mantendo
   cobertura. Não transformar presença de palavras em prova de correção semântica.
5. Calcular Evidence Recall@K por unidades anotadas recuperadas; Complete Evidence
   Recall@K só vale 1 quando todas as unidades necessárias estão presentes. Para
   ausência de resposta, essas métricas não se aplicam, em vez de receberem 1 por
   haver um conjunto esperado vazio. Recall de documento é uma métrica separada.
6. Em citações, avaliar se os trechos citados sustentam as afirmações e cobrem os
   fatos obrigatórios. A existência de `[E1]` não prova suporte. Em abstenções,
   avaliar o comportamento e a ausência de um dado inventado; não exigir citação
   positiva para algo que o corpus não informa.
7. Publicar resultados por categoria e por dificuldade, com numeradores e
   denominadores, além de uma média entre categorias. Não deixar categorias maiores
   esconderem falhas nas menores. Grader LLM, se utilizado, é complementar.

O runner configurável existente aceita este JSON e já transmite `metadata.history`.
Porém, **seus scores atuais não implementam automaticamente todas as rubricas deste
pacote**, nem o matching das 77 unidades do catálogo. O consumo desse catálogo para
métricas de evidência e das regras de abstenção/clarificação precisa ser ligado ao
avaliador antes de declarar um resultado completo sob este protocolo. Os runners
curtos `real_generation` e `real_corpus` continuam com seus casos antigos; este
trabalho amplia a base anotada, sem alterar silenciosamente seus testes padrão.

## Limites científicos e prevenção de contaminação

Esta é uma amostra intencional, estratificada por capacidade, com forte presença
de casos difíceis. Não é uma amostra aleatória de consultas de usuários, e sua
taxa de acerto não estima diretamente acurácia em produção. A dificuldade é uma
classificação de projeto, ainda não uma medida empírica do desempenho do modelo.

`family` identifica questões relacionadas. Há fatos reutilizados em perguntas
factuais, multi-hop e conversacionais para isolar a dificuldade de composição;
portanto, 80 perguntas não equivalem a 80 fatos independentes. As famílias também
podem compartilhar documentos. Não criar treino/teste aleatoriamente por linha.

O conjunto está **não executado, mas não selado como teste cego**. Os oito casos
anteriores já foram expostos, assim como os fatos de algumas questões novas. Para
medir generalização após ajustes, separar famílias e documentos relacionados antes
de desenvolver e reservar um teste independente, preferencialmente com novos
documentos. Não ajustar o sistema nas 80 perguntas e depois chamar o resultado de
holdout. Revisão humana independente deve ocorrer antes de congelar um teste final.

A inconsistência de horas do RACK foi mantida deliberadamente: as parcelas somam
21.120, enquanto a tabela imprime 21.200. O caso exige reconhecer a diferença,
sem escolher arbitrariamente qual parte do documento corrigir. A folha financeira
também contém formatação numérica irregular; só valores com leitura inequívoca
foram usados nos cálculos anotados.

## Conferência sem executar benchmark

Da raiz do repositório:

```sh
uv run --no-sync python benchmark/datasets/real/validate.py
```

Esse comando valida contagens, IDs, referências, cadeias, históricos, cálculos,
unicidade/localização literal das citações e hashes. Não importa `RAGService`, não
carrega modelos, não consulta a VM e não gera respostas. Ele verifica integridade
textual e estrutural; não substitui a revisão semântica independente.
