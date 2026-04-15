# RAG_UFC

This document describes the current structure of the project as it exists today.
It is meant to be the quickest way to understand where each part lives, how the app starts, and which modules own each responsibility.

## What This Project Does

`RAG_UFC` is a Streamlit-based retrieval application with a few connected subsystems:

- a local UI built with Streamlit
- a RAG service that indexes local Markdown collections with Hugging Face embeddings + FAISS
- answer generation through a UFC-hosted Ollama-compatible endpoint
- Google Drive ingestion into local collections
- website scraping into local collections
- a Telegram bot runtime that reuses the project services

## High-Level Architecture

```text
Streamlit UI
  -> presentation layer
  -> RAGService facade
  -> local collection loading / chunking / FAISS retrieval
  -> UFC Ollama HTTP client for final answer generation

Google Drive / Scraping
  -> service facades
  -> support modules
  -> Markdown files written to data/collections/

Telegram Bot
  -> bot runtime
  -> same service layer
```

## Repository Map

```text
RAG_UFC/
|-- application/
|   |-- app.py
|   |-- assets/
|   |-- presentation/
|   `-- service/
|-- config/
|-- data/
|   |-- cache/
|   |-- collections/
|   `-- local_chat_sessions.json
|-- docs/
|   |-- README.md
|   `-- document_retrieval_precision.md
|-- logs/
|-- tests/
|-- .env
|-- pyproject.toml
`-- uv.lock
```

## Main Entry Points

### Streamlit app

- `application/app.py`
  - loads the shared runtime config bootstrap
  - calls `presentation.app_shell.page.render_application()`

### Telegram bot

- `application/service/bot.py`
  - loads the shared runtime config bootstrap
  - builds the bot application from `service/bot_runtime/bootstrap.py`

### Service facades

- `application/service/rag.py`
- `application/service/google_drive.py`
- `application/service/scraping.py`

These are the stable public import surfaces for the main subsystems.

## `application/`

### `application/assets/`

Holds frontend assets for the Streamlit app, especially CSS used by the custom shell and sidebar.

### `application/presentation/`

Owns the UI layer.
This directory is responsible for Streamlit rendering, session-state coordination, and user actions.

Key files:

- `chat.py`
  - renders the main chat view
  - creates or reuses `RAGService`
  - triggers collection loading and question answering
- `google_drive.py`
  - renders Google Drive auth and ingestion interactions
- `scraping.py`
  - renders documentation scraping flows
- `collection_selection.py`
  - normalizes and sanitizes collection selection values
- `chat_sessions.py`
  - manages chat tabs/history metadata stored in `data/local_chat_sessions.json`

#### `presentation/app_shell/`

This folder is the Streamlit shell composition layer.
It contains the pieces that build the current two-panel UI and sidebar experience.

Notable files:

- `page.py`: top-level page layout
- `sidebar.py`: left navigation/sidebar rendering
- `collections.py`: collection/document listing helpers for the shell
- `chat_panel.py`, `files_panel.py`: main body panel rendering
- `session_state.py`: session bootstrap defaults
- `styles.py`, `theme.py`: theme and CSS application
- `uploads.py`: file upload entrypoints
- `navigation.py`, `selection.py`, `config.py`: shell support logic

#### `presentation/chat_sessions_support/`

Internal helpers for local chat session persistence and normalization.

### `application/service/`

Owns the non-UI logic.
This is where the RAG pipeline, external integrations, and bot runtime live.

Important top-level files:

- `ufc_ollama.py`
  - HTTP client for the UFC-hosted Ollama-compatible endpoint
  - final answer generation is remote through this client
- `rag.py`
  - thin facade exporting `RAGService`
- `google_drive.py`
  - public facade for Drive auth, listing, extraction, and ingestion
- `scraping.py`
  - public facade for Firecrawl-backed scraping
- `local_uploads.py`
  - local upload support
- `spreadsheet_markdown.py`
  - spreadsheet-to-Markdown conversion entrypoint
- `bot.py`
  - Telegram bot process entrypoint

## `application/service/rag_service/`

This is the core of the project.
It implements the retrieval pipeline as a facade class assembled from many mixins.

### Core idea

- `service.py` defines `RAGService`
- `RAGService` is composed from:
  - `service_parts/` for lifecycle and orchestration
  - `modules/` for reusable retrieval, routing, spreadsheet, and resolution logic

### `service.py`

Defines the main `RAGService` class by combining mixins such as:

- bootstrap
- collection loading
- question answering
- planning
- retrieval
- routing
- prompting
- spreadsheet-specific parsing/retrieval
- document resolution

### `service_parts/`

Lifecycle and top-level orchestration.

Important files:

- `bootstrap.py`
  - reads shared runtime settings from `config/config.toml`
  - creates the embedding model
  - configures the active LLM client
  - initializes prompt chains
  - initializes CrewAI adapters when enabled
- `collection_loading.py`
  - loads Markdown documents from `data/collections/`
  - fingerprints collection state
  - restores or rebuilds FAISS caches
  - builds the retriever
- `question_answering.py`
  - runs the full answer flow for a user question
  - handles casual mode vs retrieval mode
  - resolves follow-ups, document targeting, clarification, grounding, and source traces
- `selection.py`, `focus_state.py`
  - manage selected documents/collections and retrieval focus state
- `planning.py`, `planning_support.py`
  - scope planning and retrieval intent planning
- `question_follow_up.py`
  - follow-up question handling
- `trace_builders.py`
  - structured traces/sources returned to the UI

### `modules/`

Reusable behavior grouped by concern.

Important modules:

- `retrieval.py`
  - aggregates retrieval sub-mixins
- `routing.py`
  - decides which mode/route should handle a question
- `prompting.py`
  - prompt-building logic
- `text_processing.py`
  - normalization helpers
- `spreadsheet.py`
  - spreadsheet-aware retrieval behavior
- `document_resolution.py`
  - tries to resolve the intended target document from the user question

#### `modules/retrieval_parts/`

Breaks retrieval into smaller units:

- `core.py`: base retrieval operations
- `aggregation.py`: context and evidence aggregation
- `clarification.py`: asks for clarification when retrieval is ambiguous
- `intents.py`: retrieval intent classification
- `agents.py`: retrieval-side agent integration
- `spreadsheet.py`: spreadsheet-specific retrieval support

#### `modules/document_resolution_parts/`

Document matching and alias handling:

- aliases
- alias dates
- registry matching
- candidate resolution

#### `modules/spreadsheet_parts/`

Transforms spreadsheet-like Markdown into structured retrieval chunks:

- parsing
- entity extraction
- chunk building

This layer is also important for indexing cost, because the app does not only split files into plain text chunks.
It creates multiple chunk types such as document profiles, section summaries, entity indexes, spreadsheet row records, and other retrieval-oriented views.

### RAG storage model

Current behavior of the RAG layer:

- source documents are local Markdown files in `data/collections/`
- embeddings are computed locally with Hugging Face models
- vector search is local via `FAISS`
- final answer generation is remote via `UFCOllamaClient`

## Google Drive ingestion

### `application/service/google_drive_support/`

Support package for Google Drive ingestion.

Main responsibilities:

- OAuth credential loading and login
- Drive service construction
- file listing and filtering
- file extraction
- ingestion into a local collection folder

Notable files:

- `auth.py`
- `configuration.py`
- `listing.py`
- `extraction.py`
- `ingestion.py`
- `constants.py`
- `models.py`

The Google OAuth desktop credentials file currently lives in `config/google-oauth-credentials.json`.

## Scraping

### `application/service/scraping_support/`

Support package for Firecrawl-based scraping.

Main responsibilities:

- Firecrawl client bootstrap
- docs-site discovery
- crawl/scrape pipelines
- URL filtering and normalization
- Markdown persistence into collections

Notable files:

- `client.py`
- `configuration.py`
- `constants.py`
- `html.py`
- `models.py`
- `pipeline.py`
- `urls.py`

## Spreadsheet Markdown conversion

### `application/service/spreadsheet_markdown_support/`

Helpers used to convert spreadsheet-like inputs into the Markdown representation consumed by the RAG layer.

Main concerns:

- loading
- normalization
- number formatting
- people/entity extraction
- rendering
- shared models/constants

## Telegram bot

### `application/service/bot_runtime/`

Runtime wiring for the Telegram bot.

Main responsibilities:

- bot bootstrap
- handler registration
- session tracking
- onboarding and reply flows

### `application/service/bot_support/`

Shared helpers used by the bot to route users into collections and drive-related flows.

## `config/`

Contains movable configuration files and templates.

Current contents:

- `config.toml`
- `google-oauth-credentials.json`
- `.env.example`
- `README.md`

Note:

- `config/config.toml` is the main non-secret runtime config
- the real runtime `.env` remains in the project root for secrets and external credentials
- `pyproject.toml`, `uv.lock`, and `.python-version` also stay at the root because the toolchain expects them there

## `data/`

Persistent local runtime data.

### `data/collections/`

The source corpus used by the RAG system.
Google Drive ingestion, scraping, and local uploads all feed this directory.

### `data/cache/rag_index/`

Fingerprinted FAISS cache directories.
These allow the app to skip a full re-index when the collection state, chunking settings, and embedding model have not changed.

### `data/local_chat_sessions.json`

Local persistence for Streamlit chat session metadata/history.

## `docs/`

Documentation folder.

Current docs:

- `README.md`: this structure guide
- `document_retrieval_precision.md`: notes about the retrieval-improvement iteration

## `tests/`

Current automated coverage is targeted rather than exhaustive.

Existing tests focus on:

- chat history sidebar behavior
- Google Drive docling-only ingestion
- retrieval precision behavior

## Runtime Flow

### Streamlit startup flow

1. `application/app.py` loads the root `.env`.
2. `presentation.app_shell.page.render_application()` initializes session state, styles, and sidebar state.
3. `presentation.chat.show()` creates or reuses `RAGService`.
4. `RAGService.load_collection()` restores a cached FAISS index or rebuilds it from the selected collections.
5. User prompts are passed into `RAGService.ask_question_with_trace()`.
6. Retrieval traces and sources are rendered back into the chat UI.

### Collection rebuild flow

1. Markdown files are read from `data/collections/`.
2. Documents are transformed into retrieval-oriented chunks.
3. Embeddings are generated locally.
4. `FAISS` index files are written under `data/cache/rag_index/`.
5. Later runs reuse the cache if the fingerprint still matches.

## Runtime Config Sources

The app now uses two config sources:

- `config/config.toml`
  - non-secret runtime tuning such as default model, embedding model, embedding device, quantization, batch size, max length, and RAG grounding knobs
- root `.env`
  - secrets and machine-specific external credentials such as:
  - `UFC_API_KEY`
  - `UFC_API_URL` (optional override)
  - `TELEGRAM_BOT_TOKEN`
  - `GOOGLE_OAUTH_CREDENTIALS_FILE`
  - scraping-related API keys such as `SCRAPING_API_KEY` / `FIRECRAWL_API_KEY`

## Important Current Behavior

- The answer LLM is not local by default; it is called through the UFC endpoint in `application/service/ufc_ollama.py`.
- The embedding model and FAISS retrieval are local.
- The first index build can be expensive because the project generates many retrieval-oriented chunks, not just plain text splits.
- Once the FAISS cache is built, later starts are much lighter as long as the collection fingerprint stays valid.

## Recommended Reading Order

If you are onboarding to the codebase, this order is the fastest:

1. `application/app.py`
2. `application/presentation/app_shell/page.py`
3. `application/presentation/chat.py`
4. `application/service/rag.py`
5. `application/service/rag_service/service.py`
6. `application/service/rag_service/service_parts/bootstrap.py`
7. `application/service/rag_service/service_parts/collection_loading.py`
8. `application/service/rag_service/service_parts/question_answering.py`
