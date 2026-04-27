"""Verbatim context helpers for retrieval answers."""

import re


class RetrievalAggregationMixin:
    def _build_answer_context(
        self,
        docs,
        *,
        retrieval_intent: str | None = None,
        target_document_name: str | None = None,
        resolved_question: str | None = None,
        selected_evidence_spans: list[dict[str, object]] | None = None,
    ) -> str:
        """Format selected chunks as labelled blocks for the answer prompt.

        Each block carries its document/section header in a single
        compact line so the LLM can attribute the trecho without the
        embedder having to memorise repeated boilerplate.
        """
        del retrieval_intent, target_document_name, resolved_question, selected_evidence_spans

        rendered_blocks: list[str] = []
        for index, doc in enumerate(docs or [], start=1):
            metadata = getattr(doc, "metadata", {}) or {}
            document_name = str(metadata.get("document_name") or "documento desconhecido").strip()
            section_title = str(metadata.get("section_title") or "").strip()
            chunk_kind = str(metadata.get("chunk_kind") or "").strip()
            page_content = str(getattr(doc, "page_content", "") or "")
            text = self._strip_retrieval_wrapper(page_content) or page_content.strip()
            if not text:
                continue
            header_parts = [f"Trecho {index}", f"documento: {document_name}"]
            if section_title:
                header_parts.append(f"secao: {section_title}")
            if chunk_kind and chunk_kind not in {"section_detail", "text", ""}:
                header_parts.append(f"tipo: {chunk_kind}")
            header = "[" + " | ".join(header_parts) + "]"
            rendered_blocks.append(f"{header}\n{text}")
        return "\n\n".join(rendered_blocks).strip()

    def _strip_retrieval_wrapper(self, text: str) -> str:
        cleaned = re.sub(r"^Documento:\s.*?\nTrecho:\n", "", text or "", flags=re.DOTALL)
        cleaned = re.sub(r"^Documento:\s.*?\nSecao:\s.*?\nTrecho:\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Perfil do documento\s*", "", cleaned, flags=re.DOTALL)
        cleaned_lines = []
        for line in cleaned.splitlines():
            compact = line.strip()
            if compact.startswith("Documento:") or compact.startswith("Secao:"):
                continue
            for prefix in ("Resumo da secao:", "Lista ou enumeracao detectada:", "Trecho:"):
                if compact.startswith(prefix):
                    compact = compact.split(":", 1)[1].strip()
                    break
            cleaned_lines.append(compact)
        return "\n".join(line for line in cleaned_lines if line).strip()
