"""Typed state containers for RAG orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field


# Esta opcao representa uma escolha exibida quando o retrieval pede clarificacao.
@dataclass
class ClarificationOption:
    label: str
    normalized: str

    def to_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "normalized": self.normalized,
        }

    @classmethod
    def from_dict(cls, raw_option: object) -> "ClarificationOption | None":
        if not isinstance(raw_option, dict):
            return None

        label = str(raw_option.get("label") or "").strip()
        normalized = str(raw_option.get("normalized") or "").strip()
        if not label or not normalized:
            return None
        return cls(label=label, normalized=normalized)


# Este estado guarda a pergunta original e as opcoes pendentes de clarificacao.
@dataclass
class PendingRetrievalClarification:
    original_question: str
    resolved_question: str
    target_document_name: str | None
    retrieval_intent: str | None
    options: list[ClarificationOption] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "original_question": self.original_question,
            "resolved_question": self.resolved_question,
            "target_document_name": self.target_document_name,
            "retrieval_intent": self.retrieval_intent,
            "options": [option.to_dict() for option in self.options],
        }

    @classmethod
    def from_dict(cls, raw_payload: object) -> "PendingRetrievalClarification | None":
        if not isinstance(raw_payload, dict):
            return None

        options = [
            option
            for option in (
                ClarificationOption.from_dict(raw_option)
                for raw_option in list(raw_payload.get("options") or [])
            )
            if option is not None
        ]
        if not options:
            return None

        return cls(
            original_question=str(raw_payload.get("original_question") or "").strip(),
            resolved_question=str(raw_payload.get("resolved_question") or "").strip(),
            target_document_name=str(raw_payload.get("target_document_name") or "").strip() or None,
            retrieval_intent=str(raw_payload.get("retrieval_intent") or "").strip() or None,
            options=options,
        )


# Este estado guarda a lista de arquivos quando o usuario ainda precisa escolher um deles.
@dataclass
class PendingDocumentRefinement:
    matched_documents: list[str]
    resolved_question: str
    original_question: str

    def to_dict(self) -> dict[str, object]:
        return {
            "matched_documents": list(self.matched_documents),
            "resolved_question": self.resolved_question,
            "original_question": self.original_question,
        }


# Este foco lembra qual documento e qual intencao continuam ativos entre mensagens.
@dataclass
class RetrievalFocusState:
    scope_type: str
    target_document_name: str | None = None
    resolved_question: str | None = None
    retrieval_intent: str | None = None
    pending_clarification: PendingRetrievalClarification | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "scope_type": self.scope_type,
            "target_document_name": self.target_document_name,
            "resolved_question": self.resolved_question,
            "retrieval_intent": self.retrieval_intent,
            "pending_clarification": (
                self.pending_clarification.to_dict() if self.pending_clarification is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, raw_payload: object) -> "RetrievalFocusState | None":
        if not isinstance(raw_payload, dict):
            return None

        scope_type = str(raw_payload.get("scope_type") or "").strip()
        if not scope_type:
            return None

        return cls(
            scope_type=scope_type,
            target_document_name=str(raw_payload.get("target_document_name") or "").strip() or None,
            resolved_question=str(raw_payload.get("resolved_question") or "").strip() or None,
            retrieval_intent=str(raw_payload.get("retrieval_intent") or "").strip() or None,
            pending_clarification=PendingRetrievalClarification.from_dict(raw_payload.get("pending_clarification")),
        )
