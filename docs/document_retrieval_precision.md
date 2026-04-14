# Document Retrieval Precision

## Baseline Before This Improvement

- Answer model: `llama3.1:8b` via the configured Ollama-compatible UFC endpoint.
- Embeddings: `all-MiniLM-L6-v2`.
- Orchestration: CrewAI enabled by default for casual conversation, scope planning, document selection and evidence-intent planning.
- Final answer generation: prompt-chain answer synthesis over retrieved context.
- Generic chunking: recursive splitter with `chunk_size=500`, `chunk_overlap=100` and separator cascade by paragraph, line, sentence and space.
- Vector retrieval: FAISS with MMR, defaulting to `k=6`, `fetch_k=30`, `lambda_mult=0.2`.
- Locked-document retrieval: vector filter by `document_name` plus similarity fallback.
- Grounding: strict grounding enabled by default with minimum evidence score `0.22`.

## Main Flaws Observed

- Generic text documents were indexed mostly as `document_profile + plain text chunks`.
- Retrieval favored the best local chunks, not broad document coverage.
- Long documents lost attendance lists, section diversity and exact labeled facts before answer generation.
- Dense retrieval alone underperformed on names, titles, dates, roles and enumerations.
- Follow-up questions asking for more detail still reused a narrow retrieval budget.
- Spreadsheets had richer structure than generic text documents, creating an asymmetry in answer quality.

## Implemented In This Iteration

- Generic text indexing now adds:
  - `section_overview` chunks
  - `section_detail` chunks
  - `list_block` chunks for enumerations and roster-like content
  - `entity_index` chunks with generic names, dates, values and labeled facts
- Retrieval now combines:
  - FAISS dense retrieval
  - lexical retrieval over local chunk text and metadata
  - document-scoped coverage expansion for broad intents
- Retrieval intent taxonomy now includes `document_expansion` for questions such as "fale mais" and "me dê detalhes".
- Final answer context now includes an aggregated evidence pack before the raw retrieved chunks.
- Cache version was bumped to `RAG_INDEX_CACHE_VERSION = 2` because the chunking/index structure changed.

## Remaining Direction

- Add stronger evaluation coverage for long narrative reports, project documents and other non-tabular files.
- Expand aggregation for exhaustive entity extraction when the user explicitly asks for all names or all roles.
- Consider an external reranker only after the current hybrid retrieval and aggregation baseline is measured.
