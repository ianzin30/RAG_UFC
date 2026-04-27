"""
Optimize grader payload to fix JSON parsing failures.

Problems fixed:
1. Large context (>10K chars) breaks JSON serialization
2. Portuguese special characters (á, é, ã, ç) not properly escaped
3. Invalid JSON prevents agent grading

Solutions:
1. Cap context size in grader payload
2. Use selected chunks instead of full answer_context
3. Validate serialization before sending to grader
4. Progressive truncation with fallback
"""
from __future__ import annotations

import json
from typing import Any


class GraderPayloadOptimizationMixin:
    """Optimize grader payload for reliable JSON parsing."""

    MAX_CONTEXT_CHARS = 6000  # Safe threshold for JSON serialization
    CONTEXT_FALLBACK_CHARS = 4000  # Fallback size if first attempt fails

    def _truncate_context_safely(
        self,
        context: str,
        max_chars: int = MAX_CONTEXT_CHARS,
    ) -> str:
        """Truncate context with word boundary preservation.

        Args:
            context: Context string to truncate
            max_chars: Maximum characters to keep

        Returns:
            Truncated context ending at word boundary
        """
        if len(context) <= max_chars:
            return context

        # Truncate and find last complete word
        truncated = context[:max_chars]
        last_space = truncated.rfind(' ')

        if last_space > max_chars * 0.8:  # Only if we found a space reasonably close
            truncated = truncated[:last_space] + ' [...truncated]'
        else:
            truncated = truncated.strip() + ' [...truncated]'

        return truncated

    def _validate_grader_payload_json(self, payload: dict[str, Any]) -> bool:
        """Validate that payload can be serialized to JSON.

        Args:
            payload: Payload dict to validate

        Returns:
            True if payload serializes successfully
        """
        try:
            # Attempt serialization with UTF-8
            json.dumps(payload, ensure_ascii=False)
            return True
        except (TypeError, ValueError, UnicodeEncodeError):
            return False

    def _optimize_grader_payload(
        self,
        grader_payload: dict[str, object],
    ) -> dict[str, object]:
        """Optimize grader payload to fix JSON serialization.

        Steps:
        1. Truncate answer_context to MAX_CONTEXT_CHARS
        2. Validate serialization
        3. If validation fails, further truncate and try again
        4. Use selected_context chunks if full context causes issues

        Args:
            grader_payload: Raw grader payload

        Returns:
            Optimized payload that serializes reliably
        """
        optimized = dict(grader_payload)

        # Step 1: Truncate answer_context
        answer_context = str(optimized.get("answer_context") or "")
        if len(answer_context) > self.MAX_CONTEXT_CHARS:
            optimized["answer_context"] = self._truncate_context_safely(
                answer_context,
                self.MAX_CONTEXT_CHARS,
            )
            optimized["answer_context_truncated"] = True

        # Step 2: Validate serialization
        if self._validate_grader_payload_json(optimized):
            return optimized

        # Step 3: Further truncate on failure
        answer_context = str(optimized.get("answer_context") or "")
        if len(answer_context) > self.CONTEXT_FALLBACK_CHARS:
            optimized["answer_context"] = self._truncate_context_safely(
                answer_context,
                self.CONTEXT_FALLBACK_CHARS,
            )

        # Step 4: If still failing, use only selected_context excerpts
        if not self._validate_grader_payload_json(optimized):
            selected = optimized.get("selected_context", [])
            excerpt_texts = [
                str(entry.get("text") or "")[:400]  # 400 chars per excerpt
                for entry in (selected or [])
                if entry
            ]
            combined_excerpts = "\n---\n".join(excerpt_texts)
            optimized["answer_context"] = combined_excerpts
            optimized["answer_context_fallback_to_excerpts"] = True

        return optimized

    def _build_safe_grader_payload(
        self,
        question_id: str,
        question: str,
        expected_answer: str,
        generated_answer: str,
        selected_context: list[dict[str, object]],
        answer_context: str,
        deterministic_metrics: dict[str, object],
        deterministic_grounding: dict[str, object],
        deterministic_failure: dict[str, object],
    ) -> dict[str, object]:
        """Build grader payload with size and encoding safety.

        Args:
            question_id: Question ID
            question: Question text
            expected_answer: Expected answer
            generated_answer: Generated answer (clean, without wrapper)
            selected_context: Selected context chunks
            answer_context: Full answer context
            deterministic_metrics: Retrieval metrics
            deterministic_grounding: Grounding info
            deterministic_failure: Failure classification

        Returns:
            Safe grader payload
        """
        payload = {
            "question_id": str(question_id),
            "question": str(question)[:1000],  # Cap question size
            "expected_answer": str(expected_answer)[:500],
            "generated_answer": str(generated_answer)[:500],
            "selected_context": selected_context[:5],  # First 5 chunks only
            "answer_context": str(answer_context)[:self.MAX_CONTEXT_CHARS],
            "deterministic_retrieval_metrics": dict(deterministic_metrics or {}),
            "deterministic_grounding": dict(deterministic_grounding or {}),
            "deterministic_failure": dict(deterministic_failure or {}),
        }

        # Optimize and validate
        optimized = self._optimize_grader_payload(payload)

        # Final validation
        if not self._validate_grader_payload_json(optimized):
            # Last resort: minimal payload
            optimized = {
                "question_id": str(question_id),
                "question": str(question)[:200],
                "expected_answer": str(expected_answer)[:200],
                "generated_answer": str(generated_answer)[:200],
                "deterministic_retrieval_metrics": {},
                "deterministic_grounding": {},
                "deterministic_failure": {},
            }

        return optimized
