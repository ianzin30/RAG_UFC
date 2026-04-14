"""Alias and metadata helpers for document resolution."""

import re
from pathlib import Path

from .alias_dates import DocumentAliasDateMixin


# Este mixin centraliza os apelidos que representam cada documento durante a resolucao.
class DocumentAliasMixin(DocumentAliasDateMixin):
    # Esta etapa combina nome, titulo, datas e pistas de conteudo em uma lista unica de aliases.
    def _build_document_aliases(
        self,
        document_name: str,
        normalized_name: str,
        normalized_stem: str,
        title: str | None,
        title_normalized: str,
        description_excerpt: str | None,
        meeting_metadata: dict,
    ) -> list[dict]:
        alias_map: dict[str, dict] = {}

        def add_alias(display: str, weight: int, alias_kind: str) -> None:
            normalized = self._normalize_identifier(display)
            if not normalized:
                return
            existing = alias_map.get(normalized)
            payload = {
                "display": display.strip(),
                "normalized": normalized,
                "weight": weight,
                "kind": alias_kind,
            }
            if existing is None or payload["weight"] > existing["weight"]:
                alias_map[normalized] = payload

        add_alias(document_name, 320, "document_name")
        if normalized_name and normalized_name != self._normalize_identifier(document_name):
            add_alias(normalized_name, 300, "document_name")

        stem_name = Path(document_name).stem
        if stem_name:
            add_alias(stem_name, 260, "document_stem")
        if normalized_stem and normalized_stem != self._normalize_identifier(stem_name):
            add_alias(normalized_stem, 240, "document_stem")

        if title:
            add_alias(title, 220, "title")
        if title_normalized and title_normalized not in {normalized_name, normalized_stem}:
            add_alias(title_normalized, 210, "title")

        for token in re.findall(r"\b[A-Z]{3,10}\b", f"{document_name} {title or ''}"):
            add_alias(token, 250, "acronym")

        for phrase in self._build_keyword_alias_phrases(document_name, title, description_excerpt):
            add_alias(phrase, 120, "title_keywords")
        for phrase, weight, alias_kind in self._build_document_date_aliases(meeting_metadata.get("document_date")):
            add_alias(phrase, weight, alias_kind)
        if meeting_metadata.get("is_meeting_minutes"):
            for phrase, weight, alias_kind in self._build_meeting_aliases(meeting_metadata):
                add_alias(phrase, weight, alias_kind)

        return sorted(alias_map.values(), key=lambda item: (-item["weight"], item["normalized"]))

    # Este helper gera frases-curtas uteis quando o nome do arquivo sozinho nao basta.
    def _build_keyword_alias_phrases(
        self,
        document_name: str,
        title: str | None,
        description_excerpt: str | None,
    ) -> list[str]:
        phrases = []
        for raw_text in (title or "", Path(document_name).stem, description_excerpt or ""):
            tokens = self._tokenize_search_text(raw_text)
            if len(tokens) >= 2:
                phrases.append(" ".join(tokens[: min(6, len(tokens))]))
        return phrases

    # Esta heuristica evita que termos genericos dominem o ranking de candidatos.
    def _is_discriminative_query_term(self, term: str) -> bool:
        if not term or len(term) < 3:
            return False
        if re.fullmatch(r"\d{4}", term):
            return False

        generic_terms = {
            "arquivo",
            "arquivos",
            "documento",
            "documentos",
            "pdf",
            "doc",
            "docs",
            "ata",
            "atas",
            "reuniao",
            "reunioes",
            "meeting",
            "meetings",
            "minutes",
            "mes",
            "ano",
        }
        return term not in generic_terms
