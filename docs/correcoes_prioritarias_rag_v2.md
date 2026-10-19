# Correções prioritárias RAG V2 — implementação e controles

Data: 03/10/2026. Estado: **núcleo implementado, validação generativa bloqueada; não promovido como melhoria de qualidade**.

## Limites preservados

FAISS, BGE-M3 dense/sparse, RRF, reranker, CrewAI, chunking e índice foram preservados. Não houve configuração administrativa do servidor, troca de modelo, reconstrução documental ou benchmark completo nesta entrega. Métodos públicos de `RAGService`, callbacks e semântica de `sources`/`cited_sources` continuam preservados. Alterações anteriores no worktree não foram descartadas; não houve commit ou push.

Controle histórico: `benchmark/results/runs/real_80_cumbuco_phi4_params_2026-10-03`. Não foi sobrescrito. Índice utilizado nos controles: `6c49f49797c1a5cb87118650cfeea80e7f3fc5410c48124bbff673371ab45a8b` (88 documentos). Resultados operacionais permanecem ignorados pelo Git.

## 1. Transporte e observabilidade

`UfcOllama` e `Providers` agora oferecem resultado interno de geração com texto, identidade, parâmetros enviados, uso reportado e término. Agentes continuam recebendo texto. O protocolo UFC é explícito:

- `openwebui_ollama`: envelope `params`, com `num_ctx`, `max_tokens` e temperatura.
- `openai_chat`: formato anterior, preservado para compatibilidade.

A configuração compartilhada seleciona `openwebui_ollama`; os controles usam o adapter de produção. O override histórico do runner permanece somente para reprodução. Ollama e vLLM mantêm seus formatos próprios. Os registros separam configurado, enviado e observado: contexto solicitado não se transforma em contexto efetivamente confirmado. Saída no teto e uso no limite solicitado geram sinais, sem concluir truncamento ou completude apenas por `stop`.

**Controle:** três prompts curtos retornaram exatamente `OK`. Foram enviados contexto 8.192 e limite atual do papel; o servidor reportou modelo `phi4:latest`, 20 tokens de entrada e 2 de saída. Latências aproximadas: 2,94 s, 0,32 s e 0,27 s. Isso confirma transporte curto, não a janela efetiva de 8.192. Mensagens não foram redesenhadas. Digest disponível registrado nos controles: `ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba`.

## 2. Pergunta, requisitos e escopo

`Planning.py` concentra o catálogo textual e resolução documental. `QuestionContract` mantém pergunta original imutável, resolução contextual, requisitos `R1…`, entidades/datas e origem das restrições. Referências curtas `D1…` são traduzidas para IDs existentes por código.

Aliases adicionais exigem ocorrência documental; datas de reunião provêm de cabeçalhos/trechos de reunião, não de qualquer assinatura. Escopo inferido pelo planner não vira automaticamente filtro rígido. Referências resolvidas restringem a busca; referências que exigem descoberta iniciam na coleção. Queries carregam requisitos e documentos próprios. Homônimos e qualificadores de coleção têm testes. O último tópico explícito do usuário resolve follow-ups; o histórico não vira evidência citável.

**Controle:** E03, F05, E02 e Q08 tiveram três repetições cada, sem erro estrutural. O resolver apontou respectivamente para a ata de 19/08/2022, a extraordinária de 13/07/2022, RACK e a ata de 30/01/2026. Em Q08, o planner manteve o pronome na pergunta; a referência contextual correta estava no contrato. Foi acrescentado posteriormente o vínculo canônico ao tópico do histórico, coberto localmente, ainda sem nova rodada generativa.

O arquivo desse controle conserva o resumo antigo `gate_passed=false` com revisão semântica pendente; não significa que as 12 chamadas falharam. O harness atual registra `null` quando não existe gate semântico automatizado.

**Limite:** resolução textual é conservadora, não um extrator semântico universal de datas/entidades. Restrições parciais de perguntas com múltiplas datas são modeladas por requisito, mas precisam de avaliação mais ampla.

## 3. Multi-hop e contexto

`Decision.py` valida `answer/retrieve/revise_scope/clarify/abstain`. Estado legado contraditório é normalizado: ausência de suporte no contexto não prova impossibilidade no corpus. Impossibilidade exige fundamentação; restrições explícitas não podem ser ampliadas pelo agente. Limites determinísticos: três rounds e até três queries por round.

Evidências encontradas ficam separadas do contexto ativo, com IDs estáveis durante a pergunta. Fatos conservam proveniência. A recomposição prioriza suporte estabelecido e evidência recente dentro do orçamento; repetição, ausência de novidade, falta de espaço e limite são razões distintas. A matemática do retrieval não mudou.

**Controle H08:** plano correto e evidência inicial foram fornecidos explicitamente; buscas seguintes usaram o índice real inalterado. Nas três repetições houve Research e busca dependente no segundo round, identificando Pablo e CK0270. Todas terminaram abstidas na verificação. Foram sete chamadas por repetição e aproximadamente 225/243/241 s, incluindo o percurso do controle. Portanto: progressão validada, **não acerto end-to-end**.

Esse controle expôs um falso negativo lexical: `Edital` estava sendo tratado como entidade pela inicial maiúscula. O detector foi corrigido para formas nominais mais conservadoras, sem blacklist de casos, e recebeu testes. Os resultados anteriores foram preservados; a correção ainda não foi medida com geração. O verificador também propôs testemunhos parafraseados, rejeitados por não serem citações literais.

## 4. Grounding, cobertura e conflito

`Grounding.py` valida separadamente suporte, referências, cobertura por requisito e conflitos. Claims sem vínculo útil não tornam a resposta respondida. `answered` exige cobertura integral sem conflito; `partial` explicita requisitos ausentes; nenhuma cobertura útil resulta em `abstained`. Clarificação depende de ambiguidade real. Um reparo semântico é permitido, seguido de revalidação. Parsing/validação estruturados permanecem centralizados, com apenas uma tentativa adicional e erros compactos.

Cada aprovação exige testemunho literal em cada evidência citada. Espaços podem ser normalizados, paráfrases não. Restrições lexicais explícitas precisam de suporte nas citações ou aliases comprovados do mesmo documento. Essas condições são **necessárias, não prova de entailment semântico**: entidade e frase corretas ainda podem ter cargo, data ou modalidade errados.

`Coverage.py` distingue lotes preparados, enviados e concluídos. Cobertura só conta após processamento. Verificação global consolida requisitos/conflitos com claims já verificadas e seus testemunhos, sem OR de `central_question_supported`, nem concatenação ilimitada de parents.

**Falhas reais preservadas:**

- H02, com payload compacto e antes das proteções literais, teve três falsas aprovações do coordenador de outro projeto. Compactar o transporte sozinho não resolveu semântica.
- H02 com testemunhos literais foi bloqueado três vezes, mas o modelo continuou chamando a claim errada de suportada. A rejeição decorreu da alteração de pontuação na citação. Não é evidência de melhoria semântica. Um teste independente usa citação literalmente perfeita do projeto errado e verifica a restrição Redfish.
- O controle contraditório F01 passou na condição inicial, mas a condição posterior mais estrita falhou nas três repetições: o modelo duplicou a cobertura de `R1`, inclusive após o reparo estruturado permitido. O controlador rejeita, não transforma isso em resposta aprovada. Disponibilidade continua afetada.

**Gate bloqueado:** não há aprovação para uma rodada integrada de 80 casos ou alegação de qualidade. L05/U02 e demais controles generativos completos não foram declarados aprovados. Regressões locais cobrem as políticas, não substituem sua validação semântica no modelo.

## 5. Cálculos determinísticos

`Tables.py` extrai operandos temporários com valor `Decimal`, locale, unidade, cabeçalho/linha e offsets literais. Tabelas Markdown regulares são interpretadas sem reindexação. Reasoning pode selecionar IDs; código valida ocorrência/proveniência e executa soma, diferença, média, mínimo/máximo. Valores impressos e calculados permanecem distintos. Claims numéricas precisam preservar o cálculo validado; reparo generativo não pode substituir seu resultado.

**Regressões locais:** T04 mantém soma 21.120, total impresso 21.200 e diferença 80; T05 mantém R$ 6.150,04. Números tipados, strings brasileiras, vazio, locale ambíguo, unidade incompatível e tentativa de alterar o cálculo possuem testes distintos. Não houve inferência real T04/T05 nesta etapa; seleção semântica dos operandos ainda exige controle generativo. Extração temporária não cobre qualquer tabela irregular ou documento com múltiplas moedas.

## Harness e reprodução

`benchmark/datasets/real/priority_controls.json` congela os 18 diagnósticos existentes mais F05/E02/H02/H08/L05/U02/Q08: 25 casos, sem modificar os 80 ou seus gabaritos. `benchmark/priority_controls.py` fornece modos `transport`, `planner`, `negative`, `oracle`, `dependent` e `integrated`, três repetições sequenciais, payloads sem credenciais, identidade/configuração/fingerprint, snapshots de código e estado parcial em falhas. Controles com evidência/plano fornecidos são identificados, não apresentados como recuperação autônoma.

Exemplo de transporte:

```sh
uv run --no-sync python -m benchmark.priority_controls --mode transport \
  --output-dir benchmark/results/runs/NOVA_CONDICAO_TRANSPORTE
```

Demais modos e condições constam em `docs/benchmarking.md`. Usar diretório novo por condição; nunca sobrescrever controles para esconder falhas. Não executar `integrated` ou os 80 enquanto os controles críticos de verificação não passarem. As pequenas condições aqui descritas não são uma comparação científica de acurácia dos 80; mudanças e snapshots estão separados, mas nem todas as proteções têm comparação generativa isolada completa.

## Validação e próximos gates

Comandos locais: Black nos arquivos alterados; `python -m compileall -q application benchmark scripts tests`; `git diff --check`; `uv run --no-sync --with pytest==8.3.5 python -m pytest -q`.

Resultado: **207 testes passaram em 55,32 s**, com três avisos existentes de depreciação SWIG. Compilação, formatação e checagem do diff sem erros. O arquivo novo de controles contém 47 testes parametrizados/individuais passando; testes anteriores de providers, retrieval, cache, planilhas, histórico e fontes continuam na suíte. O CLI de controles também foi carregado com `--help`, sem gerar chamadas. Essas verificações não estabelecem acurácia generativa.

Pendências reais: estabilidade do schema de cobertura com Phi-4; suporte semântico correto (relação/data/modalidade); falsa abstenção por testemunho não literal; repetir controles após as últimas correções; completar os 25 casos pertinentes, incluindo cálculos, conflitos globais e negativos; só então executar os 80 uma vez e revisar os 19 acertos preliminares. Mudanças de orçamento/modelo continuam experimentos separados. Não se atribui ganho de produção a estes resultados.
