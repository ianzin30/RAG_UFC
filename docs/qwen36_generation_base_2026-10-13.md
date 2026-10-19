# Base congelada de geração — Qwen3.6 / DGX Spark

Perfil: `qwen36_spark_greedy_no_thinking_v1`, congelado em 13/10/2026. Escolha do usuário: manter temperatura zero e reasoning desligado para comparações controladas. Este registro congela a geração do benchmark; não inicia uma rodada de retrieval nem muda o LLM da aplicação.

**Base aprovada e fechada pelo usuário em 14/10/2026.** A configuração efetiva, o payload e os arquivos do tokenizer continuam idênticos aos snapshots congelados. O [registro de aprovação](../benchmark/results/diagnostics/qwen36_spark_greedy_no_thinking_v1/approval.json) referencia o fingerprint original sem reescrever seu manifesto. Os próximos experimentos partirão desta base; mudanças intencionais em geração deverão ser identificadas como outra condição/perfil, com parâmetros e resultados separados. Intervenções no agente terão planos e assinaturas próprios, mantendo estes hiperparâmetros comuns entre condições quando a geração não for a variável investigada.

## Parâmetros

| Item | Valor congelado | Significado / verificação |
|---|---|---|
| Transporte | vLLM, API compatível com OpenAI | Adaptador compartilhado existente |
| URL efetiva | `http://localhost:8000/v1/chat/completions` | Sem override de URL ativo nesta verificação |
| Modelo anunciado e retornado | `nvidia/Qwen3.6-35B-A3B-NVFP4` | Confirmado em `/models` e na geração |
| Reasoning | `enable_thinking=false` | Enviado em `chat_template_kwargs`; sem reasoning no retorno sintético |
| Temperatura | `0.0` | Decodificação greedy |
| Top-p / top-k / min-p | `0.9` / `20` / `0.0` | Enviados; não controlam amostragem em temperatura zero |
| Seed | `42` | Enviada; não garante determinismo numérico do servidor/GPU |
| Presence / frequency penalty | `0.0` / `0.0` | Explicitamente neutras |
| Repetition penalty | `1.0` | Explicitamente neutra |
| Stop personalizado | Ausente | Sem string adicional de parada; término/EOS nativo do servidor |
| Streaming | `false` | Resposta única |
| Timeout | `420 s` | Prazo da chamada, não quantidade de raciocínio |
| Mensagens | Uma mensagem `user` | O prompt inclui instrução, pergunta, histórico, observações e schema |
| Saída estruturada | Schema no prompt e validação local | Sem `response_format` forçado pelo servidor |
| Limite de geração por decisão | `4096` tokens | Mapeado para `max_tokens`; limite máximo, não quantidade obrigatória |
| Limites por papel no benchmark | `planner=4096` | Não herda `planner=512` da aplicação |
| Tokenizer | Repositório do próprio modelo NVIDIA | Arquivos, vocabulário e template salvos e verificados |
| Versão vLLM reportada | `0.1.dev19754+g3a0914114` | Autodeclaração da API; build de desenvolvimento |

Para estabilizar a base foram explicitados `min_p=0`, `presence_penalty=0`, `frequency_penalty=0` e `repetition_penalty=1`. Eles não eram enviados no primeiro teste de conectividade; essa diferença está documentada e a nova chamada validou o payload completo. Nenhum resultado histórico foi reescrito.

## Comparação imediata com a rodada local anterior

A referência anterior é a rodada **Qwen3 4B de contratos de decisão**, em `benchmark/results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01`. Os valores abaixo foram recuperados da **assinatura daquela execução** e conferidos em um evento de requisição salvo no cache; não foram inferidos da configuração atual.

| Parâmetro / comportamento | Rodada local anterior | Nova base congelada |
|---|---|---|
| Modelo | `qwen3:4b` | `nvidia/Qwen3.6-35B-A3B-NVFP4` |
| Transporte / host | Ollama local | vLLM remoto na Spark, via túnel existente |
| Endpoint | `http://localhost:11434/api/generate` | `http://localhost:8000/v1/chat/completions` |
| Quantização identificada | `Q4_K_M`, reportada pelo Ollama | `NVFP4` no ID anunciado; sem checksum dos pesos exposto pela API |
| Reasoning | **Ligado**, `think=true` | **Desligado**, `chat_template_kwargs.enable_thinking=false` |
| Temperatura | **0,6** | **0** |
| Top-p | **0,95** | **0,9**, enviado mas sem efeito de amostragem em greedy |
| Top-k | **20** | **20**, enviado mas sem efeito de amostragem em greedy |
| Min-p | **0** | **0**, explícito |
| Seed | **42** | **42** |
| Penalidade de repetição | `repeat_penalty=1,0` | `repetition_penalty=1,0` |
| Presence / frequency penalty | Não enviadas; não atribuir valores sem evidência | `0 / 0`, enviadas explicitamente |
| Orçamento total local | **16.384 tokens**, também enviado como `options.num_ctx` ao Ollama | **16.384 tokens**, orçamento do cliente; não enviado como janela do servidor |
| Entrada máxima permitida | **11.776 tokens**, incluindo template/schema | **11.776 tokens**, incluindo template/schema |
| Margem de contagem | **512 tokens** | **512 tokens** |
| Saída máxima por decisão | **4.096 tokens**, via `options.num_predict` | **4.096 tokens**, via `max_tokens` |
| Distribuição da saída | Reasoning e JSON compartilhavam o mesmo teto | Reasoning desligado; teto disponível para conteúdo final |
| Timeout | **420 segundos** | **420 segundos** |
| Tokenizer de contagem | `Qwen/Qwen3-4B`, template com thinking ligado | Tokenizer NVIDIA do modelo servido, template com thinking desligado |
| Contexto documental final | **3.000 tokens BGE**, parents inteiros | **3.000 tokens BGE**, parents inteiros |
| Saída estruturada | Schema no prompt, validação local; sem `format` forçado | Schema no prompt, validação local; sem `response_format` forçado |
| Versão de servidor reportada | Ollama **0.34.3** | vLLM **0.1.dev19754+g3a0914114** |
| Situação | Interrompida após **20/70 perguntas** concluírem todos os braços e escopos | Base auditada; nenhuma nova rodada de qualidade executada |

**Os principais orçamentos não aumentaram:** janela local, entrada permitida, saída máxima, margem, timeout e contexto documental foram mantidos. A capacidade anunciada de 262.144 tokens não era a janela ativa do Ollama: a rodada local pediu e verificou residência com 16.384. Na Spark, a API anuncia essa capacidade do servidor, mas o cliente continua limitado ao mesmo orçamento de 16.384.

Na rodada anterior, B e C usavam **o mesmo Qwen3 4B e os mesmos hiperparâmetros**; a intervenção era mudar o contrato de decisão (completo versus simplificado). Foram mantidos quatro buscas e quatro decisões máximas, seleção global, observação `compact_v1`, até seis children adicionais e dois por documento. Esses parâmetros descrevem aquele experimento de agentes; não são uma aprovação automática de repetir a mesma arquitetura com a nova base.

O evento local conferido enviou `think=true`, `num_ctx=16384`, `num_predict=4096`, temperatura `0.6`, top-p `0.95`, top-k `20`, min-p `0`, seed `42` e repeat-penalty `1`. Também enviou `keep_alive="5m"`, que controla residência do modelo, não prazo ou orçamento de raciocínio. O retorno desse evento identificou `qwen3:4b`; o digest congelado era `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.

Esta é uma comparação de **configurações**, não de qualidade ou velocidade entre modelos. Modelo, quantização, hardware/transporte, temperatura e thinking mudaram juntos. A rapidez do teste sintético da Spark não pode ser comparada diretamente ao tempo das perguntas completas da rodada local, com observações maiores e múltiplas decisões. As comparações controladas futuras devem usar a nova base comum entre suas condições.

Fontes históricas: [assinatura da execução local](../benchmark/results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01/signature.json), [cache com os eventos de requisição](../benchmark/results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01/cache.json), [verificação de residência](../benchmark/results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01/preflight.json) e [registro da interrupção](../benchmark/results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01/interruption.json). A inclusão desta comparação na documentação não altera os snapshots históricos ou o manifesto da nova base.

## Orçamento de tokens

```text
16.384 tokens de orçamento total do cliente
├── até 11.776 de entrada (prompt completo + schema + template)
├── até  4.096 de saída (reasoning, quando ligado, e conteúdo final)
└──        512 de margem para contagem/compatibilidade
```

A API anuncia capacidade de **262.144 tokens**. O cliente escolhe usar 16.384; isso não reduz a configuração física do servidor e não obriga preencher a janela. A entrada varia por pergunta. O contexto documental final permanece em **3.000 tokens BGE**, uma unidade/orçamento separado: esses parents fazem parte da entrada do planejador, junto das demais instruções e observações.

A reserva de 4.096 não exige gerar essa quantidade e não é dividida em dois tetos independentes de reasoning/resposta. Não há orçamento separado de reasoning neste perfil, que o desliga explicitamente. O modelo encerra antes do limite quando termina a decisão.

## Verificações realizadas

Foram auditadas offline as **140 entradas iniciais** (70 perguntas × dois escopos), com os dois contratos existentes. As duas variantes receberam observações documentais compartilhadas. Não houve novas buscas nem avaliação de qualidade nessa auditoria.

| Contrato | Menor entrada | Mediana | Maior entrada | Folga mínima após saída + margem |
|---|---:|---:|---:|---:|
| Completo | 4.353 | 7.396 | 11.317 | 459 |
| Simplificado | 3.774 | 6.752,5 | 10.644 | 1.132 |

A contagem é de entrada real, sem incluir a margem. Todas cabem. Etapas adaptativas futuras podem acrescentar buscas e registros, portanto esta auditoria não comprova que todas as etapas futuras caberão. O controlador continua removendo apenas amostras opcionais primeiro e falhando explicitamente se a entrada obrigatória exceder o orçamento.

Quatro chamadas de **tokenização**, sem geração, verificaram entradas representativas e máximas de ambos os contratos. Local/servidor coincidiram exatamente: **8.039, 11.317, 7.438 e 10.644 tokens**. Os casos representativos usam a observação de posição mediana superior na lista ordenada; não são a média estatística das duas posições centrais.

Uma única chamada de geração sintética foi feita **pelo adaptador real**, com todos os parâmetros congelados. Ela solicitou uma busca sobre a formação de uma inventora identificada em um trecho fictício. O teste verifica transporte/payload/contagem/retorno, não inteligência do agente ou qualidade do retrieval.

- Tempo: **1,130 s**.
- Entrada: **95 tokens**, exatamente igual à contagem local.
- Saída efetiva: **68 tokens**, contra teto de 4.096.
- Total reportado: **163 tokens**.
- Término: `stop`, sem esgotamento.
- JSON parseável; consulta mencionando a pessoa fornecida; nenhum reasoning retornado.

## Julgamento técnico

A configuração é coerente como **base greedy sem reasoning**, deliberadamente escolhida para controlar a geração. Temperatura zero não é a recomendação geral de melhor qualidade da Qwen. A documentação oficial sugere, no modo sem thinking, temperatura 0,7, top-p 0,8 e penalidade de presença 1,5; recomenda também limites de saída maiores para tarefas gerais. Esses valores são referências para outra comparação, não foram adotados nesta base. [Recomendações oficiais Qwen](https://huggingface.co/Qwen/Qwen3.6-35B-A3B#best-practices).

No vLLM, temperatura zero ativa greedy e neutraliza os filtros de amostragem top-p/top-k/min-p. Portanto, enviar top-p 0,9 e top-k 20 é compatível com a API, mas não justifica alegar que eles controlaram diversidade nesta base. A seed não elimina variações numéricas de GPU, batch ou implementação. [Semântica oficial de sampling](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/).

4.096 tokens é um teto de recursos plausível para decisões curtas sem thinking, mas ainda não é uma adequação comprovada para todos os casos. Um esgotamento será uma falha explícita; não será aumentado durante a rodada. Ligar reasoning cria outra condição experimental, e seu orçamento deverá ser avaliado antes da execução.

## Como preservar comparações

O TOML continua sendo a fonte operacional. Seu snapshot, os arquivos do tokenizer, payloads, respostas, hashes, metadados do servidor e a auditoria ficam em `benchmark/results/diagnostics/qwen36_spark_greedy_no_thinking_v1/`. O arquivo `manifest.json` identifica a base; não deve ser sobrescrito para acomodar mudanças futuras.

Em cada rodada, declarar o perfil e manter os mesmos hiperparâmetros entre condições. Arquitetura, prompts e contratos que forem objeto do experimento têm suas próprias assinaturas: a mudança intencional deve ser explicitada. Alterar parâmetros de geração exige outra versão de perfil e outro diretório, sem atualizar a base anterior. As assinaturas existentes do runner já impedem retomar resultados com código/configuração diferentes.

A mudança de um parâmetro não invalida todo o histórico: ela cria outra condição. O problema é misturar configurações na mesma comparação ou atribuir ganhos a uma única intervenção quando várias mudaram sem controle.

A API permite verificar ID, capacidade, versão reportada e retorno. Ela não oferece checksum dos pesos nem toda a configuração interna do servidor. Portanto este registro congela o contrato do cliente e a identidade anunciada, **não comprova imutabilidade física do servidor**. Mudanças do deployment precisam ser registradas como outra condição. Não houve alterações no servidor ou no túnel.

A base está congelada e auditada para comunicação/orçamento inicial. O próximo experimento de agentes ainda precisa de um plano próprio; esta auditoria não produziu novos números de completude do retrieval.

## Rodada posterior usando esta base

Em 14/10/2026, a comparação de contratos de decisão foi concluída nas 70 perguntas originais e nos dois escopos, sem alterar estes hiperparâmetros. A auditoria descrita acima é o registro anterior à rodada. Veja o [relatório concluído](../benchmark/results/rounds/decision_contract_qwen36_spark_2026-10-14/run_01/report.md), que separa evidência completa de execução sem erro. A configuração de geração continua aprovada; a candidatura da arquitetura permanece pendente da revisão do usuário.
