import os
import re
import unicodedata
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter


PERSON_QUERY_TERMS = {
    "nome",
    "nomes",
    "pessoa",
    "pessoas",
    "trabalhador",
    "trabalhadores",
    "funcionario",
    "funcionarios",
    "funcionaria",
    "funcionarias",
    "colaborador",
    "colaboradores",
    "pesquisador",
    "pesquisadores",
    "coordenador",
    "coordenadores",
    "equipe",
    "quem",
}
ROLE_HINT_TERMS = {
    "coordenador",
    "pesquisador",
    "analista",
    "desenvolvedor",
    "testador",
    "designer",
    "consultor",
    "gerente",
    "especialista",
}
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
}
SPREADSHEET_SUFFIXES = (".xlsx", ".csv")


class RAGService:
    def __init__(self, collection_name=None):
        self.project_root = Path(__file__).resolve().parents[2]
        self.collections_root = self.project_root / "data" / "collections"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.3-70b-versatile")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""],
        )

        self.vector_store = None
        self.retriever = None
        self.answer_chain = None
        self.small_talk_chain = None
        self.query_rewrite_chain = None
        self.collection_name = None
        self.document_catalog = []
        self.spreadsheet_chunk_index = {}

        if collection_name:
            self.load_collection(collection_name)

    def _normalize_whitespace(self, text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line)

    def _extract_document_header(self, text: str, max_lines: int = 8) -> str:
        return "\n".join(self._normalize_whitespace(text).split("\n")[:max_lines])

    def _extract_document_name(self, text: str, source: str | None = None) -> str:
        first_line = text.split("\n", 1)[0].strip()
        if first_line.startswith("# "):
            return first_line[2:].strip()
        if source:
            return Path(source).stem
        return "documento"

    def _extract_document_type(self, text: str) -> str:
        for line in self._normalize_whitespace(text).split("\n")[:12]:
            if line.lower().startswith("document type:"):
                return line.split(":", 1)[1].strip().lower()
        return "document"

    def _normalize_identifier(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _tokenize_search_text(self, text: str) -> list[str]:
        tokens = self._normalize_identifier(text).split()
        return [token for token in tokens if token not in QUERY_STOPWORDS and len(token) > 1]

    def _format_docs(self, docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    def _format_chat_history(self, chat_history) -> str:
        if not chat_history:
            return "Sem conversa anterior."

        formatted_messages = []
        for message in chat_history[-6:]:
            role = "Usuario" if message.get("role") == "user" else "Assistente"
            formatted_messages.append(f"{role}: {message.get('content', '')}")
        return "\n".join(formatted_messages)

    def _is_casual_message(self, question: str) -> bool:
        normalized = re.sub(r"\s+", " ", question.strip().lower())
        if not normalized:
            return True

        if re.fullmatch(r"[\?\!\.\-_,\s]{1,6}", normalized):
            return True

        question_words = ("quem", "qual", "quais", "como", "onde", "quando", "what", "who", "which", "how", "where", "when")
        if any(word in normalized for word in question_words) or "?" in normalized:
            return False

        casual_patterns = (
            r"^(oi|ola|olá|opa|e ai|e aí|hey|hi|hello|salve|bom dia|boa tarde|boa noite)\b",
            r"^(valeu|obrigado|obrigada|thanks|thank you|tmj|tamo junto)\b",
        )
        return any(re.match(pattern, normalized) for pattern in casual_patterns)

    def _should_rewrite_question(self, question: str, chat_history) -> bool:
        if not chat_history:
            return False

        normalized = self._normalize_identifier(question)
        if not normalized:
            return False

        follow_up_markers = (
            "ele",
            "ela",
            "eles",
            "elas",
            "esse",
            "essa",
            "esses",
            "essas",
            "isso",
            "isto",
            "dele",
            "dela",
            "deles",
            "delas",
            "sobre ele",
            "sobre ela",
            "quais sao",
            "qual deles",
            "qual delas",
            "e quais",
            "mas quais",
        )
        if any(marker in normalized for marker in follow_up_markers):
            return True

        return len(normalized.split()) <= 6

    def _rewrite_question_for_retrieval(self, question: str, history_text: str, chat_history) -> str:
        if not self.query_rewrite_chain or history_text == "Sem conversa anterior.":
            return question
        if not self._should_rewrite_question(question, chat_history):
            return question

        rewritten = self.query_rewrite_chain.invoke(
            {
                "chat_history": history_text,
                "question": question,
            }
        ).strip()
        rewritten = re.sub(r"^(consulta|pergunta reescrita|query)\s*:\s*", "", rewritten, flags=re.IGNORECASE).strip()
        return rewritten or question

    def _match_document_name(self, question: str) -> str | None:
        normalized_question = self._normalize_identifier(question)
        if not normalized_question:
            return None

        best_match = None
        best_score = -1
        for document in self.document_catalog:
            full_name = document["normalized_name"]
            stem_name = document["normalized_stem"]

            if full_name and full_name in normalized_question:
                score = len(full_name)
            elif stem_name and len(stem_name) >= 4 and stem_name in normalized_question:
                score = len(stem_name)
            else:
                continue

            if score > best_score:
                best_match = document["name"]
                best_score = score

        return best_match

    def _get_document_entry(self, document_name: str | None) -> dict | None:
        if not document_name:
            return None
        for document in self.document_catalog:
            if document["name"] == document_name:
                return document
        return None

    def _is_spreadsheet_document_name(self, document_name: str | None) -> bool:
        entry = self._get_document_entry(document_name)
        if entry and entry.get("document_type") == "spreadsheet":
            return True
        return bool(document_name and document_name.lower().endswith(SPREADSHEET_SUFFIXES))

    def _is_people_question(self, question: str, target_document_name: str | None = None) -> bool:
        normalized = self._normalize_identifier(question)
        query_terms = set(self._tokenize_search_text(normalized))
        has_people_term = bool(query_terms & PERSON_QUERY_TERMS)
        points_to_spreadsheet = self._is_spreadsheet_document_name(target_document_name) or any(
            marker in normalized for marker in ("planilha", ".xlsx", ".csv", "aba", "sheet")
        )
        return has_people_term and points_to_spreadsheet

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

    def _retrieve_docs(self, question: str, target_document_name: str | None = None):
        if self._is_spreadsheet_document_name(target_document_name):
            structured_docs = self._retrieve_spreadsheet_chunks(question, target_document_name)
            if structured_docs:
                return structured_docs

        if target_document_name:
            focused_question = f"{target_document_name} {question}".strip()
            docs = self.vector_store.max_marginal_relevance_search(
                focused_question,
                k=6,
                fetch_k=100,
                lambda_mult=0.2,
                filter={"document_name": target_document_name},
            )
            if docs:
                return docs

            docs = self.vector_store.similarity_search(
                target_document_name,
                k=6,
                fetch_k=100,
                filter={"document_name": target_document_name},
            )
            if docs:
                return docs

        return self.retriever.invoke(question)

    def _retrieve_spreadsheet_chunks(self, question: str, target_document_name: str) -> list[Document]:
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

    def _score_spreadsheet_chunk(
        self,
        chunk: Document,
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

    def _build_generic_chunks(self, document: Document, header: str) -> list[Document]:
        chunks = self.text_splitter.split_documents([document])
        built_chunks = []
        for chunk in chunks:
            chunk.page_content = f"Cabecalho do documento:\n{header}\n\nTrecho:\n{chunk.page_content}"
            chunk.metadata["chunk_kind"] = "text"
            chunk.metadata["search_text_normalized"] = self._normalize_identifier(chunk.page_content)
            built_chunks.append(chunk)
        return built_chunks

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
                            }
                        )

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

    def _parse_spreadsheet_markdown(self, text: str) -> dict:
        lines = [line.strip() for line in self._normalize_whitespace(text).split("\n") if line.strip()]
        summary_lines = []
        sheets = []
        current_sheet = None
        section = "summary"

        for line in lines[1:]:
            if line.startswith("## Sheet: "):
                if current_sheet is not None:
                    sheets.append(current_sheet)
                current_sheet = {
                    "name": line.split(":", 1)[1].strip(),
                    "summary_lines": [],
                    "column_profiles": [],
                    "people_index": [],
                    "row_records": [],
                }
                section = "sheet_summary"
                continue

            if current_sheet is None:
                summary_lines.append(line)
                continue

            if line == "Column profiles:":
                section = "column_profiles"
                continue
            if line == "People index:":
                section = "people_index"
                continue
            if line == "Row records:":
                section = "row_records"
                continue
            if line == "No non-empty data rows were indexed.":
                current_sheet["summary_lines"].append(line)
                continue

            if section == "column_profiles" and line.startswith("- "):
                current_sheet["column_profiles"].append(line[2:].strip())
                continue
            if section == "people_index" and line.startswith("- "):
                current_sheet["people_index"].append(line[2:].strip())
                continue
            if section == "row_records" and line.startswith("- "):
                current_sheet["row_records"].append(line[2:].strip())
                continue

            current_sheet["summary_lines"].append(line)

        if current_sheet is not None:
            sheets.append(current_sheet)

        return {"summary_lines": summary_lines, "sheets": sheets}

    def _parse_people_index_line(self, line: str, default_sheet_name: str) -> dict | None:
        parts = [part.strip() for part in line.split(" | ") if part.strip()]
        if not parts:
            return None

        entity_name = None
        entity_role = None
        sheet_name = default_sheet_name
        row_number = None

        for part in parts:
            if part.startswith("Person:"):
                entity_name = part.split(":", 1)[1].strip()
            elif part.startswith("Role:"):
                entity_role = part.split(":", 1)[1].strip()
            elif part.startswith("Sheet:"):
                sheet_name = part.split(":", 1)[1].strip()
            elif part.startswith("Row:"):
                row_value = part.split(":", 1)[1].strip()
                if row_value.isdigit():
                    row_number = int(row_value)

        if not entity_name:
            return None

        return {
            "entity_name": entity_name,
            "entity_role": entity_role,
            "sheet_name": sheet_name,
            "row_number": row_number,
        }

    def _parse_row_record_line(self, line: str, default_sheet_name: str) -> dict:
        parts = [part.strip() for part in line.split(" | ") if part.strip()]
        row_number = None
        sheet_name = default_sheet_name
        pairs = []

        for index, part in enumerate(parts):
            if index == 0 and part.startswith("Spreadsheet file "):
                continue
            if part.startswith("Sheet "):
                sheet_name = part[6:].strip()
                continue
            if part.startswith("Row "):
                row_prefix, _, first_pair = part.partition(":")
                row_id = row_prefix[4:].strip()
                if row_id.isdigit():
                    row_number = int(row_id)
                if first_pair.strip():
                    parsed_pair = self._parse_header_value_pair(first_pair.strip())
                    if parsed_pair:
                        pairs.append(parsed_pair)
                continue

            parsed_pair = self._parse_header_value_pair(part)
            if parsed_pair:
                pairs.append(parsed_pair)

        entity_name = None
        entity_role = None
        if pairs:
            first_header, first_value = pairs[0]
            if self._looks_like_person_name(first_value):
                entity_name = first_value
                entity_role = self._extract_role_from_pairs(pairs[1:])

        return {
            "sheet_name": sheet_name,
            "row_number": row_number,
            "pairs": pairs,
            "entity_name": entity_name,
            "entity_role": entity_role,
        }

    def _parse_header_value_pair(self, text: str) -> tuple[str, str] | None:
        header, separator, value = text.partition("=")
        if not separator:
            return None
        header = header.strip()
        value = value.strip()
        if not header or not value:
            return None
        return header, value

    def _looks_like_person_name(self, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if len(text) < 5 or any(char.isdigit() for char in text):
            return False
        if not any(char.islower() for char in text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        blocked_exact = {
            "nome",
            "tbd",
            "total",
            "totais",
            "subtotal",
            "sub total",
            "target",
            "rpa",
            "profissionais",
            "bolsas",
            "custo total de rh mensal",
            "encargos clt",
            "descricao",
            "descricoes",
            "rh direto bolsas",
            "rh direto celetistas",
            "rh indireto administrativo",
        }
        blocked_prefixes = ("rh ", "sub total", "subtotal", "total ", "totais ", "custo ", "historico ", "margem ")
        if normalized in blocked_exact or any(normalized.startswith(prefix) for prefix in blocked_prefixes):
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        return len(tokens) >= 2

    def _extract_role_from_pairs(self, pairs: list[tuple[str, str]]) -> str | None:
        for header, value in pairs:
            if self._looks_like_role(header, value):
                return value
        return None

    def _looks_like_role(self, header: str, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return False
        if self._to_number(text) is not None:
            return False
        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        if normalized in {"ufc", "s vinculo", "total", "totais", "custo dell"}:
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        if not tokens or len(tokens) > 12:
            return False

        normalized_header = self._normalize_identifier(header)
        if normalized_header.startswith("column_") and len(tokens) <= 1:
            return False

        return True

    def _to_number(self, value: str) -> float | None:
        if not value:
            return None

        cleaned = value.strip().replace("R$", "").replace("%", "").replace("\u00a0", " ")
        cleaned = cleaned.replace(" ", "")
        if not cleaned:
            return None

        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def load_collection(self, collection_name):
        collection_path = self.collections_root / collection_name
        if not collection_path.exists():
            raise Exception(f"Collection '{collection_name}' not found.")

        loader = DirectoryLoader(
            str(collection_path),
            glob="**/*.md",
            show_progress=True,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()
        if not documents:
            raise Exception(f"No documents found in collection '{collection_name}'.")

        chunks = []
        document_catalog = {}
        spreadsheet_chunk_index = {}

        for document in documents:
            document.page_content = self._normalize_whitespace(document.page_content)
            source = document.metadata.get("source")
            document_name = self._extract_document_name(document.page_content, source)
            document_type = self._extract_document_type(document.page_content)
            document.metadata["document_name"] = document_name
            document.metadata["document_name_normalized"] = self._normalize_identifier(document_name)
            document.metadata["document_stem_normalized"] = self._normalize_identifier(Path(document_name).stem)
            document.metadata["document_type"] = document_type

            document_catalog[document_name] = {
                "name": document_name,
                "normalized_name": document.metadata["document_name_normalized"],
                "normalized_stem": document.metadata["document_stem_normalized"],
                "document_type": document_type,
            }

            header = self._extract_document_header(document.page_content)
            if document_type == "spreadsheet":
                document_chunks = self._build_spreadsheet_chunks(document, header)
                spreadsheet_chunk_index[document_name] = document_chunks
            else:
                document_chunks = self._build_generic_chunks(document, header)

            chunks.extend(document_chunks)

        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.collection_name = collection_name
        self.document_catalog = list(document_catalog.values())
        self.spreadsheet_chunk_index = spreadsheet_chunk_index

        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": 30, "lambda_mult": 0.2},
        )

        answer_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um assistente prestativo em uma aplicacao de chat com documentos. "
                "Sua base atual e a colecao selecionada pelo usuario. "
                "Responda em portugues, de forma natural, sem soar robotico. "
                "Nao mencione identificadores tecnicos, nomes internos de colecao, slugs ou IDs ao responder. "
                "Quando fizer referencia a base carregada, prefira expressoes naturais como 'os arquivos carregados', "
                "'os documentos enviados' ou o assunto identificado no contexto. "
                "Use o historico da conversa para entender mensagens curtas de continuacao. "
                "Se a pergunta citar um arquivo especifico, concentre a resposta nesse arquivo e nao generalize para a colecao toda. "
                "Para perguntas sobre documentos, use apenas o contexto recuperado. "
                "Quando o contexto tiver entradas de pessoas ou registros de linha com nomes, liste os nomes diretamente. "
                "Nao diga que nao ha nomes explicitos se o contexto contiver campos como 'Pessoa:' ou linhas com nomes proprios. "
                "Em perguntas sobre trabalhadores, pessoas, equipe ou coordenadores, priorize nomes e funcoes antes de resumos genericos da planilha. "
                "Quando o usuario pedir nomes, liste os nomes exatos encontrados no contexto e nao os substitua por cargos ou resumos. "
                "Se o contexto for insuficiente, diga isso de forma natural e breve.",
            ),
            (
                "human",
                "Base carregada:\n{collection_name}\n\n"
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta contextualizada para busca:\n{resolved_question}\n\n"
                "Arquivo-alvo identificado:\n{target_document_name}\n\n"
                "Contexto:\n{context}\n\n"
                "Pergunta original do usuario:\n{question}\n"
                "Resposta:"
            ),
        ])
        small_talk_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um assistente amigavel em uma aplicacao de chat com documentos. "
                "Sua base atual e a colecao selecionada pelo usuario. "
                "Responda em portugues, de forma breve e natural. "
                "Nao mencione identificadores tecnicos, nomes internos de colecao, slugs ou IDs ao responder. "
                "Quando fizer referencia a base carregada, prefira expressoes naturais como 'os arquivos carregados' ou 'os documentos enviados'. "
                "Fale com seguranca sobre a colecao carregada quando o assunto estiver claro. "
                "Evite expressoes hesitantes como 'parece ser' quando voce ja tiver contexto suficiente. "
                "Use o historico da conversa para entender respostas curtas como '??'. "
                "Se fizer sentido, mencione que voce pode responder perguntas sobre os documentos selecionados, mas sem forcar isso em toda resposta.",
            ),
            (
                "human",
                "Base carregada:\n{collection_name}\n\n"
                "Historico da conversa:\n{chat_history}\n\n"
                "Mensagem do usuario:\n{question}\n"
                "Resposta:"
            ),
        ])
        rewrite_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Reescreva a pergunta do usuario como uma consulta independente para recuperacao de documentos. "
                "Use o historico apenas para resolver referencias implicitas. "
                "Preserve nomes de arquivos, abas, pessoas, valores e termos importantes. "
                "Se a pergunta ja estiver clara sozinha, devolva a propria pergunta. "
                "Responda somente com a consulta reescrita.",
            ),
            (
                "human",
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta atual:\n{question}\n\n"
                "Consulta reescrita:"
            ),
        ])

        self.answer_chain = answer_prompt | self.llm | StrOutputParser()
        self.small_talk_chain = small_talk_prompt | self.llm | StrOutputParser()
        self.query_rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()

    def ask_question(self, question: str, chat_history=None) -> str:
        if not self.retriever or not self.answer_chain or not self.small_talk_chain:
            raise Exception("No collection loaded. Please load a collection before asking questions.")

        history_text = self._format_chat_history(chat_history)
        collection_name = self.collection_name or "colecao nao identificada"

        if self._is_casual_message(question):
            return self.small_talk_chain.invoke(
                {"collection_name": collection_name, "chat_history": history_text, "question": question}
            )

        resolved_question = self._rewrite_question_for_retrieval(question, history_text, chat_history)
        target_document_name = self._match_document_name(resolved_question) or self._match_document_name(question)
        docs = self._retrieve_docs(resolved_question, target_document_name)
        context = self._format_docs(docs)
        return self.answer_chain.invoke(
            {
                "collection_name": collection_name,
                "chat_history": history_text,
                "resolved_question": resolved_question,
                "target_document_name": target_document_name or "nenhum arquivo especifico",
                "context": context,
                "question": question,
            }
        )
