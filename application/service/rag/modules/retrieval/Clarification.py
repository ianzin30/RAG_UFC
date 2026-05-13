"""Clarification and source formatting helpers."""
# Simple: Ask user to clarify when results are ambiguous

from pathlib import Path
import re


# Este mixin extrai opcoes de clarificacao e formata as fontes do retrieval.
class RetrievalClarificationMixin:
    # Esta funcao quebra um trecho grande em unidades menores candidatas a clarificacao.
    def _extract_evidence_units(self, page_content: str) -> list[str]:
        cleaned = re.sub(r"^Documento:\s.*?\nTrecho:\n", "", page_content or "", flags=re.DOTALL)
        units = []
        for line in cleaned.splitlines():
            compact_line = re.sub(r"\s+", " ", line).strip(" -\n\t")
            if not compact_line:
                continue

            if ":" in compact_line:
                if len(compact_line) >= 18:
                    units.append(compact_line)
                continue

            for part in re.split(r"(?<=[\.\!\?\;])\s+", compact_line):
                compact = re.sub(r"\s+", " ", part).strip(" -\n\t")
                if len(compact) < 24:
                    continue
                units.append(compact)
        return units

    # Esta etapa escolhe frases plausiveis para o usuario desambiguar a referencia.
    def _build_clarification_options(self, question: str, docs, limit: int = 4) -> list[dict[str, str]]:
        query_terms = self._tokenize_search_text(question)
        if not query_terms:
            return []

        query_fragments = self._build_query_fragments(query_terms)
        candidates: list[tuple[int, str, str]] = []
        ranked_docs = self._prioritize_retrieved_docs(
            docs,
            retrieval_intent="entity_lookup",
            resolved_question=question,
        )

        for doc_rank, doc in enumerate(ranked_docs[:6]):
            for unit in self._extract_evidence_units(doc.page_content):
                normalized = self._normalize_identifier(unit)
                if not normalized:
                    continue

                overlap = sum(1 for term in query_terms if term in normalized)
                fragment_overlap = sum(1 for fragment in query_fragments if fragment in normalized)
                if overlap <= 0 and fragment_overlap <= 0:
                    continue

                score = overlap * 30 + fragment_overlap * 12 + max(0, 18 - doc_rank * 3)
                if self._count_name_like_mentions(unit) >= 1:
                    score += 10

                label = unit if len(unit) <= 140 else f"{unit[:137].rstrip()}..."
                candidates.append((score, label, normalized))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        options = []
        seen = set()
        for _, label, normalized in candidates:
            if normalized in seen:
                continue
            seen.add(normalized)
            options.append({"label": label, "normalized": normalized})
            if len(options) >= limit:
                break
        return options

    # Esta resposta pausa o fluxo ate o usuario escolher uma das opcoes mostradas.
    def _build_retrieval_clarification_answer(
        self,
        options: list[dict[str, str]],
        invalid_selection: int | None = None,
    ) -> str:
        if invalid_selection is None:
            intro = "Encontrei mais de um referente plausivel no contexto recuperado e nao vou escolher no chute."
        else:
            intro = f"O numero {invalid_selection} nao corresponde a nenhuma opcao desta lista."

        option_lines = "\n".join(
            f"{index}. {option.get('label', '').strip()}"
            for index, option in enumerate(options, start=1)
            if str(option.get("label", "")).strip()
        )
        return (
            f"{intro}\n\n"
            f"Opcoes encontradas:\n{option_lines}\n\n"
            "Responda apenas com o numero da opcao desejada."
        )

    # Esta montagem resume as fontes finais sem repetir trechos praticamente iguais.
    def _build_sources(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        seen = set()

        for doc in self._prioritize_retrieved_docs(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
        )[:6]:
            document_name = (doc.metadata.get("document_name") or "documento").strip()
            chunk_kind = (doc.metadata.get("chunk_kind") or "text").strip()
            source = str(doc.metadata.get("source") or "").strip()
            source_name = Path(source).name if source else ""
            relative_path = ""
            if source:
                try:
                    source_path = Path(source).resolve()
                    relative_path = source_path.relative_to(Path(self.collections_root).resolve()).as_posix()
                except (OSError, ValueError):
                    relative_path = ""
            excerpt = re.sub(r"\s+", " ", doc.page_content or "").strip()
            if len(excerpt) > 180:
                excerpt = f"{excerpt[:177].rstrip()}..."

            unique_key = (document_name, chunk_kind, excerpt)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            sources.append(
                {
                    "document_name": document_name,
                    "chunk_kind": chunk_kind,
                    "excerpt": excerpt,
                    "source": source,
                    "source_name": source_name,
                    "relative_path": relative_path,
                }
            )
        return sources
