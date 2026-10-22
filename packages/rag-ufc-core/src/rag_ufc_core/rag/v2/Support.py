"""Shared text normalization for spreadsheet ingestion and deterministic evaluation."""

import re
import unicodedata

QUERY_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "qual",
    "quais",
    "que",
    "sobre",
    "sao",
    "se",
    "um",
    "uma",
}

def normalize_whitespace(text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line)

def normalize_identifier(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

def tokenize_search_text(text: str) -> list[str]:
        tokens = normalize_identifier(text).split()
        return [token for token in tokens if token not in QUERY_STOPWORDS and len(token) > 1]
