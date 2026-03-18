import os
import re
from collections import Counter
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from application.service.spreadsheet_markdown import (
        PERSON_QUERY_TERMS,
        ROLE_HINT_TERMS,
        build_person_entry,
        extract_role_from_pairs,
        is_human_resources_sheet,
        normalize_identifier,
        to_number,
    )
except ImportError:
    from spreadsheet_markdown import (
        PERSON_QUERY_TERMS,
        ROLE_HINT_TERMS,
        build_person_entry,
        extract_role_from_pairs,
        is_human_resources_sheet,
        normalize_identifier,
        to_number,
    )
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
PDF_SUFFIXES = (".pdf",)
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff")
PRESENTATION_SUFFIXES = (".ppt", ".pptx")
TEXT_DOCUMENT_SUFFIXES = (".doc", ".docx", ".html", ".md", ".txt")
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


class RAGService:
    def __init__(self, collection_name=None):
        self.project_root = Path(__file__).resolve().parents[2]
        self.collections_root = self.project_root / "data" / "collections"
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-120b",
            temperature=0.2,
            reasoning_effort="medium",
            model_kwargs={"include_reasoning": False},
        )
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

    def _infer_document_type_from_name(self, document_name: str | None) -> str | None:
        suffix = Path(document_name or "").suffix.lower()
        if suffix in SPREADSHEET_SUFFIXES:
            return "spreadsheet"
        if suffix in PDF_SUFFIXES:
            return "pdf"
        if suffix in IMAGE_SUFFIXES:
            return "image"
        if suffix in PRESENTATION_SUFFIXES:
            return "presentation"
        if suffix in TEXT_DOCUMENT_SUFFIXES:
            return "text_document"
        return None

    def _is_markdown_table_row(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|")

    def _is_markdown_table_separator(self, line: str) -> bool:
        if not self._is_markdown_table_row(line):
            return False

        cells = [cell.strip().replace(" ", "") for cell in line.strip().strip("|").split("|")]
        return bool(cells) and all(cell and re.fullmatch(r":?-{3,}:?", cell) for cell in cells)

    def _looks_like_markdown_table(self, text: str) -> bool:
        lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]
        return any(
            self._is_markdown_table_row(lines[index]) and self._is_markdown_table_separator(lines[index + 1])
            for index in range(len(lines) - 1)
        )

    def _extract_document_type(
        self,
        text: str,
        source: str | None = None,
        document_name: str | None = None,
    ) -> str:
        for line in self._normalize_whitespace(text).split("\n")[:12]:
            if line.lower().startswith("document type:"):
                return line.split(":", 1)[1].strip().lower()

        inferred_name = document_name or self._extract_document_name(text, source)
        inferred_type = self._infer_document_type_from_name(inferred_name)
        if inferred_type:
            return inferred_type

        return "document"

    def _extract_document_summary(self, text: str, max_lines: int = 3) -> str:
        summary_lines = []
        for line in self._normalize_whitespace(text).split("\n"):
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or stripped.startswith("# "):
                continue
            if lowered.startswith("extraction method:"):
                continue
            if lowered.startswith("document type:"):
                continue
            if lowered.startswith("spreadsheet format:"):
                continue
            if lowered.startswith("spreadsheet file:"):
                continue
            if lowered.startswith("total sheets:"):
                continue
            if lowered.startswith("sheet names:"):
                continue
            if self._is_markdown_table_row(stripped) or self._is_markdown_table_separator(stripped):
                continue

            summary_lines.append(stripped)
            if len(summary_lines) >= max_lines:
                break

        if not summary_lines and self._looks_like_markdown_table(text):
            return "Arquivo com tabelas em markdown extraidas do documento original."
        return " ".join(summary_lines)[:400]

    def _document_type_label(self, document_type: str, count: int = 1) -> str:
        plural = count != 1
        labels = {
            "spreadsheet": ("planilha", "planilhas"),
            "pdf": ("PDF", "PDFs"),
            "image": ("imagem", "imagens"),
            "presentation": ("apresentacao", "apresentacoes"),
            "text_document": ("documento de texto", "documentos de texto"),
            "document": ("arquivo", "arquivos"),
        }
        singular_label, plural_label = labels.get(document_type, ("arquivo", "arquivos"))
        return plural_label if plural else singular_label

    def _apply_catalog_display_names(self, document_catalog: list[dict]) -> None:
        counts = Counter(entry["name"] for entry in document_catalog)
        seen = Counter()

        for entry in document_catalog:
            seen[entry["name"]] += 1
            if counts[entry["name"]] == 1:
                entry["display_name"] = entry["name"]
            else:
                entry["display_name"] = f"{entry['name']} [{seen[entry['name']]}]"

    def _build_collection_overview_chunks(self, document_catalog: list[dict]) -> list[Document]:
        if not document_catalog:
            return []

        type_counts = Counter(entry["document_type"] for entry in document_catalog)
        type_summary = ", ".join(
            f"{count} {self._document_type_label(document_type, count)}"
            for document_type, count in sorted(type_counts.items())
        )
        chunks = []

        for start in range(0, len(document_catalog), MAX_CATALOG_LISTING):
            subset = document_catalog[start : start + MAX_CATALOG_LISTING]
            lines = [
                "Resumo da colecao carregada",
                f"Total de arquivos: {len(document_catalog)}",
            ]
            if type_summary:
                lines.append(f"Tipos detectados: {type_summary}")
            lines.append("Arquivos listados neste resumo:")

            for entry in subset:
                line = f"- {entry['display_name']} ({self._document_type_label(entry['document_type'])})"
                if entry.get("summary"):
                    line += f": {entry['summary']}"
                lines.append(line)

            page_content = "\n".join(lines)
            chunks.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "chunk_kind": "collection_overview",
                        "document_name": "__collection_overview__",
                        "document_type": "collection",
                        "search_text_normalized": self._normalize_identifier(page_content),
                    },
                )
            )

        return chunks

    def _normalize_identifier(self, text: str) -> str:
        return normalize_identifier(text)

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

    def _is_document_catalog_question(self, question: str, target_document_name: str | None = None) -> bool:
        normalized = self._normalize_identifier(question)
        if not normalized:
            return False
        if target_document_name:
            return False
        if any(
            phrase in normalized
            for phrase in ("o que foi carregado", "o que foi enviado", "what was loaded", "what is loaded")
        ):
            return True

        tokens = normalized.split()
        if not tokens or not set(tokens) & CATALOG_INTENT_TERMS:
            return False

        remaining_tokens = [
            token
            for token in tokens
            if token not in QUERY_STOPWORDS and token not in CATALOG_INTENT_TERMS
        ]
        return not remaining_tokens

    def _is_count_only_catalog_question(self, question: str) -> bool:
        tokens = set(self._normalize_identifier(question).split())
        has_count = bool(tokens & CATALOG_COUNT_TERMS)
        has_list = bool(tokens & CATALOG_LIST_TERMS)
        return has_count and not has_list

    def _extract_catalog_document_type(self, question: str) -> str | None:
        tokens = set(self._normalize_identifier(question).split())
        matching_types = [
            document_type
            for document_type, type_terms in CATALOG_TYPE_TERMS.items()
            if tokens & type_terms
        ]
        if len(matching_types) == 1:
            return matching_types[0]
        return None

    def _answer_document_catalog_question(self, question: str) -> str:
        if not self.document_catalog:
            return "Nao encontrei arquivos carregados nesta colecao."

        requested_type = self._extract_catalog_document_type(question)
        selected_entries = [
            entry
            for entry in self.document_catalog
            if requested_type is None or entry.get("document_type") == requested_type
        ]
        if not selected_entries:
            return f"Nao encontrei {self._document_type_label(requested_type or 'document', 2)} carregados nesta colecao."

        count = len(selected_entries)
        if self._is_count_only_catalog_question(question):
            return f"Ha {count} {self._document_type_label(requested_type or 'document', count)} carregados nesta colecao."

        lines = [f"Encontrei {count} {self._document_type_label(requested_type or 'document', count)} carregados:"]
        for entry in selected_entries[:MAX_CATALOG_LISTING]:
            if requested_type:
                lines.append(f"- {entry['display_name']}")
            else:
                lines.append(f"- {entry['display_name']} ({self._document_type_label(entry['document_type'])})")

        remaining = count - min(count, MAX_CATALOG_LISTING)
        if remaining > 0:
            lines.append(f"- ... e mais {remaining} {self._document_type_label('document', remaining)}.")
        return "\n".join(lines)

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
                if chunk.metadata.get("chunk_kind") in {"people_summary", "people_index", "row_record"}
                and (
                    chunk.metadata.get("chunk_kind") == "people_summary"
                    or chunk.metadata.get("entity_name")
                )
            ]
            if target_sheet:
                sheet_chunks = [
                    chunk
                    for chunk in entity_chunks
                    if chunk.metadata.get("sheet_name_normalized") == target_sheet
                ]
                if sheet_chunks:
                    entity_chunks = sheet_chunks
            elif any(
                is_human_resources_sheet(chunk.metadata.get("sheet_name") or "")
                and chunk.metadata.get("chunk_kind") in {"people_summary", "people_index", "row_record"}
                for chunk in entity_chunks
            ):
                entity_chunks = [
                    chunk
                    for chunk in entity_chunks
                    if is_human_resources_sheet(chunk.metadata.get("sheet_name") or "")
                ]
            if entity_chunks:
                candidate_chunks = entity_chunks

        scored_chunks = []
        for chunk in candidate_chunks:
            score = self._score_spreadsheet_chunk(
                chunk,
                query_terms,
                people_query,
                target_sheet,
            )
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
        max_selected = 6
        if people_query:
            people_count = max(
                [
                    chunk.metadata.get("people_count") or 0
                    for chunk in candidate_chunks
                    if chunk.metadata.get("chunk_kind") == "people_summary"
                ]
                or [0]
            )
            max_selected = 1 + min(20, people_count or 20)

        for _, chunk_kind, stable_row, chunk in scored_chunks:
            if people_query and chunk.metadata.get("entity_name"):
                unique_key = (
                    "person",
                    chunk.metadata.get("sheet_name"),
                    chunk.metadata.get("entity_name_normalized") or chunk.metadata.get("entity_name"),
                )
            else:
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
            if len(selected) >= max_selected:
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

        if people_query:
            if chunk_kind == "people_summary":
                score += 170
            elif chunk_kind == "people_index":
                score += 130
            elif chunk_kind == "row_record" and entity_name:
                score += 100
            else:
                score -= 20

            if is_human_resources_sheet(metadata.get("sheet_name") or ""):
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
        if self._looks_like_markdown_table(document.page_content) and "## Sheet:" not in document.page_content:
            markdown_table_chunks = self._build_markdown_table_chunks(document, header)
            if markdown_table_chunks:
                return markdown_table_chunks

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

            people_entries.sort(key=lambda item: (item.get("row_number") or 10_000, item.get("entity_name") or ""))

            if people_entries:
                role_counts = {}
                for person in people_entries:
                    role = person.get("entity_role")
                    if role:
                        role_counts[role] = role_counts.get(role, 0) + 1

                role_summary = ", ".join(
                    f"{role} ({count})"
                    for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
                )
                summary_lines = [
                    f"Documento: {base_metadata['document_name']}",
                    f"Aba: {sheet['name']}",
                    f"Total de pessoas detectadas: {len(people_entries)}",
                    "Nomes detectados: " + ", ".join(person["entity_name"] for person in people_entries),
                ]
                if role_summary:
                    summary_lines.append(f"Funcoes em destaque: {role_summary}")

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Resumo de pessoas da aba {sheet['name']}",
                        body_lines=summary_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "people_summary",
                            "people_count": len(people_entries),
                            "entity_names": [person["entity_name"] for person in people_entries],
                            "entity_names_normalized": [
                                self._normalize_identifier(person["entity_name"]) for person in people_entries
                            ],
                        },
                    )
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

    def _extract_markdown_table_blocks(self, text: str) -> list[dict]:
        lines = text.replace("\r\n", "\n").split("\n")
        blocks = []
        current_block = None
        previous_non_table_line = None

        for line_number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if self._is_markdown_table_row(stripped):
                if current_block is None:
                    current_block = {"label": previous_non_table_line, "lines": []}
                current_block["lines"].append((line_number, stripped))
                continue

            if current_block is not None:
                blocks.append(current_block)
                current_block = None

            if stripped and not stripped.startswith("# ") and not stripped.lower().startswith("extraction method:"):
                previous_non_table_line = stripped

        if current_block is not None:
            blocks.append(current_block)

        return blocks

    def _split_markdown_table_row(self, line: str) -> list[str]:
        stripped = line.strip()
        if stripped.startswith("|"):
            stripped = stripped[1:]
        if stripped.endswith("|"):
            stripped = stripped[:-1]
        return [cell.strip() for cell in stripped.split("|")]

    def _is_blank_table_row(self, cells: list[str]) -> bool:
        return not any(cell.strip() for cell in cells)

    def _looks_like_table_banner_row(self, cells: list[str]) -> bool:
        non_empty = [self._normalize_identifier(cell) for cell in cells if self._normalize_identifier(cell)]
        if len(non_empty) < 2:
            return False

        most_common_count = Counter(non_empty).most_common(1)[0][1]
        return most_common_count >= max(2, len(non_empty) - 1)

    def _looks_like_table_header_row(self, cells: list[str]) -> bool:
        non_empty = [cell.strip() for cell in cells if cell.strip()]
        if len(non_empty) < 2:
            return False

        numeric_like = 0
        short_text = 0
        header_markers = {
            "nome",
            "name",
            "cargo",
            "funcao",
            "cpf",
            "cnpj",
            "inicio",
            "fim",
            "fornecedor",
            "justificativa",
            "total",
            "mes",
            "column",
        }

        matched_markers = 0
        for cell in non_empty:
            normalized = self._normalize_identifier(cell)
            if not normalized:
                continue
            if self._to_number(cell) is not None or re.search(r"\d{4}-\d{2}-\d{2}", cell):
                numeric_like += 1
            if len(normalized.split()) <= 4:
                short_text += 1
            if any(marker in normalized for marker in header_markers):
                matched_markers += 1

        if matched_markers >= 1 and numeric_like == 0:
            return True
        return numeric_like == 0 and short_text >= max(2, len(non_empty) - 1)

    def _guess_markdown_table_name(
        self,
        header_cells: list[str],
        fallback_label: str | None,
        table_index: int,
    ) -> str:
        non_empty = [cell.strip() for cell in header_cells if cell.strip()]
        if non_empty:
            normalized_counts = Counter(self._normalize_identifier(cell) for cell in non_empty if self._normalize_identifier(cell))
            if normalized_counts:
                most_common_value, _ = normalized_counts.most_common(1)[0]
                for cell in non_empty:
                    if self._normalize_identifier(cell) == most_common_value:
                        return cell
                return non_empty[0]
        if fallback_label:
            return fallback_label
        return f"Tabela {table_index}"

    def _normalize_markdown_table_headers(self, headers: list[str], column_count: int) -> list[str]:
        normalized_headers = []
        seen = Counter()

        for index in range(column_count):
            base = headers[index].strip() if index < len(headers) else ""
            label = base or f"Column_{index + 1}"
            seen[label] += 1
            if seen[label] > 1:
                label = f"{label}_{seen[label]}"
            normalized_headers.append(label)

        return normalized_headers

    def _parse_markdown_table_block(self, block: dict, table_index: int) -> dict | None:
        table_lines = block.get("lines") or []
        if len(table_lines) < 2:
            return None

        split_rows = [
            {"line_number": line_number, "cells": self._split_markdown_table_row(line)}
            for line_number, line in table_lines
        ]
        separator_index = next(
            (
                index
                for index, (_, line) in enumerate(table_lines)
                if self._is_markdown_table_separator(line)
            ),
            None,
        )
        if separator_index is None or separator_index == 0:
            return None

        header_cells = split_rows[separator_index - 1]["cells"]
        body_rows = split_rows[separator_index + 1 :]
        table_name = self._guess_markdown_table_name(header_cells, block.get("label"), table_index)

        if self._is_blank_table_row(header_cells) and body_rows and self._looks_like_table_banner_row(body_rows[0]["cells"]):
            table_name = self._guess_markdown_table_name(body_rows[0]["cells"], block.get("label"), table_index)
            body_rows = body_rows[1:]
            header_cells = []
        elif self._looks_like_table_banner_row(header_cells):
            header_cells = []

        original_header_signature = []
        if body_rows and self._looks_like_table_header_row(body_rows[0]["cells"]):
            header_cells = body_rows[0]["cells"]
            original_header_signature = [
                self._normalize_identifier(cell) for cell in header_cells if self._normalize_identifier(cell)
            ]
            body_rows = body_rows[1:]

        column_count = max([len(header_cells)] + [len(row["cells"]) for row in body_rows] or [0])
        if column_count == 0:
            return None

        headers = self._normalize_markdown_table_headers(header_cells, column_count)
        structured_rows = []
        people_entries = []
        seen_people = set()

        for row_index, row in enumerate(body_rows, start=1):
            cells = row["cells"][:column_count]
            if len(cells) < column_count:
                cells = cells + [""] * (column_count - len(cells))
            if self._is_blank_table_row(cells):
                continue

            row_signature = [self._normalize_identifier(cell) for cell in cells if self._normalize_identifier(cell)]
            if original_header_signature and row_signature == original_header_signature:
                continue

            pairs = [(column, value.strip()) for column, value in zip(headers, cells) if value.strip()]
            if not pairs:
                continue

            entity_name = None
            entity_role = None
            first_header, first_value = pairs[0]
            if len(pairs) > 1:
                entity_role = extract_role_from_pairs(pairs[1:])
            person_entry = build_person_entry(table_name, row_index, first_header, first_value, entity_role)
            if person_entry:
                entity_name = person_entry["name"]
                entity_role = person_entry.get("role")
                unique_key = (entity_name, entity_role, row_index)
                if unique_key not in seen_people:
                    seen_people.add(unique_key)
                    people_entries.append(
                        {
                            "entity_name": entity_name,
                            "entity_role": entity_role,
                            "sheet_name": table_name,
                            "row_number": row_index,
                        }
                    )

            structured_rows.append(
                {
                    "row_number": row_index,
                    "pairs": pairs,
                    "entity_name": entity_name,
                    "entity_role": entity_role,
                }
            )

        if not structured_rows:
            return None

        return {
            "name": table_name,
            "headers": headers,
            "rows": structured_rows,
            "people_entries": people_entries,
        }

    def _build_markdown_table_chunks(self, document: Document, header: str) -> list[Document]:
        table_blocks = self._extract_markdown_table_blocks(document.page_content)
        base_metadata = dict(document.metadata)
        base_metadata["document_type"] = "spreadsheet"

        chunks = []
        table_summaries = []
        total_rows = 0

        for table_index, block in enumerate(table_blocks, start=1):
            parsed_table = self._parse_markdown_table_block(block, table_index)
            if not parsed_table:
                continue

            table_name = parsed_table["name"]
            table_headers = parsed_table["headers"]
            rows = parsed_table["rows"]
            people_entries = parsed_table["people_entries"]
            total_rows += len(rows)
            table_summaries.append(
                f"{table_name} ({len(rows)} linhas, {len(table_headers)} colunas, {len(people_entries)} pessoas)"
            )

            sheet_metadata = {
                **base_metadata,
                "sheet_name": table_name,
                "sheet_name_normalized": self._normalize_identifier(table_name),
            }
            summary_lines = [
                f"Documento: {base_metadata['document_name']}",
                f"Tabela detectada: {table_name}",
                f"Linhas indexadas: {len(rows)}",
                f"Colunas: {', '.join(table_headers[:12])}",
            ]
            if len(table_headers) > 12:
                summary_lines.append(f"Colunas adicionais omitidas no resumo: {len(table_headers) - 12}")
            if people_entries:
                summary_lines.append(f"Pessoas detectadas: {len(people_entries)}")

            chunks.append(
                self._create_spreadsheet_chunk(
                    header=header,
                    title=f"Resumo da aba {table_name}",
                    body_lines=summary_lines,
                    metadata={**sheet_metadata, "chunk_kind": "sheet_summary"},
                )
            )

            if people_entries:
                people_entries.sort(key=lambda item: (item.get("row_number") or 10_000, item.get("entity_name") or ""))
                role_counts = Counter(person.get("entity_role") for person in people_entries if person.get("entity_role"))
                people_summary_lines = [
                    f"Documento: {base_metadata['document_name']}",
                    f"Aba: {table_name}",
                    f"Total de pessoas detectadas: {len(people_entries)}",
                    "Nomes detectados: " + ", ".join(person["entity_name"] for person in people_entries),
                ]
                if role_counts:
                    top_roles = ", ".join(
                        f"{role} ({count})"
                        for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
                    )
                    people_summary_lines.append(f"Funcoes em destaque: {top_roles}")

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Resumo de pessoas da aba {table_name}",
                        body_lines=people_summary_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "people_summary",
                            "people_count": len(people_entries),
                            "entity_names": [person["entity_name"] for person in people_entries],
                            "entity_names_normalized": [
                                self._normalize_identifier(person["entity_name"]) for person in people_entries
                            ],
                        },
                    )
                )

                for person in people_entries:
                    person_lines = [
                        f"Documento: {base_metadata['document_name']}",
                        f"Aba: {person.get('sheet_name') or table_name}",
                        f"Pessoa: {person['entity_name']}",
                    ]
                    if person.get("entity_role"):
                        person_lines.append(f"Funcao: {person['entity_role']}")
                    if person.get("row_number") is not None:
                        person_lines.append(f"Linha: {person['row_number']}")

                    chunks.append(
                        self._create_spreadsheet_chunk(
                            header=header,
                            title=f"Entrada de pessoa da aba {person.get('sheet_name') or table_name}",
                            body_lines=person_lines,
                            metadata={
                                **sheet_metadata,
                                "chunk_kind": "people_index",
                                "entity_name": person["entity_name"],
                                "entity_name_normalized": self._normalize_identifier(person["entity_name"]),
                                "entity_role": person.get("entity_role"),
                                "entity_role_normalized": self._normalize_identifier(person.get("entity_role") or ""),
                                "row_number": person.get("row_number"),
                            },
                        )
                    )

            for row in rows:
                record_lines = [
                    f"Documento: {base_metadata['document_name']}",
                    f"Aba: {table_name}",
                ]
                if row.get("row_number") is not None:
                    record_lines.append(f"Linha: {row['row_number']}")
                if row.get("entity_name"):
                    record_lines.append(f"Pessoa: {row['entity_name']}")
                if row.get("entity_role"):
                    record_lines.append(f"Funcao: {row['entity_role']}")
                record_lines.append(
                    "Registro completo: " + " | ".join(f"{header_name}={value}" for header_name, value in row["pairs"])
                )

                chunks.append(
                    self._create_spreadsheet_chunk(
                        header=header,
                        title=f"Registro da aba {table_name}",
                        body_lines=record_lines,
                        metadata={
                            **sheet_metadata,
                            "chunk_kind": "row_record",
                            "row_number": row.get("row_number"),
                            "entity_name": row.get("entity_name"),
                            "entity_name_normalized": self._normalize_identifier(row.get("entity_name") or ""),
                            "entity_role": row.get("entity_role"),
                            "entity_role_normalized": self._normalize_identifier(row.get("entity_role") or ""),
                        },
                    )
                )

        if not chunks:
            return []

        overview_lines = [
            f"Documento: {base_metadata['document_name']}",
            f"Tabelas detectadas: {len(table_summaries)}",
            f"Total de linhas indexadas: {total_rows}",
            "Resumo das tabelas: " + "; ".join(table_summaries[:8]),
        ]
        if len(table_summaries) > 8:
            overview_lines.append(f"Tabelas adicionais omitidas no resumo: {len(table_summaries) - 8}")

        chunks.insert(
            0,
            self._create_spreadsheet_chunk(
                header=header,
                title="Resumo da planilha",
                body_lines=overview_lines,
                metadata={**base_metadata, "chunk_kind": "summary"},
            ),
        )
        return chunks

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

        person_entry = build_person_entry(sheet_name, row_number, "Person", entity_name, entity_role)
        if not person_entry:
            return None

        return {
            "entity_name": person_entry["name"],
            "entity_role": person_entry.get("role"),
            "sheet_name": person_entry.get("sheet_name") or sheet_name,
            "row_number": person_entry.get("row_number"),
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
            entity_role = extract_role_from_pairs(pairs[1:])
            person_entry = build_person_entry(sheet_name, row_number, first_header, first_value, entity_role)
            if person_entry:
                entity_name = person_entry["name"]
                entity_role = person_entry.get("role")

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

    def _to_number(self, value: str) -> float | None:
        return to_number(value)

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
        document_catalog = []
        spreadsheet_chunk_index = {}

        for document in documents:
            document.page_content = self._normalize_whitespace(document.page_content)
            source = document.metadata.get("source")
            document_name = self._extract_document_name(document.page_content, source)
            document_type = self._extract_document_type(document.page_content, source, document_name)
            document_summary = self._extract_document_summary(document.page_content)
            document.metadata["document_name"] = document_name
            document.metadata["document_name_normalized"] = self._normalize_identifier(document_name)
            document.metadata["document_stem_normalized"] = self._normalize_identifier(Path(document_name).stem)
            document.metadata["document_type"] = document_type

            document_catalog.append(
                {
                "name": document_name,
                "normalized_name": document.metadata["document_name_normalized"],
                "normalized_stem": document.metadata["document_stem_normalized"],
                "document_type": document_type,
                "summary": document_summary,
            }
            )

            header = self._extract_document_header(document.page_content)
            if document_type == "spreadsheet":
                document_chunks = self._build_spreadsheet_chunks(document, header)
                spreadsheet_chunk_index.setdefault(document_name, []).extend(document_chunks)
            else:
                document_chunks = self._build_generic_chunks(document, header)

            chunks.extend(document_chunks)

        self._apply_catalog_display_names(document_catalog)
        chunks.extend(self._build_collection_overview_chunks(document_catalog))
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.collection_name = collection_name
        self.document_catalog = document_catalog
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
                "Quando houver um resumo de pessoas, use-o para entender a quantidade total de nomes disponiveis no arquivo. "
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
        if self._is_document_catalog_question(resolved_question, target_document_name):
            return self._answer_document_catalog_question(resolved_question)
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
