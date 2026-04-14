"""Matching and scoring helpers for document resolution."""


# Este mixin decide quais documentos parecem ter sido citados pelo usuario.
class DocumentMatchingMixin:
    # Esta busca encontra referencias explicitas a documentos na pergunta original.
    def _match_document_names(self, question: str) -> list[str]:
        normalized_question = self._normalize_identifier(question)
        if not normalized_question:
            return []

        question_tokens = normalized_question.split()
        matches = []
        for document in self._get_document_registry():
            match_data = self._find_document_reference(document, question_tokens)
            if match_data is None:
                continue
            start_index, specificity, alias_display = match_data
            matches.append((start_index, -specificity, document["name"], alias_display))

        matches.sort()
        return [document_name for _, _, document_name, _ in matches]

    # Este atalho devolve apenas o primeiro match explicito, quando ele existe.
    def _match_document_name(self, question: str) -> str | None:
        matches = self._match_document_names(question)
        return matches[0] if matches else None

    # Esta fusao preserva a ordem e remove duplicatas entre estrategias diferentes de match.
    def _merge_document_matches(self, *match_groups: list[str]) -> list[str]:
        merged = []
        seen = set()
        for group in match_groups:
            for document_name in group:
                if document_name in seen:
                    continue
                seen.add(document_name)
                merged.append(document_name)
        return merged

    # Este fluxo mistura match explicito e ranking por aliases para escolher candidatos.
    def _resolve_documents_with_agent(
        self,
        question: str,
        resolved_question: str,
        chat_history=None,
    ) -> dict[str, object]:
        explicit_matches = self._merge_document_matches(
            self._match_document_names(question),
            self._match_document_names(resolved_question),
        )
        if explicit_matches:
            status = "single_match" if len(explicit_matches) == 1 else "multiple_matches"
            return {
                "status": status,
                "matched_documents": explicit_matches,
                "resolver_candidates": explicit_matches,
                "matched_aliases": [],
                "reason": "explicit_document_reference",
            }

        alias_matches = self._collect_resolver_matches(question, resolved_question)
        if not alias_matches:
            return {
                "status": "no_match",
                "matched_documents": [],
                "resolver_candidates": [],
                "matched_aliases": [],
                "reason": "no_alias_match",
            }

        top_score = alias_matches[0]["score"]
        selected = [match for match in alias_matches if match["score"] == top_score]
        matched_documents = [match["document_name"] for match in selected]
        matched_aliases = list(dict.fromkeys(match["alias_display"] for match in selected if match["alias_display"]))
        status = "single_match" if len(matched_documents) == 1 else "multiple_matches"
        return {
            "status": status,
            "matched_documents": matched_documents,
            "resolver_candidates": [match["document_name"] for match in alias_matches],
            "matched_aliases": matched_aliases,
            "reason": selected[0]["reason"],
        }

    # Esta coleta tenta pontuar cada documento usando a pergunta original e a pergunta reescrita.
    def _collect_resolver_matches(self, question: str, resolved_question: str) -> list[dict]:
        normalized_question = self._normalize_identifier(question)
        normalized_resolved_question = self._normalize_identifier(resolved_question)
        question_tokens = normalized_question.split()
        resolved_question_tokens = normalized_resolved_question.split()
        question_terms = set(self._tokenize_search_text(question))
        resolved_question_terms = set(self._tokenize_search_text(resolved_question))

        matches = []
        for document in self._get_document_registry():
            best_match = None
            for normalized_text, tokens, terms, reason_suffix in (
                (normalized_question, question_tokens, question_terms, "question"),
                (normalized_resolved_question, resolved_question_tokens, resolved_question_terms, "resolved_question"),
            ):
                if not normalized_text:
                    continue
                current = self._score_resolver_candidate(document, normalized_text, tokens, terms)
                if current is None:
                    continue
                current["reason"] = f"{current['reason']}:{reason_suffix}"
                if best_match is None or current["score"] > best_match["score"]:
                    best_match = current

            if best_match is None:
                continue
            matches.append(best_match)

        matches.sort(key=lambda item: (-item["score"], item["start_index"], item["document_name"]))
        return matches

    # Esta pontuacao escolhe o melhor alias ou melhor sobreposicao de termos por documento.
    def _score_resolver_candidate(
        self,
        document: dict,
        normalized_text: str,
        question_tokens: list[str],
        query_terms: set[str],
    ) -> dict | None:
        best_match = None
        for alias in document.get("aliases", []):
            alias_tokens = str(alias.get("normalized", "")).split()
            start_index = self._find_token_phrase_index(question_tokens, alias_tokens)
            if start_index is None:
                continue

            score = int(alias.get("weight", 0)) + len(alias_tokens) * 8
            alias_kind = str(alias.get("kind", "")).strip()
            if document.get("meeting_kind") == "extraordinaria" and "extraordinaria" in normalized_text:
                score += 30
            if document.get("meeting_month") and document.get("meeting_year"):
                if document["meeting_month"] in normalized_text and document["meeting_year"] in normalized_text:
                    score += 15
            if alias_kind in {"meeting_month_year", "meeting_kind_month_year"}:
                score += 30
            if alias_kind in {"meeting_date", "meeting_kind_date"}:
                score += 40
            if alias_kind == "document_month_year":
                score += 25
            if alias_kind == "document_full_date":
                score += 35

            candidate = {
                "score": score,
                "start_index": start_index,
                "document_name": document["name"],
                "alias_display": alias.get("display", ""),
                "reason": alias.get("kind", "alias"),
            }
            if best_match is None or candidate["score"] > best_match["score"]:
                best_match = candidate

        keyword_match = self._score_keyword_overlap(document, query_terms)
        if keyword_match is not None and (best_match is None or keyword_match["score"] > best_match["score"]):
            best_match = {
                **keyword_match,
                "document_name": document["name"],
            }
        return best_match

    # Esta heuristica de overlap so vale quando existem termos realmente discriminativos.
    def _score_keyword_overlap(self, document: dict, query_terms: set[str]) -> dict | None:
        keyword_terms = set(document.get("keyword_terms") or [])
        if len(keyword_terms) < 2 or not query_terms:
            return None

        overlap = keyword_terms & query_terms
        if len(overlap) < 2:
            return None

        discriminative_overlap = {term for term in overlap if self._is_discriminative_query_term(term)}
        if not discriminative_overlap:
            return None

        coverage = len(overlap) / max(len(keyword_terms), 1)
        if coverage < 0.4 and len(discriminative_overlap) < 2 and len(overlap) < 3:
            return None

        alias_display = " ".join(sorted(discriminative_overlap or overlap))
        return {
            "score": 70 + len(discriminative_overlap) * 18 + len(overlap) * 8 + int(coverage * 20),
            "start_index": 10_000,
            "alias_display": alias_display,
            "reason": "keyword_overlap",
        }

    # Esta busca explicita ignora aliases genericos para nao confundir citacoes diretas.
    def _find_document_reference(self, document: dict, question_tokens: list[str]) -> tuple[int, int, str] | None:
        candidates = []
        for alias in document.get("aliases", []):
            if alias.get("kind") in {
                "meeting_generic",
                "meeting_month_year",
                "meeting_kind",
                "meeting_kind_month_year",
                "meeting_date",
                "meeting_kind_date",
                "document_date_line",
                "document_month_year",
                "document_full_date",
                "title_keywords",
            }:
                continue

            alias_tokens = str(alias.get("normalized", "")).split()
            if not alias_tokens:
                continue
            if len(alias_tokens) == 1 and len(alias_tokens[0]) < 3:
                continue
            alias_index = self._find_token_phrase_index(question_tokens, alias_tokens)
            if alias_index is None:
                continue
            specificity = int(alias.get("weight", 0)) + len(alias_tokens) * 10 + len(" ".join(alias_tokens))
            candidates.append((alias_index, specificity, alias.get("display", "")))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], -item[1]))
        return candidates[0]
