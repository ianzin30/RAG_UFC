"""Heuristics for extracting person-like entries from spreadsheets."""
# Simple: Find people names in spreadsheet data

from __future__ import annotations

import re

from .Constants import PERSON_BLOCKLIST, PERSON_PREFIX_BLOCKLIST, ROLE_BLOCKLIST
from .Models import PersonEntry, RowRecord
from .Normalization import normalize_identifier
from .Numbers import to_number


# Esta etapa extrai um pequeno indice de pessoas a partir das linhas da planilha.
def build_people_entries(sheet_name: str, rows: list[RowRecord]) -> list[PersonEntry]:
    entries = []
    seen = set()
    for row in rows:
        entry = extract_person_entry(sheet_name, row)
        if not entry:
            continue
        key = (entry.name, entry.role, entry.row_number, entry.sheet_name)
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


# Esta heuristica tenta transformar uma linha em entidade pessoa + cargo.
def extract_person_entry(sheet_name: str, row: RowRecord) -> PersonEntry | None:
    if not row.pairs:
        return None

    first_header, first_value = row.pairs[0]
    if not looks_like_person_name(first_value):
        return None

    role = extract_role_from_pairs(row.pairs[1:])
    return PersonEntry(
        name=first_value,
        role=role,
        row_number=row.row_number,
        sheet_name=sheet_name,
        source_header=first_header,
    )


# Este helper procura o primeiro par que parece descrever um papel ou cargo.
def extract_role_from_pairs(pairs: list[tuple[str, str]]) -> str | None:
    for header, value in pairs:
        if looks_like_role(header, value):
            return value
    return None


# Esta regra tenta diferenciar nomes reais de rotulos administrativos ou totais.
def looks_like_person_name(value: str) -> bool:
    if not value:
        return False

    text = re.sub(r"\s+", " ", value).strip()
    if len(text) < 5 or any(char.isdigit() for char in text):
        return False
    if not any(char.islower() for char in text):
        return False

    normalized = normalize_identifier(text)
    if not normalized or normalized in PERSON_BLOCKLIST:
        return False
    if any(normalized.startswith(prefix) for prefix in PERSON_PREFIX_BLOCKLIST):
        return False

    tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
    return len(tokens) >= 2


# Esta regra tenta capturar cargos sem confundir datas, numeros ou ruido tabular.
def looks_like_role(header: str, value: str) -> bool:
    if not value:
        return False

    text = re.sub(r"\s+", " ", value).strip()
    normalized = normalize_identifier(text)
    if not normalized or normalized in ROLE_BLOCKLIST:
        return False
    if to_number(text) is not None:
        return False
    if re.search(r"\d{4}-\d{2}-\d{2}", text):
        return False

    tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
    if not tokens or len(tokens) > 12:
        return False

    normalized_header = normalize_identifier(header)
    if normalized_header.startswith("column_") and len(tokens) <= 1:
        return False
    return True
