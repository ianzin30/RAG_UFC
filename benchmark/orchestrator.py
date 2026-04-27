"""Benchmark orchestration over isolated retrieval sessions."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .analysis import BenchmarkAnalyzer
from .questions import BenchmarkQuestion


BenchmarkProgressCallback = Callable[[dict[str, object]], None]

ALLOWED_AGENT_CORRECTNESS = {"correct", "partially_correct", "incorrect", "abstained"}
ALLOWED_AGENT_GROUNDING = {"grounded", "weakly_grounded", "unsupported"}
ALLOWED_AGENT_FAILURES = {
    "no_failure",
    "retrieval_failure",
    "selection_failure",
    "generation_failure",
    "document_resolution_failure",
    "benchmark_data_mismatch",
}
ALLOWED_AGENT_SUPPORT = {"direct", "partial", "none"}


class BenchmarkRunner:
    def __init__(
        self,
        *,
        service_cls,
        runtime_config_loader,
        retrieval_mode_command: str,
        progress_callback: BenchmarkProgressCallback | None = None,
        progress_context: dict[str, object] | None = None,
    ) -> None:
        self.service_cls = service_cls
        self.runtime_config_loader = runtime_config_loader
        self.retrieval_mode_command = retrieval_mode_command
        self.progress_callback = progress_callback
        self.progress_context = dict(progress_context or {})
        self._services: dict[str, object] = {}
        self._corpus_cache: dict[str, list[dict[str, object]]] = {}

    def _emit_progress(self, event: dict[str, object]) -> None:
        if self.progress_callback is None:
            return
        payload = dict(event)
        payload["run_context"] = dict(self.progress_context)
        payload.update(self.progress_context)
        self.progress_callback(payload)

    def _emit_question_progress(
        self,
        *,
        event: str,
        question: BenchmarkQuestion,
        question_index: int,
        question_total: int,
    ) -> None:
        if self.progress_callback is None:
            return

        self._emit_progress({
            "event": event,
            "question_index": question_index,
            "question_total": question_total,
            "question_id": question.normalized_id,
            "collection": question.collection,
        })

    def _get_service(self, collection_name: str):
        service = self._services.get(collection_name)
        if service is not None:
            return service

        service = self.service_cls()
        if self.progress_callback is not None:
            setattr(service, "_benchmark_progress_callback", self._emit_progress)
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

    def _build_deterministic_evaluation_snapshot(self, result: dict[str, object]) -> dict[str, object]:
        retrieval = dict(result.get("retrieval") or {})
        return {
            "auto_correctness": result.get("auto_correctness"),
            "failure": copy.deepcopy(result.get("failure") or {}),
            "grounding": copy.deepcopy(result.get("grounding") or {}),
            "retrieval_metrics": copy.deepcopy(retrieval.get("metrics") or {}),
        }

    def _build_agent_grading_payload(
        self,
        question: BenchmarkQuestion,
        result: dict[str, object],
    ) -> dict[str, object]:
        retrieval = dict(result.get("retrieval") or {})
        generation = dict(result.get("question_data") or {})
        grounding = dict(result.get("grounding") or {})
        failure = dict(result.get("failure") or {})
        candidate_catalog = dict(retrieval.get("candidate_catalog") or {})
        selected_ids = list(((retrieval.get("stages") or {}).get("selected_context") or {}).get("candidate_ids") or [])
        selected_context = []
        for candidate_id in selected_ids[:10]:
            candidate = dict(candidate_catalog.get(candidate_id) or {})
            if not candidate:
                continue
            selected_context.append(
                {
                    "candidate_id": candidate_id,
                    "document_name": candidate.get("document_name"),
                    "chunk_kind": candidate.get("chunk_kind"),
                    "section_title": candidate.get("section_title"),
                    "text": str(candidate.get("text") or "")[:1400],
                }
            )

        return {
            "question_id": question.normalized_id,
            "collection": question.collection,
            "question": question.question,
            "expected_answer": question.expected_answer,
            "accepted_answers": list(question.accepted_answers),
            "source_document": question.source_document,
            "generated_answer": generation.get("generated_answer"),
            "selected_context": selected_context,
            "answer_context": str(retrieval.get("answer_context") or "")[:4000],
            "deterministic_retrieval_metrics": retrieval.get("metrics") or {},
            "deterministic_grounding": grounding,
            "deterministic_failure": failure,
            "deterministic_failure_notes": list(failure.get("notes") or []),
        }

    def _fallback_agent_grading(self, reason: str) -> dict[str, object]:
        return {
            "status": "fallback",
            "reason": reason,
        }

    def _normalize_agent_grading_result(
        self,
        raw_grading: object,
    ) -> dict[str, object]:
        if not isinstance(raw_grading, dict):
            return self._fallback_agent_grading("missing_agent_grading")

        status = str(raw_grading.get("status") or "").strip()
        if status != "graded":
            fallback = dict(raw_grading)
            fallback["status"] = "fallback"
            fallback.setdefault("reason", "agent_grading_unavailable")
            return fallback

        parsed = raw_grading.get("parsed")
        if not isinstance(parsed, dict):
            parsed = raw_grading

        correctness = str(parsed.get("correctness") or "").strip()
        grounding_status = str(parsed.get("grounding_status") or "").strip()
        failure_classification = str(parsed.get("failure_classification") or "").strip()
        evidence_support = str(parsed.get("evidence_support") or "").strip()
        try:
            confidence = float(parsed.get("confidence"))
        except (TypeError, ValueError):
            confidence = -1.0
        rationale = str(parsed.get("rationale") or "").strip()

        if (
            correctness not in ALLOWED_AGENT_CORRECTNESS
            or grounding_status not in ALLOWED_AGENT_GROUNDING
            or failure_classification not in ALLOWED_AGENT_FAILURES
            or evidence_support not in ALLOWED_AGENT_SUPPORT
            or not (0.0 <= confidence <= 1.0)
        ):
            fallback = dict(raw_grading)
            fallback["status"] = "fallback"
            fallback.setdefault("reason", "invalid_agent_grading_payload")
            return fallback

        return {
            "status": "graded",
            "correctness": correctness,
            "grounding_status": grounding_status,
            "failure_classification": failure_classification,
            "evidence_support": evidence_support,
            "confidence": round(confidence, 4),
            "rationale": rationale,
            "raw_response": raw_grading.get("raw_response"),
            "parsed": dict(parsed),
        }

    def _apply_agent_grading(
        self,
        question: BenchmarkQuestion,
        result: dict[str, object],
        service,
    ) -> dict[str, object]:
        enriched_result = dict(result)
        enriched_result["deterministic_evaluation"] = self._build_deterministic_evaluation_snapshot(result)

        grader = getattr(service, "_invoke_benchmark_grading_agent", None)
        if callable(grader):
            try:
                raw_grading = grader(self._build_agent_grading_payload(question, result))
            except Exception as exc:
                raw_grading = self._fallback_agent_grading(f"agent_grading_error: {exc}")
        else:
            raw_grading = self._fallback_agent_grading("service_has_no_benchmark_grading_agent")

        agent_grading = self._normalize_agent_grading_result(raw_grading)
        enriched_result["agent_grading"] = agent_grading
        if agent_grading.get("status") != "graded":
            return enriched_result

        failure = dict(enriched_result.get("failure") or {})
        rationale = str(agent_grading.get("rationale") or "").strip()
        failure["classification"] = str(agent_grading["failure_classification"])
        failure["notes"] = [rationale] if rationale else ["Agent benchmark grading supplied the official verdict."]
        enriched_result["failure"] = failure

        grounding = dict(enriched_result.get("grounding") or {})
        grounding["grounding_status"] = str(agent_grading["grounding_status"])
        grounding["agent_confidence"] = float(agent_grading["confidence"])
        grounding["agent_evidence_support"] = str(agent_grading["evidence_support"])
        enriched_result["grounding"] = grounding
        enriched_result["auto_correctness"] = str(agent_grading["correctness"])
        return enriched_result

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

        question_total = len(questions)
        for question_index, question in enumerate(questions, start=1):
            service = self._get_service(question.collection)
            self._emit_question_progress(
                event="question_started",
                question=question,
                question_index=question_index,
                question_total=question_total,
            )
            service.last_retrieval_focus = None
            history = self._build_retrieval_history(service)
            trace = service.ask_question_with_diagnostics(question.question, history)
            corpus_entries = self._get_collection_corpus(question.collection, service)
            deterministic_result = self._analyze_question(question, trace, corpus_entries, service)
            results.append(self._apply_agent_grading(question, deterministic_result, service))
            self._emit_question_progress(
                event="question_completed",
                question=question,
                question_index=question_index,
                question_total=question_total,
            )

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
