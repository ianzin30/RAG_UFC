"""Reproducible V2 synthetic benchmark (retrieval-only or local generation)."""

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import tempfile
import time
from benchmark.bootstrap import bootstrap_python_path
from benchmark.synthetic import CASES, DOCUMENTS


def retrieval_metrics(texts, groups, k, corpus_texts=None):
    selected = texts[:k]
    coverage = [
        any(phrase in text for phrase in group for text in selected) for group in groups
    ]
    relevant = [
        any(phrase in text for group in groups for phrase in group) for text in selected
    ]
    first = next((i for i, value in enumerate(relevant, 1) if value), None)
    dcg = sum(1 / math.log2(i + 2) for i, value in enumerate(relevant) if value)
    total_relevant = sum(
        any(phrase in text for group in groups for phrase in group)
        for text in (corpus_texts if corpus_texts is not None else texts)
    )
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, total_relevant)))
    return {
        "recall": sum(relevant) / total_relevant if total_relevant else None,
        "evidence_recall": sum(coverage) / len(groups) if groups else None,
        "complete_evidence_recall": all(coverage) if groups else None,
        "mrr": 1 / first if first else 0,
        "ndcg": dcg / ideal if ideal else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--case", action="append")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--child-tokens", type=int, default=None)
    parser.add_argument("--max-hops", type=int, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bootstrap_python_path()
    from service.rag.RagService import RAGService
    from service.RuntimeConfig import get_runtime_config

    with tempfile.TemporaryDirectory(prefix="rag-v2-corpus-") as directory:
        root = Path(directory)
        collection = root / "synthetic"
        collection.mkdir()
        for name, text in DOCUMENTS.items():
            (collection / name).write_text(text, encoding="utf-8")
        service = RAGService(model_name=args.model)
        if args.provider:
            from service.rag.v2.Providers import ProviderRegistry

            service._v2.providers = ProviderRegistry(
                service._v2.providers.config.model_copy(
                    update={"provider": args.provider}
                )
            )
        from service.rag.v2.Config import V2Config

        tuning = service._v2.config.model_dump()
        if args.child_tokens:
            tuning["child_tokens"] = args.child_tokens
        if args.max_hops:
            tuning["max_hops"] = args.max_hops
        service._v2.config = V2Config.model_validate(tuning)
        service.collections_root = root
        service.load_collection("synthetic")
        engine = service._v2
        results = []
        for case in CASES:
            if args.case and case["id"] not in args.case:
                continue
            started = time.perf_counter()
            try:
                if args.generate:
                    trace = service.ask_question_with_diagnostics(
                        case["question"], case.get("history", [])
                    )
                    texts = [item["text"] for item in trace["evidence"]]
                else:
                    candidates, diagnostic = engine.retriever.search(
                        case["question"], None, 1
                    )
                    texts = [
                        engine.retriever.chunks[item["position"]].text
                        for item in candidates
                    ]
                    trace = {"diagnostics": diagnostic}
                result = {
                    "id": case["id"],
                    "category": case["category"],
                    "metrics": retrieval_metrics(
                        texts,
                        case["required"],
                        10,
                        [chunk.text for chunk in engine.retriever.chunks],
                    ),
                    "trace": trace,
                }
                if args.generate:
                    result["answer_correctness"] = (
                        all(
                            term.casefold() in trace["answer_text"].casefold()
                            for term in case["expected"]
                        )
                        if case["expected"]
                        else trace["abstained"]
                    )
                results.append(result)
            except Exception as exc:
                results.append(
                    {"id": case["id"], "error": str(exc), "trace": engine.last_trace}
                )
            results[-1]["latency_seconds"] = time.perf_counter() - started
            print(case["id"], "error" if "error" in results[-1] else "ok", flush=True)
        payload = {
            "kind": "generation" if args.generate else "fixed_query_retrieval",
            "python": platform.python_version(),
            "config": asdict(get_runtime_config()),
            "v2_config": engine.config.model_dump(),
            "llm_config": engine.providers.config.model_dump(),
            "index": engine.load_diagnostics,
            "results": results,
        }
        output = args.output or Path("benchmark/results") / (
            "v2_"
            + (service.model_name.replace("/", "_").replace(":", "_") if args.generate else "retrieval")
            + ".json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(output)


if __name__ == "__main__":
    main()
