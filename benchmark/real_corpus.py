"""Deterministic retrieval evaluation for the uploaded real collection.

This suite deliberately measures retrieval only.  Its annotations identify the
documents containing the evidence; answer quality and citation support are
validated in a separate generation run.  It is intentionally small and
auditable: every case names its expected source file rather than relying on an
LLM judge.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import time

from benchmark.bootstrap import bootstrap_python_path


# These are documents supplied in ``data/collections/uploaded_files``.  Cases
# are skipped, rather than silently scored as failures, when a future corpus
# does not contain their source document.
CASES = (
    {
        "id": "afo_coordinator",
        "category": "single-document factual",
        "question": "Quem é o coordenador na instituição do projeto AFO?",
        "documents": ("85_AFO.md",),
    },
    {
        "id": "rack_coordinator",
        "category": "entity lookup",
        "question": "Quem é o coordenador na instituição do projeto Rack Build Deployment Validation and Provisioning II?",
        "documents": ("87_RACK.md",),
    },
    {
        "id": "afo_rack_comparison",
        "category": "cross-document",
        "question": "Compare os coordenadores dos projetos AFO e RACK.",
        "documents": ("85_AFO.md", "87_RACK.md"),
    },
    {
        "id": "oauth_coordinator",
        "category": "multi-hop",
        "question": "Qual é o nome do coordenador do projeto que prevê geração de token OAuth?",
        "documents": ("85_AFO.md",),
    },
    {
        "id": "saar_products",
        "category": "list/aggregation",
        "question": "Quais produtos de armazenamento a extensão de integração do SAAR deve incluir?",
        "documents": ("88_SAAR.md",),
    },
    {
        "id": "saar_summary",
        "category": "summary",
        "question": "Resuma as melhorias e novas funcionalidades previstas para o SAAR.",
        "documents": ("88_SAAR.md",),
    },
    {
        "id": "afo_followup",
        "category": "follow-up conversational",
        "question": "E quem coordena esse projeto na instituição?",
        "history": (
            {"role": "user", "content": "Fale sobre o projeto AFO."},
            {"role": "assistant", "content": "O AFO automatiza o onboarding federado."},
        ),
        "documents": ("85_AFO.md",),
    },
    {
        "id": "afo_unanswerable",
        "category": "unanswerable",
        "question": "Qual é o CPF do coordenador do AFO?",
        "documents": (),
    },
)


def _metrics(retrieved: list[str], relevant: tuple[str, ...], k: int) -> dict:
    # Candidate retrieval is chunk-level, whereas this real-corpus annotation
    # is document-level.  A document may legitimately contribute many chunks,
    # but it must occupy only one rank for document Recall/MRR/nDCG.
    ranked_documents = list(dict.fromkeys(retrieved))
    selected = ranked_documents[:k]
    if not relevant:
        return {
            "recall_at_k": None,
            "mrr": None,
            "ndcg": None,
            "evidence_recall_at_k": None,
            "complete_evidence_recall_at_k": None,
        }
    hits = [name in selected for name in relevant]
    first = next((index for index, name in enumerate(selected, 1) if name in relevant), None)
    dcg = sum(
        1 / math.log2(index + 1)
        for index, name in enumerate(selected, 1)
        if name in relevant
    )
    ideal = sum(1 / math.log2(index + 1) for index in range(1, min(k, len(relevant)) + 1))
    return {
        "recall_at_k": sum(hits) / len(relevant),
        "mrr": 1 / first if first else 0.0,
        "ndcg": dcg / ideal if ideal else 0.0,
        "evidence_recall_at_k": sum(hits) / len(relevant),
        "complete_evidence_recall_at_k": all(hits),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="uploaded_files")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bootstrap_python_path()
    from service.RuntimeConfig import get_runtime_config

    collection_path = Path("data/collections") / args.collection
    present = {path.name for path in collection_path.glob("*.md")}
    if not present:
        raise SystemExit(f"No Markdown documents in {collection_path}")
    runnable = [case for case in CASES if set(case["documents"]).issubset(present)]
    skipped = [case["id"] for case in CASES if case not in runnable]
    config = get_runtime_config()

    from service.rag.RagService import RAGService

    service = RAGService(model_name=config.llm_model)
    service.load_collection(args.collection)
    engine = service._v2
    index = engine.load_diagnostics

    def retrieve(case):
        candidates, diagnostic = engine.retriever.search(case["question"], None, args.k)
        return [Path(engine.retriever.chunks[item["position"]].relative_path).name for item in candidates], diagnostic

    results = []
    for case in runnable:
        started = time.perf_counter()
        retrieved, diagnostics = retrieve(case)
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_documents": case["documents"],
                "retrieved_documents": retrieved,
                "metrics": _metrics(retrieved, case["documents"], args.k),
                "latency_seconds": time.perf_counter() - started,
                "diagnostics": diagnostics,
            }
        )
        print(case["id"], flush=True)
    payload = {
        "kind": "real_corpus_fixed_query_retrieval",
        "version": "v2",
        "python": platform.python_version(),
        "collection": args.collection,
        "documents_in_collection": len(present),
        "cases_run": len(results),
        "cases_skipped": skipped,
        "non_applicable_categories": ["spreadsheet/table"],
        "config": asdict(config),
        "v2_config": engine.config.model_dump(),
        "index": index,
        "results": results,
    }
    output = args.output or Path("benchmark/results") / "real_v2_retrieval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
