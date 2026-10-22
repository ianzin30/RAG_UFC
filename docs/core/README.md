# RAG core: ownership and boundaries

Two repositories, three components:

```text
RAG-UFC (this repository)                         QwenRAG (application)
├── packages/rag-ufc-core/   shared RAG core ───▶ pinned dependency (git commit)
│     rag_ufc_core           released as 1.0.0, …   backend/   FastAPI, conversations, uploads
├── benchmark/, docs/        research              frontend/  React
├── application/             Streamlit research UI, Telegram, Google Drive
└── releases/rag-ufc-core/   release records
```

Dependency direction: research → core ← application. The core imports neither
(`packages/rag-ufc-core/tests/test_boundaries.py` enforces it).

## What the core owns

| Area | Modules |
|---|---|
| Stable API | `rag_ufc_core.RAGService`, `EngineSettings`, `DataPaths`, `pipeline_identity`, `release_manifest`, `check_adoption`, `errors`, `results`, `secret_source` |
| Engine (implementation) | `rag_ufc_core.rag.v2.*`: chunking, hybrid dense/sparse retrieval, reranking, planning and multi-hop flow, evidence coverage, grounding, verification, source focus, providers (Spark, vLLM, Ollama, UFC) |
| Ingestion | `LocalUploads`, `DocumentExtraction`, `StructuredExtraction`, `SpreadsheetMarkdown`, `spreadsheet/`: the Markdown corpus and structure sidecars the index reads |
| Release metadata | `RELEASE.json`, `identity.py`, `release.py`, `strategies.py` |

The ingestion code is in the core because the Markdown it writes is the searchable
corpus: an upload in the application and an extract used in research must produce
identical text, or index fingerprints and results stop being comparable.

Stays in this repository, outside the core: benchmarks and protocols, Streamlit (a
research and exploration interface), Telegram, Google Drive OAuth/listing, scraping,
`config/config.toml` and the research data under `data/`.

## Configuration and data are injected

The core never derives paths from its install location and never reads `.env` by
itself. Hosts provide:

* `EngineSettings` — from a document (`[llm]`, `[rag_v2]`), a TOML file, or
  `EngineSettings.from_release(deployment)` (the approved pipeline plus endpoints,
  credential variable names, timeouts and device only);
* `DataPaths` — `collections_root` and `index_cache_root`;
* secrets — `secret_source.use_secret_source(fn)`; the default is the process environment.

In this checkout, importing `application.service` (or `service`) binds those choices to
`config/config.toml`, `data/` and `.env`, so `RAGService(collection, model)`, Streamlit and the
benchmarks behave as before.

## How the research checkout keeps working

* **Same bytes at the old paths.** Files moved into the package left symlinks at their
  old paths (`application/service/rag/v2/*.py`, `UfcOllama.py`, `spreadsheet/`, …). Tools
  that hash, archive or compare files by path (`reproducibility.code_files()`, Track B
  `load_source`, `code.zip`) read exactly the code that runs.
* **Same module objects under old names.** `application/service/_core_aliases.py` maps
  `service.rag.v2.*` and `application.service.rag.v2.*` to the `rag_ufc_core` modules: one
  copy per process, so monkeypatches, classes and module state agree.
* **Thin shims where behavior needed a host.** `application/service/rag/RagService.py`
  (checkout settings and paths), `application/service/LocalUploads.py` (Drive collections
  root), root `llm_client.py` (checkout `.env` as the default for `from_env()`).

`releases/rag-ufc-core/1.0.0.lineage.json` lists every moved file with its hash before and
after: 36 of 42 are byte-identical; the 6 that changed only remove checkout coupling.

## Development loop

```bash
uv sync                                    # installs the core editable from packages/ (a path
                                           # dependency, not a workspace member: this repository's
                                           # uv sources must not leak to consumers of the core)
uv run pytest tests packages/rag-ufc-core/tests
uv run python -m benchmark.promotion check  # registry, manifest, evidence, pipeline boundary
```

Changing the core inside this repository changes what research runs immediately (editable
install). It changes nothing in QwenRAG until a release is cut and QwenRAG updates its pin.

See [promotion.md](promotion.md) for releases and [historical_reproducibility.md](historical_reproducibility.md)
for runs made before the extraction.
