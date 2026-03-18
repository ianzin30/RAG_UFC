from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ..collections.contracts import EntityRecord, SpreadsheetModel, SpreadsheetRow, SpreadsheetSheet
from .markdown import (
    build_person_entry,
    extract_role_from_pairs,
    normalize_identifier,
    to_number,
)


class SpreadsheetNormalizer:
    def normalize(
        self,
        document_name: str,
        markdown_text: str,
        document_format: str | None = None,
    ) -> SpreadsheetModel:
        normalized_format = (document_format or Path(document_name).suffix.lstrip(".") or None)
        structured = self._parse_structured_markdown(document_name, markdown_text, normalized_format)
        if structured.sheets:
            return structured

        markdown_tables = self._parse_markdown_tables(document_name, markdown_text, normalized_format)
        if markdown_tables.sheets:
            return markdown_tables

        return SpreadsheetModel(
            format=normalized_format,
            source_file=document_name,
            summary_lines=["Nao foi possivel estruturar a planilha a partir do markdown extraido."],
            sheets=[],
        )

    def _normalize_whitespace(self, text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line)

    def _parse_structured_markdown(
        self,
        document_name: str,
        markdown_text: str,
        document_format: str | None,
    ) -> SpreadsheetModel:
        lines = [line.strip() for line in self._normalize_whitespace(markdown_text).split("\n") if line.strip()]
        if not any(line.startswith("## Sheet: ") for line in lines):
            return SpreadsheetModel(format=document_format, source_file=document_name, summary_lines=[], sheets=[])

        summary_lines = []
        sheets = []
        current_sheet = None
        section = "summary"
        spreadsheet_format = document_format
        source_file = document_name

        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("Spreadsheet format:") and not spreadsheet_format:
                spreadsheet_format = line.split(":", 1)[1].strip()
                continue
            if line.startswith("Spreadsheet file:"):
                source_file = line.split(":", 1)[1].strip() or source_file
            if line.startswith("## Sheet: "):
                if current_sheet is not None:
                    sheets.append(current_sheet)
                current_sheet = SpreadsheetSheet(name=line.split(":", 1)[1].strip())
                section = "sheet_summary"
                continue

            if current_sheet is None:
                if not line.lower().startswith("document type:"):
                    summary_lines.append(line)
                continue

            if line == "Column profiles:":
                section = "column_profiles"
                continue
            if line == "People index:":
                section = "people_index"
                continue
            if line == "Row records:":
                section = "row_records"
                continue
            if line == "No non-empty data rows were indexed.":
                current_sheet.summary_lines.append(line)
                continue

            if section == "column_profiles" and line.startswith("- "):
                current_sheet.column_profiles.append(line[2:].strip())
                continue
            if section == "people_index" and line.startswith("- "):
                person = self._parse_people_index_line(line[2:].strip(), current_sheet.name)
                if person:
                    current_sheet.people.append(person)
                continue
            if section == "row_records" and line.startswith("- "):
                row = self._parse_row_record_line(line[2:].strip(), current_sheet.name)
                if row:
                    current_sheet.rows.append(row)
                continue

            current_sheet.summary_lines.append(line)

        if current_sheet is not None:
            sheets.append(current_sheet)

        for sheet in sheets:
            if sheet.people:
                continue
            seen = set()
            for row in sheet.rows:
                if not row.entity:
                    continue
                key = (row.entity.name, row.entity.role, row.entity.row_number, row.entity.sheet_name)
                if key in seen:
                    continue
                seen.add(key)
                sheet.people.append(row.entity)

        return SpreadsheetModel(
            format=spreadsheet_format,
            source_file=source_file,
            summary_lines=summary_lines,
            sheets=sheets,
        )

    def _parse_people_index_line(self, line: str, default_sheet_name: str) -> EntityRecord | None:
        parts = [part.strip() for part in line.split(" | ") if part.strip()]
        if not parts:
            return None

        entity_name = None
        entity_role = None
        sheet_name = default_sheet_name
        row_number = None

        for part in parts:
            if part.startswith("Person:"):
                entity_name = part.split(":", 1)[1].strip()
            elif part.startswith("Role:"):
                entity_role = part.split(":", 1)[1].strip()
            elif part.startswith("Sheet:"):
                sheet_name = part.split(":", 1)[1].strip()
            elif part.startswith("Row:"):
                row_value = part.split(":", 1)[1].strip()
                if row_value.isdigit():
                    row_number = int(row_value)

        if not entity_name:
            return None

        person_entry = build_person_entry(sheet_name, row_number, "Person", entity_name, entity_role)
        if not person_entry:
            return None

        return EntityRecord(
            name=person_entry["name"],
            role=person_entry.get("role"),
            sheet_name=person_entry.get("sheet_name") or sheet_name,
            row_number=person_entry.get("row_number"),
        )

    def _parse_row_record_line(self, line: str, default_sheet_name: str) -> SpreadsheetRow | None:
        parts = [part.strip() for part in line.split(" | ") if part.strip()]
        if not parts:
            return None

        row_number = None
        sheet_name = default_sheet_name
        pairs = []

        for index, part in enumerate(parts):
            if index == 0 and part.startswith("Spreadsheet file "):
                continue
            if part.startswith("Sheet "):
                sheet_name = part[6:].strip()
                continue
            if part.startswith("Row "):
                row_prefix, _, first_pair = part.partition(":")
                row_id = row_prefix[4:].strip()
                if row_id.isdigit():
                    row_number = int(row_id)
                if first_pair.strip():
                    parsed_pair = self._parse_header_value_pair(first_pair.strip())
                    if parsed_pair:
                        pairs.append(parsed_pair)
                continue

            parsed_pair = self._parse_header_value_pair(part)
            if parsed_pair:
                pairs.append(parsed_pair)

        entity = self._extract_entity(sheet_name, row_number, pairs)
        return SpreadsheetRow(
            row_number=row_number,
            pairs=[{"header": header, "value": value} for header, value in pairs],
            entity=entity,
        )

    def _parse_header_value_pair(self, text: str) -> tuple[str, str] | None:
        header, separator, value = text.partition("=")
        if not separator:
            return None
        header = header.strip()
        value = value.strip()
        if not header or not value:
            return None
        return header, value

    def _extract_entity(
        self,
        sheet_name: str,
        row_number: int | None,
        pairs: list[tuple[str, str]],
    ) -> EntityRecord | None:
        if not pairs:
            return None
        first_header, first_value = pairs[0]
        entity_role = extract_role_from_pairs(pairs[1:]) if len(pairs) > 1 else None
        person_entry = build_person_entry(sheet_name, row_number, first_header, first_value, entity_role)
        if not person_entry:
            return None
        return EntityRecord(
            name=person_entry["name"],
            role=person_entry.get("role"),
            sheet_name=person_entry.get("sheet_name") or sheet_name,
            row_number=person_entry.get("row_number"),
        )

    def _is_markdown_table_row(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|")

    def _is_markdown_table_separator(self, line: str) -> bool:
        if not self._is_markdown_table_row(line):
            return False
        cells = [cell.strip().replace(" ", "") for cell in line.strip().strip("|").split("|")]
        return bool(cells) and all(cell and re.fullmatch(r":?-{3,}:?", cell) for cell in cells)

    def _extract_markdown_table_blocks(self, text: str) -> list[dict]:
        lines = (text or "").replace("\r\n", "\n").split("\n")
        blocks = []
        current_block = None
        previous_non_table_line = None

        for line_number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if self._is_markdown_table_row(stripped):
                if current_block is None:
                    current_block = {"label": previous_non_table_line, "lines": []}
                current_block["lines"].append((line_number, stripped))
                continue

            if current_block is not None:
                blocks.append(current_block)
                current_block = None

            if stripped and not stripped.startswith("# "):
                previous_non_table_line = stripped

        if current_block is not None:
            blocks.append(current_block)

        return blocks

    def _split_markdown_table_row(self, line: str) -> list[str]:
        stripped = line.strip()
        if stripped.startswith("|"):
            stripped = stripped[1:]
        if stripped.endswith("|"):
            stripped = stripped[:-1]
        return [cell.strip() for cell in stripped.split("|")]

    def _is_blank_table_row(self, cells: list[str]) -> bool:
        return not any(cell.strip() for cell in cells)

    def _looks_like_table_banner_row(self, cells: list[str]) -> bool:
        non_empty = [normalize_identifier(cell) for cell in cells if normalize_identifier(cell)]
        if len(non_empty) < 2:
            return False
        most_common_count = Counter(non_empty).most_common(1)[0][1]
        return most_common_count >= max(2, len(non_empty) - 1)

    def _looks_like_table_header_row(self, cells: list[str]) -> bool:
        non_empty = [cell.strip() for cell in cells if cell.strip()]
        if len(non_empty) < 2:
            return False

        numeric_like = 0
        short_text = 0
        header_markers = {
            "nome",
            "name",
            "cargo",
            "funcao",
            "cpf",
            "cnpj",
            "inicio",
            "fim",
            "fornecedor",
            "justificativa",
            "total",
            "mes",
            "column",
        }

        matched_markers = 0
        for cell in non_empty:
            normalized = normalize_identifier(cell)
            if not normalized:
                continue
            if to_number(cell) is not None or re.search(r"\d{4}-\d{2}-\d{2}", cell):
                numeric_like += 1
            if len(normalized.split()) <= 4:
                short_text += 1
            if any(marker in normalized for marker in header_markers):
                matched_markers += 1

        if matched_markers >= 1 and numeric_like == 0:
            return True
        return numeric_like == 0 and short_text >= max(2, len(non_empty) - 1)

    def _guess_markdown_table_name(
        self,
        header_cells: list[str],
        fallback_label: str | None,
        table_index: int,
    ) -> str:
        non_empty = [cell.strip() for cell in header_cells if cell.strip()]
        if non_empty:
            normalized_counts = Counter(normalize_identifier(cell) for cell in non_empty if normalize_identifier(cell))
            if normalized_counts:
                most_common_value, _ = normalized_counts.most_common(1)[0]
                for cell in non_empty:
                    if normalize_identifier(cell) == most_common_value:
                        return cell
                return non_empty[0]
        if fallback_label:
            return fallback_label
        return f"Tabela {table_index}"

    def _normalize_markdown_table_headers(self, headers: list[str], column_count: int) -> list[str]:
        normalized_headers = []
        seen = Counter()

        for index in range(column_count):
            base = headers[index].strip() if index < len(headers) else ""
            label = base or f"Column_{index + 1}"
            seen[label] += 1
            if seen[label] > 1:
                label = f"{label}_{seen[label]}"
            normalized_headers.append(label)

        return normalized_headers

    def _parse_markdown_tables(
        self,
        document_name: str,
        markdown_text: str,
        document_format: str | None,
    ) -> SpreadsheetModel:
        table_blocks = self._extract_markdown_table_blocks(markdown_text)
        sheets = []
        total_rows = 0
        table_summaries = []

        for table_index, block in enumerate(table_blocks, start=1):
            parsed_table = self._parse_markdown_table_block(block, table_index)
            if not parsed_table:
                continue

            table_name = parsed_table["name"]
            headers = parsed_table["headers"]
            rows = parsed_table["rows"]
            people = parsed_table["people"]
            total_rows += len(rows)
            table_summaries.append(f"{table_name} ({len(rows)} linhas, {len(headers)} colunas, {len(people)} pessoas)")

            summary_lines = [
                f"Tabela detectada: {table_name}",
                f"Linhas indexadas: {len(rows)}",
                f"Colunas: {', '.join(headers[:12])}",
            ]
            if len(headers) > 12:
                summary_lines.append(f"Colunas adicionais omitidas no resumo: {len(headers) - 12}")
            if people:
                summary_lines.append(f"Pessoas detectadas: {len(people)}")

            sheets.append(
                SpreadsheetSheet(
                    name=table_name,
                    summary_lines=summary_lines,
                    column_profiles=[],
                    people=people,
                    rows=rows,
                )
            )

        summary_lines = []
        if table_summaries:
            summary_lines = [
                f"Tabelas detectadas: {len(table_summaries)}",
                f"Total de linhas indexadas: {total_rows}",
                "Resumo das tabelas: " + "; ".join(table_summaries[:8]),
            ]
            if len(table_summaries) > 8:
                summary_lines.append(f"Tabelas adicionais omitidas no resumo: {len(table_summaries) - 8}")

        return SpreadsheetModel(
            format=document_format,
            source_file=document_name,
            summary_lines=summary_lines,
            sheets=sheets,
        )

    def _parse_markdown_table_block(self, block: dict, table_index: int) -> dict | None:
        table_lines = block.get("lines") or []
        if len(table_lines) < 2:
            return None

        split_rows = [
            {"line_number": line_number, "cells": self._split_markdown_table_row(line)}
            for line_number, line in table_lines
        ]
        separator_index = next(
            (
                index
                for index, (_, line) in enumerate(table_lines)
                if self._is_markdown_table_separator(line)
            ),
            None,
        )
        if separator_index is None or separator_index == 0:
            return None

        header_cells = split_rows[separator_index - 1]["cells"]
        body_rows = split_rows[separator_index + 1 :]
        table_name = self._guess_markdown_table_name(header_cells, block.get("label"), table_index)

        if self._is_blank_table_row(header_cells) and body_rows and self._looks_like_table_banner_row(body_rows[0]["cells"]):
            table_name = self._guess_markdown_table_name(body_rows[0]["cells"], block.get("label"), table_index)
            body_rows = body_rows[1:]
            header_cells = []
        elif self._looks_like_table_banner_row(header_cells):
            header_cells = []

        original_header_signature = []
        if body_rows and self._looks_like_table_header_row(body_rows[0]["cells"]):
            header_cells = body_rows[0]["cells"]
            original_header_signature = [
                normalize_identifier(cell) for cell in header_cells if normalize_identifier(cell)
            ]
            body_rows = body_rows[1:]

        column_count = max([len(header_cells)] + [len(row["cells"]) for row in body_rows] or [0])
        if column_count == 0:
            return None

        headers = self._normalize_markdown_table_headers(header_cells, column_count)
        structured_rows = []
        people = []
        seen_people = set()

        for row_index, row in enumerate(body_rows, start=1):
            cells = row["cells"][:column_count]
            if len(cells) < column_count:
                cells = cells + [""] * (column_count - len(cells))
            if self._is_blank_table_row(cells):
                continue

            row_signature = [normalize_identifier(cell) for cell in cells if normalize_identifier(cell)]
            if original_header_signature and row_signature == original_header_signature:
                continue

            pairs = [(column, value.strip()) for column, value in zip(headers, cells) if value.strip()]
            if not pairs:
                continue

            entity = self._extract_entity(table_name, row_index, pairs)
            if entity:
                unique_key = (entity.name, entity.role, entity.row_number, entity.sheet_name)
                if unique_key not in seen_people:
                    seen_people.add(unique_key)
                    people.append(entity)

            structured_rows.append(
                SpreadsheetRow(
                    row_number=row_index,
                    pairs=[{"header": header, "value": value} for header, value in pairs],
                    entity=entity,
                )
            )

        if not structured_rows:
            return None

        return {
            "name": table_name,
            "headers": headers,
            "rows": structured_rows,
            "people": people,
        }
