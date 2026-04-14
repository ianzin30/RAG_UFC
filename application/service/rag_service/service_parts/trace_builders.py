"""Trace builders for retrieval and casual responses."""

from ..constants import MODE_CASUAL, MODE_RETRIEVAL


# Este mixin monta traces uniformes para todos os caminhos de resposta.
class RAGServiceTraceBuilderMixin:
    # Este trace cobre a troca explicita entre modo casual e modo retrieval.
    def _build_mode_transition_trace(self, question: str, route: str, mode_transition: str) -> dict[str, object]:
        if route == MODE_CASUAL:
            self.last_retrieval_focus = None
        return {
            "route": route,
            "answer_text": self._build_mode_transition_answer(route, mode_transition),
            "resolved_question": question,
            "matched_documents": [],
            "needs_document_refinement": False,
            "resolver_status": "no_match",
            "resolver_candidates": [],
            "matched_aliases": [],
            "sources": [],
        }

    # Este trace encapsula a resposta casual com o mesmo formato usado no retrieval.
    def _build_casual_trace(self, question: str, collection_name: str, history_text: str) -> dict[str, object]:
        self.last_retrieval_focus = None
        casual_answer = self._invoke_casual_agent(collection_name, history_text, question)
        return {
            "route": MODE_CASUAL,
            "answer_text": self._format_mode_response(MODE_CASUAL, casual_answer),
            "resolved_question": question,
            "matched_documents": [],
            "needs_document_refinement": False,
            "resolver_status": "no_match",
            "resolver_candidates": [],
            "matched_aliases": [],
            "sources": [],
        }

    # Este trace repete a lista de arquivos quando o usuario escolhe um numero invalido.
    def _build_invalid_document_selection_trace(
        self,
        question: str,
        pending_refinement: dict[str, object] | None,
        selection_number: int,
    ) -> dict[str, object]:
        matched_documents = list(pending_refinement.get("matched_documents") or []) if pending_refinement else []
        self.last_retrieval_focus = None
        return {
            "route": MODE_RETRIEVAL,
            "answer_text": self._format_mode_response(
                MODE_RETRIEVAL,
                self._build_document_refinement_answer(
                    matched_documents,
                    invalid_selection=selection_number,
                ),
            ),
            "resolved_question": str(pending_refinement.get("resolved_question") or question) if pending_refinement else question,
            "matched_documents": matched_documents,
            "needs_document_refinement": True,
            "resolver_status": "invalid_selection",
            "resolver_candidates": matched_documents,
            "matched_aliases": [],
            "sources": [],
        }

    # Este trace repete a lista de opcoes quando a clarificacao recebe um numero invalido.
    def _build_invalid_clarification_trace(
        self,
        question: str,
        pending_clarification: dict[str, object] | None,
        selection_number: int,
    ) -> dict[str, object]:
        options = list(pending_clarification.get("options") or []) if pending_clarification else []
        if pending_clarification:
            self._set_retrieval_focus(
                scope_type="clarification_pending",
                target_document_name=str(pending_clarification.get("target_document_name") or "").strip() or None,
                resolved_question=str(pending_clarification.get("resolved_question") or "").strip() or question,
                retrieval_intent=str(pending_clarification.get("retrieval_intent") or "").strip() or None,
                pending_clarification=pending_clarification,
            )

        return {
            "route": MODE_RETRIEVAL,
            "answer_text": self._format_mode_response(
                MODE_RETRIEVAL,
                self._build_retrieval_clarification_answer(
                    options,
                    invalid_selection=selection_number,
                ),
            ),
            "resolved_question": str(pending_clarification.get("resolved_question") or question) if pending_clarification else question,
            "matched_documents": [str(pending_clarification.get("target_document_name") or "").strip()]
            if pending_clarification and str(pending_clarification.get("target_document_name") or "").strip()
            else [],
            "needs_document_refinement": False,
            "resolver_status": "clarification_required",
            "resolver_candidates": [],
            "matched_aliases": [],
            "sources": [],
        }

    # Este trace suspende a resposta final ate o usuario escolher um arquivo especifico.
    def _build_document_refinement_trace(
        self,
        resolved_question: str,
        matched_documents: list[str],
        resolver_status: str,
        resolver_candidates: list[str],
        matched_aliases: list[str],
    ) -> dict[str, object]:
        self.last_retrieval_focus = None
        return {
            "route": MODE_RETRIEVAL,
            "answer_text": self._format_mode_response(
                MODE_RETRIEVAL,
                self._build_document_refinement_answer(matched_documents),
            ),
            "resolved_question": resolved_question,
            "matched_documents": matched_documents,
            "needs_document_refinement": True,
            "resolver_status": resolver_status,
            "resolver_candidates": resolver_candidates,
            "matched_aliases": matched_aliases,
            "sources": [],
        }

    # Este trace suspende a resposta final ate o usuario escolher uma referencia interna.
    def _build_clarification_required_trace(
        self,
        resolved_question: str,
        matched_documents: list[str],
        clarification_options: list[dict[str, str]],
    ) -> dict[str, object]:
        return {
            "route": MODE_RETRIEVAL,
            "answer_text": self._format_mode_response(
                MODE_RETRIEVAL,
                self._build_retrieval_clarification_answer(clarification_options),
            ),
            "resolved_question": resolved_question,
            "matched_documents": matched_documents,
            "needs_document_refinement": False,
            "resolver_status": "clarification_required",
            "resolver_candidates": [],
            "matched_aliases": [],
            "sources": [],
        }
