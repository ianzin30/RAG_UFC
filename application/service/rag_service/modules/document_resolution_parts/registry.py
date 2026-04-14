"""Document registry and spreadsheet helpers."""

import re
from pathlib import Path

from ...constants import PERSON_QUERY_TERMS, SPREADSHEET_SUFFIXES


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
    ) -> dict:
        normalized_name = self._normalize_identifier(document_name)
        normalized_stem = self._normalize_identifier(Path(document_name).stem)
        title = self._extract_document_title(text)
        title_normalized = self._normalize_identifier(title or "")
        description_excerpt = self._extract_document_description_excerpt(text, max_lines=3)
        meeting_metadata = self._extract_meeting_metadata(document_name, text, source)
        aliases = self._build_document_aliases(
            document_name=document_name,
            normalized_name=normalized_name,
            normalized_stem=normalized_stem,
            title=title,
            title_normalized=title_normalized,
            description_excerpt=description_excerpt,
            meeting_metadata=meeting_metadata,
        )

        keyword_terms = sorted(
            {
                *self._tokenize_search_text(title or ""),
                *self._tokenize_search_text(Path(document_name).stem),
            }
        )
        keyword_summary = " ".join(keyword_terms[:8]).strip()
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
            "keyword_terms": keyword_terms,
            "keyword_summary": keyword_summary,
            "aliases": aliases,
        }

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
