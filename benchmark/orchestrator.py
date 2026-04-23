"""Benchmark orchestration over isolated retrieval sessions."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from .analysis import BenchmarkAnalyzer
from .questions import BenchmarkQuestion


class BenchmarkRunner:
    def __init__(
        self,
        *,
        service_cls,
        runtime_config_loader,
        retrieval_mode_command: str,
    ) -> None:
        self.service_cls = service_cls
        self.runtime_config_loader = runtime_config_loader
        self.retrieval_mode_command = retrieval_mode_command
        self._services: dict[str, object] = {}
        self._corpus_cache: dict[str, list[dict[str, object]]] = {}

    def _get_service(self, collection_name: str):
        service = self._services.get(collection_name)
        if service is not None:
            return service

        service = self.service_cls()
        service.load_collection(collection_name)
        self._services[collection_name] = service
        return service

    def _get_collection_corpus(self, collection_name: str, service) -> list[dict[str, object]]:
        cached = self._corpus_cache.get(collection_name)
        if cached is not None:
            return cached

        corpus_entries = [
            service._build_retrieval_candidate_payload(doc)
            for doc in service._get_vector_store_documents()
        ]
        self._corpus_cache[collection_name] = corpus_entries
        return corpus_entries

    def _build_assistant_history_entry(self, trace: dict[str, object]) -> dict[str, object]:
        assistant_message = {
            "role": "assistant",
            "content": str(trace.get("answer_text") or "").strip(),
            "route": str(trace.get("route") or "").strip() or "retrieval",
        }
        resolved_question = str(trace.get("resolved_question") or "").strip()
        if resolved_question:
            assistant_message["resolved_question"] = resolved_question

        matched_documents = [
            str(document_name).strip()
            for document_name in list(trace.get("matched_documents") or [])
            if str(document_name).strip()
        ]
        if matched_documents:
            assistant_message["matched_documents"] = matched_documents
        if bool(trace.get("needs_document_refinement")):
            assistant_message["needs_document_refinement"] = True
        sources = list(trace.get("sources") or [])
        if sources:
            assistant_message["sources"] = sources
        return assistant_message

    def _build_retrieval_history(self, service) -> list[dict[str, object]]:
        transition_trace = service.ask_question_with_trace(self.retrieval_mode_command, [])
        return [
            {"role": "user", "content": self.retrieval_mode_command},
            self._build_assistant_history_entry(transition_trace),
        ]

    def _analyze_question(
        self,
        question: BenchmarkQuestion,
        trace: dict[str, object],
        corpus_entries: list[dict[str, object]],
        service,
    ) -> dict[str, object]:
        analyzer = BenchmarkAnalyzer(
            normalize_text=service._normalize_identifier,
            tokenize_text=service._tokenize_search_text,
        )
        return analyzer.build_question_result(question, trace, corpus_entries)

    def run(
        self,
        questions: list[BenchmarkQuestion],
        *,
        questions_path: Path,
    ) -> dict[str, object]:
        generated_at = datetime.now(timezone.utc)
        run_id = generated_at.strftime("%Y%m%dT%H%M%SZ")
        runtime_config = self.runtime_config_loader()
        config_snapshot = asdict(runtime_config) if is_dataclass(runtime_config) else dict(runtime_config)
        results: list[dict[str, object]] = []
        collections = sorted({question.collection for question in questions})

        for question in questions:
            service = self._get_service(question.collection)
            service.last_retrieval_focus = None
            history = self._build_retrieval_history(service)
            trace = service.ask_question_with_diagnostics(question.question, history)
            corpus_entries = self._get_collection_corpus(question.collection, service)
            results.append(self._analyze_question(question, trace, corpus_entries, service))

        failure_counts = Counter(
            str((result.get("failure") or {}).get("classification") or "unknown")
            for result in results
        )
        grounding_counts = Counter(
            str((result.get("grounding") or {}).get("grounding_status") or "unknown")
            for result in results
        )
        abstained_count = sum(
            1 for result in results if bool((result.get("grounding") or {}).get("abstained"))
        )

        return {
            "run_id": run_id,
            "generated_at": generated_at.isoformat(),
            "questions_file": str(questions_path),
            "collections": collections,
            "config_snapshot": config_snapshot,
            "failure_counts": dict(failure_counts),
            "grounding_counts": dict(grounding_counts),
            "abstained_count": abstained_count,
            "results": results,
        }
