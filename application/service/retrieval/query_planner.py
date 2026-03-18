from __future__ import annotations

from pathlib import Path

from ..collections.contracts import QueryPlan
from ..spreadsheets.markdown import PERSON_QUERY_TERMS, normalize_identifier


QUERY_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "qual",
    "quais",
    "que",
    "sobre",
    "sao",
    "se",
    "um",
    "uma",
    "voce",
    "voces",
    "vc",
    "vcs",
    "you",
}
CATALOG_DOCUMENT_TERMS = {
    "arquivo",
    "arquivos",
    "documento",
    "documentos",
    "file",
    "files",
    "doc",
    "docs",
    "pdf",
    "pdfs",
    "planilha",
    "planilhas",
    "spreadsheet",
    "spreadsheets",
    "imagem",
    "imagens",
    "image",
    "images",
}
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
CATALOG_LOAD_TERMS = {
    "seria",
    "seriam",
    "foi",
    "foram",
    "tem",
    "tenho",
    "ha",
    "carregado",
    "carregada",
    "carregados",
    "carregadas",
    "enviado",
    "enviada",
    "enviados",
    "enviadas",
    "importado",
    "importada",
    "importados",
    "importadas",
    "disponivel",
    "disponiveis",
    "presente",
    "presentes",
    "base",
    "colecao",
    "colecoes",
    "pasta",
    "loaded",
    "uploaded",
    "available",
    "existing",
    "exist",
    "exists",
    "existem",
    "processado",
    "processada",
    "processados",
    "processadas",
    "processou",
    "processaram",
    "leu",
    "lidos",
    "lidas",
}
CATALOG_TYPE_TERMS = {
    "spreadsheet": {"planilha", "planilhas", "spreadsheet", "spreadsheets", "xlsx", "csv"},
    "pdf": {"pdf", "pdfs"},
    "image": {"imagem", "imagens", "image", "images", "jpg", "jpeg", "png", "gif", "webp"},
    "presentation": {"apresentacao", "apresentacoes", "presentation", "presentations", "ppt", "pptx"},
    "text_document": {"doc", "docs", "docx", "texto", "text", "html", "markdown", "md"},
}
CATALOG_INTENT_TERMS = CATALOG_DOCUMENT_TERMS | CATALOG_LIST_TERMS | CATALOG_COUNT_TERMS | CATALOG_LOAD_TERMS
MAX_CATALOG_LISTING = 25


class QueryPlanner:
    def plan(self, question: str, resolved_query: str, document_catalog: list[dict]) -> QueryPlan:
        normalized = normalize_identifier(resolved_query or question)
        matched_document_ids = self._match_document_ids(normalized, document_catalog)
        requested_type = self._extract_catalog_document_type(normalized)
        people_query = self._is_people_query(normalized)

        if self._is_inventory_question(normalized, matched_document_ids):
            return QueryPlan(
                intent="inventory",
                target_document_ids=[],
                requested_document_type=requested_type,
                needs_structured_lookup=False,
                resolved_query=resolved_query,
                inventory_mode=self._inventory_mode(normalized),
            )

        if len(matched_document_ids) > 1:
            return QueryPlan(
                intent="multi_document",
                target_document_ids=matched_document_ids,
                requested_document_type=requested_type,
                needs_structured_lookup=people_query,
                resolved_query=resolved_query,
            )

        if len(matched_document_ids) == 1:
            matched_entry = next(
                (entry for entry in document_catalog if entry["document_id"] == matched_document_ids[0]),
                None,
            )
            if people_query and matched_entry and matched_entry.get("document_type") == "spreadsheet":
                intent = "spreadsheet_entity"
            else:
                intent = "single_document"
            return QueryPlan(
                intent=intent,
                target_document_ids=matched_document_ids,
                requested_document_type=requested_type,
                needs_structured_lookup=people_query,
                resolved_query=resolved_query,
            )

        if people_query and requested_type == "spreadsheet":
            spreadsheet_ids = [
                entry["document_id"] for entry in document_catalog if entry.get("document_type") == "spreadsheet"
            ]
            return QueryPlan(
                intent="spreadsheet_entity",
                target_document_ids=spreadsheet_ids,
                requested_document_type=requested_type,
                needs_structured_lookup=True,
                resolved_query=resolved_query,
            )

        return QueryPlan(
            intent="generic_semantic",
            target_document_ids=[],
            requested_document_type=requested_type,
            needs_structured_lookup=False,
            resolved_query=resolved_query,
        )

    def answer_inventory(self, plan: QueryPlan, document_catalog: list[dict]) -> str:
        if not document_catalog:
            return "Nao encontrei arquivos carregados nesta colecao."

        selected_entries = [
            entry
            for entry in document_catalog
            if plan.requested_document_type is None or entry.get("document_type") == plan.requested_document_type
        ]
        if not selected_entries:
            label = self._document_type_label(plan.requested_document_type or "document", 2)
            return f"Nao encontrei {label} carregados nesta colecao."

        count = len(selected_entries)
        if plan.inventory_mode == "count":
            label = self._document_type_label(plan.requested_document_type or "document", count)
            return f"Ha {count} {label} carregados nesta colecao."

        lines = [
            f"Encontrei {count} {self._document_type_label(plan.requested_document_type or 'document', count)} carregados:"
        ]
        for entry in selected_entries[:MAX_CATALOG_LISTING]:
            if plan.requested_document_type:
                lines.append(f"- {entry['display_name']}")
            else:
                lines.append(f"- {entry['display_name']} ({self._document_type_label(entry['document_type'])})")

        remaining = count - min(count, MAX_CATALOG_LISTING)
        if remaining > 0:
            lines.append(f"- ... e mais {remaining} {self._document_type_label('document', remaining)}.")
        return "\n".join(lines)

    def _match_document_ids(self, normalized_question: str, document_catalog: list[dict]) -> list[str]:
        if not normalized_question:
            return []

        matches = []
        for entry in document_catalog:
            full_name = entry.get("normalized_name") or ""
            stem_name = entry.get("normalized_stem") or ""
            if full_name and full_name in normalized_question:
                score = len(full_name)
                position = normalized_question.find(full_name)
            elif stem_name and len(stem_name) >= 4 and stem_name in normalized_question:
                score = len(stem_name)
                position = normalized_question.find(stem_name)
            else:
                continue
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

    def _is_inventory_question(self, normalized_question: str, matched_document_ids: list[str]) -> bool:
        if not normalized_question or matched_document_ids:
            return False
        if any(
            phrase in normalized_question
            for phrase in (
                "o que foi carregado",
                "o que foi enviado",
                "what was loaded",
                "what is loaded",
            )
        ):
            return True

        tokens = normalized_question.split()
        if not tokens or not set(tokens) & CATALOG_INTENT_TERMS:
            return False

        remaining_tokens = [
            token
            for token in tokens
            if token not in QUERY_STOPWORDS and token not in CATALOG_INTENT_TERMS
        ]
        return not remaining_tokens

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

    def _document_type_label(self, document_type: str, count: int = 1) -> str:
        singular = {
            "document": "arquivo",
            "spreadsheet": "planilha",
            "pdf": "PDF",
            "image": "imagem",
            "presentation": "apresentacao",
            "text_document": "documento de texto",
        }
        plural = {
            "document": "arquivos",
            "spreadsheet": "planilhas",
            "pdf": "PDFs",
            "image": "imagens",
            "presentation": "apresentacoes",
            "text_document": "documentos de texto",
        }
        if count == 1:
            return singular.get(document_type, "arquivo")
        return plural.get(document_type, "arquivos")

    def build_catalog_entry(self, document_id: str, display_name: str, document_type: str, summary: str) -> dict:
        return {
            "document_id": document_id,
            "display_name": display_name,
            "name": display_name,
            "document_type": document_type,
            "summary": summary,
            "normalized_name": normalize_identifier(display_name),
            "normalized_stem": normalize_identifier(Path(display_name).stem),
        }
