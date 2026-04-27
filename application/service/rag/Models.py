"""Typed state containers for RAG orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClarificationOption:
    """A single choice presented to the user when retrieval needs clarification."""

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


@dataclass
class PendingRetrievalClarification:
    """State when retrieval asks the user to clarify which documents or intent they meant.

    Stores the original and resolved questions plus the list of options to choose from.
    """

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


@dataclass
class PendingDocumentRefinement:
    """State when the user must choose which document(s) to search in.

    Stores matched document names and the question being refined.
    """

    matched_documents: list[str]
    resolved_question: str
    original_question: str

    def to_dict(self) -> dict[str, object]:
        return {
            "matched_documents": list(self.matched_documents),
            "resolved_question": self.resolved_question,
            "original_question": self.original_question,
        }


@dataclass
class RetrievalFocusState:
    """Persistent retrieval context across chat messages.

    Remembers the target document, retrieval intent, and focus terms so users
    can ask follow-up questions without re-specifying scope.
    """

    scope_type: str
    target_document_name: str | None = None
    resolved_question: str | None = None
    retrieval_intent: str | None = None
    focus_terms: list[str] = field(default_factory=list)
    document_shortlist: list[str] = field(default_factory=list)
    focus_decision: str | None = None
    focus_reason: str | None = None
    pending_clarification: PendingRetrievalClarification | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "scope_type": self.scope_type,
            "target_document_name": self.target_document_name,
            "resolved_question": self.resolved_question,
            "retrieval_intent": self.retrieval_intent,
            "focus_terms": list(self.focus_terms),
            "document_shortlist": list(self.document_shortlist),
            "focus_decision": self.focus_decision,
            "focus_reason": self.focus_reason,
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
            focus_terms=[
                str(term).strip()
                for term in list(raw_payload.get("focus_terms") or [])
                if str(term).strip()
            ],
            document_shortlist=[
                str(document_name).strip()
                for document_name in list(raw_payload.get("document_shortlist") or [])
                if str(document_name).strip()
            ],
            focus_decision=str(raw_payload.get("focus_decision") or "").strip() or None,
            focus_reason=str(raw_payload.get("focus_reason") or "").strip() or None,
            pending_clarification=PendingRetrievalClarification.from_dict(raw_payload.get("pending_clarification")),
        )
