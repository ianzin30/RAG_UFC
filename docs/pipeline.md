# RAG Pipeline — Architecture Overview

This document describes every stage of the pipeline, the purpose of each configuration knob, and how to add a new document collection. Nothing here is collection-specific — the pipeline is designed to work with any folder of documents placed under `data/collections/`.

---

## Data flow

```
data/collections/<name>/   ←  source documents (PDF, DOCX, XLSX, …)
         │
         ▼
   [Ingestion]  DirectoryLoader + Docling → Markdown text
         │
         ▼
   [Chunking]  Markdown-heading split → RecursiveCharacterTextSplitter windows
               Spreadsheet markdown → row/people/column-profile chunks
         │
         ▼
   [Embedding]  BAAI/bge-m3 (HuggingFace) → dense vectors
         │
         ▼
   [FAISS index]  stored at data/cache/rag_index/<fingerprint>/
         │
   ┌─────┴──────────────────┐
   │ Dense MMR retrieval    │  base_search_k candidates, MMR with lambda_mult
   │ Lexical retrieval      │  BM25-style token overlap + date/phrase bonuses
   └─────┬──────────────────┘
         │ merged + ranked by priority_score
         ▼
   [Selection]  top llm_selection_limit chunks (LLM selector optional)
         │
         ▼
   [Context formatting]  per-chunk labeled headers  [Trecho N | documento: … | secao: …]
         │
         ▼
   [Answer LLM]  Ollama (configurable model) with temperature=0
         │
         ▼
   [Answer]  returned to the UI / benchmark
```

---

## Configuration knobs (`config/config.toml`)

### `[model]`
| Key | Purpose |
|---|---|
| `ufc_model_name` | Ollama model tag used for answer, small-talk, and query-rewrite chains. `llama3.1:8b` is the default. Use `qwen2.5:14b-instruct` or `gemma3:12b` for better Portuguese factuality if VRAM allows. |

### `[generation]`
| Key | Purpose |
|---|---|
| `temperature` | Sampling temperature. `0.0` maximises copy-fidelity — the model copies names, dates, and numbers verbatim from context rather than paraphrasing. |
| `top_p` | Nucleus sampling probability. |
| `repeat_penalty` | Penalises repeating the same tokens; keeps answers concise. |
| `seed` | (optional) Makes generation deterministic across runs. |
| `num_ctx` | (optional) Overrides the model's default context window in tokens. |

### `[embeddings]`
| Key | Purpose |
|---|---|
| `model_name` | HuggingFace embedding model. `BAAI/bge-m3` is multilingual and handles Portuguese well. |
| `device` | `cuda` / `mps` / `cpu`. Auto-downgrades if the requested device is unavailable. |
| `quantization` | `4bit` (CUDA, requires bitsandbytes), `int8` (CPU ONNX), or `none`. |
| `batch_size` | How many chunks to embed at once; lower if you run out of VRAM. |
| `max_length` | Embedding model sequence length cap (tokens). |

### `[splitter]`
| Key | Purpose |
|---|---|
| `chunk_size` | Max characters per chunk window. 800 is a good default — large enough to fit a named-entity announcement plus surrounding evidence. |
| `chunk_overlap` | Characters to repeat between adjacent windows, so answers that span a boundary are not cut. |
| `separators` | Ordered list of split characters. Tried in order; fall back to the next if the chunk still exceeds `chunk_size`. |

### `[retrieval]`
| Key | Purpose |
|---|---|
| `base_search_k` | Number of nearest neighbours from FAISS dense search before MMR. |
| `base_fetch_k` | Candidate pool size passed to MMR. |
| `base_lambda_mult` | MMR diversity parameter (0 = maximum diversity, 1 = pure similarity). |
| `lexical_limit` | Max chunks returned by the BM25-style lexical pass. |
| `candidate_pool_limit` | Total candidates kept after merging dense + lexical. |
| `llm_selection_limit` | How many chunks are passed to the answer LLM. Set to 12 so answer chunks at ranks 9–11 enter context. |
| `llm_selector_enabled` | When `true`, an 8B LLM reranks candidates before they reach the answer LLM. Disabled by default because it adds latency and occasionally drops the correct chunk. Set `true` to experiment. |

### `[rag]`
| Key | Purpose |
|---|---|
| `agent_mode` | `crewai` enables CrewAI agents for grading/evaluation. Any other value disables them. |
| `strict_grounding` | When `true`, the system abstains if `evidence_score < min_evidence_score`. |
| `min_evidence_score` | Threshold below which the system returns "Não encontrei…" instead of guessing. `0.25` is a conservative floor; raise it if you see too many hallucinated answers, lower it if you see too many false abstentions. |

---

## Cache invalidation

The FAISS index is cached at `data/cache/rag_index/<fingerprint>/`. The fingerprint is a SHA-256 of the source file hashes plus the splitter config (`chunk_size`, `chunk_overlap`, `separators`). Changing any of these causes a full re-index on the next collection load. No manual action is required.

---

## Adding a new collection

1. Create a folder: `data/collections/<my_collection_name>/`
2. Drop your documents (PDF, DOCX, XLSX, TXT, …) anywhere inside that folder — subdirectories are fine.
3. Start the app (`streamlit run application/app.py`) and select `<my_collection_name>` in the sidebar. The first load triggers ingestion and index building; subsequent loads use the cache.
4. Ask questions. No code changes are needed for any collection.

### Spreadsheet documents

Excel/CSV files are detected automatically. They are chunked into `row_record`, `people_index`, and `column_profile` chunks in addition to the standard `section_detail` chunks, so questions like "who is in row 14?" work without any special configuration.

---

## Chunking strategy

**Generic documents** (PDF, DOCX, TXT, Markdown):
- A single `document_profile` chunk is built from the first non-empty paragraph for "what is this document?" queries.
- The body is split at Markdown headings (`#`–`######`). If no headings exist, the entire body is treated as one section.
- Each section is windowed through `RecursiveCharacterTextSplitter` into `section_detail` chunks.
- `page_content` contains only the raw text — no `Documento:/Secao:/Trecho:` prefixes. Labels live in `metadata` and are added by the context formatter at prompt time.

**Spreadsheets**: chunked into `row_record`, `people_index`, `column_profile`, and `sheet_summary` chunks with structured metadata for name/role lookups.

---

## Answer chain

The answer LLM receives up to `llm_selection_limit` labeled context blocks formatted as:

```
[Trecho 1 | documento: <name> | secao: <heading>]
<raw text>

[Trecho 2 | …]
…
```

The system prompt instructs the model to:
1. Use only the provided context — no external knowledge.
2. Copy proper nouns, numbers, dates, and city names **exactly** as they appear in the context (including titles such as Prof., Profa., middle names, and prepositions).
3. Abstain with a fixed phrase if no chunk contains the answer.
4. Respond in Portuguese, in at most two sentences (unless a list or longer explanation is requested).
