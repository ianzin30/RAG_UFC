"""The answer contract: trace v2 fields and citation normalization for presentation.

``RAGService.ask_question_with_trace`` returns ``answer_text``, ``status``, ``route``,
``claims``, ``cited_sources`` and ``evidence``. These helpers carry those fields into
stored messages and drop sources that do not match the answer's evidence.
"""

from .rag.v2.Sources import displayed_sources, normalize_presentation, preserve_v2_fields

ANSWER_STATES = ("answered", "partial", "casual", "abstained", "clarification_required")

__all__ = ["ANSWER_STATES", "displayed_sources", "normalize_presentation", "preserve_v2_fields"]
