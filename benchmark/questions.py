"""Question loading and validation for benchmark runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


KNOWN_QUESTION_FIELDS = {
    "id",
    "collection",
    "question",
    "expected_answer",
    "accepted_answers",
    "category",
    "source_document",
    "metadata",
}


@dataclass(frozen=True)
class BenchmarkQuestion:
    id: str | int
    collection: str
    question: str
    expected_answer: str
    accepted_answers: tuple[str, ...] = ()
    category: str | None = None
    source_document: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    extras: dict[str, object] = field(default_factory=dict)

    @property
    def normalized_id(self) -> str:
        return str(self.id).strip()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "collection": self.collection,
            "question": self.question,
            "expected_answer": self.expected_answer,
        }
        if self.accepted_answers:
            payload["accepted_answers"] = list(self.accepted_answers)
        if self.category:
            payload["category"] = self.category
        if self.source_document:
            payload["source_document"] = self.source_document
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        payload.update(self.extras)
        return payload


def _require_non_empty_string(payload: dict[str, Any], key: str, *, question_index: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Question #{question_index} is missing a non-empty '{key}' field.")
    return value.strip()


def _coerce_optional_string_list(raw_value: object, *, question_index: int) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, str):
        compact = raw_value.strip()
        return (compact,) if compact else ()
    if not isinstance(raw_value, list):
        raise ValueError(
            f"Question #{question_index} has an invalid 'accepted_answers' field. Use a string list."
        )

    answers: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_value:
        compact = str(raw_item or "").strip()
        if not compact or compact in seen:
            continue
        seen.add(compact)
        answers.append(compact)
    return tuple(answers)


def load_questions(questions_path: Path) -> list[BenchmarkQuestion]:
    try:
        payload = json.loads(questions_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Questions file not found: {questions_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in questions file {questions_path}: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("Benchmark questions file must contain a JSON array.")

    questions: list[BenchmarkQuestion] = []
    seen_ids: set[str] = set()
    for index, raw_question in enumerate(payload, start=1):
        if not isinstance(raw_question, dict):
            raise ValueError(f"Question #{index} must be a JSON object.")

        question_id = raw_question.get("id")
        if not isinstance(question_id, (str, int)) or not str(question_id).strip():
            raise ValueError(f"Question #{index} is missing a valid 'id' field.")

        normalized_id = str(question_id).strip()
        if normalized_id in seen_ids:
            raise ValueError(f"Duplicate benchmark question id: {normalized_id}")
        seen_ids.add(normalized_id)

        collection = _require_non_empty_string(raw_question, "collection", question_index=index)
        question_text = _require_non_empty_string(raw_question, "question", question_index=index)
        expected_answer = _require_non_empty_string(
            raw_question,
            "expected_answer",
            question_index=index,
        )
        accepted_answers = _coerce_optional_string_list(
            raw_question.get("accepted_answers"),
            question_index=index,
        )

        raw_metadata = raw_question.get("metadata")
        if raw_metadata is None:
            metadata: dict[str, object] = {}
        elif isinstance(raw_metadata, dict):
            metadata = dict(raw_metadata)
        else:
            raise ValueError(f"Question #{index} has an invalid 'metadata' field. Use an object.")

        category = str(raw_question.get("category") or "").strip() or None
        source_document = str(raw_question.get("source_document") or "").strip() or None
        extras = {
            key: value
            for key, value in raw_question.items()
            if key not in KNOWN_QUESTION_FIELDS
        }
        questions.append(
            BenchmarkQuestion(
                id=question_id,
                collection=collection,
                question=question_text,
                expected_answer=expected_answer,
                accepted_answers=accepted_answers,
                category=category,
                source_document=source_document,
                metadata=metadata,
                extras=extras,
            )
        )
    return questions

