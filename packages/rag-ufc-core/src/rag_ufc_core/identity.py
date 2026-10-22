"""Deterministic identity of the effective RAG pipeline.

A package version alone does not identify a pipeline: the same code behaves
differently with another model, retrieval parameter or index representation.
The identity separates

* what is fixed by a core release (source fingerprint, pipeline id, index format),
* what the host configures (``pipeline_config``: every setting that changes results),
* what only exists at runtime (the loaded index fingerprint and encoder identity).

Endpoints, credential variable names, timeouts and hardware placement are
deployment details: they never enter the signature, so diagnostics can expose it.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path

IDENTITY_VERSION = "rag_ufc_core.pipeline_identity.v1"
# The orchestrated pipeline applications run: planning, multi-hop hybrid retrieval,
# reranking, evidence coverage, generation, verification and source focus (RAGFlow).
PIPELINE_ID = "rag_v2.agentic_flow"
# The searchable text is the chunk text produced by Documents.build_document_chunks,
# without enrichment. Research representations (for example Track B E04 identity_v2)
# must declare their own id; an index built with another representation is incompatible.
REPRESENTATION_ID = "chunk_text_v1"

OPERATIONAL_LLM_FIELDS = {"timeout_seconds"}
OPERATIONAL_PROVIDER_FIELDS = {"base_url", "api_url", "api_key_env"}
OPERATIONAL_RETRIEVAL_FIELDS = {
    "device", "batch_size", "subset_cache_mb", "embedding_ollama_base_url", "embedding_timeout_seconds",
}


def canonical_hash(value) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def core_source_fingerprint() -> str:
    """SHA-256 over the installed package's Python sources (relative path + bytes).

    Identical for an editable checkout and a wheel built from the same sources, so an
    application can prove it runs the code a release was approved for.
    """
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py"), key=lambda p: p.relative_to(root).as_posix()):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def chunker_id(retrieval) -> str:
    # Same naming Engine.load_collection uses inside the index fingerprint.
    if retrieval.chunking_strategy == "legacy":
        return "structural_offsets_v3_heading_context"
    return retrieval.chunking_strategy


def pipeline_config(settings) -> dict:
    """Result-affecting settings only, restricted to the providers actually used."""
    llm = settings.llm.model_dump()
    active = {llm["provider"], *(role["provider"] for role in llm["roles"].values())}
    providers = {
        name: {key: value for key, value in options.items() if key not in OPERATIONAL_PROVIDER_FIELDS}
        for name, options in llm["providers"].items() if name in active
    }
    llm = {key: value for key, value in llm.items() if key not in OPERATIONAL_LLM_FIELDS}
    llm["providers"] = providers
    retrieval = {
        key: value for key, value in settings.retrieval.model_dump().items()
        if key not in OPERATIONAL_RETRIEVAL_FIELDS
    }
    return {"llm": llm, "retrieval": retrieval}


def model_identities(settings) -> dict:
    llm, retrieval = settings.llm, settings.retrieval
    spark = llm.providers.get("spark", {}) if "spark" in {llm.provider, *(r.provider for r in llm.roles.values())} else {}
    embedding = (
        {"provider": "ollama", "model": retrieval.embedding_ollama_model}
        if retrieval.embedding_provider == "ollama"
        else {"provider": "flagembedding", "model": retrieval.embedding_model}
    )
    return {
        "generation": {"provider": llm.provider, "model": llm.model,
                       "roles": {name: role.model_dump() for name, role in sorted(llm.roles.items())}},
        "embedding": embedding,
        "reranker": {"model": retrieval.reranker_model},
        # Declared names only: revisions are resolved from local caches at runtime.
        "tokenizers": {"generation": spark.get("tokenizer"), "retrieval": None},
    }


def pipeline_identity(settings, *, index_diagnostics=None) -> dict:
    from . import __version__
    from .rag.v2.Cache import FORMAT_VERSION

    config = pipeline_config(settings)
    config_hash = canonical_hash(config)
    index_format = {"format_version": FORMAT_VERSION, "representation_id": REPRESENTATION_ID,
                    "chunker": chunker_id(settings.retrieval)}
    static = {
        "identity_version": IDENTITY_VERSION,
        "pipeline_id": PIPELINE_ID,
        "core_version": __version__,
        "core_source_fingerprint": core_source_fingerprint(),
        "pipeline_config_hash": config_hash,
        "index_format": index_format,
    }
    runtime = None
    if index_diagnostics:
        encoder = index_diagnostics.get("encoder")
        runtime = {"index_fingerprint": index_diagnostics.get("fingerprint"), "encoder": encoder}
    return {
        **static,
        "pipeline_signature": canonical_hash(static),
        "models": model_identities(settings),
        # Prompts are code in this core; their identity is the source fingerprint.
        "prompt_set": {"location": "embedded_in_core_source", "identity": static["core_source_fingerprint"]},
        "pipeline_config": config,
        "index": runtime,
    }


def diff(expected, actual, prefix="") -> list[dict]:
    """Flattened differences between two JSON-like values, for divergence reports."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        changes = []
        for key in sorted(set(expected) | set(actual), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in actual:
                changes.append({"path": path, "expected": expected[key], "actual": None, "change": "missing"})
            elif key not in expected:
                changes.append({"path": path, "expected": None, "actual": actual[key], "change": "unexpected"})
            else:
                changes.extend(diff(expected[key], actual[key], path))
        return changes
    if expected != actual:
        return [{"path": prefix, "expected": expected, "actual": actual, "change": "different"}]
    return []
