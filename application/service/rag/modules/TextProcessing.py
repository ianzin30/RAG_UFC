"""Text cleaning and normalization utilities for documents and queries.

Handles whitespace normalization, document header/name extraction, type detection,
identifier normalization (for matching), and query keyword extraction with stopword filtering.
"""
import re
import unicodedata
from pathlib import Path

from ..Constants import QUERY_STOPWORDS


class TextProcessingMixin:
    """Clean, normalize, and extract features from text."""

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

    def _extract_extraction_method(self, text: str) -> str | None:
        for line in self._normalize_whitespace(text).split("\n")[:12]:
            if line.lower().startswith("extraction method:"):
                return line.split(":", 1)[1].strip() or None
        return None

    def _strip_document_wrapper(self, text: str) -> str:
        lines = self._normalize_whitespace(text).split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        if lines and lines[0].lower().startswith("extraction method:"):
            lines = lines[1:]
        if lines and lines[0].lower().startswith("document type:"):
            lines = lines[1:]
        return "\n".join(line for line in lines if line).strip()

    def _prepare_generic_document_body(self, text: str) -> str:
        body = self._strip_document_wrapper(text)
        lines = [line.strip() for line in body.split("\n") if line.strip()]
        if not lines:
            return ""

        merged_lines: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if next_line and self._should_merge_heading_marker_with_next_line(line, next_line):
                merged_lines.append(f"{line.rstrip()} {next_line.lstrip()}".strip())
                index += 2
                continue
            merged_lines.append(line)
            index += 1

        reflowed_lines: list[str] = []
        paragraph_parts: list[str] = []

        def flush_paragraph() -> None:
            if not paragraph_parts:
                return
            reflowed_lines.append(" ".join(paragraph_parts).strip())
            paragraph_parts.clear()

        for line in merged_lines:
            if self._should_preserve_generic_line_break(line):
                flush_paragraph()
                reflowed_lines.append(line)
                continue
            paragraph_parts.append(line)

        flush_paragraph()
        return "\n".join(line for line in reflowed_lines if line).strip()

    def _normalize_identifier(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _should_merge_heading_marker_with_next_line(self, line: str, next_line: str) -> bool:
        stripped = (line or "").strip()
        next_stripped = (next_line or "").strip()
        if not stripped or not next_stripped:
            return False
        if not re.fullmatch(r"\d+(?:\.\d+)*\.?", stripped):
            return False
        if self._is_section_heading(next_stripped):
            return False
        if next_stripped.startswith(("-", "•", "*", "#")):
            return False
        return bool(re.search(r"[A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]", next_stripped))

    def _should_preserve_generic_line_break(self, line: str) -> bool:
        stripped = (line or "").strip()
        if not stripped:
            return False
        if stripped.startswith(("#", "-", "•", "*")):
            return True
        if re.match(r"^\d+(?:\.\d+)*[\)\.]?\s+", stripped):
            return True
        if self._is_section_heading(stripped):
            return True
        if stripped.endswith(":"):
            return True
        return self._normalize_identifier(stripped) in {
            "projeto",
            "coordenador",
            "coordenadora",
            "coordenador na instituicao",
            "coordenadora na instituicao",
            "empresa",
            "instituicao",
        }

    def _find_token_phrase_index(self, haystack_tokens: list[str], needle_tokens: list[str]) -> int | None:
        if not haystack_tokens or not needle_tokens or len(needle_tokens) > len(haystack_tokens):
            return None

        window_size = len(needle_tokens)
        for index in range(len(haystack_tokens) - window_size + 1):
            if haystack_tokens[index : index + window_size] == needle_tokens:
                return index
        return None

    def _is_section_heading(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        compact = stripped.rstrip(".:")
        if re.fullmatch(r"\d+(?:\.\d+)*", compact):
            return True
        return bool(re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", stripped))

    def _extract_document_title(self, text: str) -> str | None:
        lines = self._normalize_whitespace(text).split("\n")
        for index, line in enumerate(lines[:30]):
            if self._normalize_identifier(line) == "projeto" and index + 1 < len(lines):
                candidate = lines[index + 1].strip()
                if candidate and not candidate.startswith("#"):
                    return candidate
        return None

    def _extract_document_coordinator(self, text: str) -> str | None:
        lines = self._normalize_whitespace(text).split("\n")
        markers = {
            "coordenador na instituicao",
            "coordenadora na instituicao",
            "coordenador",
            "coordenadora",
        }
        for index, line in enumerate(lines[:40]):
            if self._normalize_identifier(line) in markers and index + 1 < len(lines):
                candidate = lines[index + 1].strip()
                if candidate and self._normalize_identifier(candidate) not in {"empresa", "instituicao"}:
                    return candidate
        return None

    def _extract_document_version(self, text: str) -> str | None:
        for line in self._normalize_whitespace(text).split("\n")[:40]:
            normalized = self._normalize_identifier(line)
            if normalized.startswith("versao "):
                return line.strip()
        return None

    def _extract_document_date(self, text: str) -> str | None:
        month_pattern = re.compile(
            r"\b("
            r"janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|"
            r"january|february|march|april|may|june|july|august|september|october|november|december"
            r")\b"
        )
        for line in self._normalize_whitespace(text).split("\n")[:50]:
            normalized = self._normalize_identifier(line)
            if month_pattern.search(normalized) and any(char.isdigit() for char in normalized):
                return line.strip()
        return None

    def _extract_document_description_excerpt(self, text: str, max_lines: int = 6) -> str | None:
        lines = self._prepare_generic_document_body(text).split("\n")
        start_index = None

        for index, line in enumerate(lines):
            normalized = self._normalize_identifier(line)
            if normalized in {"introducao", "introduction"}:
                start_index = index + 1
                break
            if normalized.startswith("2 descricao do projeto") or normalized.startswith("2 description"):
                start_index = index + 1

        if start_index is None:
            body_lines = self._strip_document_wrapper(text).split("\n")
            body_lines = [line for line in body_lines if line]
            if not body_lines:
                return None
            return " ".join(body_lines[:max_lines]).strip() or None

        excerpt_lines: list[str] = []
        for line in lines[start_index:]:
            stripped = line.strip()
            if not stripped:
                continue
            normalized = self._normalize_identifier(stripped)
            if normalized in {"introducao", "introduction"}:
                continue
            if self._is_section_heading(stripped):
                if excerpt_lines:
                    break
                continue
            excerpt_lines.append(stripped)
            if len(excerpt_lines) >= max_lines:
                break
            if len(" ".join(excerpt_lines)) >= 520:
                break

        if not excerpt_lines:
            return None
        return " ".join(excerpt_lines).strip() or None

    def _build_generic_document_profile_lines(self, document_name: str, text: str) -> list[str]:
        profile_lines = [f"Documento: {document_name}"]

        title = self._extract_document_title(text)
        if title and title != document_name:
            profile_lines.append(f"Titulo: {title}")

        extraction_method = self._extract_extraction_method(text)
        if extraction_method:
            profile_lines.append(f"Metodo de extracao: {extraction_method}")

        coordinator = self._extract_document_coordinator(text)
        if coordinator:
            profile_lines.append(f"Coordenador: {coordinator}")

        version = self._extract_document_version(text)
        if version:
            profile_lines.append(version)

        date = self._extract_document_date(text)
        if date and date != version:
            profile_lines.append(f"Data: {date}")

        description = self._extract_document_description_excerpt(text)
        if description:
            profile_lines.append(f"Descricao inicial: {description}")

        return profile_lines

    def _extract_name_candidates(self, text: str, limit: int | None = None) -> list[str]:
        pattern = re.compile(
            r"\b[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][a-záàãâéêíóôõúç]+"
            r"(?:\s+(?:de|da|do|das|dos|e|Jr|Jr\.|Junior|Júnior|Filho|Neto|Sobrinho|"
            r"[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][a-záàãâéêíóôõúç]+)){1,6}"
        )
        names = []
        seen = set()
        for candidate in pattern.findall(text or ""):
            compact = re.sub(r"\s+", " ", candidate).strip(" ,;:-")
            normalized = self._normalize_identifier(compact)
            if len(compact) < 6 or len(normalized.split()) < 2:
                continue
            if self._is_noisy_name_candidate(compact):
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            names.append(compact)
            if limit is not None and len(names) >= limit:
                break
        return names

    def _is_noisy_name_candidate(self, candidate: str) -> bool:
        normalized = self._normalize_identifier(candidate)
        if not normalized:
            return True

        tokens = normalized.split()
        noisy_terms = {
            "abertura",
            "coordenador",
            "coordenadora",
            "documento",
            "empresa",
            "enumeracao",
            "extracao",
            "instituicao",
            "lista",
            "metodo",
            "perfil",
            "plano",
            "projeto",
            "resumo",
            "secao",
            "titulo",
            "trabalho",
            "versao",
        }
        noisy_count = sum(1 for token in tokens if token in noisy_terms)
        if noisy_count >= 2:
            return True
        if tokens[0] in noisy_terms or tokens[-1] in noisy_terms:
            return True
        if any(token in {"empresa", "instituicao", "versao"} for token in tokens):
            return True
        return False

    def _extract_date_candidates(self, text: str, limit: int | None = None) -> list[str]:
        patterns = (
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{1,2}\s+de\s+[A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+\s+de\s+\d{4}\b",
            r"\b(?:janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|"
            r"january|february|march|april|may|june|july|august|september|october|november|december)"
            r"(?:\s+de)?\s+\d{4}\b",
        )
        values = []
        seen = set()
        for pattern in patterns:
            for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
                compact = re.sub(r"\s+", " ", match).strip(" ,;:-")
                normalized = self._normalize_identifier(compact)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                values.append(compact)
                if limit is not None and len(values) >= limit:
                    return values
        return values

    def _extract_money_candidates(self, text: str, limit: int | None = None) -> list[str]:
        pattern = re.compile(r"(?:R\$\s*)?\d{1,3}(?:[\.\s]\d{3})*(?:,\d{2})")
        values = []
        seen = set()
        for match in pattern.findall(text or ""):
            compact = re.sub(r"\s+", " ", match).strip(" ,;:-")
            if len(compact) < 4:
                continue
            normalized = self._normalize_identifier(compact)
            if normalized in seen:
                continue
            seen.add(normalized)
            values.append(compact)
            if limit is not None and len(values) >= limit:
                break
        return values

    def _extract_labeled_facts(self, text: str, limit: int | None = None) -> list[tuple[str, str]]:
        facts = []
        seen = set()
        for raw_line in (text or "").splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if ":" not in line:
                continue
            label, value = [part.strip(" -") for part in line.split(":", 1)]
            if not label or not value:
                continue
            if len(label) > 60 or len(value) > 240:
                continue
            normalized_label = self._normalize_identifier(label)
            normalized_value = self._normalize_identifier(value)
            if not normalized_label or not normalized_value:
                continue
            unique_key = (normalized_label, normalized_value)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            facts.append((label, value))
            if limit is not None and len(facts) >= limit:
                break
        return facts

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
