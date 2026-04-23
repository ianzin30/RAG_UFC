"""Selection helpers for file and clarification follow-ups."""
# Simple: Process user selections when choosing documents

import re

from ..Models import PendingDocumentRefinement, PendingRetrievalClarification


# Este mixin resolve selecoes numericas e escolhas textuais em passos pendentes.
class RAGServiceSelectionMixin:
    # Este helper reconstrui o estado de refinamento a partir da ultima resposta do assistente.
    def _get_pending_document_refinement(self, chat_history) -> dict[str, object] | None:
        history = list(chat_history or [])
        if not history:
            return None

        last_message = history[-1]
        if not isinstance(last_message, dict):
            return None
        if str(last_message.get("role", "")).strip().lower() != "assistant":
            return None
        if not bool(last_message.get("needs_document_refinement")):
            return None

        matched_documents = [
            str(document_name).strip()
            for document_name in list(last_message.get("matched_documents") or [])
            if str(document_name).strip()
        ]
        if len(matched_documents) < 2:
            return None

        original_question = ""
        for message in reversed(history[:-1]):
            if str(message.get("role", "")).strip().lower() != "user":
                continue
            original_question = str(message.get("content", "")).strip()
            if original_question:
                break

        refinement = PendingDocumentRefinement(
            matched_documents=matched_documents,
            resolved_question=str(last_message.get("resolved_question", "")).strip() or original_question,
            original_question=original_question or str(last_message.get("resolved_question", "")).strip(),
        )
        return refinement.to_dict()

    # Esta heuristica aceita respostas curtas por texto quando o usuario nao envia apenas um numero.
    def _resolve_pending_option_selection_by_text(
        self,
        question: str,
        options: list[dict[str, object]],
    ) -> dict[str, object] | None:
        normalized_question = self._normalize_identifier(question)
        query_terms = self._tokenize_search_text(question)
        if not normalized_question or not query_terms:
            return None

        scored_options: list[tuple[int, dict[str, object]]] = []
        for option in options:
            option_normalized = str(option.get("normalized") or "").strip()
            if not option_normalized:
                continue

            overlap = sum(1 for term in query_terms if term in option_normalized)
            if overlap <= 0:
                continue

            score = overlap * 45
            if normalized_question == option_normalized:
                score += 180
            elif normalized_question in option_normalized:
                score += 120
            elif all(term in option_normalized for term in query_terms):
                score += 70

            scored_options.append((score, option))

        if not scored_options:
            return None

        scored_options.sort(key=lambda item: (-item[0], str(item[1].get("label") or "")))
        if len(scored_options) > 1 and scored_options[0][0] == scored_options[1][0]:
            return None
        return scored_options[0][1]

    # Esta etapa valida a escolha do usuario quando estamos aguardando uma clarificacao interna.
    def _resolve_pending_retrieval_clarification(
        self,
        question: str,
        pending_clarification: dict[str, object] | None,
    ) -> dict[str, object] | None:
        clarification = PendingRetrievalClarification.from_dict(pending_clarification)
        if clarification is None:
            return None

        options = [option.to_dict() for option in clarification.options]
        selected_number = self._extract_document_selection_number(question)
        if selected_number is not None:
            if 1 <= selected_number <= len(options):
                return {
                    "status": "selected",
                    "option": options[selected_number - 1],
                    "selection_number": selected_number,
                }
            return {
                "status": "invalid_selection",
                "selection_number": selected_number,
            }

        selected_option = self._resolve_pending_option_selection_by_text(question, options)
        if selected_option is not None:
            return {
                "status": "selected",
                "option": selected_option,
            }
        return None

    # Este parser aceita formatos como "2", "arquivo 2" ou "opcao 2".
    def _extract_document_selection_number(self, question: str) -> int | None:
        normalized = self._normalize_identifier(question)
        if not normalized:
            return None

        exact_match = re.fullmatch(
            r"(?:arquivo|file|item|opcao|numero|n)?\s*(\d{1,3})",
            normalized,
        )
        if exact_match:
            return int(exact_match.group(1))

        selection_match = re.fullmatch(
            r"(?:quero|escolho|escolha|seleciono|seleciona|prefiro|manda|mostra|fale|me fale|sobre)\s+"
            r"(?:o|a)?\s*(?:arquivo|file|item|opcao)?\s*(\d{1,3})",
            normalized,
        )
        if selection_match:
            return int(selection_match.group(1))
        return None

    # Esta busca textual tenta mapear pistas curtas para um documento candidato especifico.
    def _resolve_pending_document_selection_by_text(
        self,
        question: str,
        candidate_document_names: list[str],
    ) -> str | None:
        normalized_question = self._normalize_identifier(question)
        query_terms = self._tokenize_search_text(question)
        if not normalized_question or not query_terms:
            return None

        scored_candidates: list[tuple[int, str]] = []
        for document_name in candidate_document_names:
            document = self._get_document_entry(document_name)
            if document is None:
                continue

            best_score = 0
            for alias in document.get("aliases", []):
                alias_normalized = str(alias.get("normalized", "")).strip()
                if not alias_normalized:
                    continue

                overlap = sum(1 for term in query_terms if term in alias_normalized)
                if overlap <= 0:
                    continue

                score = int(alias.get("weight", 0)) + overlap * 40
                if normalized_question == alias_normalized:
                    score += 180
                elif normalized_question in alias_normalized:
                    score += 120
                elif all(term in alias_normalized for term in query_terms):
                    score += 70

                if score > best_score:
                    best_score = score

            if best_score > 0:
                scored_candidates.append((best_score, document_name))

        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda item: (-item[0], item[1]))
        if len(scored_candidates) > 1 and scored_candidates[0][0] == scored_candidates[1][0]:
            return None
        return scored_candidates[0][1]

    # Esta etapa fecha o refinamento de documento quando o usuario escolhe um item da lista.
    def _resolve_pending_document_refinement(
        self,
        question: str,
        pending_refinement: dict[str, object] | None,
    ) -> dict[str, object] | None:
        if not pending_refinement:
            return None

        matched_documents = list(pending_refinement.get("matched_documents") or [])
        if len(matched_documents) < 2:
            return None

        selected_number = self._extract_document_selection_number(question)
        if selected_number is not None:
            if 1 <= selected_number <= len(matched_documents):
                return {
                    "status": "selected",
                    "document_name": matched_documents[selected_number - 1],
                    "selection_number": selected_number,
                }
            return {
                "status": "invalid_selection",
                "selection_number": selected_number,
            }

        selected_document = self._resolve_pending_document_selection_by_text(question, matched_documents)
        if selected_document:
            return {
                "status": "selected",
                "document_name": selected_document,
            }
        return None
