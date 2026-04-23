"""Benchmark diagnostics analysis and failure classification."""

from __future__ import annotations

from typing import Callable

from .questions import BenchmarkQuestion


NormalizeFn = Callable[[str], str]
TokenizeFn = Callable[[str], list[str]]


class BenchmarkAnalyzer:
    def __init__(self, normalize_text: NormalizeFn, tokenize_text: TokenizeFn) -> None:
        self.normalize_text = normalize_text
        self.tokenize_text = tokenize_text

    def _collect_expected_variants(self, question: BenchmarkQuestion) -> list[str]:
        variants: list[str] = []
        seen: set[str] = set()
        for raw_value in [question.expected_answer, *list(question.accepted_answers)]:
            compact = str(raw_value or "").strip()
            if not compact:
                continue
            normalized = self.normalize_text(compact)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            variants.append(compact)
        return variants

    def _candidate_support_level(self, candidate: dict[str, object], variants: list[str]) -> str:
        combined_parts = [
            str(candidate.get("text") or ""),
            *list(candidate.get("entity_names") or []),
            *list(candidate.get("date_values") or []),
            *list(candidate.get("money_values") or []),
            *list(candidate.get("labeled_facts") or []),
        ]
        combined_text = " ".join(str(part).strip() for part in combined_parts if str(part).strip())
        normalized_text = self.normalize_text(combined_text)
        if not normalized_text:
            return "not_found"

        for variant in variants:
            normalized_variant = self.normalize_text(variant)
            if normalized_variant and normalized_variant in normalized_text:
                return "explicit"

        for variant in variants:
            variant_tokens = self.tokenize_text(variant)
            if variant_tokens and all(token in normalized_text for token in variant_tokens):
                return "implicit"
        return "not_found"

    def _text_support_level(self, text: str, variants: list[str]) -> str:
        pseudo_candidate = {
            "text": text,
            "entity_names": [],
            "date_values": [],
            "money_values": [],
            "labeled_facts": [],
        }
        return self._candidate_support_level(pseudo_candidate, variants)

    def _matches_source_document(self, source_document: str, candidate: dict[str, object]) -> bool:
        normalized_source = self.normalize_text(source_document)
        if not normalized_source:
            return False

        candidate_names = [
            str(candidate.get("document_name") or ""),
            str(candidate.get("source_name") or ""),
            str(candidate.get("source") or ""),
        ]
        for candidate_name in candidate_names:
            normalized_candidate = self.normalize_text(candidate_name)
            if not normalized_candidate:
                continue
            if (
                normalized_source == normalized_candidate
                or normalized_source in normalized_candidate
                or normalized_candidate in normalized_source
            ):
                return True
        return False

    def _scan_corpus(
        self,
        question: BenchmarkQuestion,
        variants: list[str],
        corpus_entries: list[dict[str, object]],
    ) -> dict[str, object]:
        source_scoped_entries = []
        if question.source_document:
            source_scoped_entries = [
                entry
                for entry in corpus_entries
                if self._matches_source_document(question.source_document, entry)
            ]

        scoped_entries = source_scoped_entries if question.source_document else corpus_entries
        relevant_hits: list[dict[str, object]] = []
        for entry in scoped_entries:
            support_level = self._candidate_support_level(entry, variants)
            if support_level == "not_found":
                continue
            relevant_hits.append(
                {
                    "candidate_id": str(entry.get("candidate_id") or ""),
                    "document_name": str(entry.get("document_name") or ""),
                    "chunk_kind": str(entry.get("chunk_kind") or ""),
                    "excerpt": str(entry.get("excerpt") or ""),
                    "match_level": support_level,
                }
            )

        if relevant_hits:
            relevant_documents = sorted({hit["document_name"] for hit in relevant_hits if hit["document_name"]})
        elif source_scoped_entries:
            relevant_documents = sorted(
                {
                    str(entry.get("document_name") or "")
                    for entry in source_scoped_entries
                    if str(entry.get("document_name") or "")
                }
            )
        else:
            relevant_documents = []

        return {
            "source_scoped_entries": source_scoped_entries,
            "relevant_hits": relevant_hits,
            "relevant_documents": relevant_documents,
        }

    def _build_stage_positions(
        self,
        stage_snapshots: dict[str, dict[str, list[str]]],
        stage_order: list[str],
    ) -> dict[str, dict[str, int]]:
        positions: dict[str, dict[str, int]] = {}
        for stage_name in stage_order:
            candidate_ids = list((stage_snapshots.get(stage_name) or {}).get("candidate_ids") or [])
            positions[stage_name] = {
                candidate_id: index + 1 for index, candidate_id in enumerate(candidate_ids)
            }
        return positions

    def _lookup_candidate(
        self,
        candidate_id: str,
        candidate_catalog: dict[str, dict[str, object]],
        corpus_lookup: dict[str, dict[str, object]],
    ) -> dict[str, object] | None:
        return candidate_catalog.get(candidate_id) or corpus_lookup.get(candidate_id)

    def _build_rank_movement(
        self,
        relevant_hits: list[dict[str, object]],
        stage_positions: dict[str, dict[str, int]],
        stage_order: list[str],
        candidate_catalog: dict[str, dict[str, object]],
        corpus_lookup: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        movement: list[dict[str, object]] = []
        seen: set[str] = set()
        for hit in relevant_hits:
            candidate_id = str(hit.get("candidate_id") or "")
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidate = self._lookup_candidate(candidate_id, candidate_catalog, corpus_lookup) or {}
            movement.append(
                {
                    "candidate_id": candidate_id,
                    "document_name": str(candidate.get("document_name") or hit.get("document_name") or ""),
                    "chunk_kind": str(candidate.get("chunk_kind") or hit.get("chunk_kind") or ""),
                    "priority_score": candidate.get("priority_score"),
                    "stage_positions": {
                        stage_name: stage_positions.get(stage_name, {}).get(candidate_id)
                        for stage_name in stage_order
                    },
                }
            )
        return movement

    def _extract_top_documents(
        self,
        prioritized_ids: list[str],
        candidate_catalog: dict[str, dict[str, object]],
        corpus_lookup: dict[str, dict[str, object]],
    ) -> list[str]:
        documents: list[str] = []
        seen: set[str] = set()
        for candidate_id in prioritized_ids:
            candidate = self._lookup_candidate(candidate_id, candidate_catalog, corpus_lookup) or {}
            document_name = str(candidate.get("document_name") or "").strip()
            if not document_name or document_name in seen:
                continue
            seen.add(document_name)
            documents.append(document_name)
            if len(documents) >= 5:
                break
        return documents

    def _extract_candidate_list(
        self,
        candidate_ids: list[str],
        candidate_catalog: dict[str, dict[str, object]],
        corpus_lookup: dict[str, dict[str, object]],
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for candidate_id in candidate_ids[:limit]:
            candidate = self._lookup_candidate(candidate_id, candidate_catalog, corpus_lookup)
            if candidate is None:
                continue
            results.append(dict(candidate))
        return results

    def _classify_failure(
        self,
        *,
        question: BenchmarkQuestion,
        trace: dict[str, object],
        relevant_hits: list[dict[str, object]],
        relevant_documents: list[str],
        stage_order: list[str],
        stage_positions: dict[str, dict[str, int]],
        prioritized_ids: list[str],
        selected_context_ids: list[str],
        retrieved_candidate_ids: set[str],
        retrieved_documents: set[str],
        answer_presence_in_evidence: str,
        generated_answer_has_expected: bool,
    ) -> tuple[str, list[str]]:
        notes: list[str] = []
        relevant_hit_ids = {
            str(hit.get("candidate_id") or "")
            for hit in relevant_hits
            if str(hit.get("candidate_id") or "")
        }
        relevant_docs_set = {document for document in relevant_documents if document}
        document_shortlist = {
            str(document_name).strip()
            for document_name in list(trace.get("document_shortlist") or [])
            if str(document_name).strip()
        }
        matched_documents = {
            str(document_name).strip()
            for document_name in list(trace.get("matched_documents") or [])
            if str(document_name).strip()
        }
        target_document_name = str(trace.get("target_document_name") or "").strip() or None
        resolver_status = str(trace.get("resolver_status") or "").strip() or "no_match"
        source_document_provided = bool(question.source_document)

        if not relevant_hits and not source_document_provided:
            notes.append("Expected answer variants were not found anywhere in the indexed corpus.")
            return "benchmark_data_mismatch", notes

        if relevant_docs_set:
            shortlist_excludes_relevant = bool(
                document_shortlist and relevant_docs_set.isdisjoint(document_shortlist)
            )
            matched_excludes_relevant = bool(
                matched_documents and relevant_docs_set.isdisjoint(matched_documents)
            )
            target_excludes_relevant = bool(
                target_document_name is not None and target_document_name not in relevant_docs_set
            )
            if (
                shortlist_excludes_relevant or matched_excludes_relevant or target_excludes_relevant
            ) and relevant_docs_set.isdisjoint(retrieved_documents):
                notes.append(
                    "Relevant document evidence existed in the corpus but was excluded before retrieval."
                )
                notes.append(f"Resolver status: {resolver_status}")
                return "document_resolution_failure", notes

        if relevant_hit_ids and relevant_hit_ids.isdisjoint(retrieved_candidate_ids):
            if relevant_docs_set and relevant_docs_set & retrieved_documents:
                notes.append(
                    "The right document was retrieved, but the chunk containing the expected answer never surfaced."
                )
                return "chunking_failure", notes
            notes.append("Relevant evidence never appeared in the retrieval stages.")
            return "semantic_search_failure", notes

        if relevant_hit_ids and relevant_hit_ids.isdisjoint(set(selected_context_ids)):
            prioritized_positions = stage_positions.get("prioritized", {})
            selected_position_cutoff = len(selected_context_ids)
            best_relevant_rank = min(
                (
                    prioritized_positions[candidate_id]
                    for candidate_id in relevant_hit_ids
                    if candidate_id in prioritized_positions
                ),
                default=None,
            )
            selected_prioritized_ranks = [
                prioritized_positions[candidate_id]
                for candidate_id in selected_context_ids
                if candidate_id in prioritized_positions
            ]
            worst_selected_rank = max(selected_prioritized_ranks, default=selected_position_cutoff)
            if best_relevant_rank is not None and best_relevant_rank > selected_position_cutoff:
                notes.append(
                    "Relevant evidence was present before context assembly but fell below the selected-context cutoff after reranking."
                )
                return "reranking_failure", notes

            if best_relevant_rank is not None and best_relevant_rank < worst_selected_rank:
                notes.append(
                    "A relevant chunk ranked above at least one selected chunk but was still omitted from the final context."
                )
                return "context_assembly_failure", notes

            selected_is_prefix = prioritized_ids[: len(selected_context_ids)] == selected_context_ids
            if not selected_is_prefix:
                notes.append(
                    "Relevant evidence remained in prioritized results but was filtered out during context assembly."
                )
                return "context_assembly_failure", notes

            notes.append(
                "Relevant evidence was ranked too low after prioritization to enter the final context."
            )
            return "reranking_failure", notes

        if answer_presence_in_evidence == "explicit" and not generated_answer_has_expected:
            notes.append(
                "The selected context explicitly contained the expected answer, but the generated answer did not use it."
            )
            return "generation_failure", notes

        if bool(trace.get("abstained")):
            notes.append("The system abstained because retrieved evidence remained weak.")
        else:
            notes.append("Retrieved evidence and the final answer path are aligned.")
        return "no_failure", notes

    def build_question_result(
        self,
        question: BenchmarkQuestion,
        trace: dict[str, object],
        corpus_entries: list[dict[str, object]],
    ) -> dict[str, object]:
        expected_variants = self._collect_expected_variants(question)
        candidate_catalog = {
            str(candidate_id): dict(payload)
            for candidate_id, payload in dict(trace.get("candidate_catalog") or {}).items()
        }
        corpus_lookup = {
            str(entry.get("candidate_id") or ""): dict(entry)
            for entry in corpus_entries
            if str(entry.get("candidate_id") or "")
        }
        stage_snapshots = {
            str(stage_name): {"candidate_ids": list(stage_payload.get("candidate_ids") or [])}
            for stage_name, stage_payload in dict(trace.get("retrieval_stages") or {}).items()
        }
        stage_order = list(trace.get("retrieval_stage_order") or stage_snapshots.keys())
        stage_positions = self._build_stage_positions(stage_snapshots, stage_order)
        prioritized_ids = list((stage_snapshots.get("prioritized") or {}).get("candidate_ids") or [])
        selected_context_ids = list(
            (stage_snapshots.get("selected_context") or {}).get("candidate_ids") or []
        )
        retrieved_candidate_ids = {
            candidate_id
            for stage_name in stage_order
            for candidate_id in list((stage_snapshots.get(stage_name) or {}).get("candidate_ids") or [])
        }
        retrieved_documents = {
            str(
                (
                    self._lookup_candidate(candidate_id, candidate_catalog, corpus_lookup) or {}
                ).get("document_name")
                or ""
            ).strip()
            for candidate_id in retrieved_candidate_ids
        }
        retrieved_documents.discard("")

        corpus_scan = self._scan_corpus(question, expected_variants, corpus_entries)
        relevant_hits = list(corpus_scan["relevant_hits"])
        relevant_documents = list(corpus_scan["relevant_documents"])
        selected_context_entries = self._extract_candidate_list(
            selected_context_ids,
            candidate_catalog,
            corpus_lookup,
            limit=max(len(selected_context_ids), 8),
        )
        answer_presence_in_evidence = "not_found"
        for candidate in selected_context_entries:
            support_level = self._candidate_support_level(candidate, expected_variants)
            if support_level == "explicit":
                answer_presence_in_evidence = "explicit"
                break
            if support_level == "implicit":
                answer_presence_in_evidence = "implicit"

        generated_answer = str(trace.get("answer_text") or "").strip()
        generated_answer_support = self._text_support_level(generated_answer, expected_variants)
        generated_answer_has_expected = generated_answer_support in {"explicit", "implicit"}
        abstained = bool(trace.get("abstained"))
        retrieval_confidence = float(trace.get("evidence_score") or 0.0)

        if answer_presence_in_evidence == "explicit" and generated_answer_has_expected:
            grounding_status = "grounded"
        elif answer_presence_in_evidence in {"explicit", "implicit"}:
            grounding_status = "weakly_grounded"
        else:
            grounding_status = "unsupported"

        if abstained:
            answer_confidence = 0.0
        elif grounding_status == "grounded":
            answer_confidence = min(1.0, retrieval_confidence + 0.20)
        elif grounding_status == "weakly_grounded":
            answer_confidence = min(1.0, retrieval_confidence + 0.05)
        else:
            answer_confidence = max(0.0, retrieval_confidence - 0.25)

        failure_classification, failure_notes = self._classify_failure(
            question=question,
            trace=trace,
            relevant_hits=relevant_hits,
            relevant_documents=relevant_documents,
            stage_order=stage_order,
            stage_positions=stage_positions,
            prioritized_ids=prioritized_ids,
            selected_context_ids=selected_context_ids,
            retrieved_candidate_ids=retrieved_candidate_ids,
            retrieved_documents=retrieved_documents,
            answer_presence_in_evidence=answer_presence_in_evidence,
            generated_answer_has_expected=generated_answer_has_expected,
        )

        missed_relevant_hits: list[dict[str, object]] = []
        for hit in relevant_hits:
            candidate_id = str(hit.get("candidate_id") or "")
            stage_presence = {
                stage_name: stage_positions.get(stage_name, {}).get(candidate_id)
                for stage_name in stage_order
            }
            if stage_presence.get("selected_context") is not None:
                continue
            retrieval_gap = "not_retrieved"
            if any(position is not None for position in stage_presence.values()):
                retrieval_gap = "not_selected"
            missed_relevant_hits.append(
                {
                    **hit,
                    "retrieval_gap": retrieval_gap,
                    "stage_positions": stage_presence,
                }
            )

        rank_movement = self._build_rank_movement(
            relevant_hits,
            stage_positions,
            stage_order,
            candidate_catalog,
            corpus_lookup,
        )
        top_chunks = self._extract_candidate_list(
            prioritized_ids,
            candidate_catalog,
            corpus_lookup,
            limit=5,
        )

        return {
            "question": question.to_dict(),
            "question_data": {
                "id": question.id,
                "collection": question.collection,
                "question": question.question,
                "expected_answer": question.expected_answer,
                "generated_answer": generated_answer,
                "resolved_question": str(trace.get("resolved_question") or "").strip(),
            },
            "auto_correctness": "not_evaluated",
            "document_resolution": {
                "resolver_status": str(trace.get("resolver_status") or "no_match"),
                "resolver_confidence": float(trace.get("resolver_confidence") or 0.0),
                "resolver_selection_mode": str(trace.get("resolver_selection_mode") or "").strip() or None,
                "document_shortlist": list(trace.get("document_shortlist") or []),
                "matched_documents": list(trace.get("matched_documents") or []),
                "matched_aliases": list(trace.get("matched_aliases") or []),
                "document_scores": list(trace.get("document_scores") or []),
                "recovery_search_performed": bool(trace.get("recovery_search_performed")),
                "recovery_matched_documents": list(trace.get("recovery_matched_documents") or []),
                "extraction_diagnostics": list(trace.get("extraction_diagnostics") or []),
            },
            "retrieval": {
                "retrieval_intent": trace.get("retrieval_intent"),
                "target_document_name": trace.get("target_document_name"),
                "retrieval_confidence": retrieval_confidence,
                "evidence_score": retrieval_confidence,
                "sources": list(trace.get("sources") or []),
                "answer_context": str(trace.get("answer_context") or ""),
                "selected_evidence_spans": list(trace.get("selected_evidence_spans") or []),
                "focused_evidence_context_built": bool(trace.get("focused_evidence_context_built")),
                "stage_order": stage_order,
                "stages": stage_snapshots,
                "candidate_catalog": candidate_catalog,
                "top_documents": self._extract_top_documents(
                    prioritized_ids,
                    candidate_catalog,
                    corpus_lookup,
                ),
                "top_chunks": top_chunks,
                "rank_movement": rank_movement,
                "relevant_corpus_hits": relevant_hits,
                "missed_relevant_corpus_hits": missed_relevant_hits,
            },
            "grounding": {
                "retrieval_confidence": retrieval_confidence,
                "answer_confidence": round(answer_confidence, 4),
                "grounding_status": grounding_status,
                "answer_presence_in_evidence": answer_presence_in_evidence,
                "generated_answer_support": generated_answer_support,
                "abstained": abstained,
            },
            "generation": {
                "answer_shape": str(trace.get("answer_shape") or "").strip() or None,
                "explicit_answer_candidates": list(trace.get("explicit_answer_candidates") or []),
                "consensus_dominant_candidate": (
                    dict(trace.get("consensus_dominant_candidate") or {})
                    if isinstance(trace.get("consensus_dominant_candidate"), dict)
                    else None
                ),
                "candidate_consensus_details": list(
                    trace.get("candidate_consensus_details")
                    or trace.get("explicit_answer_candidates")
                    or []
                ),
                "answer_matches_top_evidence_span": trace.get("answer_matches_top_evidence_span"),
                "answer_ignored_top_evidence_span": bool(trace.get("answer_ignored_top_evidence_span")),
                "answer_repair_applied": bool(trace.get("answer_repair_applied")),
                "answer_repair_reason": str(trace.get("answer_repair_reason") or "").strip() or None,
                "final_answer_origin": str(trace.get("final_answer_origin") or "").strip() or "llm",
            },
            "failure": {
                "classification": failure_classification,
                "notes": failure_notes,
            },
        }
