"""Follow-up resolution helpers for retrieval mode."""


# Este mixin resolve respostas curtas que continuam uma escolha pendente do turno anterior.
class RAGServiceFollowUpMixin:
    # Esta etapa reconstrui a pergunta real quando o usuario responde apenas um numero ou uma opcao.
    def _resolve_pending_follow_up(
        self,
        question: str,
        chat_history,
        pending_refinement: dict[str, object] | None,
        refinement_resolution: dict[str, object] | None,
        pending_clarification: dict[str, object] | None,
        clarification_resolution: dict[str, object] | None,
    ) -> dict[str, object]:
        history_text = self._format_chat_history(chat_history)
        result = {
            "user_question": question,
            "resolved_question": None,
            "retrieval_history_text": history_text,
            "retrieval_intent": None,
            "matched_documents": [],
            "resolver_status": "no_match",
            "resolver_candidates": [],
            "matched_aliases": [],
        }

        if clarification_resolution and clarification_resolution.get("status") == "selected" and pending_clarification:
            selected_option = clarification_resolution.get("option") or {}
            selected_label = str(selected_option.get("label") or "").strip()
            target_document_name = str(pending_clarification.get("target_document_name") or "").strip() or None
            result["user_question"] = str(pending_clarification.get("original_question") or "").strip() or question
            resolved_question = (
                str(pending_clarification.get("resolved_question") or "").strip() or result["user_question"]
            )
            if selected_label:
                resolved_question = f"{resolved_question} referente a {selected_label}".strip()
            result["resolved_question"] = resolved_question
            result["retrieval_history_text"] = self._build_effective_history_text(chat_history, pending_clarification)
            result["retrieval_intent"] = (
                str(pending_clarification.get("retrieval_intent") or "").strip()
                or self._infer_retrieval_intent(result["user_question"], resolved_question)
            )
            result["matched_documents"] = [target_document_name] if target_document_name else []
            result["resolver_status"] = "clarification_resolved"
            result["resolver_candidates"] = list(result["matched_documents"])
            result["matched_aliases"] = [selected_label] if selected_label else []
            return result

        if refinement_resolution and refinement_resolution.get("status") == "selected" and pending_refinement:
            selected_document_name = str(refinement_resolution.get("document_name") or "").strip()
            result["resolved_question"] = str(pending_refinement.get("resolved_question") or "").strip()
            result["user_question"] = str(pending_refinement.get("original_question") or "").strip() or question
            result["retrieval_history_text"] = self._build_effective_history_text(chat_history, pending_refinement)
            if not result["resolved_question"]:
                result["resolved_question"] = result["user_question"]
            result["matched_documents"] = [selected_document_name] if selected_document_name else []
            result["resolver_status"] = "selection_resolved"
            result["resolver_candidates"] = list(pending_refinement.get("matched_documents") or [])
            return result

        return result
