from __future__ import annotations

import re

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from ..collections.contracts import NormalizedDocument, SpreadsheetModel
from ..spreadsheets.markdown import ROLE_HINT_TERMS, is_human_resources_sheet, normalize_identifier


class RetrievalCoordinator:
    def __init__(self, text_splitter):
        self.text_splitter = text_splitter

    def build_indexes(self, documents: list[NormalizedDocument], document_catalog: list[dict], embeddings):
        chunks = []
        spreadsheet_chunk_index = {}

        for document in documents:
            if document.document_type == "spreadsheet":
                spreadsheet_model = SpreadsheetModel.from_dict(document.structured_data)
                document_chunks = self._build_spreadsheet_chunks(document, spreadsheet_model)
                spreadsheet_chunk_index[document.document_id] = document_chunks
            else:
                document_chunks = self._build_generic_chunks(document)
            chunks.extend(document_chunks)

        chunks.extend(self._build_collection_overview_chunks(document_catalog))
        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": 30, "lambda_mult": 0.2},
        )
        return vector_store, retriever, spreadsheet_chunk_index

    def retrieve(self, plan, vector_store, retriever, spreadsheet_chunk_index, document_catalog):
        if plan.intent == "spreadsheet_entity":
            documents = []
            target_ids = plan.target_document_ids or [
                document_id
                for entry in document_catalog
                if entry.get("document_type") == "spreadsheet" or "spreadsheet" in (entry.get("contained_document_types") or [])
                for document_id in (entry.get("backing_document_ids") or [entry["document_id"]])
            ]
            for document_id in target_ids:
                documents.extend(self._retrieve_spreadsheet_chunks(plan.resolved_query, document_id, spreadsheet_chunk_index))
            return self._deduplicate_docs(documents)

        if plan.target_document_ids:
            if plan.retrieval_profile in {"parent_overview_first", "csv_child_first"}:
                hybrid_entry = self._find_hybrid_catalog_entry(plan.target_document_ids, document_catalog)
                if hybrid_entry:
                    return self._retrieve_doc_csv_hybrid_docs(
                        question=plan.resolved_query,
                        entry=hybrid_entry,
                        vector_store=vector_store,
                        retrieval_profile=plan.retrieval_profile,
                    )
            documents = []
            for document_id in plan.target_document_ids:
                documents.extend(self._retrieve_target_document_docs(plan.resolved_query, document_id, vector_store))
            return self._deduplicate_docs(documents)

        return retriever.invoke(plan.resolved_query)

    def _build_generic_chunks(self, document: NormalizedDocument) -> list[Document]:
        source_document = Document(
            page_content=document.content_text,
            metadata=self._base_metadata(document),
        )
        chunks = self.text_splitter.split_documents([source_document])
        built_chunks = []
        header = self._document_header(document)
        for chunk in chunks:
            chunk.page_content = f"Cabecalho do documento:\n{header}\n\nTrecho:\n{chunk.page_content}"
            chunk.metadata["chunk_kind"] = "text"
            chunk.metadata["search_text_normalized"] = normalize_identifier(chunk.page_content)
            built_chunks.append(chunk)
        return built_chunks

    def _build_spreadsheet_chunks(
        self,
        document: NormalizedDocument,
        spreadsheet_model: SpreadsheetModel | None,
    ) -> list[Document]:
        if not spreadsheet_model:
            return self._build_generic_chunks(document)

        header = self._document_header(document)
        base_metadata = self._base_metadata(document)
        chunks = []
        overview_only = (
            document.extraction_method == "doc-csv"
            and document.component_kind == "spreadsheet_parent"
        )

        if spreadsheet_model.summary_lines:
            chunks.append(
                self._create_spreadsheet_chunk(
                    header=header,
                    title="Resumo da planilha",
                    body_lines=spreadsheet_model.summary_lines,
                    metadata={**base_metadata, "chunk_kind": "summary"},
                )
            )

        for sheet in spreadsheet_model.sheets:
            sheet_metadata = {
                **base_metadata,
                "sheet_name": sheet.name,
                "sheet_name_normalized": normalize_identifier(sheet.name),
            }
            if sheet.summary_lines:
                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Resumo da aba {sheet.name}",
                        body_lines=sheet.summary_lines,
                        metadata={**sheet_metadata, "chunk_kind": "sheet_summary"},
                    )
                )

            if overview_only:
                continue

            for profile in sheet.column_profiles:
                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Perfil de coluna da aba {sheet.name}",
                        body_lines=[profile],
                        metadata={**sheet_metadata, "chunk_kind": "column_profile"},
                    )
                )

            if sheet.people:
                role_counts = {}
                for person in sheet.people:
                    if person.role:
                        role_counts[person.role] = role_counts.get(person.role, 0) + 1
                summary_lines = [
                    f"Documento: {document.display_name}",
                    f"Aba: {sheet.name}",
                    f"Total de pessoas detectadas: {len(sheet.people)}",
                    "Nomes detectados: " + ", ".join(person.name for person in sheet.people),
                ]
                if role_counts:
                    role_summary = ", ".join(
                        f"{role} ({count})"
                        for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
                    )
                    summary_lines.append(f"Funcoes em destaque: {role_summary}")

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Resumo de pessoas da aba {sheet.name}",
                        body_lines=summary_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "people_summary",
                            "people_count": len(sheet.people),
                            "entity_names": [person.name for person in sheet.people],
                            "entity_names_normalized": [normalize_identifier(person.name) for person in sheet.people],
                        },
                    )
                )

            for person in sheet.people:
                person_lines = [
                    f"Documento: {document.display_name}",
                    f"Aba: {person.sheet_name or sheet.name}",
                    f"Pessoa: {person.name}",
                ]
                if person.role:
                    person_lines.append(f"Funcao: {person.role}")
                if person.row_number is not None:
                    person_lines.append(f"Linha: {person.row_number}")

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Entrada de pessoa da aba {person.sheet_name or sheet.name}",
                        body_lines=person_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "people_index",
                            "entity_name": person.name,
                            "entity_name_normalized": normalize_identifier(person.name),
                            "entity_role": person.role,
                            "entity_role_normalized": normalize_identifier(person.role or ""),
                            "row_number": person.row_number,
                        },
                    )
                )

            for row in sheet.rows:
                record_lines = [
                    f"Documento: {document.display_name}",
                    f"Aba: {sheet.name}",
                ]
                if row.row_number is not None:
                    record_lines.append(f"Linha: {row.row_number}")
                if row.entity:
                    record_lines.append(f"Pessoa: {row.entity.name}")
                    if row.entity.role:
                        record_lines.append(f"Funcao: {row.entity.role}")
                record_lines.append(
                    "Registro completo: "
                    + " | ".join(f"{pair['header']}={pair['value']}" for pair in row.pairs)
                )

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Registro da aba {sheet.name}",
                        body_lines=record_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "row_record",
                            "row_number": row.row_number,
                            "entity_name": row.entity.name if row.entity else None,
                            "entity_name_normalized": normalize_identifier(row.entity.name if row.entity else ""),
                            "entity_role": row.entity.role if row.entity else None,
                            "entity_role_normalized": normalize_identifier(row.entity.role if row.entity else ""),
                        },
                    )
                )

        return chunks

    def _base_metadata(self, document: NormalizedDocument) -> dict:
        return {
            "document_id": document.document_id,
            "document_name": document.display_name,
            "document_type": document.document_type,
            "logical_item_id": document.logical_item_id,
            "catalog_visibility": document.catalog_visibility or "visible",
            "parent_document_id": document.parent_document_id,
            "component_kind": document.component_kind,
            "component_name": document.component_name,
            "component_name_normalized": normalize_identifier(document.component_name or ""),
            "extraction_method": document.extraction_method,
        }

    def _create_spreadsheet_chunk(self, header: str, title: str, body_lines: list[str], metadata: dict) -> Document:
        content_lines = [f"Cabecalho do documento:\n{header}", "", title, *body_lines]
        page_content = "\n".join(line for line in content_lines if line is not None).strip()
        metadata = dict(metadata)
        metadata["search_text_normalized"] = normalize_identifier(" ".join(body_lines))
        return Document(page_content=page_content, metadata=metadata)

    def _document_header(self, document: NormalizedDocument) -> str:
        lines = [
            f"Nome: {document.display_name}",
            f"Tipo: {document.document_type}",
        ]
        if document.summary:
            lines.append(f"Resumo: {document.summary}")
        return "\n".join(lines)

    def _build_collection_overview_chunks(self, document_catalog: list[dict]) -> list[Document]:
        if not document_catalog:
            return []

        lines = [f"Total de arquivos carregados: {len(document_catalog)}"]
        type_groups = {}
        for entry in document_catalog:
            document_type = entry.get("document_type") or "document"
            type_groups.setdefault(document_type, []).append(entry["display_name"])
        for document_type, names in sorted(type_groups.items()):
            lines.append(f"{document_type}: {', '.join(names[:10])}")

        return [
            Document(
                page_content="\n".join(lines),
                metadata={
                    "document_id": "__collection_overview__",
                    "document_name": "collection_overview",
                    "document_type": "document",
                    "chunk_kind": "collection_overview",
                    "search_text_normalized": normalize_identifier(" ".join(lines)),
                },
            )
        ]

    def _retrieve_target_document_docs(self, question: str, document_id: str, vector_store, k: int = 6):
        docs = vector_store.max_marginal_relevance_search(
            f"{document_id} {question}".strip(),
            k=k,
            fetch_k=100,
            lambda_mult=0.2,
            filter={"document_id": document_id},
        )
        if docs:
            return docs

        return vector_store.similarity_search(
            question,
            k=k,
            fetch_k=100,
            filter={"document_id": document_id},
        )

    def _retrieve_doc_csv_hybrid_docs(self, question: str, entry: dict, vector_store, retrieval_profile: str):
        primary_document_id = entry.get("primary_document_id")
        child_document_ids = list(entry.get("child_document_ids") or [])
        targeted_child_ids = self._match_child_sheet_ids(question, entry) or child_document_ids
        documents = []

        if retrieval_profile == "parent_overview_first":
            if primary_document_id:
                documents.extend(self._retrieve_target_document_docs(question, primary_document_id, vector_store, k=3))
            child_docs = self._retrieve_document_ids(
                question,
                targeted_child_ids,
                vector_store,
                per_document_k=2,
                overall_limit=6,
            )
            if not child_docs and targeted_child_ids != child_document_ids:
                child_docs = self._retrieve_document_ids(
                    question,
                    child_document_ids,
                    vector_store,
                    per_document_k=2,
                    overall_limit=6,
                )
            documents.extend(child_docs)
            return self._deduplicate_docs(documents)[:8]

        child_docs = self._retrieve_document_ids(
            question,
            targeted_child_ids,
            vector_store,
            per_document_k=3,
            overall_limit=8,
        )
        if not child_docs and targeted_child_ids != child_document_ids:
            child_docs = self._retrieve_document_ids(
                question,
                child_document_ids,
                vector_store,
                per_document_k=3,
                overall_limit=8,
            )
        documents.extend(child_docs)
        if primary_document_id:
            documents.extend(self._retrieve_target_document_docs(question, primary_document_id, vector_store, k=1))
        return self._deduplicate_docs(documents)[:8]

    def _retrieve_document_ids(
        self,
        question: str,
        document_ids: list[str],
        vector_store,
        *,
        per_document_k: int,
        overall_limit: int,
    ) -> list[Document]:
        documents = []
        for document_id in document_ids:
            documents.extend(self._retrieve_target_document_docs(question, document_id, vector_store, k=per_document_k))
            if len(documents) >= overall_limit:
                break
        return documents[:overall_limit]

    def _find_hybrid_catalog_entry(self, target_document_ids: list[str], document_catalog: list[dict]) -> dict | None:
        target_set = set(target_document_ids)
        for entry in document_catalog:
            if not entry.get("supports_doc_csv_hybrid"):
                continue
            backing_ids = set(entry.get("backing_document_ids") or [entry["document_id"]])
            if target_set and target_set <= backing_ids:
                return entry
        for entry in document_catalog:
            if not entry.get("supports_doc_csv_hybrid"):
                continue
            if entry.get("primary_document_id") in target_set:
                return entry
        return None

    def _match_child_sheet_ids(self, question: str, entry: dict) -> list[str]:
        normalized_question = normalize_identifier(question)
        matches = []
        for child in entry.get("child_components") or []:
            component_name = child.get("component_name") or ""
            component_name_normalized = normalize_identifier(component_name)
            if not component_name_normalized:
                continue
            if component_name_normalized in normalized_question:
                matches.append(child["document_id"])
                continue
            if f"aba {component_name_normalized}" in normalized_question or f"sheet {component_name_normalized}" in normalized_question:
                matches.append(child["document_id"])
                continue
            if component_name_normalized == "rh" and re.search(r"\brh\b", normalized_question):
                matches.append(child["document_id"])
        return matches

    def _retrieve_spreadsheet_chunks(self, question: str, document_id: str, spreadsheet_chunk_index: dict[str, list[Document]]):
        chunks = spreadsheet_chunk_index.get(document_id) or []
        if not chunks:
            return []

        normalized_question = normalize_identifier(question)
        target_sheet = self._extract_sheet_reference(normalized_question, chunks)
        query_terms = [term for term in normalized_question.split() if term]

        candidate_chunks = [
            chunk
            for chunk in chunks
            if chunk.metadata.get("chunk_kind") in {"people_summary", "people_index", "row_record", "sheet_summary"}
        ]
        if target_sheet:
            candidate_chunks = [
                chunk
                for chunk in candidate_chunks
                if chunk.metadata.get("sheet_name_normalized") == target_sheet
            ] or candidate_chunks

        scored_chunks = []
        for chunk in candidate_chunks:
            score = self._score_spreadsheet_chunk(chunk, query_terms, target_sheet)
            if score <= 0:
                continue
            row_number = chunk.metadata.get("row_number")
            stable_row = row_number if isinstance(row_number, int) else 10_000
            scored_chunks.append((score, chunk.metadata.get("chunk_kind") or "", stable_row, chunk))

        scored_chunks.sort(key=lambda item: (-item[0], item[1], item[2]))

        selected = []
        seen = set()
        for _, _, stable_row, chunk in scored_chunks:
            if chunk.metadata.get("entity_name"):
                unique_key = (
                    "person",
                    chunk.metadata.get("sheet_name"),
                    chunk.metadata.get("entity_name_normalized") or chunk.metadata.get("entity_name"),
                )
            else:
                unique_key = (
                    chunk.metadata.get("chunk_kind"),
                    chunk.metadata.get("sheet_name"),
                    stable_row,
                    chunk.metadata.get("entity_name"),
                )
            if unique_key in seen:
                continue
            seen.add(unique_key)
            selected.append(chunk)
            if len(selected) >= 12:
                break

        selected.sort(
            key=lambda chunk: (
                0 if chunk.metadata.get("chunk_kind") == "people_summary" else 1,
                0 if chunk.metadata.get("entity_name") else 1,
                chunk.metadata.get("row_number") if isinstance(chunk.metadata.get("row_number"), int) else 10_000,
                chunk.metadata.get("entity_name") or "",
            )
        )
        return selected

    def _extract_sheet_reference(self, normalized_question: str, chunks: list[Document]) -> str | None:
        for chunk in chunks:
            sheet_name_normalized = chunk.metadata.get("sheet_name_normalized")
            if not sheet_name_normalized:
                continue
            if sheet_name_normalized in normalized_question or f"aba {sheet_name_normalized}" in normalized_question:
                return sheet_name_normalized
        if re.search(r"\brh\b", normalized_question):
            return "rh"
        return None

    def _score_spreadsheet_chunk(self, chunk: Document, query_terms: list[str], target_sheet: str | None) -> float:
        metadata = chunk.metadata
        chunk_kind = metadata.get("chunk_kind") or ""
        search_text = metadata.get("search_text_normalized") or normalize_identifier(chunk.page_content)
        sheet_name_normalized = metadata.get("sheet_name_normalized")
        entity_name_normalized = metadata.get("entity_name_normalized") or ""
        entity_role_normalized = metadata.get("entity_role_normalized") or ""
        row_number = metadata.get("row_number")

        overlap_count = sum(1 for term in query_terms if term in search_text)
        score = overlap_count * 12

        kind_weights = {
            "summary": 20,
            "sheet_summary": 24,
            "column_profile": 12,
            "people_summary": 52,
            "people_index": 38,
            "row_record": 28,
        }
        score += kind_weights.get(chunk_kind, 0)

        if target_sheet:
            if sheet_name_normalized == target_sheet:
                score += 50
            elif sheet_name_normalized:
                score -= 8

        if entity_name_normalized:
            score += sum(1 for term in query_terms if term in entity_name_normalized) * 40
        if entity_role_normalized:
            score += sum(1 for term in query_terms if term in entity_role_normalized) * 18
            if any(term in entity_role_normalized for term in ROLE_HINT_TERMS):
                score += 8
        if is_human_resources_sheet(metadata.get("sheet_name") or ""):
            score += 20
        if isinstance(row_number, int):
            score += max(0, 30 - min(row_number, 30)) * 3

        return score

    def _deduplicate_docs(self, docs: list[Document]) -> list[Document]:
        selected = []
        seen = set()
        for doc in docs:
            key = (
                doc.metadata.get("document_id"),
                doc.metadata.get("chunk_kind"),
                doc.metadata.get("sheet_name"),
                doc.metadata.get("row_number"),
                doc.metadata.get("entity_name"),
                doc.page_content[:120],
            )
            if key in seen:
                continue
            seen.add(key)
            selected.append(doc)
        return selected
