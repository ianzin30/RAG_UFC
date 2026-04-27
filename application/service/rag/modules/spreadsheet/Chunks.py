"""Chunk builders for generic documents and spreadsheets."""
# Simple: Break documents into smaller pieces for searching

import re

from langchain_core.documents import Document


_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class SpreadsheetChunkBuilderMixin:
    # ------------------------------------------------------------------
    # Generic document chunking
    # ------------------------------------------------------------------
    # The strategy is collection-agnostic:
    #   1. Strip the document wrapper (filename header, extraction metadata).
    #   2. Split by markdown headings when present; otherwise treat the
    #      entire body as a single section.
    #   3. Window each section through the configured RecursiveCharacterTextSplitter.
    # Each emitted chunk holds raw text in `page_content` (no labelled prefixes
    # like "Documento: X / Secao: Y / Trecho:") so the embedder and the LLM
    # see the actual content. Document/section labels live only in metadata
    # and are surfaced to the LLM via the prompt formatter.
    def _build_generic_chunks(self, document: Document, header: str) -> list[Document]:
        del header  # Document headers are surfaced via metadata, not content prefixes.
        chunks: list[Document] = []

        profile_chunk = self._create_generic_document_profile_chunk(document)
        if profile_chunk is not None:
            chunks.append(profile_chunk)

        body_text = self._prepare_generic_document_body(document.page_content)
        if not body_text:
            body_text = self._strip_document_wrapper(document.page_content) or self._normalize_whitespace(
                document.page_content
            )

        document_name = str(document.metadata.get("document_name") or "documento").strip()
        base_metadata = dict(document.metadata)
        sections = self._split_by_markdown_headings(body_text)
        for section_index, section in enumerate(sections):
            section_text = (section.get("text") or "").strip()
            if not section_text:
                continue
            section_title = section.get("title")
            section_source = Document(page_content=section_text, metadata=dict(base_metadata))
            windows = self.text_splitter.split_documents([section_source])
            for window_index, window in enumerate(windows):
                window_text = self._normalize_whitespace(window.page_content)
                if not window_text:
                    continue
                chunk_metadata = dict(base_metadata)
                chunk_metadata["chunk_kind"] = "section_detail"
                chunk_metadata["chunk_order"] = section_index * 1000 + window_index
                chunk_metadata["section_title"] = section_title or ""
                chunk_metadata["section_title_normalized"] = self._normalize_identifier(section_title or "")
                chunk_metadata["section_key"] = f"section-{section_index}"
                chunk_metadata["section_is_header_metadata"] = False
                chunk_metadata["search_text_normalized"] = self._normalize_identifier(
                    " ".join(
                        part
                        for part in (document_name, section_title or "", window_text)
                        if part
                    )
                )
                chunks.append(Document(page_content=window_text, metadata=chunk_metadata))
        return chunks

    def _create_generic_document_profile_chunk(self, document: Document) -> Document | None:
        document_name = str(document.metadata.get("document_name") or "").strip()
        if not document_name:
            return None
        body = self._strip_document_wrapper(document.page_content) or self._normalize_whitespace(
            document.page_content
        )
        if not body:
            return None
        opening_lines: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("<!--") or stripped.startswith("#"):
                continue
            opening_lines.append(stripped)
            if len(opening_lines) >= 3:
                break
        if not opening_lines:
            return None
        page_content = " ".join(opening_lines)[:600].strip()
        if not page_content:
            return None
        metadata = dict(document.metadata)
        metadata["chunk_kind"] = "document_profile"
        metadata["chunk_order"] = -1
        metadata["section_title"] = ""
        metadata["section_title_normalized"] = ""
        metadata["section_key"] = "document-profile"
        metadata["section_is_header_metadata"] = False
        metadata["search_text_normalized"] = self._normalize_identifier(
            " ".join([document_name, page_content])
        )
        return Document(page_content=page_content, metadata=metadata)

    def _split_by_markdown_headings(self, text: str) -> list[dict]:
        """Split text by Markdown headings (`#`...`######`).

        Returns a list of {title, text} dicts in document order. Text appearing
        before the first heading is emitted as a leading section with `title=None`.
        Falls back to a single section when no headings are present.
        """
        if not text:
            return []

        sections: list[dict] = []
        current_title: str | None = None
        current_lines: list[str] = []

        def flush_current() -> None:
            if current_lines:
                sections.append(
                    {"title": current_title, "text": "\n".join(current_lines).strip()}
                )

        for line in text.splitlines():
            stripped = line.strip()
            heading_match = _MARKDOWN_HEADING_RE.match(stripped)
            if heading_match and len(heading_match.group(1)) <= 6:
                heading_text = heading_match.group(2).strip()
                # Skip pure-marker headings like "# 01_01-2022_Ata" that are
                # really filename echoes; they offer no section signal but
                # still mark a structural boundary, so we just close the
                # current section without setting a new title.
                flush_current()
                current_lines = []
                current_title = heading_text or None
                continue
            current_lines.append(line)

        flush_current()
        if not sections:
            return [{"title": None, "text": text.strip()}]
        return sections

    # ------------------------------------------------------------------
    # Spreadsheet chunking (unchanged)
    # ------------------------------------------------------------------
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

