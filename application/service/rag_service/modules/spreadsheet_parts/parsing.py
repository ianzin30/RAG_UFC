"""Markdown parsing helpers for indexed spreadsheets."""


class SpreadsheetParsingMixin:
    def _parse_spreadsheet_markdown(self, text: str) -> dict:
        lines = [line.strip() for line in self._normalize_whitespace(text).split("\n") if line.strip()]
        summary_lines = []
        sheets = []
        current_sheet = None
        section = "summary"

        for line in lines[1:]:
            if line.startswith("## Sheet: "):
                if current_sheet is not None:
                    sheets.append(current_sheet)
                current_sheet = {
                    "name": line.split(":", 1)[1].strip(),
                    "summary_lines": [],
                    "column_profiles": [],
                    "people_index": [],
                    "row_records": [],
                }
                section = "sheet_summary"
                continue

            if current_sheet is None:
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
                current_sheet["summary_lines"].append(line)
                continue

            if section == "column_profiles" and line.startswith("- "):
                current_sheet["column_profiles"].append(line[2:].strip())
                continue
            if section == "people_index" and line.startswith("- "):
                current_sheet["people_index"].append(line[2:].strip())
                continue
            if section == "row_records" and line.startswith("- "):
                current_sheet["row_records"].append(line[2:].strip())
                continue

            current_sheet["summary_lines"].append(line)

        if current_sheet is not None:
            sheets.append(current_sheet)
        return {"summary_lines": summary_lines, "sheets": sheets}

    def _parse_people_index_line(self, line: str, default_sheet_name: str) -> dict | None:
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
        return {
            "entity_name": entity_name,
            "entity_role": entity_role,
            "sheet_name": sheet_name,
            "row_number": row_number,
        }

    def _parse_row_record_line(self, line: str, default_sheet_name: str) -> dict:
        parts = [part.strip() for part in line.split(" | ") if part.strip()]
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

        entity_name = None
        entity_role = None
        if pairs:
            _, first_value = pairs[0]
            if self._looks_like_person_name(first_value):
                entity_name = first_value
                entity_role = self._extract_role_from_pairs(pairs[1:])

        return {
            "sheet_name": sheet_name,
            "row_number": row_number,
            "pairs": pairs,
            "entity_name": entity_name,
            "entity_role": entity_role,
        }

    def _parse_header_value_pair(self, text: str) -> tuple[str, str] | None:
        header, separator, value = text.partition("=")
        if not separator:
            return None
        header = header.strip()
        value = value.strip()
        if not header or not value:
            return None
        return header, value
