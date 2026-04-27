# Benchmarking Guide

This document explains how to write benchmark questions, run the benchmark suite, and interpret the results.

---

## Running the benchmark

```bash
python -m benchmark.run
```

Results are written to `benchmark/results/<run_id>_diagnostics.json` and `benchmark/results/<run_id>_study.md`.

---

## Question format

Questions live in YAML files inside `benchmark/questions/`. Each question is a mapping:

```yaml
- id: "01"
  collection: google_drive_rag          # must match a folder in data/collections/
  question: "Quem convocou a reunião?"
  expected_answer: "Prof. Fernando Antonio Mota Trinta"
  accepted_answers:
    - "Fernando Antonio Mota Trinta"
    - "Fernando Trinta"
  source_document: "01_01-2022_Ata"     # optional: file name hint for retrieval scoping
```

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Unique identifier within the file (used in report headings). |
| `collection` | yes | The collection folder to query. |
| `question` | yes | Exactly what gets sent to the RAG service. |
| `expected_answer` | yes | Canonical correct answer. Used for lexical matching. |
| `accepted_answers` | no | Alternate phrasings also counted as correct. |
| `source_document` | no | Partial or full file name. Constrains the corpus scan to that document's chunks when checking whether the expected answer is retrievable. |

### Tips for good questions

- Use the exact phrasing a real user would type — don't simplify or translate to English.
- For name questions, set `expected_answer` to the **full official form** (titles, middle names, prepositions). The benchmark measures whether the LLM copies this exactly.
- Always set `source_document` when the question targets a specific file, or you risk false `retrieval_failure` classifications (the answer may exist in multiple documents under different wordings).

---

## Failure classifications

Each question result carries a `failure.classification`:

| Classification | Meaning |
|---|---|
| `no_failure` | The system retrieved and generated the correct answer. |
| `retrieval_failure` | The expected-answer chunk never entered the dense/lexical candidate pool. Fix: tune `base_search_k`, `base_fetch_k`, or improve chunk quality. |
| `selection_failure` | The chunk was in the pool but was not promoted to the final context. Fix: increase `llm_selection_limit`, or investigate lexical scoring. |
| `generation_failure` | The correct chunk was in the selected context but the LLM did not use it. Fix: lower temperature, switch to a stronger model, or simplify the prompt. |
| `document_resolution_failure` | The document resolver steered retrieval to the wrong document. Fix: check `source_document` hints or improve the resolver. |
| `benchmark_data_mismatch` | The expected answer was not found anywhere in the indexed corpus. Fix: check the question, the `expected_answer` spelling, and the `source_document` field. |

### Grounding status

| Status | Meaning |
|---|---|
| `grounded` | The context explicitly contained the expected answer AND the generated answer matched it. |
| `weakly_grounded` | The context had the answer but the generated answer was only a partial match. |
| `unsupported` | Neither the context nor the generated answer contained the expected answer. |

---

## Reading the diagnostics JSON

Each element of `results[]` in the JSON contains:

- **`question_data`** — the question, expected answer, generated answer, and resolved question after query rewrite.
- **`retrieval.metrics`** — boolean flags: `expected_answer_in_pool`, `expected_answer_in_context`, `source_document_in_pool`, plus `source_document_rank` (rank of the source document's first chunk in the candidate pool).
- **`retrieval.rank_movement`** — for each relevant chunk, its rank at each pipeline stage (`dense_mmr`, `lexical`, `candidate_pool`, `selected_context`). Essential for diagnosing whether a chunk was dropped by dense retrieval, lexical merging, or context selection.
- **`retrieval.answer_context`** — the exact context string sent to the answer LLM, formatted with labeled chunk headers.
- **`generation.prompt_text`** — the full prompt sent to the LLM (system message + all context + question). Present only when diagnostics capture is active (benchmark runs always enable it).
- **`generation.raw_llm_response`** — the raw text returned by the LLM before any post-processing.
- **`generation.generation_params`** — the Ollama sampling options used (`temperature`, `top_p`, `repeat_penalty`, and optionally `seed`, `num_ctx`).
- **`agent_grading`** — the CrewAI agent's verdict (`correctness`, `grounding_status`, `failure_classification`, `confidence`, `rationale`), or `status: fallback` if the agent was unavailable.

### Diagnosing `generation_failure`

When `failure_classification = generation_failure` and `expected_answer_in_context = true`, the study report shows a **"Diagnostico de falha de geracao"** section with:
- The exact substring of the context containing the expected answer (with byte offset), confirming the LLM had the answer literally in front of it.
- The raw LLM response (first 200 chars) for comparison.
- The generation params used.
- The first 400 chars of the prompt text.

If you see this pattern repeatedly, the most effective remedies (in order) are:
1. Switch to a stronger model (e.g. `qwen2.5:14b-instruct`).
2. Confirm `temperature = 0.0` in `config.toml`.
3. Reduce the number of context chunks so the relevant chunk is more prominent.

---

## Config snapshot

The JSON root contains `config_snapshot` — a complete copy of the `AppRuntimeConfig` at the time of the run, including all `[generation]`, `[retrieval]`, `[splitter]`, and `[embeddings]` values. This makes every run self-documenting and reproducible.

To reproduce a run exactly, restore `config.toml` to match the snapshot values and set `generation.seed` to the value recorded in `generation_params` (if present).
