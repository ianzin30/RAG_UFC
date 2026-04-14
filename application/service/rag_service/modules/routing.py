import re

from ..constants import (
    CASUAL_RESPONSE_FOOTER,
    CASUAL_RESPONSE_TITLE,
    MODE_CASUAL,
    MODE_RETRIEVAL,
    MODE_SWITCH_TO_CASUAL_COMMAND,
    MODE_SWITCH_TO_RETRIEVAL_COMMAND,
    RETRIEVAL_RESPONSE_FOOTER,
    RETRIEVAL_RESPONSE_TITLE,
    REWRITE_REFERENCE_MARKERS,
)


class RoutingMixin:
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
