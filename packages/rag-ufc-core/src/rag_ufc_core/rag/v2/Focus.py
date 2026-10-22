"""Literal source-focus validation and compact source presentation data."""

from __future__ import annotations

import re
from collections import defaultdict


def _normalized_with_offsets(text: str) -> tuple[str, list[int]]:
    """Normalize whitespace while retaining the original position of each char."""
    normalized: list[str] = []
    positions: list[int] = []
    pending_space = False
    for index, char in enumerate(text):
        if char.isspace():
            pending_space = bool(normalized)
            continue
        if pending_space:
            normalized.append(" ")
            positions.append(index)
            pending_space = False
        normalized.append(char)
        positions.append(index)
    return "".join(normalized), positions


def literal_span(text: str, quote: str) -> tuple[int, int] | None:
    """Find a literal quote allowing only whitespace differences."""
    normalized_text, positions = _normalized_with_offsets(text)
    normalized_quote, _ = _normalized_with_offsets(quote)
    if not normalized_quote:
        return None
    start = normalized_text.casefold().find(normalized_quote.casefold())
    if start < 0:
        return None
    end = start + len(normalized_quote)
    return positions[start], positions[end - 1] + 1


def resolve_focus_spans(selections, evidence_by_id, claim_ids) -> dict[str, list[dict]]:
    """Validate agent selections and merge exact/overlapping source intervals."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    claim_ids = set(claim_ids)
    for selection in selections:
        claim_id = str(getattr(selection, "claim_id", "") or "")
        evidence_id = str(getattr(selection, "evidence_id", "") or "")
        quote = str(getattr(selection, "quote", "") or "").strip()
        evidence = evidence_by_id.get(evidence_id)
        if claim_id not in claim_ids or evidence is None or not quote:
            continue
        span = literal_span(evidence.excerpt, quote)
        if span is None:
            continue
        grouped[evidence_id].append(
            {
                "claim_ids": [claim_id],
                "quote": evidence.excerpt[span[0] : span[1]],
                "start": span[0],
                "end": span[1],
            }
        )

    resolved: dict[str, list[dict]] = {}
    for evidence_id, spans in grouped.items():
        merged: list[dict] = []
        for span in sorted(spans, key=lambda item: (item["start"], item["end"])):
            if merged and span["start"] <= merged[-1]["end"]:
                previous = merged[-1]
                previous["end"] = max(previous["end"], span["end"])
                previous["quote"] = evidence_by_id[evidence_id].excerpt[
                    previous["start"] : previous["end"]
                ]
                previous["claim_ids"] = list(
                    dict.fromkeys(previous["claim_ids"] + span["claim_ids"])
                )
            else:
                merged.append(span)
        resolved[evidence_id] = merged
    return resolved
