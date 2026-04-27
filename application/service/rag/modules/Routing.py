"""Query routing — classify questions as retrieval or casual conversation.

Decides whether to answer from documents or use a general chat model, extracts
focus terms for persistent retrieval context, and formats responses with
mode-specific headers and footers.
"""
import re

from ..Constants import (
    CASUAL_RESPONSE_FOOTER,
    CASUAL_RESPONSE_TITLE,
    MODE_CASUAL,
    MODE_RETRIEVAL,
    MODE_SWITCH_TO_CASUAL_COMMAND,
    MODE_SWITCH_TO_RETRIEVAL_COMMAND,
    MONTH_NAME_TO_NUMBER,
    RETRIEVAL_RESPONSE_FOOTER,
    RETRIEVAL_RESPONSE_TITLE,
    REWRITE_REFERENCE_MARKERS,
)


class RoutingMixin:
    """Classify questions and route to retrieval or casual mode."""

    def _extract_focus_terms(self, text: str, limit: int = 12) -> list[str]:
        normalized = self._normalize_identifier(text)
        focus_terms = []
        seen = set()

        for token in normalized.split():
            if token in seen:
                continue
            if re.fullmatch(r"\d{4}", token) or self._is_discriminative_query_term(token):
                seen.add(token)
                focus_terms.append(token)
            if len(focus_terms) >= limit:
                return focus_terms

        for token in self._tokenize_search_text(text):
            if token in seen:
                continue
            seen.add(token)
            focus_terms.append(token)
            if len(focus_terms) >= limit:
                break
        return focus_terms

    def _question_has_explicit_referential_focus(self, question: str) -> bool:
        normalized = self._normalize_identifier(question)
        if not normalized:
            return False

        referential_markers = (
            "esse documento",
            "essa reuniao",
            "essa ata",
            "esse arquivo",
            "esse pdf",
            "este documento",
            "esta reuniao",
            "dessa reuniao",
            "desse documento",
            "desse arquivo",
            "nessa reuniao",
            "nesse documento",
            "dele",
            "dela",
        )
        return any(marker in normalized for marker in referential_markers)

    def _extract_focus_years(self, text: str) -> set[str]:
        return set(re.findall(r"\b\d{4}\b", self._normalize_identifier(text)))

    def _extract_focus_month_terms(self, terms: list[str]) -> set[str]:
        return {term for term in terms if term in MONTH_NAME_TO_NUMBER}

    def _detect_focus_release_reason(
        self,
        question: str,
        resolved_question: str,
        locked_document_name: str,
    ) -> str | None:
        focus_state = self._get_retrieval_focus_state()
        locked_entry = self._get_document_entry(locked_document_name)
        current_terms = self._extract_focus_terms(resolved_question or question, limit=16)
        if not current_terms:
            return None

        previous_focus_terms = set((focus_state.focus_terms if focus_state is not None else []) or [])
        if not previous_focus_terms and focus_state is not None and focus_state.resolved_question:
            previous_focus_terms = set(self._extract_focus_terms(focus_state.resolved_question, limit=16))

        locked_terms = set(str(term).strip() for term in list((locked_entry or {}).get("keyword_terms") or []) if str(term).strip())
        locked_search_terms = set(str((locked_entry or {}).get("search_text_normalized") or "").split())
        supported_terms = previous_focus_terms | locked_terms | locked_search_terms

        current_years = self._extract_focus_years(resolved_question or question)
        locked_years = set()
        if focus_state is not None and focus_state.resolved_question:
            locked_years |= self._extract_focus_years(focus_state.resolved_question)
        if locked_entry is not None and str(locked_entry.get("meeting_year") or "").strip():
            locked_years.add(str(locked_entry.get("meeting_year") or "").strip())
        novel_years = {year for year in current_years if year not in locked_years}
        if novel_years:
            return "new_year_anchor"

        current_months = self._extract_focus_month_terms(current_terms)
        locked_months = self._extract_focus_month_terms(list(supported_terms))
        if current_months and current_months.isdisjoint(locked_months):
            return "new_month_anchor"

        query_phrases = self._extract_query_signal_phrases(self._normalize_identifier(resolved_question or question))
        locked_search_text = str((locked_entry or {}).get("search_text_normalized") or "").strip()
        supported_phrase_hits = [phrase for phrase in query_phrases if phrase and phrase in locked_search_text]

        novel_terms = [term for term in current_terms if term not in supported_terms]
        supported_overlap = [term for term in current_terms if term in supported_terms]
        if len(novel_terms) >= 2 and len(supported_overlap) <= 1 and not supported_phrase_hits:
            return "new_content_anchors"
        return None

    def _has_focus_continuity(
        self,
        question: str,
        resolved_question: str,
        locked_document_name: str,
    ) -> bool:
        focus_state = self._get_retrieval_focus_state()
        locked_entry = self._get_document_entry(locked_document_name)
        current_terms = set(self._extract_focus_terms(resolved_question or question, limit=16))
        if not current_terms:
            return False

        previous_focus_terms = set((focus_state.focus_terms if focus_state is not None else []) or [])
        if focus_state is not None and focus_state.resolved_question:
            previous_focus_terms |= set(self._extract_focus_terms(focus_state.resolved_question, limit=16))

        locked_terms = set(str(term).strip() for term in list((locked_entry or {}).get("keyword_terms") or []) if str(term).strip())
        locked_terms |= set(str((locked_entry or {}).get("search_text_normalized") or "").split())

        overlap_with_previous = current_terms & previous_focus_terms
        overlap_with_locked = current_terms & locked_terms
        return len(overlap_with_previous) >= 2 or len(overlap_with_locked) >= 2

    def _decide_focus_scope(
        self,
        question: str,
        resolved_question: str,
        locked_document_name: str | None,
    ) -> dict[str, object]:
        if self._question_requests_collection_scope(question, resolved_question):
            return {
                "focus_decision": "collection_wide",
                "focus_release_reason": "explicit_collection_scope",
            }

        if not locked_document_name:
            return {
                "focus_decision": "release_to_discovery",
                "focus_release_reason": "no_locked_document",
            }

        release_reason = self._detect_focus_release_reason(question, resolved_question, locked_document_name)
        if self._question_has_explicit_referential_focus(question):
            return {
                "focus_decision": "keep_locked_document",
                "focus_release_reason": "explicit_referential_follow_up",
            }
        if self._is_follow_up_ambiguous(question) and release_reason is None:
            return {
                "focus_decision": "keep_locked_document",
                "focus_release_reason": "ambiguous_follow_up",
            }

        current_focus_terms = self._extract_focus_terms(resolved_question or question, limit=16)
        if len(current_focus_terms) <= 3 and release_reason is None:
            return {
                "focus_decision": "keep_locked_document",
                "focus_release_reason": "under_specified_follow_up",
            }
        if release_reason is not None:
            return {
                "focus_decision": "release_to_discovery",
                "focus_release_reason": release_reason,
            }
        if self._has_focus_continuity(question, resolved_question, locked_document_name):
            return {
                "focus_decision": "keep_locked_document",
                "focus_release_reason": "continuity_overlap",
            }
        return {
            "focus_decision": "release_to_discovery",
            "focus_release_reason": "self_contained_new_question",
        }

    def _get_active_mode(self, chat_history) -> str:
        for message in reversed(list(chat_history or [])):
            if str(message.get("role", "")).strip().lower() != "assistant":
                continue
            route = str(message.get("route", "")).strip().lower()
            if route in {MODE_CASUAL, MODE_RETRIEVAL}:
                return route
        return MODE_CASUAL

    def _resolve_requested_mode(self, question: str, chat_history) -> tuple[str, str | None]:
        active_mode = self._get_active_mode(chat_history)
        normalized_question = self._normalize_identifier(question)
        retrieval_command = self._normalize_identifier(MODE_SWITCH_TO_RETRIEVAL_COMMAND)
        casual_command = self._normalize_identifier(MODE_SWITCH_TO_CASUAL_COMMAND)

        if normalized_question == retrieval_command:
            if active_mode == MODE_RETRIEVAL:
                return MODE_RETRIEVAL, "already_retrieval"
            return MODE_RETRIEVAL, "switched_to_retrieval"

        if normalized_question == casual_command:
            if active_mode == MODE_CASUAL:
                return MODE_CASUAL, "already_casual"
            return MODE_CASUAL, "switched_to_casual"

        return active_mode, None

    def _format_mode_response(self, mode: str, answer_text: str) -> str:
        body = str(answer_text or "").strip()

        if mode == MODE_RETRIEVAL:
            title = RETRIEVAL_RESPONSE_TITLE
            footer = RETRIEVAL_RESPONSE_FOOTER
            fallback_body = "Modo retrieval ativo."
        else:
            title = CASUAL_RESPONSE_TITLE
            footer = CASUAL_RESPONSE_FOOTER
            fallback_body = "Modo casual ativo."

        if not body:
            body = fallback_body

        return f"**{title}**\n\n{body}\n\n{footer}"

    def _build_mode_transition_answer(self, mode: str, transition: str) -> str:
        transitions = {
            (MODE_CASUAL, "switched_to_casual"): "Modo casual ativado. Vou manter a conversa sem buscar nos documentos.",
            (MODE_CASUAL, "already_casual"): "Voce ja esta no modo casual.",
            (MODE_RETRIEVAL, "switched_to_retrieval"): "Modo retrieval ativado. Agora vou responder com base nos documentos recuperados.",
            (MODE_RETRIEVAL, "already_retrieval"): "Voce ja esta no modo retrieval.",
        }
        body = transitions.get((mode, transition), "Modo atualizado.")
        return self._format_mode_response(mode, body)

    def _is_follow_up_ambiguous(self, question: str) -> bool:
        normalized = self._normalize_identifier(question)
        if not normalized:
            return False
        if any(marker in normalized for marker in REWRITE_REFERENCE_MARKERS):
            return True
        return len(normalized.split()) <= 5 and normalized in {
            "e aquela reuniao",
            "e essa reuniao",
            "essa reuniao",
            "aquela reuniao",
            "e isso",
            "e essa",
            "e esse",
            "isso",
            "essa",
            "esse",
        }

    def _should_rewrite_question(self, question: str, chat_history) -> bool:
        if not chat_history:
            return False

        normalized = self._normalize_identifier(question)
        if not normalized:
            return False

        follow_up_markers = (
            "ele",
            "ela",
            "eles",
            "elas",
            "esse",
            "essa",
            "esses",
            "essas",
            "isso",
            "isto",
            "dele",
            "dela",
            "deles",
            "delas",
            "sobre ele",
            "sobre ela",
            "quais sao",
            "qual deles",
            "qual delas",
            "e quais",
            "mas quais",
        )
        if any(marker in normalized for marker in follow_up_markers):
            return True

        return len(normalized.split()) <= 6

    def _rewrite_question_for_retrieval(self, question: str, history_text: str, chat_history, force: bool = False) -> str:
        if not self.query_rewrite_chain or history_text == "Sem conversa anterior.":
            return question
        if not force and not self._should_rewrite_question(question, chat_history):
            return question

        rewritten = self.query_rewrite_chain.invoke(
            {
                "chat_history": history_text,
                "question": question,
            }
        ).strip()
        rewritten = re.sub(r"^(consulta|pergunta reescrita|query)\s*:\s*", "", rewritten, flags=re.IGNORECASE).strip()
        return rewritten or question
