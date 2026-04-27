"""
Answer processing and cleaning for generation and evaluation.

Separates:
- answer_text: formatted answer for display (with mode wrapper)
- generated_answer: clean answer for evaluation (without wrapper)

This ensures benchmark diagnostics evaluate the actual answer content,
while preserving the chat interface formatting for live usage.
"""
from __future__ import annotations

import re


class AnswerProcessingMixin:
    """Clean and extract answers from generated text."""

    def _extract_clean_answer(self, answer_text: str) -> str:
        """Extract clean answer by removing wrapper markers and mode-switching text.

        Removes:
        - "**RETRIEVAL**" or "**CASUAL**" headers
        - "Para sair do modo..." footers (mode switching instructions)
        - Extra whitespace

        Args:
            answer_text: Full formatted answer with wrapper

        Returns:
            Clean answer suitable for evaluation
        """
        text = str(answer_text or "").strip()

        # Remove mode headers like "**RETRIEVAL**" or "**CASUAL**"
        text = re.sub(r'^\*\*[A-Z]+\*\*\s*', '', text)

        # Remove mode switching footers
        # Match: "Para sair do modo de [retrieval|casual], digite [command]."
        text = re.sub(
            r'Para\s+sair\s+do\s+modo\s+de\s+\w+,\s+digite\s+"[^"]*"\.',
            '',
            text,
            flags=re.IGNORECASE
        )

        # Remove extra whitespace created by removal
        text = re.sub(r'\n\n+', '\n', text)
        text = text.strip()

        return text

    def _build_answer_for_display(self, clean_answer: str, mode: str) -> str:
        """Format clean answer with mode wrapper for display.

        Args:
            clean_answer: Core answer content
            mode: Either "retrieval" or "casual"

        Returns:
            Formatted answer with wrapper for display
        """
        return self._format_mode_response(mode, clean_answer)
