"""Intent and evidence-shape helpers for retrieval."""
# Simple: Understand what type of answer user is looking for

import re


# Este mixin infere a forma esperada da evidencia antes do ranking dos trechos.
class RetrievalIntentMixin:
    # Esta heuristica decide se a pergunta pede resumo, lista, entidade ou fato pontual.
    def _infer_retrieval_intent(self, question: str, resolved_question: str | None = None) -> str:
        normalized = self._normalize_identifier(" ".join(part for part in [question, resolved_question or ""] if part))
        if not normalized:
            return "specific_fact"

        expansion_markers = (
            "fale mais",
            "me de detalhes",
            "me dê detalhes",
            "mais detalhes",
            "aprofunde",
            "explique melhor",
            "detalhe",
            "detalhes",
            "traga mais informacoes",
        )
        summary_markers = (
            "fale sobre",
            "me fale sobre",
            "resuma",
            "resumo",
            "do que trata",
            "sobre esse documento",
            "sobre este documento",
            "sobre esse arquivo",
            "sobre este arquivo",
            "sobre essa reuniao",
            "sobre esta reuniao",
            "sobre essa ata",
            "sobre esta ata",
        )
        list_markers = (
            "quais sao",
            "quais são",
            "liste",
            "listar",
            "lista",
            "todos os",
            "todas as",
            "nomes",
        )
        entity_markers = (
            "quem",
            "qual",
            "coordenador",
            "coordenadora",
            "coordenadores",
            "professor",
            "professora",
            "responsavel",
            "responsável",
            "autor",
            "autora",
        )

        if any(marker in normalized for marker in list_markers):
            return "list_extraction"
        if any(marker in normalized for marker in expansion_markers):
            return "document_expansion"
        if any(marker in normalized for marker in summary_markers):
            return "summary"
        if any(marker in normalized for marker in entity_markers):
            return "entity_lookup"
        return "specific_fact"

    # Estes fragmentos curtos ajudam a detectar variantes de termos parecidos no contexto.
    def _build_query_fragments(self, query_terms: list[str]) -> set[str]:
        return {term[:6] for term in query_terms if len(term) >= 5}

    # Esta contagem detecta nomes proprios para favorecer listas e respostas sobre pessoas.
    def _count_name_like_mentions(self, text: str) -> int:
        candidates = re.findall(
            r"\b[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][a-záàãâéêíóôõúç]+(?:\s+[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][a-záàãâéêíóôõúç]+)+",
            text or "",
        )
        return len(candidates)
