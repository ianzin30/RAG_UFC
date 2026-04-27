"""Explicit-only document registry and resolution helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from ..Constants import MONTH_NAME_TO_NUMBER, PERSON_QUERY_TERMS, SPREADSHEET_SUFFIXES


class DocumentResolutionMixin:
    """Resolve documents only from explicit references.

    The resolver intentionally ignores content-derived clues such as people,
    roles, entities, projects, month/year-only dates, and benchmark-style facts.
    Non-explicit questions should remain collection-wide retrieval questions.
    """

    def _get_document_registry(self) -> list[dict]:
        registry = getattr(self, "document_registry", None)
        if registry:
            return registry
        return getattr(self, "document_catalog", [])

    def _get_document_entry(self, document_name: str | None) -> dict | None:
        if not document_name:
            return None
        for entry in self._get_document_registry():
            if entry.get("name") == document_name or entry.get("document_name") == document_name:
                return entry
        return None

    def _build_document_registry_entry(
        self,
        document_name: str,
        document_type: str,
        text: str,
        source: str | None = None,
        chunks: list | None = None,
    ) -> dict:
        normalized_name = self._normalize_identifier(document_name)
        normalized_stem = self._normalize_identifier(Path(document_name).stem)
        title = self._extract_document_title(text) or self._extract_heading_title(text, document_name)
        title_normalized = self._normalize_identifier(title or "")
        meeting_metadata = self._extract_meeting_metadata(document_name, text, source)
        description_excerpt = self._extract_document_description_excerpt(text, max_lines=2)
        source_name = Path(source).name if source else None

        aliases = self._build_document_aliases(
            document_name=document_name,
            normalized_name=normalized_name,
            normalized_stem=normalized_stem,
            title=title,
            title_normalized=title_normalized,
        )
        keyword_terms = self._collect_unique_document_values(
            [
                *self._tokenize_search_text(document_name),
                *self._tokenize_search_text(Path(document_name).stem),
                *self._tokenize_search_text(title or ""),
            ],
            limit=48,
        )

        return {
            "name": document_name,
            "document_name": document_name,
            "source": source,
            "source_name": source_name,
            "normalized_name": normalized_name,
            "normalized_stem": normalized_stem,
            "document_type": document_type,
            "title": title,
            "title_normalized": title_normalized,
            "document_date": meeting_metadata.get("document_date"),
            "document_full_dates": list(meeting_metadata.get("document_full_dates") or []),
            "meeting_date": meeting_metadata.get("meeting_date"),
            "meeting_day": meeting_metadata.get("meeting_day"),
            "meeting_month": meeting_metadata.get("meeting_month"),
            "meeting_year": meeting_metadata.get("meeting_year"),
            "meeting_kind": meeting_metadata.get("meeting_kind"),
            "is_meeting_minutes": meeting_metadata.get("is_meeting_minutes", False),
            "description_excerpt": description_excerpt,
            "search_text_normalized": self._normalize_identifier(
                " ".join(part for part in [document_name, Path(document_name).stem, title or ""] if part)
            ),
            "keyword_terms": keyword_terms,
            "keyword_summary": "; ".join(keyword_terms[:12]),
            "high_value_excerpt": description_excerpt,
            "signal_phrases": [],
            "section_titles": [],
            "section_terms": [],
            "entity_names": [],
            "entity_terms": [],
            "date_values": list(meeting_metadata.get("document_full_dates") or []),
            "money_values": [],
            "fact_lines": [],
            "fact_terms": [],
            "acronyms": self._extract_signal_acronyms(document_name, limit=12),
            "extraction_diagnostics": self._build_document_extraction_diagnostics(
                text=text,
                source=source,
                chunks=chunks or [],
            ),
            "aliases": aliases,
        }

    def _extract_heading_title(self, text: str, fallback: str) -> str | None:
        for line in self._normalize_whitespace(text).splitlines()[:8]:
            compact = line.strip()
            if compact.startswith("# "):
                heading = compact[2:].strip()
                return heading or fallback
        return None

    def _build_document_extraction_diagnostics(
        self,
        *,
        text: str,
        source: str | None,
        chunks: list,
    ) -> dict[str, object]:
        body_text = self._strip_document_wrapper(text)
        return {
            "source": source,
            "chunk_count": len(chunks or []),
            "body_word_count": len(self._tokenize_search_text(body_text)),
            "body_char_count": len(body_text or ""),
            "source_quality": "registry_compact",
        }

    def _build_document_aliases(
        self,
        *,
        document_name: str,
        normalized_name: str,
        normalized_stem: str,
        title: str | None,
        title_normalized: str,
    ) -> list[dict[str, object]]:
        aliases: list[dict[str, object]] = []
        seen: set[str] = set()

        def add_alias(display: str, normalized: str, kind: str, weight: int) -> None:
            compact = re.sub(r"\s+", " ", str(display or "")).strip()
            normalized_alias = self._normalize_identifier(normalized or compact)
            if not compact or not normalized_alias or normalized_alias in seen:
                return
            seen.add(normalized_alias)
            aliases.append(
                {
                    "display": compact,
                    "normalized": normalized_alias,
                    "kind": kind,
                    "weight": int(weight),
                }
            )

        add_alias(document_name, normalized_name, "filename", 100)
        add_alias(Path(document_name).stem, normalized_stem, "stem", 90)
        if title_normalized and title_normalized not in {normalized_name, normalized_stem}:
            add_alias(title or "", title_normalized, "title", 85)
        return aliases

    def _match_document_names(self, question: str) -> list[str]:
        normalized_question = self._normalize_identifier(question)
        if not normalized_question:
            return []

        matches: list[tuple[int, int, str]] = []
        seen: set[str] = set()
        for document in self._get_document_registry():
            match_data = self._find_document_reference(document, normalized_question)
            if match_data is None:
                continue
            start_index, specificity = match_data
            document_name = str(document.get("name") or document.get("document_name") or "").strip()
            if not document_name or document_name in seen:
                continue
            seen.add(document_name)
            matches.append((start_index, -specificity, document_name))

        for document_name in self._match_documents_by_unique_full_date(question):
            if document_name in seen:
                continue
            seen.add(document_name)
            matches.append((10_000 + len(matches), -75, document_name))

        matches.sort()
        return [document_name for _, _, document_name in matches]

    def _match_document_name(self, question: str) -> str | None:
        matches = self._match_document_names(question)
        return matches[0] if matches else None

    def _merge_document_matches(self, *match_groups: list[str]) -> list[str]:
        merged = []
        seen = set()
        for group in match_groups:
            for document_name in group or []:
                compact = str(document_name or "").strip()
                if not compact or compact in seen:
                    continue
                seen.add(compact)
                merged.append(compact)
        return merged

    def _resolve_documents_with_agent(
        self,
        question: str,
        resolved_question: str,
        chat_history=None,
    ) -> dict[str, object]:
        explicit_matches = self._merge_document_matches(
            self._match_document_names(question),
            self._match_document_names(resolved_question),
        )
        if explicit_matches:
            status = "single_match" if len(explicit_matches) == 1 else "multiple_matches"
            return {
                "status": status,
                "matched_documents": explicit_matches,
                "document_shortlist": explicit_matches,
                "resolver_candidates": explicit_matches,
                "matched_aliases": [],
                "document_scores": self._build_document_score_trace_for_explicit_matches(explicit_matches),
                "resolver_confidence": 1.0 if len(explicit_matches) == 1 else 0.72,
                "reason": "explicit_document_reference",
            }
        return {
            "status": "no_match",
            "matched_documents": [],
            "document_shortlist": [],
            "resolver_candidates": [],
            "matched_aliases": [],
            "document_scores": [],
            "resolver_confidence": 0.0,
            "reason": "collection_wide_default",
        }

    def _build_document_score_trace_for_explicit_matches(self, document_names: list[str]) -> list[dict[str, object]]:
        return [
            {
                "document_name": document_name,
                "score": 999,
                "reason": "explicit_document_reference",
                "matched_terms": [],
                "matched_phrases": [],
                "score_components": {
                    **self._empty_score_components(),
                    "alias_score": 999,
                },
            }
            for document_name in document_names[:5]
        ]

    def _find_document_reference(self, document: dict, normalized_question: str) -> tuple[int, int] | None:
        best_match: tuple[int, int] | None = None
        for alias in list(document.get("aliases") or []):
            normalized_alias = str(alias.get("normalized") or "").strip()
            if not normalized_alias:
                continue
            if not self._is_explicit_alias_match(normalized_question, normalized_alias):
                continue
            start = normalized_question.find(normalized_alias)
            specificity = len(normalized_alias.split()) * 20 + int(alias.get("weight") or 0)
            if best_match is None or (start, -specificity) < (best_match[0], -best_match[1]):
                best_match = (start, specificity)
        return best_match

    def _is_explicit_alias_match(self, normalized_question: str, normalized_alias: str) -> bool:
        alias_tokens = normalized_alias.split()
        if len(alias_tokens) == 1 and len(normalized_alias) < 3:
            return False
        pattern = rf"(?<!\w){re.escape(normalized_alias)}(?!\w)"
        return bool(re.search(pattern, normalized_question))

    def _match_documents_by_unique_full_date(self, question: str) -> list[str]:
        question_dates = self._extract_normalized_full_dates(question)
        if not question_dates:
            return []

        matches = []
        for normalized_date in question_dates:
            documents_for_date = []
            for document in self._get_document_registry():
                document_dates = set(str(value) for value in list(document.get("document_full_dates") or []))
                meeting_date = str(document.get("meeting_date") or "").strip()
                if meeting_date:
                    document_dates.add(meeting_date)
                if normalized_date in document_dates:
                    document_name = str(document.get("name") or document.get("document_name") or "").strip()
                    if document_name:
                        documents_for_date.append(document_name)
            if len(set(documents_for_date)) == 1:
                matches.extend(documents_for_date)
        return list(dict.fromkeys(matches))

    def _extract_meeting_metadata(self, document_name: str, text: str, source: str | None = None) -> dict:
        full_dates = self._collect_unique_document_values(
            [
                *self._extract_normalized_full_dates(document_name),
                *self._extract_normalized_full_dates(source or ""),
                *self._extract_normalized_full_dates(text),
            ],
            limit=12,
        )
        meeting_date = full_dates[0] if full_dates else None
        meeting_day = meeting_month = meeting_year = None
        if meeting_date:
            year, month, day = meeting_date.split("-", 2)
            meeting_day = day
            meeting_month = month
            meeting_year = year

        normalized_name = self._normalize_identifier(document_name)
        normalized_text_head = self._normalize_identifier(" ".join((text or "").splitlines()[:12]))
        is_meeting_minutes = any(marker in f"{normalized_name} {normalized_text_head}" for marker in ("ata", "reuniao"))
        return {
            "document_date": meeting_date,
            "document_full_dates": full_dates,
            "meeting_date": meeting_date,
            "meeting_day": meeting_day,
            "meeting_month": meeting_month,
            "meeting_year": meeting_year,
            "meeting_kind": "ata" if is_meeting_minutes else None,
            "is_meeting_minutes": is_meeting_minutes,
        }

    def _extract_normalized_full_dates(self, text: str) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()

        def add(year: int, month: int, day: int) -> None:
            try:
                normalized = date(year, month, day).isoformat()
            except ValueError:
                return
            if normalized in seen:
                return
            seen.add(normalized)
            values.append(normalized)

        raw_text = str(text or "")
        for day, month, year in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", raw_text):
            parsed_year = int(year)
            if parsed_year < 100:
                parsed_year += 2000
            add(parsed_year, int(month), int(day))

        for year, month, day in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", raw_text):
            add(int(year), int(month), int(day))

        month_pattern = "|".join(sorted(MONTH_NAME_TO_NUMBER, key=len, reverse=True))
        textual_pattern = re.compile(
            rf"\b(\d{{1,2}})\s+(?:de\s+)?({month_pattern})\s+(?:de\s+)?(\d{{4}})\b",
            flags=re.IGNORECASE,
        )
        for day, month_name, year in textual_pattern.findall(self._normalize_identifier(raw_text)):
            month_number = MONTH_NAME_TO_NUMBER.get(month_name)
            if not month_number:
                continue
            add(int(year), int(month_number), int(day))
        return values

    def _empty_score_components(self) -> dict[str, int]:
        return {
            "alias_score": 0,
            "keyword_score": 0,
            "signal_score": 0,
            "phrase_score": 0,
            "specificity_score": 0,
            "generic_penalty": 0,
            "blend_bonus": 0,
        }

    def _collect_resolver_matches(
        self,
        question: str,
        resolved_question: str,
        retrieval_intent: str | None = None,
    ) -> list[dict]:
        return [
            {
                "document_name": document_name,
                "score": 999,
                "reason": "explicit_document_reference",
                "matched_terms": [],
                "matched_phrases": [],
                "score_components": {
                    **self._empty_score_components(),
                    "alias_score": 999,
                },
            }
            for document_name in self._merge_document_matches(
                self._match_document_names(question),
                self._match_document_names(resolved_question),
            )
        ]

    def _extract_explicit_query_phrases(self, raw_text: str) -> list[str]:
        phrases = []
        seen = set()
        for match in re.findall("[\"'\u201c\u201d]([^\"'\u201c\u201d]{3,160})[\"'\u201c\u201d]", raw_text or ""):
            compact = re.sub(r"\s+", " ", str(match or "")).strip(" -:;,.")
            normalized = self._normalize_identifier(compact)
            if len(normalized.split()) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            phrases.append(normalized)
        return phrases

    def _extract_query_signal_phrases(self, normalized_text: str) -> list[str]:
        terms = [term for term in str(normalized_text or "").split() if self._is_discriminative_query_term(term)]
        phrases = []
        seen = set()
        for window_size in (4, 3, 2):
            if len(terms) < window_size:
                continue
            for index in range(0, len(terms) - window_size + 1):
                phrase = " ".join(terms[index : index + window_size])
                if phrase in seen:
                    continue
                seen.add(phrase)
                phrases.append(phrase)
        return phrases[:12]

    def _get_generic_query_terms(self) -> set[str]:
        return set(PERSON_QUERY_TERMS) | {
            "arquivo",
            "documento",
            "ata",
            "reuniao",
            "pdf",
            "projeto",
            "curso",
            "departamento",
            "ufc",
            "empresa",
            "qual",
            "quais",
            "quem",
            "quando",
            "onde",
            "como",
        }

    def _is_resolver_generic_query_term(self, term: str) -> bool:
        return str(term or "").strip() in self._get_generic_query_terms()

    def _is_discriminative_query_term(self, term: str) -> bool:
        compact = str(term or "").strip()
        if len(compact) < 3:
            return False
        if self._is_resolver_generic_query_term(compact):
            return False
        return True

    def _collect_unique_document_values(self, values: list[str], limit: int | None = None) -> list[str]:
        collected = []
        seen = set()
        for value in values or []:
            compact = re.sub(r"\s+", " ", str(value or "")).strip(" -:;,.")
            normalized = self._normalize_identifier(compact)
            if not compact or not normalized or normalized in seen:
                continue
            seen.add(normalized)
            collected.append(compact)
            if limit is not None and len(collected) >= limit:
                break
        return collected

    def _coerce_document_registry_values(self, raw_value: object) -> list[str]:
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str) and raw_value.strip():
            return [raw_value.strip()]
        return []

    def _clean_document_signal_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", self._strip_retrieval_wrapper(text) if hasattr(self, "_strip_retrieval_wrapper") else text).strip()

    def _extract_signal_acronyms(self, text: str, limit: int | None = None) -> list[str]:
        acronyms = []
        seen = set()
        for match in re.findall(r"\b[A-Z]{2,}[A-Z0-9&./-]{0,12}\b", text or ""):
            normalized = self._normalize_identifier(match)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            acronyms.append(match)
            if limit is not None and len(acronyms) >= limit:
                break
        return acronyms

    def _build_trace_extraction_diagnostics(self, document_names: list[str]) -> list[dict[str, object]]:
        diagnostics = []
        for document_name in document_names or []:
            entry = self._get_document_entry(document_name)
            if entry is None:
                continue
            diagnostics.append(
                {
                    "document_name": document_name,
                    **dict(entry.get("extraction_diagnostics") or {}),
                }
            )
        return diagnostics

    def _is_spreadsheet_document_name(self, document_name: str | None) -> bool:
        entry = self._get_document_entry(document_name)
        if entry is not None and entry.get("document_type") == "spreadsheet":
            return True
        return str(document_name or "").strip().lower().endswith(SPREADSHEET_SUFFIXES)

    def _is_people_question(self, question: str, target_document_name: str | None = None) -> bool:
        normalized_terms = set(self._tokenize_search_text(question))
        points_to_spreadsheet = self._is_spreadsheet_document_name(target_document_name) or any(
            term in normalized_terms for term in ("planilha", "aba", "sheet")
        )
        return points_to_spreadsheet and bool(normalized_terms & PERSON_QUERY_TERMS)

    def _extract_sheet_reference(self, question: str, target_document_name: str | None = None) -> str | None:
        if not self._is_spreadsheet_document_name(target_document_name):
            return None
        normalized_question = self._normalize_identifier(question)
        for chunk in getattr(self, "spreadsheet_chunk_index", {}).get(target_document_name, []):
            metadata = getattr(chunk, "metadata", {}) or {}
            sheet_name = str(metadata.get("sheet_name") or "").strip()
            if sheet_name and self._normalize_identifier(sheet_name) in normalized_question:
                return sheet_name
        return None
