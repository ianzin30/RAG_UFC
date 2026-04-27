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
        return self._format_docs(docs)

    def _strip_retrieval_wrapper(self, text: str) -> str:
        cleaned = re.sub(r"^Documento:\s.*?\nTrecho:\n", "", text or "", flags=re.DOTALL)
        cleaned = re.sub(r"^Documento:\s.*?\nSecao:\s.*?\nTrecho:\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Perfil do documento\s*", "", cleaned, flags=re.DOTALL)
        cleaned_lines = []
        for line in cleaned.splitlines():
            compact = line.strip()
            if compact.startswith("Documento:") or compact.startswith("Secao:"):
                continue
            for prefix in ("Resumo da secao:", "Lista ou enumeracao detectada:"):
                if compact.startswith(prefix):
                    compact = compact.split(":", 1)[1].strip()
                    break
            cleaned_lines.append(compact)
        return "\n".join(line for line in cleaned_lines if line).strip()
