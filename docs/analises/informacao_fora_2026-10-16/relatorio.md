# Investigação da informação que ficou de fora e das duas perguntas que melhoraram

16/10/2026. Dados salvos das 70 perguntas originais, examinando três casos da coleção. Nenhuma busca, chamada ao modelo ou classificação nova. Nenhuma regra de seleção foi alterada.

**Resultado:** a ordem dos blocos determina quem ocupa o espaço primeiro. A alternância ajudou quando trouxe a informação necessária para o começo da fila. Em C08, um bloco grande de outra data entrou cedo nos dois métodos, impedindo que as duas informações necessárias fossem reunidas.

Aqui, “completa” significa conter todas as evidências exigidas pelo avaliador congelado, `evidence_v2`. Não foram geradas respostas finais. “Tokens” são as unidades usadas para medir o tamanho do texto; o limite continua em 3.000 tokens BGE, com blocos inteiros.

| Pergunta | O que pede | Juntar e reordenar | Alternar entre buscas | Motivo observado |
|---|---|---|---|---|
| C08 | Chefia nas aberturas de duas atas, setembro/2020 e junho/2024 | Só junho/2024 | Só setembro/2020 | Um bloco de julho/2024 ocupa espaço antes de reunir as duas aberturas. |
| C02 | Comparar os objetivos de AFO, RACK e SAAR | Nenhum dos três objetivos anotados no contexto final | Os três objetivos | Os blocos necessários passam das posições 32/33/67 para 7/4/6. |
| L05 | Comissão completa, com funções, aprovada em 21/02/2025 | Bloco da comissão fora do contexto | Bloco da comissão dentro | O bloco passa da posição 4 para a 2, antes de o espaço ser ocupado. |

## C08 — Por que uma das duas informações fica de fora

A pergunta exige a abertura da ata de **04/09/2020** e a da ata de **21/06/2024**. Os blocos necessários têm 979 e 888 tokens. Juntos custam **1.867**, portanto cabem no limite de 3.000.

Um terceiro bloco, de uma ata de **19/07/2024**, tem **1.339 tokens**. Ele menciona Fernando Trinta e trata de outros assuntos, incluindo planejamento, extensão e comissões de progressão. Não cobre as passagens de abertura das duas datas pedidas. Ele pode parecer relacionado à pergunta pelo nome e pelo conteúdo institucional, mas essa proximidade não substitui as evidências exigidas. A razão interna do escore do reranker não foi examinada; a interferência desse bloco no encaixe foi medida.

### Como o método atual preenche o espaço

| Ordem | Bloco | Tamanho | Espaço antes | Decisão |
|---:|---|---:|---:|---|
| 1 | Abertura de junho/2024 | 888 | 3.000 | Entra |
| 2 | Outro trecho, de julho/2024 | 1.339 | 2.112 | Entra |
| 3 | Trecho de agosto/2022 | 239 | 773 | Entra |
| 4 | Assinatura da ata de junho/2024 | 94 | 534 | Entra |
| 5 | Abertura de setembro/2020 | 979 | **440** | Não cabe |

### Como a alternância preenche o espaço

| Ordem | Bloco | Tamanho | Espaço antes | Decisão |
|---:|---|---:|---:|---|
| 1 | Outro trecho, de julho/2024 | 1.339 | 3.000 | Entra |
| 2 | Abertura de setembro/2020 | 979 | 1.661 | Entra |
| 3 | Abertura de junho/2024 | 888 | **682** | Não cabe |

As duas aberturas e o trecho de julho somam **3.206 tokens**. A alternância chega ao bloco de junho com um déficit de **206 tokens**. Depois ela ainda inclui outros blocos menores, inclusive assinaturas, mas não recupera a passagem de abertura que faltou.

**O que aconteceu ao longo das buscas:** setembro já estava no contexto inicial dos dois métodos. A primeira busca complementar não mudou essa cobertura. A segunda trouxe a abertura de junho para os candidatos. A partir daí, o método atual incluiu junho e retirou setembro; a alternância manteve setembro e não conseguiu incluir junho.

Assim, a expressão anterior “a alternativa perdeu junho” descreve a comparação dos contextos finais. Dentro da trajetória alternativa, junho **nunca esteve selecionado**. A perda temporal comprovada ocorreu no método atual, que já mostrava setembro e deixou de mostrá-lo.

### Verificação da causa no encaixe

Como diagnóstico, retiramos **somente o bloco de julho**, mantivemos a ordem dos demais candidatos e executamos novamente o mesmo encaixe. **Os dois métodos passaram a incluir as duas evidências**, sem aumentar o orçamento. Os contextos resultantes ficaram em 3.000 e 2.997 tokens.

Foram testadas, individualmente, as exclusões de todos os blocos selecionados que não cobrem caracteres das exigências anotadas: 12 no método atual e oito na alternância. Nesse conjunto de verificações, o bloco de julho foi a única exclusão individual que completou C08 em cada método.

Isso confirma sua interferência neste conjunto fixo de candidatos. A escolha dos blocos para esse diagnóstico usa as anotações offline; **não foi criada uma regra para excluir esse documento nem uma nova política de seleção**.

## C02 — Por que a comparação entre os três projetos passou

A busca original já tinha os objetivos anotados de AFO e SAAR nos candidatos. A primeira busca complementar, sobre RACK, completou a cobertura dos **três objetivos nos candidatos**. Portanto, depois dessa busca já existia informação suficiente para montar um contexto completo.

As buscas seguintes sobre AFO e SAAR não acrescentaram novas evidências exigidas pelo avaliador ao conjunto acumulado. Na alternância, porém, trouxeram essas evidências para perto do início das listas locais.

| Objetivo | Tamanho | Posição na fila atual | Espaço disponível nessa posição | Posição na alternância | Espaço disponível nessa posição |
|---|---:|---:|---:|---:|---:|
| AFO | 62 | 32 | 17 | 7 | 2.298 |
| SAAR | 97 | 33 | 17 | 4 | 2.679 |
| RACK | 126 | 67 | 0 | 6 | 2.424 |

Os três blocos custam apenas **285 tokens**. No método atual, eles chegam tarde: outros blocos já ocuparam o orçamento. Na alternância, os três entram entre as primeiras sete posições.

| Estado após a busca | Evidências nos candidatos | No contexto atual | No contexto alternativo |
|---|---|---|---|
| Original | AFO e SAAR | AFO | AFO |
| Complementar sobre RACK | AFO, RACK e SAAR | Nenhuma das três anotadas | RACK |
| Complementar sobre AFO | AFO, RACK e SAAR | Nenhuma das três anotadas | AFO e RACK |
| Complementar sobre SAAR | AFO, RACK e SAAR | Nenhuma das três anotadas | AFO, RACK e SAAR |

O contexto atual inclui textos relacionados, como escopo, introdução, metodologia e etapas de execução. “Nenhuma das três anotadas” não significa que todo esse conteúdo seja inútil ou semanticamente irrelevante; significa que as passagens exigidas pelo avaliador ficaram de fora. Não foi feita uma nova avaliação de equivalência semântica de todas as passagens alternativas.

**Por que passou:** a alternância preservou a prioridade local dos blocos de objetivo e conseguiu reunir os três. O ganho foi de composição do contexto sobre as buscas salvas. Não demonstra como o agente teria pesquisado se já estivesse observando o contexto alternativo.

## L05 — Por que a comissão completa passou

O bloco com a comissão aprovada em **21/02/2025** tem **664 tokens**. Ele já estava nos candidatos da busca original, em quarto lugar entre os parents.

No método atual, os primeiros blocos são de atas de março/2025, junho/2022 e janeiro/2025. Eles ocupam **710 + 719 + 1.361 = 2.790 tokens**. Quando chega o bloco correto, restam somente **210**: faltam 454 tokens para incluí-lo.

A busca complementar restrita ao documento correto põe esse mesmo bloco em primeiro lugar na lista local. Ele se torna o **segundo** bloco visitado na alternância:

| Método | O que entra antes da comissão | Espaço antes da comissão | Resultado |
|---|---|---:|---|
| Atual | Três blocos, total de 2.790 tokens | 210 | Comissão não cabe |
| Alternância | Um bloco de 710 tokens | 2.290 | Comissão entra, usando 664 |

Mais adiante, o bloco de janeiro/2025, de 1.361 tokens, é descartado pela alternância por falta de espaço. O contexto conserva a comissão necessária.

**Por que passou:** o resultado relevante chegou antes dos blocos que impediam seu encaixe. A evidência não foi descoberta pela primeira vez na busca complementar; já estava encontrada, mas não estava sendo entregue no contexto.

## O que esta investigação permite concluir

1. **A alternância pode aproveitar melhor uma busca direcionada.** Isso explica C02 e L05.
2. **A alternância não verifica se o conjunto final responde a todas as partes do pedido.** Em C08, trazer uma evidência para o início não garante espaço para a outra.
3. **A seleção atual também pode retirar uma evidência já mostrada.** Isso ocorreu em C08 e com o objetivo de AFO em C02.
4. **A falta de espaço nestes casos depende do que foi escolhido antes.** Não é impossibilidade de acomodar as evidências necessárias nos 3.000 tokens.

A próxima hipótese deve tratar a contribuição conjunta dos blocos e o custo de incluí-los. Esta investigação não identifica uma solução genérica pronta e não justifica aumentar o orçamento ou trocar o modelo. A alternância continua com recomendação de revisão, conforme o critério previamente definido.

## Conferência e reprodução

Foram reproduzidos **nove estados documentais e 18 seleções**, cobrindo os três casos. Os textos foram reconstruídos do índice congelado e as avaliações foram conferidas nas posições originais do corpus. Os resultados finais e todos os traces auditados coincidiram com os arquivos salvos.

Os hashes das entradas foram conferidos antes e depois. Os resultados históricos foram preservados. Não houve chamadas novas ao modelo, retriever ou reranker. O diagnóstico de exclusão de blocos ficou separado dos resultados do experimento original.

- [Dados, ordens completas e verificações](investigation.json).
- [Script da investigação](../investigar_informacao_fora.py).
- [Comparação original](../../../benchmark/results/rounds/global_order_replay_2026-10-15/run_02/report.md).

Execute a partir da raiz, escolhendo um diretório de saída novo:

```sh
.venv/bin/python docs/analises/investigar_informacao_fora.py \
  --output-dir /tmp/investigacao_informacao_fora_2026-10-16
```
