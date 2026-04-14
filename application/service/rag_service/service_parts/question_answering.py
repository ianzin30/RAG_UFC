"""Question orchestration for the RAG service."""

from ..constants import MODE_CASUAL, MODE_RETRIEVAL
from .question_follow_up import RAGServiceFollowUpMixin


# Este mixin coordena o fluxo completo de uma pergunta em modo casual ou retrieval.
class RAGServiceQuestionAnsweringMixin(RAGServiceFollowUpMixin):
    # Esta funcao principal resolve modo, documento, retrieval e rastros de depuracao.
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

        # Primeiro resolvemos selecoes pendentes, como escolha de arquivo ou clarificacao interna.
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
        resolved_question = follow_up["resolved_question"]

        # Se ainda nao ha pergunta resolvida, planejamos escopo e documento a partir do contexto atual.
        if resolved_question is None:
            force_rewrite = self.last_retrieval_focus is not None and self._is_follow_up_ambiguous(question)
            resolved_question = self._rewrite_question_for_retrieval(
                question,
                history_text,
                chat_history,
                force=force_rewrite,
            )
            scope_plan = self._plan_scope(question, resolved_question, chat_history, locked_document_name)
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

        if len(matched_documents) > 1:
            return self._build_document_refinement_trace(
                resolved_question,
                matched_documents,
                resolver_status,
                resolver_candidates,
                matched_aliases,
            )

        target_document_name = matched_documents[0] if matched_documents else None
        if not target_document_name and locked_document_name and resolver_status != "collection_wide":
            target_document_name = locked_document_name
            matched_documents = [target_document_name]
            resolver_status = "scope_locked"
        if target_document_name and not matched_documents:
            matched_documents = [target_document_name]

        if retrieval_intent is None:
            retrieval_intent = self._plan_evidence_retrieval(
                user_question,
                resolved_question,
                target_document_name,
                chat_history,
            ).get("retrieval_intent")

        # Aqui recuperamos, reordenamos e eventualmente pedimos nova clarificacao antes de responder.
        docs = self._retrieve_docs(
            resolved_question,
            target_document_name,
            retrieval_intent=retrieval_intent,
        )
        docs = self._prioritize_retrieved_docs(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
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
            self._set_retrieval_focus(
                scope_type="clarification_pending",
                target_document_name=target_document_name,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
                pending_clarification={
                    "original_question": user_question,
                    "resolved_question": resolved_question,
                    "target_document_name": target_document_name,
                    "retrieval_intent": retrieval_intent,
                    "options": clarification_options,
                },
            )
            return self._build_clarification_required_trace(
                resolved_question,
                matched_documents,
                clarification_options,
            )

        # So montamos a resposta final depois de escolher os melhores trechos e medir a evidencia.
        docs = self._select_docs_for_context(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
        )
        evidence_score = self._score_retrieval_evidence(resolved_question, docs, target_document_name)
        sources = self._build_sources(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
        )

        if self.strict_grounding and evidence_score < self.min_evidence_score:
            self._set_retrieval_focus(
                scope_type="document" if target_document_name else "collection_wide",
                target_document_name=target_document_name,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
            )
            return {
                "route": MODE_RETRIEVAL,
                "answer_text": self._format_mode_response(MODE_RETRIEVAL, self._build_abstain_answer()),
                "resolved_question": resolved_question,
                "matched_documents": matched_documents,
                "needs_document_refinement": False,
                "resolver_status": resolver_status,
                "resolver_candidates": resolver_candidates,
                "matched_aliases": matched_aliases,
                "sources": sources,
            }

        retrieval_answer = self._invoke_retrieval_agent(
            collection_name=collection_name,
            history_text=retrieval_history_text,
            resolved_question=resolved_question,
            matched_documents=", ".join(matched_documents) if matched_documents else "nenhum documento identificado",
            target_document_name=target_document_name,
            context=self._build_answer_context(
                docs,
                retrieval_intent=retrieval_intent,
                target_document_name=target_document_name,
                resolved_question=resolved_question,
            ),
            question=user_question,
        )
        self._set_retrieval_focus(
            scope_type="document" if target_document_name else "collection_wide",
            target_document_name=target_document_name,
            resolved_question=resolved_question,
            retrieval_intent=retrieval_intent,
        )
        return {
            "route": MODE_RETRIEVAL,
            "answer_text": self._format_mode_response(MODE_RETRIEVAL, retrieval_answer),
            "resolved_question": resolved_question,
            "matched_documents": matched_documents,
            "needs_document_refinement": False,
            "resolver_status": resolver_status,
            "resolver_candidates": resolver_candidates,
            "matched_aliases": matched_aliases,
            "sources": sources,
        }

    # Esta versao enxuta so devolve o texto final quando o chamador nao precisa do trace detalhado.
    def ask_question(self, question: str, chat_history=None) -> str:
        trace = self.ask_question_with_trace(question, chat_history)
        return str(trace.get("answer_text", "")).strip()
