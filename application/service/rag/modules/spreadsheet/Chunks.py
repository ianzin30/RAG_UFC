"""Chunk builders for generic documents and spreadsheets."""
# Simple: Break documents into smaller pieces for searching

import re

from langchain_core.documents import Document


class SpreadsheetChunkBuilderMixin:
    def _build_generic_chunks(self, document: Document, header: str) -> list[Document]:
        built_chunks = []
        profile_chunk = self._create_generic_document_profile_chunk(document)
        if profile_chunk is not None:
            built_chunks.append(profile_chunk)

        body_text = self._prepare_generic_document_body(document.page_content)
        if not body_text:
            body_text = self._strip_document_wrapper(document.page_content) or self._normalize_whitespace(document.page_content)
        document_name = str(document.metadata.get("document_name") or "documento").strip()
        base_metadata = dict(document.metadata)
        sections = self._split_generic_sections(body_text)

        if not sections:
            sections = [{"title": "Conteudo principal", "text": body_text, "order": 0, "section_key": "section-0"}]

        for section in sections:
            overview_chunk = self._create_generic_section_overview_chunk(base_metadata, section)
            if overview_chunk is not None:
                built_chunks.append(overview_chunk)

            entity_chunk = self._create_generic_entity_index_chunk(base_metadata, section)
            if entity_chunk is not None:
                built_chunks.append(entity_chunk)

            list_chunk = self._create_generic_list_chunk(base_metadata, section)
            if list_chunk is not None:
                built_chunks.append(list_chunk)

            built_chunks.extend(self._build_generic_section_detail_chunks(base_metadata, document_name, section))
        return built_chunks

    def _create_generic_document_profile_chunk(self, document: Document) -> Document | None:
        document_name = str(document.metadata.get("document_name") or "documento").strip()
        profile_lines = self._build_generic_document_profile_lines(document_name, document.page_content)
        if not profile_lines:
            return None

        metadata = dict(document.metadata)
        metadata["chunk_kind"] = "document_profile"
        metadata["chunk_order"] = -1
        metadata["search_text_normalized"] = self._normalize_identifier(" ".join(profile_lines))
        page_content = "\n".join(["Perfil do documento", *profile_lines]).strip()
        return Document(page_content=page_content, metadata=metadata)

    def _split_generic_sections(self, text: str) -> list[dict]:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        if not lines:
            return []

        sections = []
        current_title = "Abertura"
        current_lines = []

        for line in lines:
            if self._looks_like_generic_section_heading(line):
                if current_lines:
                    sections.append(
                        self._build_generic_section_payload(current_title, current_lines, len(sections))
                    )
                current_title = line.rstrip(":").strip() or f"Secao {len(sections) + 1}"
                current_lines = []
                continue
            current_lines.append(line)

        if current_lines:
            sections.append(self._build_generic_section_payload(current_title, current_lines, len(sections)))
        return sections

    def _looks_like_generic_section_heading(self, line: str) -> bool:
        stripped = (line or "").strip()
        if not stripped:
            return False
        if self._is_section_heading(stripped):
            return True
        if self._is_noise_like_generic_heading(stripped):
            return False
        if stripped.endswith(":") and 2 <= len(stripped.split()) <= 10:
            return True
        letters = [char for char in stripped if char.isalpha()]
        if letters:
            uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
            if uppercase_ratio >= 0.75 and 2 <= len(stripped.split()) <= 10 and len(stripped) <= 120:
                return True
        return False

    def _is_noise_like_generic_heading(self, line: str) -> bool:
        normalized = self._normalize_identifier(line)
        if not normalized:
            return True

        tokens = normalized.split()
        if len(tokens) == 1:
            token = tokens[0]
            if re.fullmatch(r"(?:[ivxlcdm]+|fy\d{2,4}|\d+)", token):
                return True
            if len(token) <= 6:
                return True

        compact = re.sub(r"[^A-Za-z0-9]", "", line or "")
        if compact and compact.isupper() and len(tokens) <= 3:
            return True
        if re.fullmatch(r"[A-Z0-9/\-()]+", (line or "").strip()):
            return True
        return False

    def _build_generic_section_payload(self, title: str, lines: list[str], order: int) -> dict:
        section_text = "\n".join(lines).strip()
        section_key = f"section-{order}-{self._normalize_identifier(title)[:32] or 'conteudo'}"
        return {
            "title": title.strip() or f"Secao {order + 1}",
            "text": section_text,
            "order": order,
            "section_key": section_key,
            "is_header_metadata": self._looks_like_header_metadata_section(section_text),
            "names": self._extract_name_candidates(section_text, limit=60),
            "dates": self._extract_date_candidates(section_text, limit=12),
            "money_values": self._extract_money_candidates(section_text, limit=12),
            "labeled_facts": self._extract_labeled_facts(section_text, limit=20),
        }

    def _looks_like_header_metadata_section(self, section_text: str) -> bool:
        normalized = self._normalize_identifier(section_text)
        metadata_markers = (
            "coordenador",
            "coordenadora",
            "empresa",
            "instituicao",
            "versao",
        )
        marker_hits = sum(1 for marker in metadata_markers if marker in normalized)
        return marker_hits >= 3 and len(section_text.split()) <= 120

    def _create_generic_section_overview_chunk(self, metadata: dict, section: dict) -> Document | None:
        section_text = str(section.get("text") or "").strip()
        if not section_text:
            return None

        excerpt_lines = [line for line in section_text.splitlines()[:6] if line.strip()]
        body_lines = [
            f"Documento: {metadata.get('document_name')}",
            f"Secao: {section.get('title')}",
            f"Resumo da secao: {' '.join(excerpt_lines)[:800].strip()}",
        ]
        chunk_metadata = self._build_generic_chunk_metadata(
            metadata,
            section,
            chunk_kind="section_overview",
            search_parts=[metadata.get("document_name"), section.get("title"), *excerpt_lines],
        )
        return Document(page_content="\n".join(body_lines).strip(), metadata=chunk_metadata)

    def _create_generic_entity_index_chunk(self, metadata: dict, section: dict) -> Document | None:
        names = [] if section.get("is_header_metadata") else list(section.get("names") or [])
        dates = list(section.get("dates") or [])
        money_values = list(section.get("money_values") or [])
        labeled_facts = list(section.get("labeled_facts") or [])
        if not any((names, dates, money_values, labeled_facts)):
            return None

        body_lines = [
            f"Documento: {metadata.get('document_name')}",
            f"Secao: {section.get('title')}",
        ]
        if names:
            body_lines.append(f"Pessoas ou entidades: {'; '.join(names[:24])}")
        if dates:
            body_lines.append(f"Datas citadas: {'; '.join(dates[:12])}")
        if money_values:
            body_lines.append(f"Valores citados: {'; '.join(money_values[:12])}")
        for label, value in labeled_facts[:12]:
            body_lines.append(f"{label}: {value}")

        chunk_metadata = self._build_generic_chunk_metadata(
            metadata,
            section,
            chunk_kind="entity_index",
            extra_metadata={
                "entity_names": names,
                "date_values": dates,
                "money_values": money_values,
                "labeled_facts": [f"{label}: {value}" for label, value in labeled_facts],
            },
            search_parts=[
                metadata.get("document_name"),
                section.get("title"),
                *names,
                *dates,
                *money_values,
                *(f"{label} {value}" for label, value in labeled_facts),
            ],
        )
        return Document(page_content="\n".join(body_lines).strip(), metadata=chunk_metadata)

    def _create_generic_list_chunk(self, metadata: dict, section: dict) -> Document | None:
        if section.get("is_header_metadata"):
            return None
        section_text = str(section.get("text") or "").strip()
        if not section_text:
            return None

        list_like_lines = []
        for line in section_text.splitlines():
            compact = self._normalize_whitespace(line)
            if not compact:
                continue
            if compact.startswith(("-", "•", "*")) or self._count_name_like_mentions(compact) >= 3:
                list_like_lines.append(compact)
                continue
            if compact.count(",") >= 2 or compact.count(";") >= 2 or re.match(r"^\d+(?:\.\d+)*[\)\.]?\s+", compact):
                list_like_lines.append(compact)

        if len(list_like_lines) < 2 and len(section.get("names") or []) < 6:
            return None

        rendered_lines = list_like_lines[:10]
        if not rendered_lines and section.get("names"):
            rendered_lines = [name for name in list(section.get("names") or [])[:20]]

        body_lines = [
            f"Documento: {metadata.get('document_name')}",
            f"Secao: {section.get('title')}",
            "Lista ou enumeracao detectada:",
            *rendered_lines,
        ]
        chunk_metadata = self._build_generic_chunk_metadata(
            metadata,
            section,
            chunk_kind="list_block",
            search_parts=[metadata.get("document_name"), section.get("title"), *rendered_lines],
        )
        return Document(page_content="\n".join(body_lines).strip(), metadata=chunk_metadata)

    def _build_generic_section_detail_chunks(self, metadata: dict, document_name: str, section: dict) -> list[Document]:
        section_text = str(section.get("text") or "").strip()
        if not section_text:
            return []

        section_source = Document(page_content=section_text, metadata=dict(metadata))
        chunks = self.text_splitter.split_documents([section_source])
        built_chunks = []
        for index, chunk in enumerate(chunks):
            chunk_text = self._normalize_whitespace(chunk.page_content)
            if not chunk_text:
                continue
            chunk.page_content = (
                f"Documento: {document_name}\n"
                f"Secao: {section.get('title')}\n"
                f"Trecho:\n{chunk_text}"
            )
            chunk.metadata.update(
                self._build_generic_chunk_metadata(
                    metadata,
                    section,
                    chunk_kind="section_detail",
                    extra_metadata={"chunk_order": int(section.get("order") or 0) * 10 + index},
                    search_parts=[document_name, section.get("title"), chunk_text],
                )
            )
            built_chunks.append(chunk)
        return built_chunks

    def _build_generic_chunk_metadata(
        self,
        metadata: dict,
        section: dict,
        *,
        chunk_kind: str,
        extra_metadata: dict | None = None,
        search_parts: list | None = None,
    ) -> dict:
        chunk_metadata = dict(metadata)
        chunk_metadata["chunk_kind"] = chunk_kind
        chunk_metadata["chunk_order"] = int(section.get("order") or 0)
        chunk_metadata["section_title"] = str(section.get("title") or "").strip()
        chunk_metadata["section_title_normalized"] = self._normalize_identifier(chunk_metadata["section_title"])
        chunk_metadata["section_key"] = str(section.get("section_key") or "").strip()
        chunk_metadata["section_is_header_metadata"] = bool(section.get("is_header_metadata"))
        if extra_metadata:
            chunk_metadata.update(extra_metadata)
        chunk_metadata["search_text_normalized"] = self._normalize_identifier(
            " ".join(str(part or "").strip() for part in (search_parts or []) if str(part or "").strip())
        )
        return chunk_metadata

    def _build_spreadsheet_chunks(self, document: Document, header: str) -> list[Document]:
        parsed = self._parse_spreadsheet_markdown(document.page_content)
        base_metadata = dict(document.metadata)
        base_metadata["document_type"] = "spreadsheet"
        chunks = []

        if parsed["summary_lines"]:
            chunks.append(
                self._create_spreadsheet_chunk(
                    header=header,
                    title="Resumo da planilha",
                    body_lines=parsed["summary_lines"],
                    metadata={**base_metadata, "chunk_kind": "summary"},
                )
            )

        for sheet in parsed["sheets"]:
            sheet_metadata = {
                **base_metadata,
                "sheet_name": sheet["name"],
                "sheet_name_normalized": self._normalize_identifier(sheet["name"]),
            }
            if sheet["summary_lines"]:
                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Resumo da aba {sheet['name']}",
                        body_lines=sheet["summary_lines"],
                        metadata={**sheet_metadata, "chunk_kind": "sheet_summary"},
                    )
                )

            for profile in sheet["column_profiles"]:
                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Perfil de coluna da aba {sheet['name']}",
                        body_lines=[profile],
                        metadata={**sheet_metadata, "chunk_kind": "column_profile"},
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
            person_lines = [
                f"Documento: {base_metadata['document_name']}",
                f"Aba: {person.get('sheet_name') or sheet['name']}",
                f"Pessoa: {person['entity_name']}",
            ]
            if person.get("entity_role"):
                person_lines.append(f"Funcao: {person['entity_role']}")
            if person.get("row_number") is not None:
                person_lines.append(f"Linha: {person['row_number']}")

            metadata = {
                **sheet_metadata,
                "chunk_kind": "people_index",
                "entity_name": person["entity_name"],
                "entity_name_normalized": self._normalize_identifier(person["entity_name"]),
                "entity_role": person.get("entity_role"),
                "entity_role_normalized": self._normalize_identifier(person.get("entity_role") or ""),
                "row_number": person.get("row_number"),
            }
            chunks.append(
                self._create_spreadsheet_chunk(
                    header=header,
                    title=f"Entrada de pessoa da aba {person.get('sheet_name') or sheet['name']}",
                    body_lines=person_lines,
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
            body_lines = [
                f"Documento: {base_metadata['document_name']}",
                f"Aba: {row_data.get('sheet_name') or sheet['name']}",
            ]
            if row_data.get("row_number") is not None:
                body_lines.append(f"Linha: {row_data['row_number']}")
            if row_data.get("entity_name"):
                body_lines.append(f"Pessoa: {row_data['entity_name']}")
            if row_data.get("entity_role"):
                body_lines.append(f"Funcao: {row_data['entity_role']}")
            body_lines.append(f"Registro completo: {row_record}")

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
                self._create_spreadsheet_chunk(
                    header=header,
                    title=f"Registro da aba {row_data.get('sheet_name') or sheet['name']}",
                    body_lines=body_lines,
                    metadata=metadata,
                )
            )
        return chunks

    def _create_spreadsheet_chunk(
        self,
        header: str,
        title: str,
        body_lines: list[str],
        metadata: dict,
    ) -> Document:
        content_lines = [
            f"Cabecalho do documento:\n{header}",
            "",
            title,
            *body_lines,
        ]
        page_content = "\n".join(line for line in content_lines if line is not None).strip()
        metadata = dict(metadata)
        metadata["search_text_normalized"] = self._normalize_identifier(" ".join(body_lines))
        return Document(page_content=page_content, metadata=metadata)
