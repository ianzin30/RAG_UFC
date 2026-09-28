"""Auditable local-generation checks for the uploaded real collection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import time

from benchmark.bootstrap import bootstrap_python_path


CASES = (
    {
        "id": "factual",
        "question": "Quem é o coordenador na instituição do projeto AFO?",
        "expected_terms": ("Fernando Antonio Mota Trinta",),
    },
    {
        "id": "cross_document",
        "question": "Compare os coordenadores dos projetos AFO e RACK.",
        "expected_terms": ("Fernando Antonio Mota Trinta", "Paulo Antonio Leal Rego"),
    },
    {
        "id": "multi_hop",
        "question": "Qual é o nome do coordenador do projeto que prevê geração de token OAuth?",
        "expected_terms": ("Fernando Antonio Mota Trinta",),
    },
    {
        "id": "unanswerable",
        "question": "Qual é o CPF do coordenador do AFO?",
        "expected_terms": (),
    },
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--collection", default="uploaded_files")
    parser.add_argument("--case", action="append")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bootstrap_python_path()
    from service.rag.RagService import RAGService

    service = RAGService(model_name=args.model)
    service.load_collection(args.collection)
    results = []
    for case in CASES:
        if args.case and case["id"] not in args.case:
            continue
        started = time.perf_counter()
        try:
            trace = service.ask_question_with_diagnostics(case["question"])
            answer = trace["answer_text"]
            expected = case["expected_terms"]
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected_terms": expected,
                    "answer_correctness_deterministic": (
                        trace["abstained"]
                        if not expected
                        else all(term.casefold() in answer.casefold() for term in expected)
                    ),
                    "citation_support": bool(trace["claims"]) and all(
                        claim["evidence_ids"] for claim in trace["claims"]
                    ),
                    "status": trace["status"],
                    "stop_reason": trace["stop_reason"],
                    "answer": answer,
                    "claims": trace["claims"],
                    "cited_sources": trace["cited_sources"],
                    "provider_calls": trace["provider_calls"],
                }
            )
        except Exception as exc:
            failed_trace = service._v2.last_trace or {}
            results.append(
                {
                    "id": case["id"],
                    "error": str(exc),
                    "provider_calls": failed_trace.get(
                        "provider_calls", list(service._v2.providers.calls)
                    ),
                }
            )
        results[-1]["latency_seconds"] = time.perf_counter() - started
        print(case["id"], flush=True)
    payload = {
        "kind": "real_corpus_generation",
        "python": platform.python_version(),
        "collection": args.collection,
        "logical_model": service.model_name,
        "llm_config": service._v2.providers.config.model_dump(),
        "v2_config": service._v2.config.model_dump(),
        "index": service._v2.load_diagnostics,
        "results": results,
    }
    output = args.output or Path("benchmark/results") / f"real_{service.model_name.replace('/', '_').replace(':', '_')}_generation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
