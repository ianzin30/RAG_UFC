"""Focus state helpers for retrieval continuity."""

from ..models import PendingRetrievalClarification, RetrievalFocusState


# Este mixin guarda o foco conversacional entre uma pergunta e a proxima.
class RAGServiceFocusStateMixin:
    # Este historico efetivo remove a mensagem de refinamento quando ela nao deve contaminar o retrieval.
    def _build_effective_history_text(self, chat_history, pending_refinement: dict[str, object] | None = None) -> str:
        history = list(chat_history or [])
        
        # Strip pending refinement or empty interaction turns where the bot asked for clarification that was ignored.
        cleaned_history = []
        for i in range(len(history)):
            msg = history[i]
            role = str(msg.get("role", "")).strip().lower()
            if role == "assistant":
                content = str(msg.get("content", ""))
                # If this message was a clarification/disambiguation prompt:
                if "Responda apenas com o numero da opcao desejada." in content or "Por favor, digite apenas o" in content:
                    # If this is the most recent assistant message and we are ignoring it/re-routing
                    if i == len(history) - 2 or (pending_refinement and i == len(history) - 1):
                        # Also pop the immediately preceding user question to completely erase the aborted topic
                        if cleaned_history and cleaned_history[-1].get("role") == "user":
                            cleaned_history.pop()
                        continue
            cleaned_history.append(msg)
            
        history = list(cleaned_history)
        if pending_refinement and history and history[-1].get("role") == "assistant" and "needs_document_refinement" in history[-1]:
            history = history[:-1]
            
        return self._format_chat_history(history)

    # Esta leitura devolve o foco atual ja normalizado para um dicionario simples.
    def _get_retrieval_focus(self) -> dict[str, object]:
        focus = RetrievalFocusState.from_dict(getattr(self, "last_retrieval_focus", None))
        return focus.to_dict() if focus is not None else {}

    # Esta escrita registra o escopo atual para os follow-ups seguintes.
    def _set_retrieval_focus(
        self,
        *,
        scope_type: str,
        target_document_name: str | None = None,
        resolved_question: str | None = None,
        retrieval_intent: str | None = None,
        pending_clarification: dict[str, object] | None = None,
    ) -> None:
        focus = RetrievalFocusState(
            scope_type=scope_type,
            target_document_name=target_document_name,
            resolved_question=resolved_question,
            retrieval_intent=retrieval_intent,
            pending_clarification=PendingRetrievalClarification.from_dict(pending_clarification),
        )
        self.last_retrieval_focus = focus.to_dict()

    # Este helper decide se ainda existe um documento travado para perguntas de continuidade.
    def _get_locked_target_document_name(self) -> str | None:
        focus = RetrievalFocusState.from_dict(getattr(self, "last_retrieval_focus", None))
        if focus is None or not focus.target_document_name:
            return None

        if focus.scope_type in {"document", "scope_locked", "clarification_pending", "clarification_resolved"}:
            return focus.target_document_name
        if focus.scope_type in {"collection", "collection_wide"}:
            return None
        if focus.pending_clarification is not None:
            return focus.target_document_name
        return focus.target_document_name

    # Este helper recupera a clarificacao pendente quando o usuario ainda precisa escolher uma opcao.
    def _get_pending_retrieval_clarification(self) -> dict[str, object] | None:
        focus = RetrievalFocusState.from_dict(getattr(self, "last_retrieval_focus", None))
        if focus is None or focus.pending_clarification is None:
            return None
        return focus.pending_clarification.to_dict()
