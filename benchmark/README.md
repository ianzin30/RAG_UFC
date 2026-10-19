# Benchmark: retrieval experiments and historical studies

## Teste completo com o dobro de documentos

`document_budget_cycle` executa o agente com 3.000 e 6.000 tokens BGE de
documentos. Ambos os braços usam a API atual configurada em `.env`
(`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`); a chave nunca entra nos artefatos.
Isso evita confundir a mudança de endpoint com o efeito do orçamento.
O resultado histórico de D aparece somente como referência secundária.

```bash
.venv/bin/python -m benchmark search --study document_budget_cycle \
  --source-run benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01 \
  --output-dir benchmark/results/rounds/dobro_documentos_ciclo_completo_2026-10-16/run_01
```

`--preflight-only` reproduz os controles e confere todas as entradas iniciais
sem acesso à rede. Use um diretório separado para essa verificação.
Na execução completa, o modelo escolhe buscas e paradas novamente. São 70
perguntas, dois escopos e dois braços; não há geração de respostas finais.
Mantêm-se ranking global, reranking local, modelo, janela de 16.384 tokens,
reserva de saída de 4.096, margem de 512, parâmetros e quatro buscas/decisões.
A remoção existente de amostras extras continua ativa.

Chamadas são sequenciais, sem retry ou fallback. Apenas requisições idênticas
**desta rodada** compartilham decisões; respostas históricas do modelo não são
reutilizadas. Buscas e rankings históricos podem ser reaproveitados quando
consulta, escopo e índice coincidem. Custos físicos, lógicos e históricos são
registrados separadamente. A ordem efetiva é 3.000 primeiro na coleção e 6.000
primeiro em `oracle_scope`; os tempos físicos por braço dependem do cache
compartilhado e não comparam velocidade sem cache.

`signature.json` e `code.zip` congelam código, entradas, endpoint e políticas.
Retomadas exigem assinatura idêntica e nunca repetem operações de resultado
desconhecido. `cache.json` registra requisições, respostas e operações;
`D3000/retrieval.json` e `D6000/retrieval.json` preservam os contextos e trajetórias;
`comparison.json`, `report.md`, `execution_status.json` e `timing.json` resumem
qualidade, regressões, erros e custos. O uso de tokens informado pelo servidor é
conferido por chamada, sem presumir atestação dos pesos ou do template remoto.
Não altera aplicação, servidor ou monitor.

## Teste com o dobro de documentos

O estudo `document_budget_replay` executa a seleção atual em dois limites:
**3.000 e 6.000 tokens BGE de documentos**. Usa as buscas salvas de D, nas mesmas
70 perguntas originais e nos dois escopos, sem chamadas ao modelo ou novas buscas.
Apenas o limite dos documentos muda: ranking global, parents inteiros, consultas,
avaliadores e janela local do modelo ficam fixos.

```bash
.venv/bin/python -m benchmark search --study document_budget_replay \
  --source-run benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01 \
  --output-dir benchmark/results/rounds/dobro_documentos_2026-10-16/run_01
```

O controle reproduz todos os contextos e avaliações históricos. O estudo reporta
ganhos e perdas por pergunta e por evidência, inclusive após cada busca. Dobrar o
limite não garante seleção monotônica: um bloco grande antes descartado pode
passar a entrar antes de outra evidência.

O tokenizer Qwen e seu template congelados conferem localmente a janela de 16.384
tokens, com saída reservada de 4.096 e margem de 512. São reconstruídas as
requisições das decisões históricas e dimensionado cada contexto final, sem gerar
novas decisões. A regra existente pode remover amostras extras; não corta os
blocos documentais. Contextos que ainda não cabem são registrados explicitamente.
Esta auditoria não confirma a janela ou o template efetivos do Open WebUI atual.

`report.md` e `comparison.json` apresentam os resultados; `results.json` e
`trajectories.json` preservam seleções e avaliações; `window_audit.json` mostra
contagens, remoção de amostras e impedimentos. Assinatura, snapshot do código,
reprodução e preservação acompanham a rodada. Retomada exige assinatura idêntica.
O tempo registrado é do teste local; latência e qualidade das respostas do modelo
não são medidas. Nenhuma configuração da aplicação ou do servidor é alterada.

## Current offline study: global order versus local alternation

`global_order_replay` compares context selection on the saved **D_feedback**
trajectories of the completed interface study. It runs both scopes of the same
70 original questions, without inference, retrieval, reranking or answer generation.
Network connections are forbidden during execution. The cached BGE tokenizer is
loaded from its local snapshot directory; no model or retriever is initialized.

```bash
.venv/bin/python -m benchmark search --study global_order_replay \
  --source-run benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01 \
  --output-dir benchmark/results/rounds/global_order_replay_2026-10-15/run_02
```

The study accepts only its source and output options; live-run flags are rejected.
Existing studies retain their commands and defaults. Use a new output directory
outside the historical source and ancestors. A resume requires the identical full
signature, including actual code, dependencies, configuration, inputs and tokenizer.
Preparation failures are marked incomplete; use a new directory after correcting
an unsigned preparation failure. Missing/unknown required operations block execution;
the runner never fills a historical gap with a new call or silently skips a question.

| Arm | Selection order | Other behavior |
|---|---|---|
| G_global | Saved global ranking against the original query | Whole parents, greedy packing, 3,000 BGE tokens |
| L_local | Chronological round-robin over local parent lists | Identical parents, text, metadata, token counts and packing |

Local lists retain the first occurrence of each parent. Each round visits Q0–Q3
in search order, taking the next unseen parent from each list; duplicates do not
consume a turn. Oversized parents are skipped and packing continues. There is no
shortlist, MMR, document quota, truncation, new score cache or question-specific rule.

All G final records and available intermediate records must reproduce before L is
evaluated. Feedback/rejected actions preserve state. Historical requests remain
available in `historical_observations.json`, attributed only to D. Queries and
stopping decisions are fixed replay inputs, not decisions made by an agent seeing L.

Outputs: `signature.json`, `manifest.json`, `code.zip`, `reproduction.json`,
`results.json`, `trajectories.json`, `comparison.json`, `historical_observations.json`,
`preservation.json`, `execution_status.json`, `timing.json` and `report.md`.
Results include whole/partial coverage, paired question and evidence changes,
intermediate evidence losses, packing traces and gold-informed minimum-parent
feasibility. Gold annotations are used only after selection. `evidence_v2` remains
primary; `literal_v1` and alignment pending cases are also reported.

Recommend a later full-cycle comparison only when neither scope loses a previously
complete question or any final evidence covered by G under `evidence_v2`, reproduction
passes, and L needs no global reranking. Otherwise recommend **revise**, without
tuning alternation after inspecting results. Intermediate losses are reported
separately. Logical operations/pairs dispensed and unique historical operations
are distinct from physical replay time; actual full-cycle latency savings and new
agent sufficiency/error rates are **not measured**. No application promotion or
monitor activation occurs.

## Previous iteration: document search and bounded feedback

`python -m benchmark search --study agent_interface` compares two generic changes:
an optional authorized document filter without copied scope proofs, then corrective
tool feedback within the existing **four decisions and four searches**. The model
and application defaults are unchanged. Qwen3.6/Spark remains **thinking off**,
temperature 0, seed 42, top-p 0.9, top-k 20, min-p 0, penalties 0/0/1,
local window 16,384, maximum output 4,096, margin 512 and timeout 420 seconds.
Retrieval remains Gemma dense + BGE sparse + BGE reranker, 30/channel, full union,
global whole-parent selection within 3,000 BGE tokens.

The same **70 questions in both scopes** are used. These are repeated evaluations,
not new questions:

| Condition | Behavior | Purpose |
|---|---|---|
| A_baseline | Saved original retrieval | Reference without investigation |
| B_tolerant | Previous tolerant minimal agent, reproduced offline | Current architecture reference |
| C_simple | `document_search_v1`; errors stop | C vs B measures the simpler interface |
| D_feedback | Same contract with `bounded_feedback_v1` | D vs C measures error recovery |

```bash
python -m benchmark search --study agent_interface \
  --source-run benchmark/results/rounds/reason_validation_qwen36_spark_2026-10-14/run_01 \
  --output-dir benchmark/results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01
```

`--preflight-only` reproduces A/B and audits initial input budgets offline, without
inference or retrieval. The normal run performs those checks first, verifies the
effective model/transport/tokenizer and makes **two separately recorded synthetic
calls** before measured work. Endpoint or accounting failures block preparation.
The runner does not open tunnels, substitute models or enable a scheduled monitor.

`document_search_v1` returns `action`, `queries` and `reason`. Each query contains
only `text` (up to 500 characters) and optional `document_id`. Unknown or forbidden
IDs reject the action; filters are never silently removed. Existing aliases and
the allowed scope remain authoritative. Document choice is a search strategy,
not a factual claim. Results supply their own provenance; `source_proof` stays
empty for these experimental queries. The sent schema requests a short reason;
local acceptance preserves longer nonblank reasons and records a diagnostic.

C/D use identical prompts and observations until C's first rejection. Requests
are shared only under the same signature and exact observed state. Old-contract
model decisions are never imported into the new contract. Identical retrieval
operations can reuse verified historical or current caches. D's correction calls
count against the same four decisions; there is no hidden parser-repair request.

Recoverable errors include completed malformed JSON, invalid arguments/action,
invalid document filters, repeated queries and exhausted search budget. The next
observation names the error and remaining budgets; rejected actions do not execute
retrieval. Timeout, unknown outcome, input/output exhaustion and retrieval failures
remain terminal and preserve the last context. Three consecutive physical
transport failures stop the run as incomplete. Unknown started calls are not
automatically repeated on resume.

`execution_status.json` counts an original question complete only when C and D
have both scopes. `timing.json` uses UTC and monotonic active durations, separating
preparation, evaluation, reporting, replay, new work and synthetic calls. Reports
present Fortaleza time. Cached calls do not add physical tokens or time again;
logical costs and historical costs remain available separately. Signatures pin
source files, model/configuration, corpus/index/dataset/evaluators, prompts,
schemas, policies and code. An incompatible resume requires a new directory.

`report.html` provides a selector for every original question, scope and condition.
Its trace shows requested/effective action, feedback, selected/discarded parents,
independent context/candidate evidence, budgets, latency and stop reason.
`report.md` and `comparison.json` reuse the existing evaluators and pairwise
reporting. `interface_audit` distinguishes **without terminal error** from
**without any incident**, recovered incidents, false sufficiency and documentary
alignment pending cases. Valid JSON, an authorized filter or accepted stopping
does not establish factual support. Approval of each intervention remains pending
user review; no application promotion occurs automatically.

The measured `agent_interface_qwen36_spark_2026-10-15/run_01` completed all 70
questions in both scopes in **28 min 58 s**, with 182 unique quality planning calls
and two synthetic calls. Collection completeness was A/B/C/D = 51/51/52/52;
terminal errors were 0/27/6/1. Feedback recovered five collection executions
operationally, without adding a complete question. In the diagnostic document
scope, B/C/D completeness was 60/58/58; F02 and H01 stopped incomplete before
trying complementary searches. Both interventions are **revise**, pending user
review. This is an engineering improvement with limited documentary gain, not
approval of the full agent architecture. See the [visual report](results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01/report.html)
and [critical review](results/rounds/agent_interface_qwen36_spark_2026-10-15/run_01/report.md).

## Previous iteration: local reason-length acceptance

`--study reason_validation` tests one change to `minimal_action_v1`: a nonempty
string `reason` longer than 300 characters is accepted locally and logged as
`reason_length_exceeded`. The full original text is preserved. The model-facing
prompt and schema still request at most 300 characters. Query text, scope quotes,
references, action validation, controller limits and application defaults remain
unchanged. This is a generic local acceptance policy, not a question-specific rule.

The same original 70 questions run in both scopes. A is saved original retrieval;
B reproduces the historical strict minimal contract; C revalidates saved decisions
and continues only newly opened trajectories. The full evidence contract is not run.
The source is the completed Spark **no-thinking** `run_01` from 2026-10-14.

```bash
python -m benchmark search --study reason_validation \
  --source-run benchmark/results/rounds/decision_contract_qwen36_spark_2026-10-14/run_01 \
  --output-dir benchmark/results/rounds/reason_validation_qwen36_spark_2026-10-14/run_01
```

Add `--preflight-only` to reproduce the controls and revalidate saved responses
**offline, without generation or retrieval**. This writes an incomplete report;
`response_revalidation.json` is a parser audit, not a completed C trajectory or
evidence-quality result. Removing that flag resumes only an identical signature.
The connected run checks `/models`, the tokenizer/template, actual transmitted
parameters and two separately accounted synthetic planning calls before new work.
If the endpoint is unavailable, preparation blocks without opening a tunnel or
changing provider.

Import requires an identical rendered request, canonical observation and reference
maps, plus the verified source model, generation settings, corpus, index and
evaluators. Raw saved responses are parsed again; saved success/error labels are
not treated as validation. The original prompt/schema, raw response and local
acceptance schema have separate snapshots/hashes. Unknown started decisions or
retrieval operations are not automatically repeated. Historical files are read-only.

The frozen base remains Qwen3.6/Spark, thinking off, temperature 0, seed 42,
top-p 0.9, top-k 20, min-p 0, penalties 0/0/1, local window 16,384, output 4,096,
timeout 420 s and input margin 512. Retrieval retains 30/channel, full union,
global whole-parent selection at 3,000 tokens, four total searches and four decisions.

`timing.json` records UTC timestamps and monotonic active durations by session,
preparation/evaluation/reporting phases, replay, new live work, retriever setup and
synthetic calls. Resumes distinguish active time from elapsed time including pauses;
an unobserved crash tail stays unknown. `execution_status.json` counts completed
original questions only when C has both scopes. Cache hits do not add physical
calls or tokens again. Source latencies remain historical costs, not current speed.

Reports (`report.md`, `report.html`, `comparison.json`) separate evidence completeness,
absence of operational error, the conjunction of both, false sufficiency, documentary
pending alignments, gains/losses and their source positions. New physical attempts,
including failures, have median/p95 latency; replay is reported separately. An accepted
decision alone is not a retrieval improvement. Recommendation requires critical review;
approval and application promotion remain with the user. No scheduled monitor is resumed.

The interrupted Qwen3 4B iteration tested whether a smaller decision contract makes adaptive retrieval
more reliable and faster, while preserving documentary evidence. It uses the
original **70 questions**, both existing scopes, and three conditions:

| Condition | Behavior |
|---|---|
| A_baseline | Verified saved original search and global selection |
| B_full_contract | Adaptive decisions with needs, dependencies and cited support |
| C_minimal_contract | Same adaptive controller; action, one optional query and short reason |

There are **420 context evaluations of the same 70 questions**. C versus B is the
main comparison. Both also compare against A. A valid C decision is not evidence
of correctness: `finish_sufficient` is an unverified model declaration audited
by the independent `evidence_v2` evaluator; `literal_v1` is retained.

## Communication interface: DGX Spark / vLLM

The Qwen3.6 Spark decision-contract run finished on **2026-10-14**, using the
approved generation base unchanged. All 70 original questions were evaluated in
both scopes. Collection completeness was **51/70 original, 52/70 full contract,
51/70 minimal contract**; complete contexts without operational errors were
**51/70, 7/70 and 22/70**, respectively. See the
[completed report](results/rounds/decision_contract_qwen36_spark_2026-10-14/run_01/report.md)
and `outcome_summary.json` there. Architecture approval remains pending user review.

The
Qwen3 4B quality run was stopped by request after **20/70 original questions**
completed both contracts in both scopes. Its results, snapshots and historical
settings remain in `results/rounds/decision_contract_qwen3_4b_2026-10-13/run_01`;
see `INTERRUPTED.md` and `interruption.json`. The old `report.md` is an early
snapshot, not a final comparison.

`config/config.toml` now selects the Spark for benchmark calls only:

```toml
[benchmark.llm]
provider = "vllm"
model = "nvidia/Qwen3.6-35B-A3B-NVFP4"
tokenizer = "nvidia/Qwen3.6-35B-A3B-NVFP4"
temperature = 0.0
num_ctx = 16384
max_output_tokens = 4096
timeout_seconds = 420

[benchmark.llm.providers.vllm]
base_url = "http://localhost:8000/v1"
enable_thinking = false

[benchmark.llm.providers.vllm.options]
top_p = 0.9
top_k = 20
seed = 42
min_p = 0.0
presence_penalty = 0.0
frequency_penalty = 0.0
repetition_penalty = 1.0
```

These generation settings are now frozen as **qwen36_spark_greedy_no_thinking_v1**.
The user approved this base on **2026-10-14**; the approval record preserves the
original profile fingerprint. Future agent studies start from this generation base.
See the [audited generation base](../docs/qwen36_generation_base_2026-10-13.md),
with token budgets, actual wire validation and snapshots. The completed Spark
study referenced that exact base. A change in generation parameters requires a new profile and
output directory; never overwrite the prior base. At temperature zero, vLLM uses
greedy decoding and top-p/top-k/min-p do not control sampling.

The interface still allows `enable_thinking` to enable/disable reasoning; omitting
it uses the server default, but that would differ from the frozen base. Optional
sampling keys are omitted from requests when absent. Supported
options are `top_p`, `top_k` (-1 or positive), `min_p`, `seed`, `presence_penalty`,
`frequency_penalty`, `repetition_penalty` and `stop` (string or list). Unknown keys,
invalid ranges and incorrect types fail validation. `repetition_penalty` is the
vLLM name; Ollama's `repeat_penalty` is not interchangeable.

`[llm]` and `[llm.providers.*]` continue to control the application. Benchmark
provider overrides are separate; environment `VLLM_BASE_URL` takes precedence in
both flows. `VLLM_API_KEY` is optional; the current Spark API needs no authentication.
The effective URL and transmitted parameters are recorded without credentials.

`num_ctx` is a **client input/output budget**, not a parameter that enlarges the
server window. Readiness verifies the configured model and `max_model_len` from
`/models`, loads the configured tokenizer and counts the same messages and thinking
options that the adapter sends, reserving output plus 512 tokens. Template/vocabulary
hashes and model metadata are frozen. No alternate model or tokenizer is substituted.
The 3,000-token documentary context uses BGE and is a separate retrieval budget.

The adapter calls `/chat/completions`, using schema instructions and local validation
in the benchmark, without server-enforced JSON. `content` is used by the controller;
`reasoning`/`reasoning_content` is logged separately and never added to documentary
observations. Output tokens include reasoning. Empty content, truncation and transport
failures retain available usage, reasoning, finish reason and request parameters.
Token usage does not provide a reasoning-only count unless the server reports it.

The interface never opens tunnels, installs server models, switches providers or
retries unknown-outcome calls. A connection failure requires checking the existing
tunnel/server. New generation calls and the next study require their separate plan.
Historical signatures prevent resuming Qwen3 4B results under the new configuration.

The existing `python -m benchmark search` CLI remains available. Do not run it against
an old output directory after changing configuration. Current transport validation
uses mocked tests, without inference. The earlier two-call real connectivity check is
preserved in `results/diagnostics/qwen36_spark_api_smoke_2026-10-13T18-31-12Z/REPORT.md`:
1.24 s without reasoning and 9.13 s with reasoning on a tiny synthetic input. Those
measurements do not predict full retrieval quality or large-input latency.

## Frozen retrieval and interpretation

Gemma dense, BGE sparse, BGE-Reranker, corpus/index, frozen histories, evaluation
and scope rules remain unchanged. Each query retrieves 30 per channel, with the
full deduplicated union reranked. Global whole-parent selection uses 3000 BGE
tokens. Compact observations contain original selected parents, scoped document
catalog and up to six additional children (two per document). Optional samples
are removed first to fit; mandatory input is never silently truncated.

B retains its monotonic needs and documentary citation checks. C removes that
ledger but shares query/scope validation and controller limits. Private thinking
is logged for diagnostics and never inserted into subsequent observations or
context. No fixed fields, alternation, additional reader/critic or new datasets
are introduced. B/C order is balanced across questions; execution is sequential.

The timing pilot separates server load, prefill and generation time, includes
failures and notes prefix-cache effects. Its small sample is not an accuracy test.
The full report distinguishes protocol compatibility, evidence completeness and
compute cost. One seeded quality run does not characterize stochastic variability
or demonstrate transfer to unseen domains.

## Results and review

Separate directories preserve historical artifacts. Signatures include contracts,
prompts, code, configuration, model/tokenizer identity, datasets, index and input
state. Runs save code/schema snapshots, sanitized prompts/responses, trajectories,
per-condition `retrieval.json`, `comparison.json`, `report.md`, physical costs,
execution status and historical-preservation verification. Authentication headers
are never stored. Resume requires an identical signature.

The report includes categories, evidence gains/losses, partial coverage, false
sufficiency, failure stage, search/call/token counts, reranker workload and median/
p95 latencies. Approval stays **pending user review**; no automatic threshold or
application promotion. The recommendation distinguishes evidence gains from easier
JSON acceptance and preserved context on errors.

## Existing studies

`--study adaptive` (default) retains the prior A original/B single-shot/C adaptive
comparison and `--search-policy all|single_shot|adaptive`. Existing
`--planner-input-format legacy_v1|compact_v1`, `--audit-inputs` and `--speed-test`
remain available for the historical input-format study, using explicitly configured
provider/model parameters. Old runs are read-only and cannot resume under changed
signatures. No deleted historical runner is restored.
