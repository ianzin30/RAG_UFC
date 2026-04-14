"""Spreadsheet-specific retrieval helpers."""

from ...constants import ROLE_HINT_TERMS


# Este mixin aplica um ranking proprio para chunks estruturados de planilhas.
class SpreadsheetRetrievalMixin:
    # Esta busca privilegia pessoas, abas e linhas antes de recorrer ao retrieval generico.
    def _retrieve_spreadsheet_chunks(self, question: str, target_document_name: str) -> list:
        chunks = self.spreadsheet_chunk_index.get(target_document_name) or []
        if not chunks:
            return []

        people_query = self._is_people_question(question, target_document_name)
        target_sheet = self._extract_sheet_reference(question, target_document_name)
        query_terms = self._tokenize_search_text(question)

        candidate_chunks = chunks
        if people_query:
            entity_chunks = [
                chunk
                for chunk in chunks
                if chunk.metadata.get("chunk_kind") in {"people_index", "row_record"}
                and chunk.metadata.get("entity_name")
            ]
            if target_sheet:
                sheet_chunks = [
                    chunk
                    for chunk in entity_chunks
                    if chunk.metadata.get("sheet_name_normalized") == target_sheet
                ]
                if sheet_chunks:
                    entity_chunks = sheet_chunks
            if entity_chunks:
                candidate_chunks = entity_chunks

        scored_chunks = []
        for chunk in candidate_chunks:
            score = self._score_spreadsheet_chunk(chunk, query_terms, people_query, target_sheet)
            if score <= 0:
                continue

            row_number = chunk.metadata.get("row_number")
            stable_row = row_number if isinstance(row_number, int) else 10_000
            chunk_kind = chunk.metadata.get("chunk_kind") or ""
            scored_chunks.append((score, chunk_kind, stable_row, chunk))

        if not scored_chunks:
            return []

        scored_chunks.sort(key=lambda item: (-item[0], item[1], item[2]))
        selected = []
        seen = set()
        for _, chunk_kind, stable_row, chunk in scored_chunks:
            unique_key = (
                chunk_kind,
                chunk.metadata.get("sheet_name"),
                stable_row,
                chunk.metadata.get("entity_name"),
                chunk.page_content[:80],
            )
            if unique_key in seen:
                continue
            seen.add(unique_key)
            selected.append(chunk)
            if len(selected) >= 6:
                break
        return selected

    # Esta pontuacao combina sinais de aba, entidade, papel e sobreposicao textual.
    def _score_spreadsheet_chunk(
        self,
        chunk,
        query_terms: list[str],
        people_query: bool,
        target_sheet: str | None,
    ) -> float:
        metadata = chunk.metadata
        chunk_kind = metadata.get("chunk_kind") or ""
        search_text = metadata.get("search_text_normalized") or self._normalize_identifier(chunk.page_content)
        sheet_name_normalized = metadata.get("sheet_name_normalized")
        entity_name = metadata.get("entity_name")
        entity_name_normalized = metadata.get("entity_name_normalized") or ""
        entity_role_normalized = metadata.get("entity_role_normalized") or ""
        row_number = metadata.get("row_number")

        overlap_count = sum(1 for term in query_terms if term in search_text)
        score = overlap_count * 12

        kind_weights = {
            "summary": 30,
            "sheet_summary": 24,
            "column_profile": 12,
            "people_index": 38,
            "row_record": 28,
        }
        score += kind_weights.get(chunk_kind, 0)

        if target_sheet:
            if sheet_name_normalized == target_sheet:
                score += 50
            elif sheet_name_normalized:
                score -= 8

        if people_query:
            if chunk_kind == "people_index":
                score += 130
            elif chunk_kind == "row_record" and entity_name:
                score += 100
            else:
                score -= 20

            if sheet_name_normalized == "rh":
                score += 45
            if entity_name:
                score += 20
            if entity_role_normalized:
                score += 10

        else:
            if chunk_kind == "summary" and any(term in query_terms for term in ("arquivo", "planilha", "resumo", "sobre")):
                score += 45
            if chunk_kind == "sheet_summary" and any(term in query_terms for term in ("aba", "abas", "sheet")):
                score += 40
            if chunk_kind == "column_profile" and any(term in query_terms for term in ROLE_HINT_TERMS):
                score += 10

        if entity_name_normalized:
            name_overlap = sum(1 for term in query_terms if term in entity_name_normalized)
            score += name_overlap * 40

        if entity_role_normalized:
            role_overlap = sum(1 for term in query_terms if term in entity_role_normalized)
            score += role_overlap * 18
            if any(term in entity_role_normalized for term in ROLE_HINT_TERMS):
                score += 8

        if people_query and entity_name and isinstance(row_number, int):
            score += max(0, 30 - min(row_number, 30)) * 0.5
        return score
