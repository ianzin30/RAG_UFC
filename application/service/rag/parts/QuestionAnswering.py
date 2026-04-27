"""Question orchestration for the RAG service."""

from ..Constants import MODE_CASUAL, MODE_RETRIEVAL
from .QuestionFollowUp import RAGServiceFollowUpMixin


class RAGServiceQuestionAnsweringMixin(RAGServiceFollowUpMixin):
    def _execute_retrieval_pass(
        self,
        *,
        user_question: str,
        resolved_question: str,
        target_document_name: str | None,
        retrieval_intent: str,
        document_shortlist: list[str],
        clarification_resolution: dict[str, object] | None,
    ) -> dict[str, object]:
        docs = self._retrieve_docs(
            resolved_question,
            target_document_name,
            retrieval_intent=retrieval_intent,
            document_shortlist=document_shortlist,
        )

        clarification_options = []
        if not clarification_resolution:
            clarification_options = self._should_request_retrieval_clarification(
                user_question,
                target_document_name,
                retrieval_intent or "specific_fact",
                docs,
            )

        if len(clarification_options) > 1:
            return {
                "clarification_options": clarification_options,
                "docs": docs,
                "selected_docs": [],
                "evidence_score": 0.0,
                "sources": [],
            }

        selected_docs = self._select_docs_for_context(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
        )
        self._record_retrieval_stage("selected_context", selected_docs)
        evidence_score = self._score_retrieval_evidence(
            resolved_question,
            selected_docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            document_shortlist=document_shortlist,
        )
        sources = self._build_sources(
            selected_docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
        )
        return {
            "clarification_options": [],
            "docs": docs,
            "selected_docs": selected_docs,
            "evidence_score": evidence_score,
            "sources": sources,
        }

    def ask_question_with_trace(self, question: str, chat_history=None) -> dict[str, object]:
        if not self.retriever or not self.answer_chain or not self.small_talk_chain:
            raise Exception("No collection loaded. Please load a collection before asking questions.")

        history_text = self._format_chat_history(chat_history)
        collection_name = self.collection_name or "colecao nao identificada"
        route, mode_transition = self._resolve_requested_mode(question, chat_history)

        if mode_transition:
            return self._build_mode_transition_trace(question, route, mode_transition)
        if route == MODE_CASUAL:
            return self._build_casual_trace(question, collection_name, history_text)

        pending_refinement = self._get_pending_document_refinement(chat_history)
        refinement_resolution = self._resolve_pending_document_refinement(question, pending_refinement)
        pending_clarification = self._get_pending_retrieval_clarification()
        clarification_resolution = self._resolve_pending_retrieval_clarification(question, pending_clarification)
        locked_document_name = self._get_locked_target_document_name()

        if refinement_resolution and refinement_resolution.get("status") == "invalid_selection":
            return self._build_invalid_document_selection_trace(
                question,
                pending_refinement,
                int(refinement_resolution.get("selection_number") or 0),
            )
        if clarification_resolution and clarification_resolution.get("status") == "invalid_selection":
            return self._build_invalid_clarification_trace(
                question,
                pending_clarification,
                int(clarification_resolution.get("selection_number") or 0),
            )

        follow_up = self._resolve_pending_follow_up(
            question,
            chat_history,
            pending_refinement,
            refinement_resolution,
            pending_clarification,
            clarification_resolution,
        )
        user_question = str(follow_up["user_question"])
        retrieval_history_text = str(follow_up["retrieval_history_text"])
        retrieval_intent = follow_up["retrieval_intent"]
        matched_documents = list(follow_up["matched_documents"])
        resolver_status = str(follow_up["resolver_status"])
        resolver_candidates = list(follow_up["resolver_candidates"])
        matched_aliases = list(follow_up["matched_aliases"])
        resolver_selection_mode = str(follow_up.get("resolver_selection_mode") or "").strip() or None
        resolved_question = follow_up["resolved_question"]
        document_shortlist = list(matched_documents)
        document_scores: list[dict[str, object]] = []
        resolver_confidence = 0.0
        focus_decision = None
        focus_release_reason = None
        recovery_search_performed = False
        recovery_matched_documents: list[str] = []

        if resolved_question is None:
            force_rewrite = self.last_retrieval_focus is not None and self._is_follow_up_ambiguous(question)
            resolved_question = self._rewrite_question_for_retrieval(
                question,
                history_text,
                chat_history,
                force=force_rewrite,
            )
            scope_plan = self._plan_scope(question, resolved_question, chat_history, locked_document_name)
            focus_decision = str(scope_plan.get("focus_decision") or "").strip() or None
            focus_release_reason = str(scope_plan.get("focus_release_reason") or "").strip() or None
            resolution = self._plan_document_selection(
                question,
                resolved_question,
                chat_history,
                scope_plan,
                locked_document_name,
            )
            matched_documents = list(resolution.get("matched_documents") or [])
            resolver_status = str(resolution.get("status") or "no_match")
            resolver_candidates = list(resolution.get("resolver_candidates") or [])
            matched_aliases = list(resolution.get("matched_aliases") or [])
            document_shortlist = list(
                resolution.get("document_shortlist")
                or matched_documents
                or []
            )
            document_scores = list(resolution.get("document_scores") or [])
            resolver_confidence = float(resolution.get("resolver_confidence") or 0.0)
            resolver_selection_mode = str(resolution.get("resolver_selection_mode") or "").strip() or None
        elif resolver_status == "selection_resolved":
            focus_decision = "manual_selection"
            focus_release_reason = "document_selection"
            resolver_selection_mode = "manual_selection"
        elif resolver_status == "clarification_resolved":
            focus_decision = "clarification_selection"
            focus_release_reason = "clarification_selection"
            resolver_selection_mode = "clarification_selection"

        extraction_diagnostics = self._build_trace_extraction_diagnostics(document_shortlist)

        if len(matched_documents) > 1:
            return self._attach_debug_trace_fields(
                self._build_document_refinement_trace(
                    resolved_question,
                    matched_documents,
                    resolver_status,
                    resolver_candidates,
                    matched_aliases,
                ),
                document_shortlist=document_shortlist,
                document_scores=document_scores,
                resolver_confidence=resolver_confidence,
                extraction_diagnostics=extraction_diagnostics,
                resolver_selection_mode=resolver_selection_mode,
                focus_decision=focus_decision,
                focus_release_reason=focus_release_reason,
                recovery_search_performed=recovery_search_performed,
                recovery_matched_documents=recovery_matched_documents,
            )

        target_document_name = matched_documents[0] if matched_documents else None
        if not document_shortlist and target_document_name:
            document_shortlist = [target_document_name]
        extraction_diagnostics = self._build_trace_extraction_diagnostics(document_shortlist)

        if retrieval_intent is None:
            retrieval_intent = self._plan_evidence_retrieval(
                user_question,
                resolved_question,
                target_document_name,
                chat_history,
            ).get("retrieval_intent")
        self._update_retrieval_diagnostics_summary(
            retrieval_intent=retrieval_intent,
            target_document_name=target_document_name,
        )

        retrieval_pass = self._execute_retrieval_pass(
            user_question=user_question,
            resolved_question=resolved_question,
            target_document_name=target_document_name,
            retrieval_intent=retrieval_intent,
            document_shortlist=document_shortlist,
            clarification_resolution=clarification_resolution,
        )
        clarification_options = list(retrieval_pass.get("clarification_options") or [])

        if len(clarification_options) > 1:
            self._set_retrieval_focus(
                scope_type="clarification_pending",
                target_document_name=target_document_name,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
                document_shortlist=document_shortlist,
                focus_decision=focus_decision,
                focus_reason=focus_release_reason,
                pending_clarification={
                    "original_question": user_question,
                    "resolved_question": resolved_question,
                    "target_document_name": target_document_name,
                    "retrieval_intent": retrieval_intent,
                    "options": clarification_options,
                },
            )
            return self._attach_debug_trace_fields(
                self._build_clarification_required_trace(
                    resolved_question,
                    matched_documents,
                    clarification_options,
                ),
                document_shortlist=document_shortlist,
                document_scores=document_scores,
                resolver_confidence=resolver_confidence,
                extraction_diagnostics=extraction_diagnostics,
                resolver_selection_mode=resolver_selection_mode,
                focus_decision=focus_decision,
                focus_release_reason=focus_release_reason,
                recovery_search_performed=recovery_search_performed,
                recovery_matched_documents=recovery_matched_documents,
            )

        selected_docs = list(retrieval_pass.get("selected_docs") or [])
        evidence_score = float(retrieval_pass.get("evidence_score") or 0.0)
        sources = list(retrieval_pass.get("sources") or [])
        answer_context = self._build_answer_context(
            selected_docs,
            retrieval_intent=retrieval_intent,
            target_document_name=target_document_name,
            resolved_question=resolved_question,
            selected_evidence_spans=[],
        )
        self._update_retrieval_diagnostics_summary(
            retrieval_intent=retrieval_intent,
            target_document_name=target_document_name,
            evidence_score=evidence_score,
            answer_context=answer_context,
            selected_evidence_spans=[],
            focused_evidence_context_built=False,
            abstained=False,
        )

        if self.strict_grounding and evidence_score < self.min_evidence_score:
            self._set_retrieval_focus(
                scope_type="document" if target_document_name else "collection_wide",
                target_document_name=target_document_name,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
                document_shortlist=document_shortlist,
                focus_decision=focus_decision,
                focus_reason=focus_release_reason,
            )
            self._update_retrieval_diagnostics_summary(
                abstained=True,
                answer_repair_applied=False,
                answer_repair_reason=None,
                final_answer_origin="llm",
            )
            return self._attach_debug_trace_fields(
                {
                    "route": MODE_RETRIEVAL,
                    "answer_text": self._format_mode_response(MODE_RETRIEVAL, self._build_abstain_answer()),
                    "resolved_question": resolved_question,
                    "matched_documents": matched_documents,
                    "needs_document_refinement": False,
                    "resolver_status": resolver_status,
                    "resolver_candidates": resolver_candidates,
                    "matched_aliases": matched_aliases,
                    "sources": sources,
                },
                document_shortlist=document_shortlist,
                document_scores=document_scores,
                resolver_confidence=resolver_confidence,
                extraction_diagnostics=extraction_diagnostics,
                resolver_selection_mode=resolver_selection_mode,
                focus_decision=focus_decision,
                focus_release_reason=focus_release_reason,
                recovery_search_performed=recovery_search_performed,
                recovery_matched_documents=recovery_matched_documents,
            )

        retrieval_answer = self._invoke_retrieval_agent(
            collection_name=collection_name,
            history_text=retrieval_history_text,
            resolved_question=resolved_question,
            matched_documents=", ".join(matched_documents) if matched_documents else "nenhum documento identificado",
            target_document_name=target_document_name,
            context=answer_context,
            question=user_question,
        )
        self._update_retrieval_diagnostics_summary(
            answer_shape=None,
            explicit_answer_candidates=[],
            consensus_dominant_candidate=None,
            candidate_consensus_details=[],
            answer_matches_top_evidence_span=None,
            answer_ignored_top_evidence_span=False,
            answer_repair_applied=False,
            answer_repair_reason=None,
            final_answer_origin="llm",
        )
        self._set_retrieval_focus(
            scope_type="document" if target_document_name else "collection_wide",
            target_document_name=target_document_name,
            resolved_question=resolved_question,
            retrieval_intent=retrieval_intent,
            document_shortlist=document_shortlist,
            focus_decision=focus_decision,
            focus_reason=focus_release_reason,
        )
        return self._attach_debug_trace_fields(
            {
                "route": MODE_RETRIEVAL,
                "answer_text": self._format_mode_response(MODE_RETRIEVAL, retrieval_answer),
                "resolved_question": resolved_question,
                "matched_documents": matched_documents,
                "needs_document_refinement": False,
                "resolver_status": resolver_status,
                "resolver_candidates": resolver_candidates,
                "matched_aliases": matched_aliases,
                "sources": sources,
            },
            document_shortlist=document_shortlist,
            document_scores=document_scores,
            resolver_confidence=resolver_confidence,
            extraction_diagnostics=extraction_diagnostics,
            resolver_selection_mode=resolver_selection_mode,
            focus_decision=focus_decision,
            focus_release_reason=focus_release_reason,
            recovery_search_performed=recovery_search_performed,
            recovery_matched_documents=recovery_matched_documents,
        )

    def ask_question(self, question: str, chat_history=None) -> str:
        trace = self.ask_question_with_trace(question, chat_history)
        return str(trace.get("answer_text", "")).strip()

    def ask_question_with_diagnostics(self, question: str, chat_history=None) -> dict[str, object]:
        self._begin_retrieval_diagnostics_capture()
        try:
            trace = self.ask_question_with_trace(question, chat_history)
            diagnostics = self._finish_retrieval_diagnostics_capture()
        except Exception:
            self._finish_retrieval_diagnostics_capture()
            raise

        enriched_trace = dict(trace)
        enriched_trace["retrieval_intent"] = diagnostics.get("retrieval_intent")
        enriched_trace["target_document_name"] = diagnostics.get("target_document_name")
        enriched_trace["evidence_score"] = float(diagnostics.get("evidence_score") or 0.0)
        enriched_trace["abstained"] = bool(diagnostics.get("abstained"))
        enriched_trace["answer_context"] = str(diagnostics.get("answer_context") or "")
        enriched_trace["answer_shape"] = None
        enriched_trace["selected_evidence_spans"] = []
        enriched_trace["focused_evidence_context_built"] = False
        enriched_trace["answer_matches_top_evidence_span"] = None
        enriched_trace["answer_ignored_top_evidence_span"] = False
        enriched_trace["explicit_answer_candidates"] = []
        enriched_trace["consensus_dominant_candidate"] = None
        enriched_trace["candidate_consensus_details"] = []
        enriched_trace["answer_repair_applied"] = False
        enriched_trace["answer_repair_reason"] = None
        enriched_trace["final_answer_origin"] = "llm"
        enriched_trace["retrieval_stages"] = dict(diagnostics.get("retrieval_stages") or {})
        enriched_trace["retrieval_stage_order"] = list(diagnostics.get("stage_order") or [])
        enriched_trace["candidate_catalog"] = dict(diagnostics.get("candidate_catalog") or {})
        return enriched_trace
