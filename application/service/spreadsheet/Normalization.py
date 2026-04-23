"""Normalization helpers for spreadsheet markdown extraction."""
# Simple: Clean and standardize spreadsheet data

from __future__ import annotations

import re
import unicodedata

from .Constants import MAX_CELL_CHARS


def normalize_identifier(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_cell(value) -> str:
    if value is None:
        return ""

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ")
        except TypeError:
            return value.isoformat()

    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) > MAX_CELL_CHARS:
        return text[: MAX_CELL_CHARS - 3] + "..."
    return text


def make_headers(raw_headers: list[str]) -> list[str]:
    headers = []
    seen = {}
    for index, raw_header in enumerate(raw_headers, start=1):
        base = raw_header or f"Column_{index}"
        normalized = re.sub(r"\s+", " ", str(base)).strip() or f"Column_{index}"
        count = seen.get(normalized, 0)
        seen[normalized] = count + 1
        headers.append(normalized if count == 0 else f"{normalized}_{count + 1}")
    return headers
