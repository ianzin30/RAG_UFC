"""Planning helpers for document scope and retrieval intent."""

import json

from .planning_support import RAGServicePlanningSupportMixin


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
            return {"scope_type": "explicit_document", "matched_documents": explicit_matches}
        if self._question_requests_collection_scope(question, resolved_question):
            return {"scope_type": "collection_wide", "matched_documents": []}

        if locked_document_name:
            payload = self._invoke_json_crewai_agent(
                getattr(self, "crewai_scope_agent", None),
                description=(
                    "Determine o escopo da pergunta do usuario em um chat com documentos.\n\n"
                    f"Documento atualmente travado: {locked_document_name}\n"
                    f"Historico: {self._format_chat_history(chat_history)}\n"
                    f"Pergunta original: {question}\n"
                    f"Pergunta reescrita: {resolved_question}\n\n"
                    "Retorne JSON com as chaves:\n"
                    '- "scope_type": "locked_document" ou "collection_wide"\n'
                    '- "reason": texto curto\n'
                ),
                expected_output='JSON valido, por exemplo {"scope_type":"locked_document","reason":"follow_up"}',
            )
            scope_type = str((payload or {}).get("scope_type") or "").strip()
            if scope_type == "collection_wide" and self._question_requests_collection_scope(question, resolved_question):
                return {"scope_type": "collection_wide", "matched_documents": []}
            return {"scope_type": "locked_document", "matched_documents": [locked_document_name]}

        return {"scope_type": "discovery", "matched_documents": []}

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
                "resolver_candidates": explicit_matches,
                "matched_aliases": [],
            }

        if str(scope_plan.get("scope_type") or "") == "collection_wide":
            return {
                "status": "collection_wide",
                "matched_documents": [],
                "resolver_candidates": [],
                "matched_aliases": [],
            }

        resolver_result = self._resolve_documents_with_agent(question, resolved_question, chat_history)
        if locked_document_name and str(scope_plan.get("scope_type") or "") == "locked_document":
            return {
                "status": "scope_locked",
                "matched_documents": [locked_document_name],
                "resolver_candidates": list(resolver_result.get("resolver_candidates") or [locked_document_name]),
                "matched_aliases": list(resolver_result.get("matched_aliases") or []),
            }

        candidate_names = list(resolver_result.get("resolver_candidates") or resolver_result.get("matched_documents") or [])
        if getattr(self, "crewai_document_selection_agent", None) and len(candidate_names) > 1:
            payload = self._invoke_json_crewai_agent(
                getattr(self, "crewai_document_selection_agent", None),
                description=(
                    "Selecione os documentos mais provaveis para responder a pergunta do usuario.\n\n"
                    f"Historico: {self._format_chat_history(chat_history)}\n"
                    f"Pergunta original: {question}\n"
                    f"Pergunta reescrita: {resolved_question}\n"
                    f"Documento atualmente travado: {locked_document_name or 'nenhum'}\n"
                    f"Candidatos: {json.dumps(self._build_candidate_documents_payload(candidate_names), ensure_ascii=False)}\n\n"
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
                    "resolver_candidates": candidate_names,
                    "matched_aliases": list(resolver_result.get("matched_aliases") or []),
                }
            if selection == "multiple" and selected_documents:
                return {
                    "status": "multiple_matches",
                    "matched_documents": selected_documents,
                    "resolver_candidates": candidate_names,
                    "matched_aliases": list(resolver_result.get("matched_aliases") or []),
                }
        return resolver_result

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
