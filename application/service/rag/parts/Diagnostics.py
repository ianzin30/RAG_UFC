"""Diagnostics helpers for benchmark-oriented retrieval tracing."""
# Simple: Capture retrieval stages without changing the main answer flow

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re


class RAGServiceDiagnosticsMixin:
    def _build_empty_retrieval_diagnostics_state(self) -> dict[str, object]:
        return {
            "retrieval_intent": None,
            "target_document_name": None,
            "evidence_score": 0.0,
            "abstained": False,
            "answer_context": "",
            "prompt_text": "",
            "raw_llm_response": "",
            "answer_shape": None,
            "explicit_answer_candidates": [],
            "consensus_dominant_candidate": None,
            "candidate_consensus_details": [],
            "selected_evidence_spans": [],
            "focused_evidence_context_built": False,
            "answer_matches_top_evidence_span": None,
            "answer_ignored_top_evidence_span": False,
            "answer_repair_applied": False,
            "answer_repair_reason": None,
            "final_answer_origin": "llm",
            "retrieval_stages": {},
            "stage_order": [],
            "candidate_catalog": {},
        }

    def _begin_retrieval_diagnostics_capture(self) -> None:
        self._retrieval_diagnostics_enabled = True
        self._retrieval_diagnostics_state = self._build_empty_retrieval_diagnostics_state()

    def _finish_retrieval_diagnostics_capture(self) -> dict[str, object]:
        state = copy.deepcopy(
            self._retrieval_diagnostics_state or self._build_empty_retrieval_diagnostics_state()
        )
        self._retrieval_diagnostics_enabled = False
        self._retrieval_diagnostics_state = None
        return state

    def _is_retrieval_diagnostics_enabled(self) -> bool:
        return bool(
            getattr(self, "_retrieval_diagnostics_enabled", False)
            and isinstance(getattr(self, "_retrieval_diagnostics_state", None), dict)
        )

    def _update_retrieval_diagnostics_summary(self, **values: object) -> None:
        if not self._is_retrieval_diagnostics_enabled():
            return

        state = self._retrieval_diagnostics_state
        for key, value in values.items():
            if key not in state:
                continue
            state[key] = value

    def _coerce_diagnostic_metadata_values(self, raw_value: object) -> list[str]:
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str) and raw_value.strip():
            return [raw_value.strip()]
        return []

    def _get_retrieval_candidate_id(self, doc) -> str:
        metadata = getattr(doc, "metadata", {}) or {}
        fingerprint = "\x1f".join(
            [
                str(metadata.get("document_name") or "").strip(),
                str(metadata.get("chunk_kind") or "").strip(),
                str(metadata.get("chunk_order") if metadata.get("chunk_order") is not None else ""),
                str(metadata.get("section_title") or metadata.get("sheet_name") or "").strip(),
                re.sub(r"\s+", " ", getattr(doc, "page_content", "") or "").strip(),
            ]
        )
        digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()
        return f"cand_{digest[:16]}"

    def _build_retrieval_candidate_payload(
        self,
        doc,
        *,
        priority_score: int | None = None,
        priority_components: dict[str, int] | None = None,
    ) -> dict[str, object]:
        metadata = getattr(doc, "metadata", {}) or {}
        text = getattr(doc, "page_content", "") or ""
        source = str(metadata.get("source") or "").strip()
        excerpt = re.sub(r"\s+", " ", text).strip()
        if len(excerpt) > 240:
            excerpt = f"{excerpt[:237].rstrip()}..."

        return {
            "candidate_id": self._get_retrieval_candidate_id(doc),
            "document_name": str(metadata.get("document_name") or "").strip() or "documento",
            "source": source or None,
            "source_name": Path(source).name if source else None,
            "chunk_kind": str(metadata.get("chunk_kind") or "text").strip() or "text",
            "chunk_order": metadata.get("chunk_order")
            if isinstance(metadata.get("chunk_order"), int)
            else None,
            "section_title": (
                str(metadata.get("section_title") or metadata.get("sheet_name") or "").strip() or None
            ),
            "excerpt": excerpt,
            "text": text,
            "priority_score": int(priority_score) if priority_score is not None else None,
            "priority_score_components": {
                str(key): int(value)
                for key, value in dict(priority_components or {}).items()
                if isinstance(value, (int, float))
            }
            or None,
            "entity_names": self._coerce_diagnostic_metadata_values(metadata.get("entity_names")),
            "date_values": self._coerce_diagnostic_metadata_values(metadata.get("date_values")),
            "money_values": self._coerce_diagnostic_metadata_values(metadata.get("money_values")),
            "labeled_facts": self._coerce_diagnostic_metadata_values(
                metadata.get("labeled_facts") or metadata.get("fact_lines")
            ),
        }

    def _register_retrieval_candidate(
        self,
        doc,
        *,
        priority_score: int | None = None,
        priority_components: dict[str, int] | None = None,
    ) -> str:
        candidate = self._build_retrieval_candidate_payload(
            doc,
            priority_score=priority_score,
            priority_components=priority_components,
        )
        candidate_id = str(candidate["candidate_id"])
        if not self._is_retrieval_diagnostics_enabled():
            return candidate_id

        catalog = self._retrieval_diagnostics_state["candidate_catalog"]
        existing = catalog.get(candidate_id)
        if existing is None:
            catalog[candidate_id] = candidate
            return candidate_id

        if priority_score is not None:
            existing["priority_score"] = int(priority_score)
        if priority_components:
            existing["priority_score_components"] = {
                str(key): int(value)
                for key, value in dict(priority_components).items()
                if isinstance(value, (int, float))
            } or None
        return candidate_id

    def _record_retrieval_stage(
        self,
        stage_name: str,
        docs,
        *,
        priority_score_resolver=None,
        priority_breakdown_resolver=None,
    ) -> None:
        if not self._is_retrieval_diagnostics_enabled():
            return

        compact_stage_name = str(stage_name or "").strip()
        if not compact_stage_name:
            return

        state = self._retrieval_diagnostics_state
        if compact_stage_name not in state["retrieval_stages"]:
            state["retrieval_stages"][compact_stage_name] = {"candidate_ids": []}
            state["stage_order"].append(compact_stage_name)

        stage_payload = state["retrieval_stages"][compact_stage_name]
        seen = set(stage_payload["candidate_ids"])
        for doc in docs or []:
            priority_score = priority_score_resolver(doc) if priority_score_resolver is not None else None
            priority_components = (
                priority_breakdown_resolver(doc)
                if priority_breakdown_resolver is not None
                else None
            )
            candidate_id = self._register_retrieval_candidate(
                doc,
                priority_score=priority_score,
                priority_components=priority_components,
            )
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            stage_payload["candidate_ids"].append(candidate_id)
