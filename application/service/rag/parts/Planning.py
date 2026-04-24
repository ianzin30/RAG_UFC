"""Planning helpers for document scope and retrieval intent."""
# Simple: Decide search strategy based on user question

import json

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
        if self._question_requests_collection_scope(question, resolved_question):
            return {
                "scope_type": "collection_wide",
                "matched_documents": [],
                "focus_decision": "collection_wide",
                "focus_release_reason": "explicit_collection_scope",
            }

        focus_plan = self._decide_focus_scope(question, resolved_question, locked_document_name)
        focus_decision = str(focus_plan.get("focus_decision") or "release_to_discovery")
        focus_release_reason = str(focus_plan.get("focus_release_reason") or "").strip() or None

        if focus_decision == "collection_wide":
            return {
                "scope_type": "collection_wide",
                "matched_documents": [],
                "focus_decision": focus_decision,
                "focus_release_reason": focus_release_reason,
            }

        if locked_document_name and focus_decision == "keep_locked_document":
            payload = self._invoke_json_crewai_agent(
                getattr(self, "crewai_scope_agent", None),
                description=(
                    "Determine o escopo da pergunta do usuario em um chat com documentos.\n\n"
                    f"Documento atualmente travado: {locked_document_name}\n"
                    f"Historico: {self._format_chat_history(chat_history)}\n"
                    f"Pergunta original: {question}\n"
                    f"Pergunta reescrita: {resolved_question}\n\n"
                    f"Decisao deterministica atual: {focus_decision}\n"
                    f"Motivo principal: {focus_release_reason or 'continuity'}\n\n"
                    "Retorne JSON com as chaves:\n"
                    '- "scope_type": "locked_document", "discovery" ou "collection_wide"\n'
                    '- "reason": texto curto\n'
                ),
                expected_output='JSON valido, por exemplo {"scope_type":"locked_document","reason":"follow_up"}',
            )
            scope_type = str((payload or {}).get("scope_type") or "").strip()
            if scope_type == "collection_wide" and self._question_requests_collection_scope(question, resolved_question):
                return {
                    "scope_type": "collection_wide",
                    "matched_documents": [],
                    "focus_decision": "collection_wide",
                    "focus_release_reason": "explicit_collection_scope",
                }
            if scope_type == "discovery":
                return {
                    "scope_type": "discovery",
                    "matched_documents": [],
                    "focus_decision": "release_to_discovery",
                    "focus_release_reason": str((payload or {}).get("reason") or "").strip() or "agent_released_lock",
                }
            return {
                "scope_type": "locked_document",
                "matched_documents": [locked_document_name],
                "focus_decision": focus_decision,
                "focus_release_reason": focus_release_reason,
            }

        return {
            "scope_type": "discovery",
            "matched_documents": [],
            "focus_decision": "release_to_discovery",
            "focus_release_reason": focus_release_reason or "self_contained_new_question",
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

        resolver_result = self._resolve_documents_with_agent(question, resolved_question, chat_history)
        retrieval_intent_hint = self._infer_retrieval_intent(question, resolved_question)
        document_scores = list(resolver_result.get("document_scores") or [])
        score_lookup = {
            str(item.get("document_name") or "").strip(): item
            for item in document_scores
            if str(item.get("document_name") or "").strip()
        }
        if locked_document_name and str(scope_plan.get("scope_type") or "") == "locked_document":
            return {
                "status": "scope_locked",
                "matched_documents": [locked_document_name],
                "document_shortlist": list(resolver_result.get("document_shortlist") or [locked_document_name]),
                "resolver_candidates": list(resolver_result.get("resolver_candidates") or [locked_document_name]),
                "matched_aliases": list(resolver_result.get("matched_aliases") or []),
                "document_scores": document_scores,
                "resolver_confidence": float(resolver_result.get("resolver_confidence") or 0.0),
                "resolver_selection_mode": "locked_document",
            }

        candidate_names = list(
            resolver_result.get("document_shortlist")
            or resolver_result.get("matched_documents")
            or resolver_result.get("resolver_candidates")
            or []
        )
        if getattr(self, "crewai_document_selection_agent", None) and len(candidate_names) > 1:
            payload = self._invoke_json_crewai_agent(
                getattr(self, "crewai_document_selection_agent", None),
                description=(
                    "Selecione os documentos mais provaveis para responder a pergunta do usuario.\n\n"
                    f"Historico: {self._format_chat_history(chat_history)}\n"
                    f"Pergunta original: {question}\n"
                    f"Pergunta reescrita: {resolved_question}\n"
                    f"Documento atualmente travado: {locked_document_name or 'nenhum'}\n"
                    f"Candidatos: {json.dumps(self._build_candidate_documents_payload(candidate_names, score_lookup), ensure_ascii=False)}\n\n"
                    "Retorne JSON com as chaves:\n"
                    '- "selection": "single" ou "multiple"\n'
                    '- "documents": lista de nomes dentre os candidatos\n'
                ),
                expected_output='JSON valido, por exemplo {"selection":"single","documents":["arquivo.pdf"]}',
            )
            selected_documents = [
                str(document_name).strip()
                for document_name in list((payload or {}).get("documents") or [])
                if str(document_name).strip() in candidate_names
            ]
            selection = str((payload or {}).get("selection") or "").strip()
            if selection == "single" and len(selected_documents) == 1:
                return {
                    "status": "single_match",
                    "matched_documents": selected_documents,
                    "document_shortlist": candidate_names,
                    "resolver_candidates": candidate_names,
                    "matched_aliases": list(resolver_result.get("matched_aliases") or []),
                    "document_scores": document_scores,
                    "resolver_confidence": max(float(resolver_result.get("resolver_confidence") or 0.0), 0.82),
                    "resolver_selection_mode": "agent_selected",
                }
            if selection == "multiple" and selected_documents:
                candidate_names = selected_documents

        if len(candidate_names) > 1:
            return {
                "status": "shortlist",
                "matched_documents": [],
                "document_shortlist": candidate_names,
                "resolver_candidates": list(resolver_result.get("resolver_candidates") or candidate_names),
                "matched_aliases": list(resolver_result.get("matched_aliases") or []),
                "document_scores": document_scores,
                "resolver_confidence": float(resolver_result.get("resolver_confidence") or 0.0),
                "resolver_selection_mode": "multi_document_shortlist",
            }

        return {
            "status": str(resolver_result.get("status") or "no_match"),
            "matched_documents": candidate_names if len(candidate_names) != 1 else candidate_names[:1],
            "document_shortlist": candidate_names,
            "resolver_candidates": list(resolver_result.get("resolver_candidates") or candidate_names),
            "matched_aliases": list(resolver_result.get("matched_aliases") or []),
            "document_scores": document_scores,
            "resolver_confidence": float(resolver_result.get("resolver_confidence") or 0.0),
            "resolver_selection_mode": (
                "top_ranked_single"
                if len(candidate_names) == 1
                else "ranked_shortlist"
                if candidate_names
                else "no_match"
            ),
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
