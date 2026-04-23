"""Date and meeting metadata helpers for document aliases."""
# Simple: Create alternative names for documents using dates

import re

from ...Constants import MONTH_NAME_TO_NUMBER, MONTH_NUMBER_TO_NAME


# Este mixin gera aliases temporais e metadados de reuniao a partir do nome e do conteudo.
class DocumentAliasDateMixin:
    # Esta funcao transforma datas detectadas em apelidos que o usuario pode citar naturalmente.
    def _build_document_date_aliases(self, document_date: str | None) -> list[tuple[str, int, str]]:
        raw_date = str(document_date or "").strip()
        if not raw_date:
            return []

        aliases: list[tuple[str, int, str]] = []
        seen = set()

        def add_alias(display: str, weight: int, alias_kind: str) -> None:
            normalized = self._normalize_identifier(display)
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            aliases.append((display, weight, alias_kind))

        month_name_pattern = "|".join(sorted(MONTH_NAME_TO_NUMBER.keys(), key=len, reverse=True))
        normalized_date = self._normalize_identifier(raw_date)
        add_alias(raw_date, 150, "document_date_line")

        numeric_date_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", raw_date)
        if numeric_date_match:
            day = int(numeric_date_match.group(1))
            month = f"{int(numeric_date_match.group(2)):02d}"
            year = numeric_date_match.group(3)
            month_name = MONTH_NUMBER_TO_NAME.get(month, month)
            add_alias(f"{day:02d}/{month}/{year}", 210, "document_full_date")
            add_alias(f"{day} de {month_name} de {year}", 215, "document_full_date")
            add_alias(f"{month_name} de {year}", 185, "document_month_year")
            add_alias(f"{month_name} {year}", 190, "document_month_year")
            add_alias(f"{month}/{year}", 195, "document_month_year")
            add_alias(f"{year}-{month}", 195, "document_month_year")
            return aliases

        month_year_match = re.search(rf"\b({month_name_pattern})(?:\s+de)?\s+(\d{{4}})\b", normalized_date)
        if month_year_match:
            month_name = month_year_match.group(1)
            month = MONTH_NAME_TO_NUMBER.get(month_name)
            year = month_year_match.group(2)
            add_alias(f"{month_name} de {year}", 185, "document_month_year")
            add_alias(f"{month_name} {year}", 190, "document_month_year")
            if month:
                add_alias(f"{month}/{year}", 195, "document_month_year")
                add_alias(f"{year}-{month}", 195, "document_month_year")

        compact_month_year_match = re.search(r"\b(\d{2})[-_/](\d{4})\b", raw_date)
        if compact_month_year_match:
            month = compact_month_year_match.group(1)
            year = compact_month_year_match.group(2)
            month_name = MONTH_NUMBER_TO_NAME.get(month, month)
            add_alias(f"{month_name} de {year}", 185, "document_month_year")
            add_alias(f"{month_name} {year}", 190, "document_month_year")
            add_alias(f"{month}/{year}", 195, "document_month_year")
            add_alias(f"{year}-{month}", 195, "document_month_year")

        reverse_month_year_match = re.search(r"\b(\d{4})[-_/](\d{2})\b", raw_date)
        if reverse_month_year_match:
            year = reverse_month_year_match.group(1)
            month = reverse_month_year_match.group(2)
            month_name = MONTH_NUMBER_TO_NAME.get(month, month)
            add_alias(f"{month_name} de {year}", 185, "document_month_year")
            add_alias(f"{month_name} {year}", 190, "document_month_year")
            add_alias(f"{month}/{year}", 195, "document_month_year")
            add_alias(f"{year}-{month}", 195, "document_month_year")
        return aliases

    # Esta funcao gera apelidos especificos para atas e reunioes com mes, ano e tipo.
    def _build_meeting_aliases(self, meeting_metadata: dict) -> list[tuple[str, int, str]]:
        aliases: list[tuple[str, int, str]] = [("ata de reuniao", 80, "meeting_generic")]
        meeting_kind = meeting_metadata.get("meeting_kind")
        meeting_year = meeting_metadata.get("meeting_year")
        meeting_month = meeting_metadata.get("meeting_month")
        meeting_date = meeting_metadata.get("meeting_date")

        if meeting_kind == "extraordinaria":
            aliases.extend(
                [
                    ("ata extraordinaria", 180, "meeting_kind"),
                    ("reuniao extraordinaria", 170, "meeting_kind"),
                    ("ata de reuniao extraordinaria", 190, "meeting_kind"),
                ]
            )

        if meeting_month and meeting_year:
            month_name = MONTH_NUMBER_TO_NAME.get(meeting_month, meeting_month)
            aliases.extend(
                [
                    (f"ata de reuniao de {month_name} de {meeting_year}", 200, "meeting_month_year"),
                    (f"ata de reuniao {month_name} {meeting_year}", 195, "meeting_month_year"),
                    (f"ata de {month_name} de {meeting_year}", 225, "meeting_month_year"),
                    (f"ata {month_name} {meeting_year}", 220, "meeting_month_year"),
                    (f"reuniao de {month_name} de {meeting_year}", 170, "meeting_month_year"),
                    (f"reuniao {month_name} {meeting_year}", 180, "meeting_month_year"),
                    (f"{month_name} {meeting_year}", 150, "meeting_month_year"),
                    (f"{month_name} de {meeting_year}", 130, "meeting_month_year"),
                    (f"{meeting_month}-{meeting_year}", 210, "meeting_month_year"),
                    (f"{meeting_year}-{meeting_month}", 210, "meeting_month_year"),
                    (f"{meeting_month}/{meeting_year}", 210, "meeting_month_year"),
                    (f"{meeting_year}/{meeting_month}", 210, "meeting_month_year"),
                ]
            )
            if meeting_kind == "extraordinaria":
                aliases.extend(
                    [
                        (f"ata extraordinaria de {month_name} de {meeting_year}", 260, "meeting_kind_month_year"),
                        (f"ata de reuniao extraordinaria de {month_name} de {meeting_year}", 270, "meeting_kind_month_year"),
                        (f"reuniao extraordinaria de {month_name} de {meeting_year}", 250, "meeting_kind_month_year"),
                    ]
                )

        if meeting_date:
            day, month, year = meeting_date.split("/")
            month_name = MONTH_NUMBER_TO_NAME.get(month, month)
            aliases.extend(
                [
                    (f"ata de reuniao de {meeting_date}", 250, "meeting_date"),
                    (f"reuniao de {meeting_date}", 230, "meeting_date"),
                    (f"{meeting_date}", 210, "meeting_date"),
                    (f"{int(day)} de {month_name} de {year}", 220, "meeting_date"),
                ]
            )
            if meeting_kind == "extraordinaria":
                aliases.append((f"ata extraordinaria de {meeting_date}", 280, "meeting_kind_date"))
        return aliases

    # Esta extração resume sinais de data e tipo de reuniao para o restante do resolver.
    def _extract_meeting_metadata(self, document_name: str, text: str, source: str | None = None) -> dict:
        normalized_name = self._normalize_identifier(document_name)
        normalized_source = self._normalize_identifier(source or "")
        normalized_text = self._normalize_identifier("\n".join(self._normalize_whitespace(text).split("\n")[:60]))
        is_meeting_minutes = "ata de reuniao" in normalized_name or "ata de reuniao" in normalized_text
        meeting_kind = None
        if "extraordin" in normalized_name or "extraordin" in normalized_text or "extraordin" in normalized_source:
            meeting_kind = "extraordinaria"
            is_meeting_minutes = True
        elif is_meeting_minutes:
            meeting_kind = "ordinaria"

        meeting_date = None
        meeting_month = None
        meeting_year = None
        for raw_value in (source or "", document_name):
            month_year = re.search(r"(?<!\d)(\d{2})[-_/](\d{4})(?!\d)", raw_value)
            if month_year:
                meeting_month = month_year.group(1)
                meeting_year = month_year.group(2)
                break
            year_month = re.search(r"(?<!\d)(\d{4})[-_/](\d{2})(?!\d)", raw_value)
            if year_month:
                meeting_year = year_month.group(1)
                meeting_month = year_month.group(2)
                break

        if text:
            raw_preview = "\n".join(self._normalize_whitespace(text).split("\n")[:80])
            date_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", raw_preview)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = date_match.group(3)
                meeting_date = f"{day:02d}/{month:02d}/{year}"
                meeting_month = meeting_month or f"{month:02d}"
                meeting_year = meeting_year or year
            else:
                month_name_pattern = "|".join(sorted(MONTH_NAME_TO_NUMBER.keys(), key=len, reverse=True))
                month_name_match = re.search(
                    rf"\b(\d{{1,2}})\s+de\s+({month_name_pattern})\s+de\s+(\d{{4}})\b",
                    normalized_text,
                )
                if month_name_match:
                    day = int(month_name_match.group(1))
                    month_name = month_name_match.group(2)
                    month = MONTH_NAME_TO_NUMBER.get(month_name)
                    year = month_name_match.group(3)
                    if month:
                        meeting_date = f"{day:02d}/{month}/{year}"
                        meeting_month = meeting_month or month
                        meeting_year = meeting_year or year

            if not (meeting_month and meeting_year):
                month_name_pattern = "|".join(sorted(MONTH_NAME_TO_NUMBER.keys(), key=len, reverse=True))
                month_year_match = re.search(rf"\b({month_name_pattern})\s+de\s+(\d{{4}})\b", normalized_text)
                if month_year_match:
                    meeting_month = MONTH_NAME_TO_NUMBER.get(month_year_match.group(1), meeting_month)
                    meeting_year = month_year_match.group(2)

        return {
            "is_meeting_minutes": is_meeting_minutes,
            "meeting_kind": meeting_kind,
            "meeting_month": meeting_month,
            "meeting_year": meeting_year,
            "meeting_date": meeting_date,
            "document_date": self._extract_document_date(text),
        }
