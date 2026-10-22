"""Specialized spreadsheet chunks, preserved from the original ingestion contract."""

import re
from langchain_core.documents import Document
from .Support import normalize_identifier, normalize_whitespace


class SpreadsheetChunker:
    _normalize_identifier = staticmethod(normalize_identifier)
    _normalize_whitespace = staticmethod(normalize_whitespace)

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

    def _looks_like_person_name(self, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if len(text) < 5 or any(char.isdigit() for char in text):
            return False
        if not any(char.islower() for char in text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        blocked_exact = {
            "nome",
            "tbd",
            "total",
            "totais",
            "subtotal",
            "sub total",
            "target",
            "rpa",
            "profissionais",
            "bolsas",
            "custo total de rh mensal",
            "encargos clt",
            "descricao",
            "descricoes",
            "rh direto bolsas",
            "rh direto celetistas",
            "rh indireto administrativo",
        }
        blocked_prefixes = ("rh ", "sub total", "subtotal", "total ", "totais ", "custo ", "historico ", "margem ")
        if normalized in blocked_exact or any(normalized.startswith(prefix) for prefix in blocked_prefixes):
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        return len(tokens) >= 2

    def _extract_role_from_pairs(self, pairs: list[tuple[str, str]]) -> str | None:
        for header, value in pairs:
            if self._looks_like_role(header, value):
                return value
        return None

    def _looks_like_role(self, header: str, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return False
        if self._to_number(text) is not None:
            return False
        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        if normalized in {"ufc", "s vinculo", "total", "totais", "custo dell"}:
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        if not tokens or len(tokens) > 12:
            return False

        normalized_header = self._normalize_identifier(header)
        if normalized_header.startswith("column_") and len(tokens) <= 1:
            return False
        return True

    def _to_number(self, value: str) -> float | None:
        if not value:
            return None

        cleaned = value.strip().replace("R$", "").replace("%", "").replace("\u00a0", " ")
        cleaned = cleaned.replace(" ", "")
        if not cleaned:
            return None

        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _build_spreadsheet_chunks(self, document: Document, header: str) -> list[Document]:
        parsed = self._parse_spreadsheet_markdown(document.page_content)
        base_metadata = dict(document.metadata)
        base_metadata["document_type"] = "spreadsheet"
        chunks = []

        if parsed["summary_lines"]:
            page_content = "\n".join(parsed["summary_lines"]).strip()
            metadata = {**base_metadata, "chunk_kind": "summary"}
            metadata["search_text_normalized"] = self._normalize_identifier(page_content)
            chunks.append(
                Document(
                    page_content=page_content,
                    metadata=metadata,
                )
            )

        for sheet in parsed["sheets"]:
            sheet_metadata = {
                **base_metadata,
                "sheet_name": sheet["name"],
                "sheet_name_normalized": self._normalize_identifier(sheet["name"]),
            }
            if sheet["summary_lines"]:
                page_content = "\n".join(sheet["summary_lines"]).strip()
                metadata = {**sheet_metadata, "chunk_kind": "sheet_summary"}
                metadata["search_text_normalized"] = self._normalize_identifier(page_content)
                chunks.append(
                    Document(
                        page_content=page_content,
                        metadata=metadata,
                    )
                )

            for profile in sheet["column_profiles"]:
                metadata = {**sheet_metadata, "chunk_kind": "column_profile"}
                metadata["search_text_normalized"] = self._normalize_identifier(profile)
                chunks.append(
                    Document(
                        page_content=profile.strip(),
                        metadata=metadata,
                    )
                )

            people_entries = self._collect_spreadsheet_people_entries(sheet, base_metadata["document_name"])
            chunks.extend(self._build_spreadsheet_people_chunks(sheet, base_metadata, sheet_metadata, header, people_entries))
            chunks.extend(self._build_spreadsheet_row_record_chunks(sheet, base_metadata, sheet_metadata, header))
        return chunks

    def _collect_spreadsheet_people_entries(self, sheet: dict, document_name: str) -> list[dict]:
        people_entries = []
        seen_people_keys = set()
        for raw_entry in sheet["people_index"]:
            parsed_entry = self._parse_people_index_line(raw_entry, sheet["name"])
            if not parsed_entry:
                continue
            unique_key = (parsed_entry["entity_name"], parsed_entry.get("entity_role"), parsed_entry.get("row_number"))
            if unique_key in seen_people_keys:
                continue
            seen_people_keys.add(unique_key)
            people_entries.append(parsed_entry)

        for row_record in sheet["row_records"]:
            row_data = self._parse_row_record_line(row_record, sheet["name"])
            if row_data.get("entity_name"):
                unique_key = (row_data["entity_name"], row_data.get("entity_role"), row_data.get("row_number"))
                if unique_key not in seen_people_keys:
                    seen_people_keys.add(unique_key)
                    people_entries.append(
                        {
                            "entity_name": row_data["entity_name"],
                            "entity_role": row_data.get("entity_role"),
                            "sheet_name": row_data.get("sheet_name") or sheet["name"],
                            "row_number": row_data.get("row_number"),
                            "document_name": document_name,
                        }
                    )
        return people_entries

    def _build_spreadsheet_people_chunks(
        self,
        sheet: dict,
        base_metadata: dict,
        sheet_metadata: dict,
        header: str,
        people_entries: list[dict],
    ) -> list[Document]:
        chunks = []
        for person in people_entries:
            # Build clean page_content with just the essential info; metadata goes in the dict.
            content_parts = [person["entity_name"]]
            if person.get("entity_role"):
                content_parts.append(f"Cargo: {person['entity_role']}")

            metadata = {
                **sheet_metadata,
                "chunk_kind": "people_index",
                "entity_name": person["entity_name"],
                "entity_name_normalized": self._normalize_identifier(person["entity_name"]),
                "entity_role": person.get("entity_role"),
                "entity_role_normalized": self._normalize_identifier(person.get("entity_role") or ""),
                "row_number": person.get("row_number"),
            }
            page_content = "\n".join(content_parts).strip()
            chunks.append(
                Document(
                    page_content=page_content,
                    metadata=metadata,
                )
            )
        return chunks

    def _build_spreadsheet_row_record_chunks(
        self,
        sheet: dict,
        base_metadata: dict,
        sheet_metadata: dict,
        header: str,
    ) -> list[Document]:
        chunks = []
        for row_record in sheet["row_records"]:
            row_data = self._parse_row_record_line(row_record, sheet["name"])
            # page_content holds just the row record; metadata goes in the dict.
            page_content = row_record.strip()

            metadata = {
                **sheet_metadata,
                "chunk_kind": "row_record",
                "row_number": row_data.get("row_number"),
                "row_values": dict(row_data.get("pairs") or []),
                "entity_name": row_data.get("entity_name"),
                "entity_name_normalized": self._normalize_identifier(row_data.get("entity_name") or ""),
                "entity_role": row_data.get("entity_role"),
                "entity_role_normalized": self._normalize_identifier(row_data.get("entity_role") or ""),
            }
            chunks.append(
                Document(
                    page_content=page_content,
                    metadata=metadata,
                )
            )
        return chunks
