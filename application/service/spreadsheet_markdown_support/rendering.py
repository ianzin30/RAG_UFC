"""Markdown rendering helpers for spreadsheet extraction."""

from __future__ import annotations

from .constants import MAX_SAMPLE_VALUES
from .models import SheetData
from .numbers import format_number, to_number


# Esta renderizacao transforma a estrutura da planilha em markdown legivel e indexavel.
def render_sheet(sheet: SheetData, file_name: str) -> list[str]:
    lines = [
        f"## Sheet: {sheet.name}",
        "",
        f"Spreadsheet file: {file_name}",
        f"Sheet name: {sheet.name}",
        f"Header columns: {', '.join(sheet.headers) if sheet.headers else 'No headers detected'}",
        f"Data rows indexed: {len(sheet.rows)}",
    ]

    if sheet.omitted_rows:
        lines.append(f"Omitted rows: {sheet.omitted_rows}")

    column_profiles = build_column_profiles(sheet.headers, sheet.rows)
    if column_profiles:
        lines.extend(["", "Column profiles:"])
        for profile in column_profiles:
            lines.append(f"- {profile}")

    if sheet.people_entries:
        lines.extend(["", "People index:"])
        for entry in sheet.people_entries:
            role_suffix = f" | Role: {entry.role}" if entry.role else ""
            lines.append(
                f"- Person: {entry.name}{role_suffix} | Sheet: {sheet.name} | Row: {entry.row_number}"
            )

    if sheet.rows:
        lines.extend(["", "Row records:"])
        for row in sheet.rows:
            pairs_text = " | ".join(f"{header}={value}" for header, value in row.pairs)
            lines.append(
                f"- Spreadsheet file {file_name} | Sheet {sheet.name} | Row {row.row_number}: {pairs_text}"
            )
    else:
        lines.extend(["", "No non-empty data rows were indexed."])

    lines.append("")
    return lines


# Estes perfis resumem colunas para melhorar busca e entendimento do conteudo.
def build_column_profiles(headers: list[str], rows) -> list[str]:
    profiles = []
    for header in headers:
        values = []
        for row in rows:
            for row_header, row_value in row.pairs:
                if row_header == header and row_value:
                    values.append(row_value)
                    break

        if not values:
            continue

        numeric_values = [to_number(value) for value in values]
        numeric_values = [value for value in numeric_values if value is not None]
        if len(numeric_values) >= 2:
            profiles.append(
                (
                    f"{header}: numeric count={len(numeric_values)}, "
                    f"sum={format_number(sum(numeric_values))}, "
                    f"min={format_number(min(numeric_values))}, "
                    f"max={format_number(max(numeric_values))}"
                )
            )
            continue

        samples = []
        seen = set()
        for value in values:
            sample = value[:80]
            if sample in seen:
                continue
            seen.add(sample)
            samples.append(sample)
            if len(samples) >= MAX_SAMPLE_VALUES:
                break

        if samples:
            profiles.append(f"{header}: sample values={'; '.join(samples)}")

    return profiles
