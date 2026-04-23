"""Intent detection helpers for collection-routing replies."""
# Simple: Understand what the user is asking for

from __future__ import annotations

import re
import unicodedata

from .RouteConstants import INVENTORY_VERBS


def normalize_text(text: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def detect_collection_intent(normalized: str) -> str | None:
    if is_spreadsheet_question(normalized):
        return "spreadsheets"
    if is_image_question(normalized):
        return "images"
    if is_pdf_question(normalized):
        return "pdfs"
    if is_extractor_question(normalized):
        return "extractor"
    if is_folder_question(normalized):
        return "folder"
    if is_files_question(normalized):
        return "files"
    return None


def is_collection_follow_up(normalized: str) -> bool:
    relaxed = re.sub(r"[^a-z0-9\s]+", " ", normalized)
    relaxed = re.sub(r"\s+", " ", relaxed).strip()
    if len(relaxed.split()) > 8:
        return False

    follow_up_patterns = (
        r"^(e|mas|certo|ok|beleza|perfeito|entendi)( mas)?( quais( sao)?| qual( deles| delas)?| os nomes| as planilhas| os pdfs| as imagens)?$",
        r"^quais( sao)?\??$",
        r"^qual( deles| delas)?\??$",
        r"^e quais( sao)?\??$",
        r"^mas quais( sao)?\??$",
        r"^os nomes\??$",
    )
    return any(re.search(pattern, relaxed) for pattern in follow_up_patterns)


def is_inventory_question(normalized: str, nouns: tuple[str, ...]) -> bool:
    if not any(noun in normalized for noun in nouns):
        return False
    return any(re.search(rf"\b{verb}", normalized) for verb in INVENTORY_VERBS)


def is_files_question(normalized: str) -> bool:
    return is_inventory_question(normalized, ("arquivo", "arquivos", "documento", "documentos"))


def is_spreadsheet_question(normalized: str) -> bool:
    nouns = ("planilha", "planilhas", "excel", "excels", "xls", ".xls", ".xlsx", ".csv", "sheet", "sheets")
    return is_inventory_question(normalized, nouns)


def is_image_question(normalized: str) -> bool:
    nouns = ("imagem", "imagens", ".png", ".jpg", ".jpeg", ".webp", "foto", "fotos")
    return is_inventory_question(normalized, nouns)


def is_pdf_question(normalized: str) -> bool:
    return is_inventory_question(normalized, ("pdf", "pdfs"))


def is_extractor_question(normalized: str) -> bool:
    return is_inventory_question(normalized, ("extrator", "extractor", "metodo de extracao", "metodo de ingestao"))


def is_folder_question(normalized: str) -> bool:
    folder_patterns = (
        r"\bde qual pasta\b",
        r"\bqual pasta\b",
        r"\bnome da pasta\b",
        r"\bpasta de origem\b",
        r"\borigem da pasta\b",
        r"\bvieram da pasta\b",
        r"\bveio da pasta\b",
        r"\bpasta do google drive\b",
    )
    return any(re.search(pattern, normalized) for pattern in folder_patterns)
