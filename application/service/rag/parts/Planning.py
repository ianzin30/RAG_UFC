"""Planning helpers for document scope and retrieval intent."""
# Simple: Decide search strategy based on user question

from .PlanningSupport import RAGServicePlanningSupportMixin


# Este mixin decide escopo, documento-alvo e intencao de retrieval.
class RAGServicePlanningMixin(RAGServicePlanningSupportMixin):
    # Esta etapa define se a pergunta esta presa a um documento, a colecao inteira ou a descoberta livre.
    def _plan_scope(
        self,
        question: str,
        resolved_question: str,
        chat_history,
        locked_document_name: str | None,
    ) -> dict[str, object]:
        explicit_matches = self._merge_document_matches(
            self._match_document_names(question),
            self._match_document_names(resolved_question),
        )
        if explicit_matches:
            return {
                "scope_type": "explicit_document",
                "matched_documents": explicit_matches,
                "focus_decision": "release_to_discovery",
                "focus_release_reason": "explicit_document_reference",
            }
        return {
            "scope_type": "collection_wide",
            "matched_documents": [],
            "focus_decision": "collection_wide",
            "focus_release_reason": "collection_wide_default",
        }

    # Esta etapa escolhe o melhor documento ou preserva a lista para refinamento do usuario.
    def _plan_document_selection(
        self,
        question: str,
        resolved_question: str,
        chat_history,
        scope_plan: dict[str, object],
        locked_document_name: str | None,
    ) -> dict[str, object]:
        explicit_matches = list(scope_plan.get("matched_documents") or [])
        if explicit_matches:
            status = "single_match" if len(explicit_matches) == 1 else "multiple_matches"
            return {
                "status": status,
                "matched_documents": explicit_matches,
                "document_shortlist": explicit_matches[:3],
                "resolver_candidates": explicit_matches,
                "matched_aliases": [],
                "document_scores": [
                    {
                        "document_name": document_name,
                        "score": 999,
                        "reason": "explicit_document_reference",
                        "matched_terms": [],
                        "matched_phrases": [],
                        "score_components": {
                            "alias_score": 999,
                            "keyword_score": 0,
                            "signal_score": 0,
                            "phrase_score": 0,
                            "specificity_score": 0,
                            "generic_penalty": 0,
                            "blend_bonus": 0,
                        },
                    }
                    for document_name in explicit_matches[:5]
                ],
                "resolver_confidence": 1.0 if len(explicit_matches) == 1 else 0.72,
                "resolver_selection_mode": "explicit_reference",
            }

        if str(scope_plan.get("scope_type") or "") == "collection_wide":
            return {
                "status": "collection_wide",
                "matched_documents": [],
                "document_shortlist": [],
                "resolver_candidates": [],
                "matched_aliases": [],
                "document_scores": [],
                "resolver_confidence": 0.0,
                "resolver_selection_mode": "collection_wide",
            }

        return {
            "status": "collection_wide",
            "matched_documents": [],
            "document_shortlist": [],
            "resolver_candidates": [],
            "matched_aliases": [],
            "document_scores": [],
            "resolver_confidence": 0.0,
            "resolver_selection_mode": "collection_wide",
        }

    # Esta etapa classifica a pergunta para orientar ranking e montagem do contexto.
    def _plan_evidence_retrieval(
        self,
        question: str,
        resolved_question: str,
        target_document_name: str | None,
        chat_history,
    ) -> dict[str, object]:
        fallback_intent = self._infer_retrieval_intent(question, resolved_question)
        payload = self._invoke_json_crewai_agent(
            getattr(self, "crewai_evidence_planning_agent", None),
            description=(
                "Classifique a intencao de retrieval da pergunta do usuario.\n\n"
                f"Historico: {self._format_chat_history(chat_history)}\n"
                f"Pergunta original: {question}\n"
                f"Pergunta reescrita: {resolved_question}\n"
                f"Documento-alvo atual: {target_document_name or 'nenhum'}\n\n"
                "Retorne JSON com as chaves:\n"
                '- "retrieval_intent": "summary", "document_expansion", "entity_lookup", "list_extraction" ou "specific_fact"\n'
                '- "reason": texto curto\n'
            ),
            expected_output='JSON valido, por exemplo {"retrieval_intent":"document_expansion","reason":"broad follow-up"}',
        )
        retrieval_intent = str((payload or {}).get("retrieval_intent") or "").strip()
        if retrieval_intent not in {"summary", "document_expansion", "entity_lookup", "list_extraction", "specific_fact"}:
            retrieval_intent = fallback_intent
        return {"retrieval_intent": retrieval_intent}
