"""Typed spreadsheet structures used by the markdown renderer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RowRecord:
    row_number: int
    pairs: list[tuple[str, str]]


@dataclass(frozen=True)
class PersonEntry:
    name: str
    role: str | None
    row_number: int
    sheet_name: str
    source_header: str


@dataclass(frozen=True)
class SheetData:
    name: str
    headers: list[str]
    rows: list[RowRecord]
    omitted_rows: int
    people_entries: list[PersonEntry]
