# rag-ufc-core

The reusable RAG engine of the RAG-UFC project: document chunking, hybrid dense/sparse
retrieval, reranking, multi-hop agentic planning, evidence coverage, grounded generation
with claims and citations, source focus, and Markdown ingestion.

It is developed and scientifically validated in the RAG-UFC research repository and consumed
by applications (QwenRAG) as a pinned, versioned dependency. Applications never copy it.

## Stable API

```python
from rag_ufc_core import RAGService, EngineSettings, DataPaths, pipeline_identity, check_adoption

settings = EngineSettings.from_toml("config/rag.toml")      # [llm] and [rag_v2] sections
paths = DataPaths.under("/srv/qwenrag/data")              # collections/ and cache/rag_v2/
service = RAGService(settings, paths)
service.check_model_ready()
service.load_collection(["uploaded_files"])
trace = service.ask_question_with_trace("Quem coordena o AFO?", chat_history=[])
trace["answer_text"], trace["claims"], trace["cited_sources"]

identity = service.pipeline_identity()      # what is actually running
report = check_adoption(identity)            # compared with RELEASE.json
```

* `ask_question_with_trace` returns the trace v2 dictionary: `answer_text`, `status`
  (`answered`, `partial`, `casual`, `abstained`, `clarification_required`), `route`,
  `claims`, `cited_sources` (with `focus_spans` and `provenance`), `evidence` and
  `provider_calls`.
* Progress: `set_response_status_callback(fn)` receives `{"stage", "message", "mode", "agent"}`;
  `set_collection_progress_callback(fn)` receives `{"event", ...}` while indexes load or build.
* Errors to catch: `rag_ufc_core.errors` (`ProviderError`, `InputBudgetError`, `LLMError`,
  `LLMConnectionError`); their messages are safe to show.
* Presentation of answers: `rag_ufc_core.results` (`normalize_presentation`, `preserve_v2_fields`,
  `displayed_sources`) keeps claims and citations consistent with the answer's evidence.
* Secrets: providers read credentials through `rag_ufc_core.secret_source.read_secret`
  (process environment by default; `use_secret_source(fn)` registers another source).
  Settings, identities and logs never contain secret values.
* Ingestion: `rag_ufc_core.LocalUploads.LocalUploadService(collections_root)` converts uploads
  to the Markdown corpus the index reads. Docling is the optional extra `rag-ufc-core[docling]`.

Everything under `rag_ufc_core.rag.v2` is implementation. Research protocols use it directly;
applications should not. `rag_ufc_core.strategies` lists which strategies there are
experimental and therefore not part of the application pipeline.

## Releases

`RELEASE.json` (inside the package) records the approved pipeline configuration, the index
format it reads, the approval decision and the evidence behind it. A package version alone
does not identify a pipeline; `pipeline_identity()` and `check_adoption()` do.
See `docs/core/` in the RAG-UFC repository for the promotion workflow.
