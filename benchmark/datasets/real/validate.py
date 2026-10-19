"""Validate annotations against local text only; never run RAG or load models."""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys


DATASET = Path(__file__).resolve().parent
ROOT = DATASET.parents[2]
EXPECTED_COUNTS = {
    "single-document factual": 10,
    "entity lookup": 8,
    "cross-document": 10,
    "multi-hop": 10,
    "list/aggregation": 8,
    "summary": 6,
    "spreadsheet/table": 8,
    "unanswerable": 10,
    "follow-up conversational": 10,
}


def normalize(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", type=Path,
        default=ROOT / "data/collections/uploaded_files",
    )
    args = parser.parse_args()
    questions = json.loads((DATASET / "questions.json").read_text())
    evidence = json.loads((DATASET / "evidence.json").read_text())
    errors: list[str] = []
    counts = Counter(item["category"] for item in questions)
    if dict(counts) != EXPECTED_COUNTS:
        errors.append(f"Unexpected category counts: {dict(counts)}")
    if len({item["id"] for item in questions}) != len(questions):
        errors.append("Duplicate question IDs")
    if len({normalize(item["question"]).casefold() for item in questions}) != len(questions):
        errors.append("Duplicate question texts")

    used_evidence: set[str] = set()
    for item in questions:
        case_id = item["id"]
        for key in ("id", "collection", "category", "question", "expected_answer"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{case_id}: missing {key}")
        metadata = item["metadata"]
        if metadata.get("difficulty") not in {"normal", "critical"}:
            errors.append(f"{case_id}: invalid difficulty")
        if not metadata.get("family") or not metadata.get("required_facts"):
            errors.append(f"{case_id}: missing family or answer rubric")
        refs = metadata.get("evidence_ids", [])
        context_refs = metadata.get("context_evidence_ids", [])
        used_evidence.update(refs + context_refs)
        unknown = set(refs + context_refs) - evidence.keys()
        if unknown:
            errors.append(f"{case_id}: unknown evidence {unknown}")
        if item["category"] == "unanswerable":
            if refs or not context_refs or not metadata.get("absence_scope"):
                errors.append(f"{case_id}: missing absence annotation or false positive evidence")
            if metadata.get("expected_behavior") not in {"abstain", "clarify"}:
                errors.append(f"{case_id}: invalid expected behavior")
        elif not refs:
            errors.append(f"{case_id}: answerable case without evidence")
        if item["category"] == "multi-hop":
            steps = metadata.get("reasoning_steps", [])
            if len(steps) < 2 or len(set(refs)) < 2:
                errors.append(f"{case_id}: multi-hop needs distinct evidence and steps")
            step_refs = set()
            for step in steps:
                if not step.get("fact") or not step.get("evidence_ids"):
                    errors.append(f"{case_id}: incomplete reasoning step")
                step_refs.update(step.get("evidence_ids", []))
            if step_refs != set(refs):
                errors.append(f"{case_id}: evidence/steps mismatch")
        if item["category"] == "cross-document":
            docs = {evidence[key]["document"] for key in refs if key in evidence}
            if len(docs) < 2:
                errors.append(f"{case_id}: cross-document needs two documents")
        if item["category"] == "follow-up conversational":
            history = metadata.get("history", [])
            if len(history) < 2 or any(
                turn.get("role") not in {"user", "assistant"} or not turn.get("content")
                for turn in history
            ):
                errors.append(f"{case_id}: invalid fixed conversation history")
        calculation = metadata.get("calculation")
        if calculation:
            values = [Decimal(str(value)) for value in calculation["operands"]]
            if calculation["operator"] == "sum":
                actual = sum(values)
            elif calculation["operator"] == "subtract" and len(values) == 2:
                actual = values[0] - values[1]
            else:
                errors.append(f"{case_id}: invalid arithmetic operator")
                continue
            if actual != Decimal(str(calculation["result"])):
                errors.append(f"{case_id}: incorrect annotated arithmetic")

    if used_evidence != evidence.keys():
        errors.append(f"Unused evidence: {evidence.keys() - used_evidence}")
    documents = {entry["document"] for entry in evidence.values()}
    texts = {}
    for document in sorted(documents):
        path = args.corpus / document
        if not path.is_file():
            errors.append(f"Missing document: {document}")
        else:
            texts[document] = normalize(path.read_text())
    for key, entry in evidence.items():
        text = texts.get(entry["document"], "")
        quote = normalize(entry["quote"])
        if not quote or quote not in text:
            errors.append(f"{key}: quote not found in {entry['document']}")
        elif text.count(quote) != 1:
            errors.append(f"{key}: ambiguous quote; expand its context")

    manifest_path = DATASET / "manifest.json"
    if not manifest_path.is_file():
        errors.append("Missing manifest.json")
    else:
        manifest = json.loads(manifest_path.read_text())
        actual_files = {path.name for path in args.corpus.glob("*.md")}
        if actual_files != manifest["documents"].keys():
            errors.append("Corpus file inventory differs from frozen manifest")
        for name, expected_hash in manifest["documents"].items():
            path = args.corpus / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                errors.append(f"Corpus fingerprint mismatch: {name}")
        for name, expected_hash in manifest["annotations"].items():
            if hashlib.sha256((DATASET / name).read_bytes()).hexdigest() != expected_hash:
                errors.append(f"Annotation fingerprint mismatch: {name}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps({
        "validation": "annotations_only_no_inference",
        "questions": len(questions),
        "categories": dict(counts),
        "evidence_anchors": len(evidence),
        "annotated_documents": len(documents),
        "corpus_documents": len(manifest["documents"]),
        "difficulty": dict(Counter(item["metadata"]["difficulty"] for item in questions)),
        "legacy_cases": sum("legacy_case" in item["metadata"] for item in questions),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
