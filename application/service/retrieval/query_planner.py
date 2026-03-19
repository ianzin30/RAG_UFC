from __future__ import annotations

from pathlib import Path

from ..collections.contracts import QueryPlan
from ..spreadsheets.markdown import PERSON_QUERY_TERMS, normalize_identifier


CATALOG_LIST_TERMS = {
    "qual",
    "quais",
    "lista",
    "listar",
    "liste",
    "mostre",
    "mostrar",
    "nome",
    "nomes",
    "what",
    "which",
    "show",
    "list",
}
CATALOG_COUNT_TERMS = {
    "quanto",
    "quantos",
    "quantas",
    "quantidade",
    "numero",
    "number",
    "many",
    "total",
}
CATALOG_TYPE_TERMS = {
    "spreadsheet": {"planilha", "planilhas", "spreadsheet", "spreadsheets", "xlsx", "csv"},
    "pdf": {"pdf", "pdfs"},
    "image": {"imagem", "imagens", "image", "images", "jpg", "jpeg", "png", "gif", "webp"},
    "presentation": {"apresentacao", "apresentacoes", "presentation", "presentations", "ppt", "pptx"},
    "text_document": {"doc", "docs", "docx", "texto", "text", "html", "markdown", "md"},
}
MAX_CATALOG_LISTING = 25
BROAD_FILE_QUERY_PHRASES = (
    "me fale sobre",
    "fale sobre",
    "resuma",
    "resumo",
    "sobre o arquivo",
    "sobre a planilha",
    "o que este arquivo contem",
    "o que esse arquivo contem",
    "o que este documento contem",
    "o que esse documento contem",
    "what is this file about",
)
CSV_CHILD_PRIORITY_TERMS = {
    "aba",
    "sheet",
    "linha",
    "linhas",
    "row",
    "rows",
    "coluna",
    "colunas",
    "column",
    "columns",
    "valor",
    "valores",
    "value",
    "values",
    "tabela",
    "tabelas",
    "table",
    "tables",
}


class QueryPlanner:
    def plan(
        self,
        question: str,
        resolved_query: str,
        document_catalog: list[dict],
        intent_decision: dict | None = None,
    ) -> QueryPlan:
        normalized = normalize_identifier(resolved_query or question)
        matched_catalog_ids = self._match_document_ids(normalized, document_catalog)
        requested_type = self._extract_catalog_document_type(normalized)
        people_query = self._is_people_query(normalized)

        if self._is_inventory_decision(intent_decision):
            return QueryPlan(
                intent="inventory",
                target_document_ids=[],
                requested_document_type=requested_type,
                needs_structured_lookup=False,
                resolved_query=resolved_query,
                inventory_mode=self._inventory_mode(normalized),
            )

        matched_entries = self._entries_from_ids(matched_catalog_ids, document_catalog)

        if len(matched_entries) > 1:
            return QueryPlan(
                intent="multi_document",
                target_document_ids=self._flatten_backing_document_ids(matched_entries),
                requested_document_type=requested_type,
                needs_structured_lookup=people_query,
                resolved_query=resolved_query,
            )

        if len(matched_entries) == 1:
            matched_entry = matched_entries[0]
            if matched_entry.get("supports_doc_csv_hybrid"):
                return self._build_doc_csv_hybrid_plan(
                    matched_entry=matched_entry,
                    requested_type=requested_type,
                    people_query=people_query,
                    normalized_question=normalized,
                    resolved_query=resolved_query,
                )
            if people_query and matched_entry and matched_entry.get("document_type") == "spreadsheet":
                intent = "spreadsheet_entity"
            else:
                intent = "single_document"
            return QueryPlan(
                intent=intent,
                target_document_ids=list(matched_entry.get("backing_document_ids") or [matched_entry["document_id"]]),
                requested_document_type=requested_type,
                needs_structured_lookup=people_query,
                resolved_query=resolved_query,
                retrieval_profile="default",
            )

        if people_query and requested_type == "spreadsheet":
            spreadsheet_entries = [
                entry for entry in document_catalog if self._entry_matches_requested_type(entry, "spreadsheet")
            ]
            return QueryPlan(
                intent="spreadsheet_entity",
                target_document_ids=self._flatten_backing_document_ids(spreadsheet_entries),
                requested_document_type=requested_type,
                needs_structured_lookup=True,
                resolved_query=resolved_query,
                retrieval_profile="default",
            )

        return QueryPlan(
            intent="generic_semantic",
            target_document_ids=[],
            requested_document_type=requested_type,
            needs_structured_lookup=False,
            resolved_query=resolved_query,
            retrieval_profile="default",
        )

    def _build_doc_csv_hybrid_plan(
        self,
        *,
        matched_entry: dict,
        requested_type: str | None,
        people_query: bool,
        normalized_question: str,
        resolved_query: str,
    ) -> QueryPlan:
        primary_document_id = matched_entry.get("primary_document_id") or matched_entry["document_id"]
        child_document_ids = list(matched_entry.get("child_document_ids") or [])

        if child_document_ids and self._prefers_csv_children(normalized_question, people_query):
            target_document_ids = self._ordered_unique(child_document_ids + [primary_document_id])
            retrieval_profile = "csv_child_first"
        else:
            target_document_ids = self._ordered_unique([primary_document_id] + child_document_ids)
            retrieval_profile = "parent_overview_first"

        return QueryPlan(
            intent="single_document",
            target_document_ids=target_document_ids,
            requested_document_type=requested_type,
            needs_structured_lookup=False,
            resolved_query=resolved_query,
            retrieval_profile=retrieval_profile,
        )

    def answer_inventory(self, plan: QueryPlan, document_catalog: list[dict]) -> str:
        if not document_catalog:
            return "Nao encontrei arquivos carregados nesta colecao."

        selected_entries = [
            entry
            for entry in document_catalog
            if plan.requested_document_type is None or self._entry_matches_requested_type(entry, plan.requested_document_type)
        ]
        if not selected_entries:
            label = self._document_type_label(plan.requested_document_type or "document", 2)
            return f"Nao encontrei {label} carregados nesta colecao."

        count = len(selected_entries)
        if plan.inventory_mode == "count":
            label = self._inventory_label(selected_entries, plan.requested_document_type, count)
            return f"Ha {count} {label} carregados nesta colecao."

        lines = [
            f"Encontrei {count} {self._inventory_label(selected_entries, plan.requested_document_type, count)} carregados:"
        ]
        for entry in selected_entries[:MAX_CATALOG_LISTING]:
            lines.append(f"- {self._catalog_entry_label(entry, plan.requested_document_type is None)}")

        remaining = count - min(count, MAX_CATALOG_LISTING)
        if remaining > 0:
            lines.append(f"- ... e mais {remaining} {self._document_type_label('document', remaining)}.")
        return "\n".join(lines)

    def _match_document_ids(self, normalized_question: str, document_catalog: list[dict]) -> list[str]:
        if not normalized_question:
            return []

        matches = []
        for entry in document_catalog:
            alias_matches = []
            for alias in entry.get("normalized_aliases") or []:
                if alias and alias in normalized_question:
                    alias_matches.append((normalized_question.find(alias), len(alias)))
            if not alias_matches:
                continue
            position, score = min(alias_matches, key=lambda item: (item[0] if item[0] >= 0 else 10_000, -item[1]))
            matches.append((position if position >= 0 else 10_000, -score, entry["document_id"]))

        matches.sort()
        seen = set()
        ordered_ids = []
        for _, _, document_id in matches:
            if document_id in seen:
                continue
            seen.add(document_id)
            ordered_ids.append(document_id)
        return ordered_ids

    def _entries_from_ids(self, entry_ids: list[str], document_catalog: list[dict]) -> list[dict]:
        entries_by_id = {entry["document_id"]: entry for entry in document_catalog}
        return [entries_by_id[entry_id] for entry_id in entry_ids if entry_id in entries_by_id]

    def _flatten_backing_document_ids(self, entries: list[dict]) -> list[str]:
        ordered_ids = []
        seen = set()
        for entry in entries:
            for document_id in entry.get("backing_document_ids") or [entry["document_id"]]:
                if document_id in seen:
                    continue
                seen.add(document_id)
                ordered_ids.append(document_id)
        return ordered_ids

    def _is_inventory_decision(self, intent_decision: dict | None) -> bool:
        if not intent_decision:
            return False
        intent = (intent_decision.get("intent") or "").strip().lower()
        confidence = intent_decision.get("confidence")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0
        return intent == "inventory_query" and confidence_value >= 0.90

    def _inventory_mode(self, normalized_question: str) -> str:
        tokens = set(normalized_question.split())
        has_count = bool(tokens & CATALOG_COUNT_TERMS)
        has_list = bool(tokens & CATALOG_LIST_TERMS)
        if has_count and not has_list:
            return "count"
        return "list"

    def _extract_catalog_document_type(self, normalized_question: str) -> str | None:
        tokens = set(normalized_question.split())
        matching_types = [
            document_type
            for document_type, type_terms in CATALOG_TYPE_TERMS.items()
            if tokens & type_terms
        ]
        if len(matching_types) == 1:
            return matching_types[0]
        return None

    def _is_people_query(self, normalized_question: str) -> bool:
        query_terms = set(normalized_question.split())
        return bool(query_terms & PERSON_QUERY_TERMS)

    def _entry_matches_requested_type(self, entry: dict, requested_type: str) -> bool:
        if entry.get("document_type") == requested_type:
            return True
        return requested_type in (entry.get("contained_document_types") or [])

    def _prefers_csv_children(self, normalized_question: str, people_query: bool) -> bool:
        if people_query:
            return True
        tokens = set(normalized_question.split())
        if tokens & CSV_CHILD_PRIORITY_TERMS:
            return True
        return not self._is_broad_file_query(normalized_question)

    def _is_broad_file_query(self, normalized_question: str) -> bool:
        if any(phrase in normalized_question for phrase in BROAD_FILE_QUERY_PHRASES):
            return True
        broad_starts = (
            "me fale",
            "fale",
            "resuma",
            "resumo",
            "sobre ",
            "qual o resumo",
            "qual é o resumo",
        )
        return normalized_question.startswith(broad_starts)

    def _ordered_unique(self, values: list[str]) -> list[str]:
        ordered = []
        seen = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _inventory_label(self, entries: list[dict], requested_document_type: str | None, count: int) -> str:
        if requested_document_type:
            return self._document_type_label(requested_document_type, count)
        if any(entry.get("logical_item_kind") == "folder" for entry in entries):
            return "item" if count == 1 else "itens"
        return self._document_type_label("document", count)

    def _catalog_entry_label(self, entry: dict, include_type_label: bool) -> str:
        display_name = entry["display_name"]
        if entry.get("logical_item_kind") == "folder":
            member_count = entry.get("member_count") or len(entry.get("backing_document_ids") or [])
            folder_label = f"pasta com {member_count} arquivo" if member_count == 1 else f"pasta com {member_count} arquivos"
            if include_type_label:
                contained_types = entry.get("contained_document_types") or []
                if len(contained_types) == 1:
                    return f"{display_name} ({folder_label}, {self._document_type_label(contained_types[0], member_count)})"
            return f"{display_name} ({folder_label})"
        if include_type_label:
            return f"{display_name} ({self._document_type_label(entry['document_type'])})"
        return display_name

    def _document_type_label(self, document_type: str, count: int = 1) -> str:
        singular = {
            "document": "arquivo",
            "spreadsheet": "planilha",
            "pdf": "PDF",
            "image": "imagem",
            "presentation": "apresentacao",
            "text_document": "documento de texto",
            "folder": "pasta",
        }
        plural = {
            "document": "arquivos",
            "spreadsheet": "planilhas",
            "pdf": "PDFs",
            "image": "imagens",
            "presentation": "apresentacoes",
            "text_document": "documentos de texto",
            "folder": "pastas",
        }
        if count == 1:
            return singular.get(document_type, "arquivo")
        return plural.get(document_type, "arquivos")

    def build_catalog_entry(
        self,
        document_id: str,
        display_name: str,
        document_type: str,
        summary: str,
        *,
        backing_document_ids: list[str] | None = None,
        primary_document_id: str | None = None,
        child_document_ids: list[str] | None = None,
        supports_doc_csv_hybrid: bool = False,
        logical_item_kind: str = "file",
        member_count: int = 1,
        match_names: list[str] | None = None,
        contained_document_types: list[str] | None = None,
        child_components: list[dict] | None = None,
    ) -> dict:
        aliases = [display_name]
        if match_names:
            aliases.extend(match_names)
        normalized_aliases = []
        seen_aliases = set()
        for alias in aliases:
            full_name = normalize_identifier(alias)
            if full_name and full_name not in seen_aliases:
                seen_aliases.add(full_name)
                normalized_aliases.append(full_name)
            stem_name = normalize_identifier(Path(alias).stem)
            if stem_name and len(stem_name) >= 4 and stem_name not in seen_aliases:
                seen_aliases.add(stem_name)
                normalized_aliases.append(stem_name)
        return {
            "document_id": document_id,
            "display_name": display_name,
            "name": display_name,
            "document_type": document_type,
            "summary": summary,
            "normalized_name": normalize_identifier(display_name),
            "normalized_stem": normalize_identifier(Path(display_name).stem),
            "normalized_aliases": normalized_aliases,
            "backing_document_ids": list(backing_document_ids or [document_id]),
            "primary_document_id": primary_document_id or document_id,
            "child_document_ids": list(child_document_ids or []),
            "supports_doc_csv_hybrid": supports_doc_csv_hybrid,
            "logical_item_kind": logical_item_kind,
            "member_count": member_count,
            "contained_document_types": list(contained_document_types or [document_type]),
            "child_components": list(child_components or []),
        }
