"""Document registry and spreadsheet helpers."""
# Simple: Keep track of all uploaded documents and their info

import re
from pathlib import Path

from ...Constants import MONTH_NAME_TO_NUMBER, PERSON_QUERY_TERMS, SPREADSHEET_SUFFIXES


# Este mixin mantem o catalogo de documentos e suas pistas estruturadas.
class DocumentRegistryMixin:
    # Este helper devolve o registro mais completo disponivel no estado atual.
    def _get_document_registry(self) -> list[dict]:
        registry = getattr(self, "document_registry", None)
        if registry:
            return registry
        return getattr(self, "document_catalog", [])

    # Esta montagem transforma um documento bruto em metadados prontos para o resolver.
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
        title = self._extract_document_title(text)
        title_normalized = self._normalize_identifier(title or "")
        description_excerpt = self._extract_document_description_excerpt(text, max_lines=3)
        meeting_metadata = self._extract_meeting_metadata(document_name, text, source)
        aggregated_signals = self._build_document_aggregated_signals(text, chunks or [])
        aliases = self._build_document_aliases(
            document_name=document_name,
            normalized_name=normalized_name,
            normalized_stem=normalized_stem,
            title=title,
            title_normalized=title_normalized,
            description_excerpt=description_excerpt,
            meeting_metadata=meeting_metadata,
        )

        keyword_terms = self._collect_unique_document_values(
            [
                *self._tokenize_search_text(title or ""),
                *self._tokenize_search_text(description_excerpt or ""),
                *self._tokenize_search_text(Path(document_name).stem),
                *list(aggregated_signals.get("keyword_terms") or []),
            ],
            limit=96,
        )
        keyword_summary = self._build_keyword_summary(aggregated_signals)
        search_text_normalized = self._normalize_identifier(
            " ".join(
                part
                for part in [
                    title or "",
                    description_excerpt or "",
                    str(aggregated_signals.get("search_text_normalized") or ""),
                ]
                if part
            )
        )
        return {
            "name": document_name,
            "document_name": document_name,
            "normalized_name": normalized_name,
            "normalized_stem": normalized_stem,
            "document_type": document_type,
            "title": title,
            "title_normalized": title_normalized,
            "document_date": meeting_metadata.get("document_date"),
            "meeting_month": meeting_metadata.get("meeting_month"),
            "meeting_year": meeting_metadata.get("meeting_year"),
            "meeting_date": meeting_metadata.get("meeting_date"),
            "meeting_kind": meeting_metadata.get("meeting_kind"),
            "is_meeting_minutes": meeting_metadata.get("is_meeting_minutes", False),
            "description_excerpt": description_excerpt,
            "search_text_normalized": search_text_normalized,
            "keyword_terms": keyword_terms,
            "keyword_summary": keyword_summary,
            "high_value_excerpt": aggregated_signals.get("high_value_excerpt"),
            "signal_phrases": aggregated_signals.get("signal_phrases", []),
            "section_titles": aggregated_signals.get("section_titles", []),
            "section_terms": aggregated_signals.get("section_terms", []),
            "entity_names": aggregated_signals.get("entity_names", []),
            "entity_terms": aggregated_signals.get("entity_terms", []),
            "date_values": aggregated_signals.get("date_values", []),
            "money_values": aggregated_signals.get("money_values", []),
            "fact_lines": aggregated_signals.get("fact_lines", []),
            "fact_terms": aggregated_signals.get("fact_terms", []),
            "acronyms": aggregated_signals.get("acronyms", []),
            "extraction_diagnostics": aggregated_signals.get("extraction_diagnostics", {}),
            "aliases": aliases,
        }

    def _build_document_aggregated_signals(self, text: str, chunks: list) -> dict:
        body_text = self._prepare_generic_document_body(text)
        if not body_text:
            body_text = self._strip_document_wrapper(text)

        section_titles: list[str] = []
        entity_names: list[str] = []
        date_values: list[str] = []
        money_values: list[str] = []
        fact_lines: list[str] = []
        acronyms = self._extract_signal_acronyms(body_text, limit=24)
        high_value_snippets: list[str] = []
        signal_phrases: list[str] = []
        detail_snippets: list[str] = []

        for chunk in chunks:
            metadata = getattr(chunk, "metadata", {}) or {}
            section_title = str(metadata.get("section_title") or metadata.get("sheet_name") or "").strip()
            if section_title:
                section_titles.append(section_title)

            entity_names.extend(self._coerce_document_registry_values(metadata.get("entity_names")))
            entity_name = str(metadata.get("entity_name") or "").strip()
            if entity_name:
                entity_names.append(entity_name)

            date_values.extend(self._coerce_document_registry_values(metadata.get("date_values")))
            money_values.extend(self._coerce_document_registry_values(metadata.get("money_values")))
            fact_lines.extend(self._coerce_document_registry_values(metadata.get("labeled_facts")))

            chunk_kind = str(metadata.get("chunk_kind") or "").strip()
            cleaned_snippet = self._clean_document_signal_text(chunk.page_content or "")
            if cleaned_snippet and chunk_kind == "section_detail" and self._is_salient_detail_snippet(cleaned_snippet):
                detail_snippets.append(cleaned_snippet[:320].strip())
                signal_phrases.extend(self._extract_document_signal_phrases(chunk.page_content or "", limit=6))
                acronyms.extend(self._extract_signal_acronyms(cleaned_snippet, limit=8))

            if chunk_kind not in {
                "document_profile",
                "section_overview",
                "entity_index",
                "list_block",
                "sheet_summary",
                "people_index",
                "summary",
            }:
                continue
            if cleaned_snippet:
                high_value_snippets.append(cleaned_snippet[:260].strip())
                signal_phrases.extend(self._extract_document_signal_phrases(chunk.page_content or "", limit=4))
                acronyms.extend(self._extract_signal_acronyms(cleaned_snippet, limit=8))

        if not entity_names:
            entity_names = self._extract_name_candidates(body_text, limit=40)
        if not date_values:
            date_values = self._extract_date_candidates(body_text, limit=16)
        if not money_values:
            money_values = self._extract_money_candidates(body_text, limit=16)
        if not fact_lines:
            fact_lines = [
                f"{label}: {value}"
                for label, value in self._extract_labeled_facts(body_text, limit=24)
            ]
        if not high_value_snippets and body_text:
            fallback_excerpt = " ".join(line.strip() for line in body_text.splitlines()[:8] if line.strip())
            if fallback_excerpt:
                high_value_snippets = [fallback_excerpt[:320].strip()]

        detail_signal_text = " ".join(detail_snippets).strip()
        if detail_signal_text:
            signal_phrases.extend(self._extract_document_signal_phrases(detail_signal_text, limit=24))
        signal_phrases.extend(self._extract_document_signal_phrases(body_text, limit=12))
        high_value_snippets.extend(detail_snippets[:6])

        section_titles = self._collect_unique_document_values(section_titles, limit=12)
        entity_names = self._collect_unique_document_values(entity_names, limit=40)
        date_values = self._collect_unique_document_values(date_values, limit=16)
        money_values = self._collect_unique_document_values(money_values, limit=16)
        fact_lines = self._collect_unique_document_values(fact_lines, limit=24)
        acronyms = self._collect_unique_document_values(acronyms, limit=24)
        high_value_snippets = self._collect_unique_document_values(high_value_snippets, limit=8)
        signal_phrases = self._collect_unique_document_values(signal_phrases, limit=32)

        section_terms = self._collect_unique_document_values(
            self._tokenize_search_text(" ".join(section_titles)),
            limit=48,
        )
        entity_terms = self._collect_unique_document_values(
            self._tokenize_search_text(" ".join(entity_names)),
            limit=64,
        )
        fact_terms = self._collect_unique_document_values(
            self._tokenize_search_text(" ".join(fact_lines)),
            limit=64,
        )

        signal_parts = [
            *section_titles,
            *entity_names,
            *date_values,
            *money_values,
            *fact_lines,
            *acronyms,
            detail_signal_text,
            *signal_phrases,
            *high_value_snippets,
        ]
        keyword_terms = self._collect_unique_document_values(
            self._tokenize_search_text(" ".join(signal_parts)),
            limit=96,
        )
        search_text_normalized = self._normalize_identifier(" ".join(signal_parts))
        extraction_diagnostics = self._build_document_extraction_diagnostics(
            text=text,
            body_text=body_text,
            chunks=chunks,
            section_titles=section_titles,
            entity_names=entity_names,
            date_values=date_values,
            money_values=money_values,
            fact_lines=fact_lines,
            high_value_snippets=high_value_snippets,
        )
        return {
            "search_text_normalized": search_text_normalized,
            "keyword_terms": keyword_terms,
            "high_value_excerpt": " ".join(high_value_snippets).strip() or None,
            "signal_phrases": signal_phrases,
            "section_titles": section_titles,
            "section_terms": section_terms,
            "entity_names": entity_names,
            "entity_terms": entity_terms,
            "date_values": date_values,
            "money_values": money_values,
            "fact_lines": fact_lines,
            "fact_terms": fact_terms,
            "acronyms": acronyms,
            "extraction_diagnostics": extraction_diagnostics,
        }

    def _build_document_extraction_diagnostics(
        self,
        *,
        text: str,
        body_text: str,
        chunks: list,
        section_titles: list[str],
        entity_names: list[str],
        date_values: list[str],
        money_values: list[str],
        fact_lines: list[str],
        high_value_snippets: list[str],
    ) -> dict:
        stripped_body = body_text or self._strip_document_wrapper(text)
        body_lines = [line.strip() for line in stripped_body.splitlines() if line.strip()]
        body_word_count = len(self._tokenize_search_text(stripped_body))
        body_char_count = len(stripped_body)
        density = round(body_word_count / max(len(body_lines), 1), 2)

        noise_markers = (
            "image",
            "table",
            "page",
            "assinado eletronicamente",
            "rubrica",
        )
        normalized_body = self._normalize_identifier(stripped_body)
        noise_marker_hits = sum(1 for marker in noise_markers if marker in normalized_body)

        chunk_kinds = {}
        for chunk in chunks:
            chunk_kind = str((getattr(chunk, "metadata", {}) or {}).get("chunk_kind") or "text").strip()
            chunk_kinds[chunk_kind] = chunk_kinds.get(chunk_kind, 0) + 1

        quality_reasons = []
        if body_word_count < 120:
            quality_reasons.append("low_text_volume")
        if len(section_titles) < 2:
            quality_reasons.append("limited_section_coverage")
        if not entity_names and not fact_lines:
            quality_reasons.append("missing_entity_and_fact_signals")
        if noise_marker_hits >= 3:
            quality_reasons.append("noise_markers_detected")
        if not high_value_snippets:
            quality_reasons.append("missing_high_value_snippets")

        if {"low_text_volume", "missing_entity_and_fact_signals"} <= set(quality_reasons) or len(quality_reasons) >= 3:
            source_quality = "weak"
        elif quality_reasons:
            source_quality = "medium"
        else:
            source_quality = "strong"

        return {
            "extraction_method": self._extract_extraction_method(text) or "unknown",
            "source_quality": source_quality,
            "quality_reasons": quality_reasons,
            "body_char_count": body_char_count,
            "body_word_count": body_word_count,
            "line_count": len(body_lines),
            "text_density": density,
            "section_count": len(section_titles),
            "entity_count": len(entity_names),
            "date_count": len(date_values),
            "money_count": len(money_values),
            "fact_count": len(fact_lines),
            "high_value_snippet_count": len(high_value_snippets),
            "noise_marker_hits": noise_marker_hits,
            "chunk_kind_counts": chunk_kinds,
        }

    def _extract_document_signal_phrases(self, text: str, limit: int | None = None) -> list[str]:
        phrases: list[str] = []
        seen: set[str] = set()

        for match in re.findall("[\"'\u201c\u201d]([^\"'\u201c\u201d]{3,120})[\"'\u201c\u201d]", text or ""):
            compact = re.sub(r"\s+", " ", str(match or "")).strip(" -:;,.")
            normalized = self._normalize_identifier(compact)
            if len(normalized.split()) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            phrases.append(compact)
            if limit is not None and len(phrases) >= limit:
                return phrases

        tokens = self._tokenize_search_text(text or "")
        for window_size in range(5, 1, -1):
            for index in range(len(tokens) - window_size + 1):
                window = tokens[index : index + window_size]
                discriminative_terms = [term for term in window if self._is_discriminative_query_term(term)]
                if len(discriminative_terms) < 2:
                    continue
                phrase = " ".join(window).strip()
                if len(phrase) < 10 or phrase in seen:
                    continue
                seen.add(phrase)
                phrases.append(phrase)
                if limit is not None and len(phrases) >= limit:
                    return phrases
        return phrases

    def _is_salient_detail_snippet(self, text: str) -> bool:
        normalized = self._normalize_identifier(text)
        if not normalized:
            return False

        salient_markers = (
            "ai for customer support",
            "empresa junior",
            "parceria",
            "parceira",
            "projeto",
            "intitulado",
            "evento",
            "afastamento",
            "chefia",
            "subchefia",
            "olimpiada",
            "iniciativa",
            "lia",
            "laboratorio",
            "infraestrutura",
            "materiais",
            "servidor",
            "estagio pos doutoral",
            "coppe",
            "ufrj",
        )
        if any(marker in normalized for marker in salient_markers):
            return True

        if self._extract_document_signal_phrases(text, limit=2):
            return True
        if self._extract_name_candidates(text, limit=2):
            return True
        if any(month_name in normalized for month_name in MONTH_NAME_TO_NUMBER):
            return True
        return False

    def _build_keyword_summary(self, aggregated_signals: dict) -> str:
        summary_parts = [
            *list(aggregated_signals.get("section_titles") or [])[:3],
            *list(aggregated_signals.get("entity_names") or [])[:3],
            *list(aggregated_signals.get("acronyms") or [])[:3],
        ]
        if aggregated_signals.get("fact_lines"):
            summary_parts.append(str(list(aggregated_signals.get("fact_lines") or [])[0]))
        summary_parts = self._collect_unique_document_values(summary_parts, limit=8)
        return "; ".join(summary_parts)[:260].strip()

    def _collect_unique_document_values(self, values: list[str], limit: int | None = None) -> list[str]:
        unique_values = []
        seen = set()
        for raw_value in values:
            compact = re.sub(r"\s+", " ", str(raw_value or "")).strip(" -")
            if not compact:
                continue
            normalized = self._normalize_identifier(compact)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(compact)
            if limit is not None and len(unique_values) >= limit:
                break
        return unique_values

    def _coerce_document_registry_values(self, raw_value: object) -> list[str]:
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str) and raw_value.strip():
            return [raw_value.strip()]
        return []

    def _clean_document_signal_text(self, text: str) -> str:
        cleaned = re.sub(r"^Documento:\s.*?\n", "", text or "", flags=re.DOTALL)
        cleaned = re.sub(r"^Secao:\s.*?\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Aba:\s.*?\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Trecho:\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Perfil do documento\s*", "", cleaned, flags=re.DOTALL)
        compact_lines = []
        for line in cleaned.splitlines():
            compact = re.sub(r"\s+", " ", line).strip(" -")
            if not compact or compact.startswith("Documento:") or compact.startswith("Secao:") or compact.startswith("Aba:"):
                continue
            compact_lines.append(compact)
        return " ".join(compact_lines).strip()

    def _extract_signal_acronyms(self, text: str, limit: int | None = None) -> list[str]:
        acronyms = []
        seen = set()
        for match in re.findall(r"\b[A-Z]{2,}[A-Z0-9/-]{0,10}\b", text or ""):
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
        seen = set()
        for document_name in document_names:
            if document_name in seen:
                continue
            seen.add(document_name)
            entry = self._get_document_entry(document_name)
            if entry is None:
                continue
            payload = dict(entry.get("extraction_diagnostics") or {})
            if not payload:
                continue
            diagnostics.append(
                {
                    "document_name": document_name,
                    "diagnostics": payload,
                }
            )
        return diagnostics

    # Este helper localiza uma entrada unica do catalogo pelo nome do documento.
    def _get_document_entry(self, document_name: str | None) -> dict | None:
        if not document_name:
            return None
        for document in self._get_document_registry():
            if document["name"] == document_name:
                return document
        return None

    # Esta checagem identifica planilhas mesmo quando o alvo veio apenas pelo nome do arquivo.
    def _is_spreadsheet_document_name(self, document_name: str | None) -> bool:
        entry = self._get_document_entry(document_name)
        if entry and entry.get("document_type") == "spreadsheet":
            return True
        return bool(document_name and document_name.lower().endswith(SPREADSHEET_SUFFIXES))

    # Esta heuristica ativa o caminho de pessoas quando a pergunta aponta para nomes em planilhas.
    def _is_people_question(self, question: str, target_document_name: str | None = None) -> bool:
        normalized = self._normalize_identifier(question)
        query_terms = set(self._tokenize_search_text(normalized))
        has_people_term = bool(query_terms & PERSON_QUERY_TERMS)
        points_to_spreadsheet = self._is_spreadsheet_document_name(target_document_name) or any(
            marker in normalized for marker in ("planilha", ".xlsx", ".csv", "aba", "sheet")
        )
        return has_people_term and points_to_spreadsheet

    # Esta extracao tenta travar a aba correta antes do ranking de chunks da planilha.
    def _extract_sheet_reference(self, question: str, target_document_name: str | None = None) -> str | None:
        normalized = self._normalize_identifier(question)
        if not normalized:
            return None

        chunks = self.spreadsheet_chunk_index.get(target_document_name or "", [])
        for chunk in chunks:
            sheet_name = chunk.metadata.get("sheet_name")
            sheet_name_normalized = chunk.metadata.get("sheet_name_normalized")
            if not sheet_name or not sheet_name_normalized:
                continue
            if sheet_name_normalized in normalized or f"aba {sheet_name_normalized}" in normalized:
                return sheet_name_normalized

        if re.search(r"\brh\b", normalized):
            return "rh"
        return None
