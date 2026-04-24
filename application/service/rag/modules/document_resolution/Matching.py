"""Matching and scoring helpers for document resolution."""
# Simple: Find which documents the user is asking about

import re

# Este mixin decide quais documentos parecem ter sido citados pelo usuario.
class DocumentMatchingMixin:
    def _empty_score_components(self) -> dict[str, int]:
        return {
            "alias_score": 0,
            "keyword_score": 0,
            "signal_score": 0,
            "phrase_score": 0,
            "specificity_score": 0,
            "generic_penalty": 0,
            "blend_bonus": 0,
        }

    def _merge_score_components(self, *component_groups: dict[str, int] | None) -> dict[str, int]:
        merged = self._empty_score_components()
        for group in component_groups:
            if not isinstance(group, dict):
                continue
            for key in merged:
                value = group.get(key)
                if isinstance(value, (int, float)):
                    merged[key] += int(value)
        return merged

    def _requires_specific_resolver_signals(self, retrieval_intent: str | None) -> bool:
        return retrieval_intent in {"specific_fact", "entity_lookup"}

    def _extract_explicit_query_phrases(self, raw_text: str) -> list[str]:
        phrases = []
        seen = set()
        for match in re.findall("[\"'\u201c\u201d]([^\"'\u201c\u201d]{3,120})[\"'\u201c\u201d]", raw_text or ""):
            compact = re.sub(r"\s+", " ", str(match or "")).strip(" -:;,.")
            normalized = self._normalize_identifier(compact)
            if len(normalized.split()) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            phrases.append(normalized)
        return phrases

    def _build_resolver_query_profile(
        self,
        raw_text: str,
        normalized_text: str,
        query_terms: set[str],
        query_phrases: list[str],
    ) -> dict[str, object]:
        generic_terms = {term for term in query_terms if self._is_resolver_generic_query_term(term)}
        year_terms = {term for term in query_terms if re.fullmatch(r"\d{4}", term)}
        specific_terms = {
            term
            for term in query_terms
            if term not in generic_terms and term not in year_terms
        }
        acronyms = {
            self._normalize_identifier(match)
            for match in re.findall(r"\b[A-Z]{2,}[A-Z0-9/-]{0,10}\b", raw_text or "")
            if self._normalize_identifier(match)
        }
        name_terms = set()
        for name in self._extract_name_candidates(raw_text or "", limit=8):
            for token in self._tokenize_search_text(name):
                if token and not self._is_resolver_generic_query_term(token):
                    name_terms.add(token)

        phrases = []
        seen_phrases = set()
        for phrase in [*self._extract_explicit_query_phrases(raw_text), *list(query_phrases or [])]:
            normalized_phrase = self._normalize_identifier(phrase)
            if len(normalized_phrase.split()) < 2 or normalized_phrase in seen_phrases:
                continue
            seen_phrases.add(normalized_phrase)
            phrases.append(normalized_phrase)

        return {
            "normalized_text": normalized_text,
            "raw_text": raw_text,
            "query_terms": set(query_terms),
            "generic_terms": generic_terms,
            "specific_terms": specific_terms,
            "year_terms": year_terms,
            "acronyms": acronyms,
            "name_terms": name_terms,
            "phrases": phrases,
        }

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
                "document_shortlist": explicit_matches[:3],
                "resolver_candidates": explicit_matches,
                "matched_aliases": [],
                "document_scores": [
                    {
                        "document_name": document_name,
                        "score": 999,
                        "reason": "explicit_document_reference",
                        "matched_terms": [],
                        "matched_phrases": [],
                        "score_components": {
                            **self._empty_score_components(),
                            "alias_score": 999,
                        },
                    }
                    for document_name in explicit_matches[:5]
                ],
                "resolver_confidence": 1.0 if len(explicit_matches) == 1 else 0.72,
                "reason": "explicit_document_reference",
            }

        retrieval_intent = self._infer_retrieval_intent(question, resolved_question)
        alias_matches = self._collect_resolver_matches(
            question,
            resolved_question,
            retrieval_intent=retrieval_intent,
        )
        if not alias_matches:
            return {
                "status": "no_match",
                "matched_documents": [],
                "document_shortlist": [],
                "resolver_candidates": [],
                "matched_aliases": [],
                "document_scores": [],
                "resolver_confidence": 0.0,
                "reason": "no_alias_match",
            }

        document_shortlist = self._build_document_shortlist(
            alias_matches,
            retrieval_intent=retrieval_intent,
        )
        selected = [match for match in alias_matches if match["document_name"] in document_shortlist]
        matched_documents = list(document_shortlist)
        matched_aliases = list(dict.fromkeys(match["alias_display"] for match in selected if match["alias_display"]))
        status = "single_match" if len(matched_documents) == 1 else "multiple_matches"
        return {
            "status": status,
            "matched_documents": matched_documents,
            "document_shortlist": document_shortlist,
            "resolver_candidates": [match["document_name"] for match in alias_matches],
            "matched_aliases": matched_aliases,
            "document_scores": self._build_document_score_trace(alias_matches),
            "resolver_confidence": self._estimate_resolver_confidence(alias_matches, document_shortlist),
            "reason": selected[0]["reason"],
        }

    # Esta coleta tenta pontuar cada documento usando a pergunta original e a pergunta reescrita.
    def _collect_resolver_matches(
        self,
        question: str,
        resolved_question: str,
        retrieval_intent: str | None = None,
    ) -> list[dict]:
        normalized_question = self._normalize_identifier(question)
        normalized_resolved_question = self._normalize_identifier(resolved_question)
        question_tokens = normalized_question.split()
        resolved_question_tokens = normalized_resolved_question.split()
        question_terms = set(self._tokenize_search_text(question))
        resolved_question_terms = set(self._tokenize_search_text(resolved_question))
        question_phrases = self._extract_query_signal_phrases(normalized_question)
        resolved_question_phrases = self._extract_query_signal_phrases(normalized_resolved_question)
        question_profile = self._build_resolver_query_profile(
            question,
            normalized_question,
            question_terms,
            question_phrases,
        )
        resolved_question_profile = self._build_resolver_query_profile(
            resolved_question,
            normalized_resolved_question,
            resolved_question_terms,
            resolved_question_phrases,
        )

        matches = []
        for document in self._get_document_registry():
            best_match = None
            for normalized_text, tokens, terms, phrases, query_profile, reason_suffix in (
                (
                    normalized_question,
                    question_tokens,
                    question_terms,
                    question_phrases,
                    question_profile,
                    "question",
                ),
                (
                    normalized_resolved_question,
                    resolved_question_tokens,
                    resolved_question_terms,
                    resolved_question_phrases,
                    resolved_question_profile,
                    "resolved_question",
                ),
            ):
                if not normalized_text:
                    continue
                current = self._score_resolver_candidate(
                    document,
                    normalized_text,
                    tokens,
                    terms,
                    phrases,
                    retrieval_intent=retrieval_intent,
                    query_profile=query_profile,
                )
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
        query_phrases: list[str],
        *,
        retrieval_intent: str | None = None,
        query_profile: dict[str, object] | None = None,
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
                score += 60
            if alias_kind in {"meeting_date", "meeting_kind_date"}:
                score += 60
            if alias_kind == "document_month_year":
                score += 40
            if alias_kind == "document_full_date":
                score += 55

            candidate = {
                "score": score,
                "start_index": start_index,
                "document_name": document["name"],
                "alias_display": alias.get("display", ""),
                "reason": alias.get("kind", "alias"),
                "matched_terms": [],
                "matched_phrases": [],
                "score_components": {
                    **self._empty_score_components(),
                    "alias_score": score,
                    "specificity_score": len(alias_tokens) * 6,
                },
            }
            if best_match is None or candidate["score"] > best_match["score"]:
                best_match = candidate

        keyword_match = self._score_keyword_overlap(
            document,
            query_terms,
            retrieval_intent=retrieval_intent,
            query_profile=query_profile,
        )
        signal_match = self._score_document_signal_overlap(
            document,
            normalized_text,
            query_terms,
            query_phrases,
            retrieval_intent=retrieval_intent,
            query_profile=query_profile,
        )

        combined_match = self._combine_resolver_match_components(
            document=document,
            best_alias_match=best_match,
            keyword_match=keyword_match,
            signal_match=signal_match,
        )
        if combined_match is not None:
            return combined_match

        if keyword_match is not None:
            return {
                **keyword_match,
                "document_name": document["name"],
            }
        return best_match

    # Esta heuristica de overlap so vale quando existem termos realmente discriminativos.
    def _score_keyword_overlap(
        self,
        document: dict,
        query_terms: set[str],
        *,
        retrieval_intent: str | None = None,
        query_profile: dict[str, object] | None = None,
    ) -> dict | None:
        keyword_terms = set(document.get("keyword_terms") or [])
        if not keyword_terms or not query_terms:
            return None

        overlap = keyword_terms & query_terms
        if not overlap:
            return None

        profile = query_profile or {}
        generic_overlap = overlap & set(profile.get("generic_terms") or set())
        specific_overlap = overlap & set(profile.get("specific_terms") or set())
        year_overlap = overlap & set(profile.get("year_terms") or set())
        acronym_overlap = overlap & set(profile.get("acronyms") or set())
        name_overlap = overlap & set(profile.get("name_terms") or set())
        requires_specific = self._requires_specific_resolver_signals(retrieval_intent)

        if requires_specific and not (specific_overlap or year_overlap or acronym_overlap or name_overlap):
            return None

        if len(overlap) < 2 and not (year_overlap or acronym_overlap or name_overlap):
            return None

        coverage = len(overlap) / max(len(query_terms), 1)
        specificity_score = (
            len(specific_overlap) * 24
            + len(year_overlap) * 28
            + len(acronym_overlap) * 18
            + len(name_overlap) * 14
        )
        generic_penalty = len(generic_overlap) * (6 if requires_specific else 2)
        keyword_score = 48 + len(overlap) * 8 + int(coverage * 18) + specificity_score - generic_penalty
        if keyword_score < 56:
            return None

        matched_terms = sorted(specific_overlap or year_overlap or acronym_overlap or name_overlap or overlap)
        alias_display = " ".join(matched_terms[:6]).strip()
        return {
            "score": keyword_score,
            "start_index": 10_000,
            "alias_display": alias_display,
            "reason": "keyword_overlap",
            "matched_terms": matched_terms,
            "matched_phrases": [],
            "score_components": {
                **self._empty_score_components(),
                "keyword_score": keyword_score,
                "specificity_score": specificity_score,
                "generic_penalty": -generic_penalty,
            },
        }

    def _score_resolver_relationship_bonus(
        self,
        normalized_query: str,
        phrase_haystacks: list[str],
        *,
        phrase_hits: list[str],
        specific_overlap: set[str],
        acronym_overlap: set[str],
        name_overlap: set[str],
    ) -> int:
        haystacks = [haystack for haystack in phrase_haystacks if haystack]
        if not normalized_query or not haystacks:
            return 0

        has_specific_anchor = bool(phrase_hits or specific_overlap or acronym_overlap or name_overlap)
        if not has_specific_anchor:
            return 0

        bonus = 0
        partnership_query = "empresa" in normalized_query and any(
            marker in normalized_query for marker in ("parceira", "parceria", "convenio")
        )
        if partnership_query and any(
            any(cue in haystack for cue in ("empresa parceira", "parceria com", "parceira do projeto", "convenio"))
            for haystack in haystacks
        ):
            bonus += 36

        if "empresa junior" in normalized_query and any("empresa junior" in haystack for haystack in haystacks):
            bonus += 34

        if "projeto" in normalized_query and any(
            cue in haystack for haystack in haystacks for cue in ("projeto", "intitulado")
        ):
            bonus += 12

        return bonus

    def _score_document_signal_overlap(
        self,
        document: dict,
        normalized_text: str,
        query_terms: set[str],
        query_phrases: list[str],
        *,
        retrieval_intent: str | None = None,
        query_profile: dict[str, object] | None = None,
    ) -> dict | None:
        search_text = str(document.get("search_text_normalized") or "").strip()
        if not search_text or not query_terms:
            return None

        profile = query_profile or {}
        keyword_terms = set(document.get("keyword_terms") or [])
        section_terms = set(document.get("section_terms") or [])
        entity_terms = set(document.get("entity_terms") or [])
        fact_terms = set(document.get("fact_terms") or [])
        acronyms = {self._normalize_identifier(acronym) for acronym in list(document.get("acronyms") or [])}
        high_value_excerpt = self._normalize_identifier(str(document.get("high_value_excerpt") or ""))
        keyword_summary = self._normalize_identifier(str(document.get("keyword_summary") or ""))
        signal_phrase_texts = [
            self._normalize_identifier(str(phrase or ""))
            for phrase in list(document.get("signal_phrases") or [])
            if self._normalize_identifier(str(phrase or ""))
        ]
        search_terms = set(search_text.split())

        overlap = {term for term in query_terms if term in keyword_terms or term in search_terms or term in search_text}
        generic_overlap = overlap & set(profile.get("generic_terms") or set())
        specific_overlap = overlap & set(profile.get("specific_terms") or set())
        section_overlap = {term for term in query_terms if term in section_terms}
        entity_overlap = {term for term in query_terms if term in entity_terms}
        fact_overlap = {term for term in query_terms if term in fact_terms}
        acronym_overlap = {
            term
            for term in set(profile.get("acronyms") or set())
            if term in acronyms or term in search_terms
        }
        year_overlap = {term for term in set(profile.get("year_terms") or set()) if term in search_terms}
        name_overlap = {term for term in set(profile.get("name_terms") or set()) if term in entity_terms or term in search_terms}
        phrase_haystacks = [high_value_excerpt, keyword_summary, *signal_phrase_texts]
        phrase_hits = [
            phrase
            for phrase in list(profile.get("phrases") or query_phrases or [])
            if phrase and any(phrase in haystack for haystack in phrase_haystacks if haystack)
        ]
        requires_specific = self._requires_specific_resolver_signals(retrieval_intent)
        has_specific_signal = bool(
            specific_overlap
            or acronym_overlap
            or year_overlap
            or name_overlap
            or phrase_hits
        )
        if requires_specific and not has_specific_signal:
            return None
        if len(overlap) < 2 and not has_specific_signal:
            return None

        phrase_score = 0
        for phrase in phrase_hits[:4]:
            phrase_tokens = self._tokenize_search_text(phrase)
            phrase_score += 88 if len(phrase_tokens) >= 3 else 60

        normalized_query = str(profile.get("normalized_text") or normalized_text)
        relationship_bonus = self._score_resolver_relationship_bonus(
            normalized_query,
            [high_value_excerpt, keyword_summary, search_text, *signal_phrase_texts],
            phrase_hits=phrase_hits,
            specific_overlap=specific_overlap,
            acronym_overlap=acronym_overlap,
            name_overlap=name_overlap,
        )
        if "nome" in normalized_query and "empresa junior" in normalized_query:
            definitional_haystacks = [high_value_excerpt, *signal_phrase_texts, search_text]
            if any(" e a empresa junior " in f" {haystack} " for haystack in definitional_haystacks if haystack):
                phrase_score += 36
                specificity_score = (
                    len(specific_overlap) * 26
                    + len(acronym_overlap) * 24
                    + len(name_overlap) * 18
                    + len(year_overlap) * 16
                    + 18
                )
            else:
                specificity_score = (
                    len(specific_overlap) * 26
                    + len(acronym_overlap) * 24
                    + len(name_overlap) * 18
                    + len(year_overlap) * 16
                )
        else:
            specificity_score = (
                len(specific_overlap) * 26
                + len(acronym_overlap) * 24
                + len(name_overlap) * 18
                + len(year_overlap) * 16
            )
        signal_score = (
            len(overlap) * 10
            + len(section_overlap) * 10
            + len(entity_overlap) * 16
            + len(fact_overlap) * 14
        )
        generic_penalty = len(generic_overlap) * (5 if requires_specific else 1)
        phrase_score += relationship_bonus

        score = signal_score + specificity_score + phrase_score - generic_penalty

        document_year = str(document.get("meeting_year") or "").strip()
        all_year_terms_in_query = set(profile.get("year_terms") or set())
        if document_year and document_year in normalized_text:
            specificity_score += 50
            score += 50
        elif requires_specific and all_year_terms_in_query:
            if not document_year:
                score -= 30
            else:
                score -= 40
        meeting_month = str(document.get("meeting_month") or "").strip()
        if meeting_month and meeting_month in normalized_text:
            signal_score += 16
            score += 16

        if score < 68:
            return None

        matched_terms = sorted(specific_overlap or name_overlap or year_overlap or overlap)
        alias_display = " ".join(matched_terms[:6]).strip()
        if not alias_display and phrase_hits:
            alias_display = phrase_hits[0]
        return {
            "score": score,
            "start_index": 10_000,
            "alias_display": alias_display,
            "reason": "document_signal_overlap",
            "matched_terms": matched_terms,
            "matched_phrases": phrase_hits[:4],
            "score_components": {
                **self._empty_score_components(),
                "signal_score": signal_score,
                "phrase_score": phrase_score,
                "specificity_score": specificity_score,
                "generic_penalty": -generic_penalty,
            },
        }

    def _combine_resolver_match_components(
        self,
        *,
        document: dict,
        best_alias_match: dict | None,
        keyword_match: dict | None,
        signal_match: dict | None,
    ) -> dict | None:
        if best_alias_match is None and keyword_match is None and signal_match is None:
            return None

        if best_alias_match is not None:
            combined = dict(best_alias_match)
            combined["matched_terms"] = list(best_alias_match.get("matched_terms") or [])
            combined["matched_phrases"] = list(best_alias_match.get("matched_phrases") or [])
            combined["score_components"] = self._merge_score_components(
                best_alias_match.get("score_components"),
                signal_match.get("score_components") if signal_match is not None else None,
                keyword_match.get("score_components") if keyword_match is not None else None,
            )
            if signal_match is not None:
                blend_bonus = min(48, max(18, signal_match["score"] // 4))
                combined["score"] += blend_bonus
                combined["matched_terms"] = list(signal_match.get("matched_terms") or [])
                combined["matched_phrases"] = list(signal_match.get("matched_phrases") or [])
                combined["score_components"]["blend_bonus"] += blend_bonus
            elif keyword_match is not None:
                blend_bonus = min(24, keyword_match["score"] // 6)
                combined["score"] += blend_bonus
                combined["matched_terms"] = list(keyword_match.get("matched_terms") or [])
                combined["score_components"]["blend_bonus"] += blend_bonus
            combined["document_name"] = document["name"]
            return combined

        base_match = signal_match if signal_match is not None else keyword_match
        if base_match is None:
            return None

        combined = {
            **base_match,
            "document_name": document["name"],
            "matched_terms": list(base_match.get("matched_terms") or []),
            "matched_phrases": list(base_match.get("matched_phrases") or []),
            "score_components": self._merge_score_components(base_match.get("score_components")),
        }
        if keyword_match is not None and signal_match is not None and keyword_match is not signal_match:
            blend_bonus = min(32, keyword_match["score"] // 5)
            combined["score"] += blend_bonus
            combined["matched_terms"] = sorted(
                set(combined["matched_terms"]) | set(keyword_match.get("matched_terms") or [])
            )
            combined["score_components"] = self._merge_score_components(
                combined["score_components"],
                keyword_match.get("score_components"),
                {"blend_bonus": blend_bonus},
            )
        return combined

    def _build_document_shortlist(
        self,
        matches: list[dict],
        limit: int = 3,
        retrieval_intent: str | None = None,
    ) -> list[str]:
        if not matches:
            return []

        top_score = int(matches[0]["score"])
        top_components = dict(matches[0].get("score_components") or {})
        requires_specific = self._requires_specific_resolver_signals(retrieval_intent)
        top_is_decisive = requires_specific and (
            int(top_components.get("phrase_score") or 0) >= 88
            or int(top_components.get("specificity_score") or 0) >= 80
            or int(top_components.get("signal_score") or 0) >= 96
        )
        shortlist = [matches[0]["document_name"]]
        for match in matches[1:]:
            if len(shortlist) >= limit:
                break
            score = int(match["score"])
            score_gap = top_score - score
            if score <= 0:
                continue
            if top_is_decisive:
                runner_components = dict(match.get("score_components") or {})
                runner_is_specific = (
                    int(runner_components.get("phrase_score") or 0) >= 88
                    or int(runner_components.get("specificity_score") or 0) >= 80
                    or int(runner_components.get("signal_score") or 0) >= 96
                )
                if score_gap <= 16 or (score >= int(top_score * 0.95) and runner_is_specific):
                    shortlist.append(match["document_name"])
                continue
            if score_gap <= 24 or score >= int(top_score * 0.9):
                shortlist.append(match["document_name"])
        return shortlist

    def _estimate_resolver_confidence(self, matches: list[dict], document_shortlist: list[str]) -> float:
        if not matches:
            return 0.0
        if len(document_shortlist) == 1 and matches[0]["reason"].startswith("document_name"):
            return 0.99

        top_score = float(matches[0]["score"])
        runner_up = float(matches[1]["score"]) if len(matches) > 1 else 0.0
        gap_ratio = (top_score - runner_up) / max(top_score, 1.0)
        confidence = min(0.55 + top_score / 320.0, 0.94)
        if len(document_shortlist) == 1:
            confidence += 0.12
        else:
            confidence -= 0.08 * max(len(document_shortlist) - 1, 0)
        if gap_ratio >= 0.35:
            confidence += 0.14
        elif gap_ratio >= 0.18:
            confidence += 0.06
        else:
            confidence -= 0.1
        top_components = dict(matches[0].get("score_components") or {})
        if len(document_shortlist) == 1 and (
            int(top_components.get("phrase_score") or 0) >= 88
            or int(top_components.get("specificity_score") or 0) >= 80
            or int(top_components.get("signal_score") or 0) >= 96
        ):
            confidence += 0.06
        return round(max(0.0, min(confidence, 0.99)), 3)

    def _build_document_score_trace(self, matches: list[dict], limit: int = 5) -> list[dict[str, object]]:
        trace = []
        for match in matches[:limit]:
            trace.append(
                {
                    "document_name": match["document_name"],
                    "score": int(match["score"]),
                    "reason": str(match.get("reason") or ""),
                    "matched_terms": list(match.get("matched_terms") or []),
                    "matched_phrases": list(match.get("matched_phrases") or []),
                    "score_components": dict(match.get("score_components") or self._empty_score_components()),
                }
            )
        return trace

    def _extract_query_signal_phrases(self, normalized_text: str) -> list[str]:
        tokens = self._tokenize_search_text(normalized_text)
        phrases = []
        seen = set()
        for window_size in range(5, 2, -1):
            for index in range(len(tokens) - window_size + 1):
                window = tokens[index : index + window_size]
                discriminative_terms = [term for term in window if self._is_discriminative_query_term(term)]
                if len(discriminative_terms) < 2:
                    continue
                phrase = " ".join(window).strip()
                if len(phrase) < 8 or phrase in seen:
                    continue
                seen.add(phrase)
                phrases.append(phrase)
                if len(phrases) >= 8:
                    return phrases
        for window_size in range(3, 1, -1):
            for index in range(len(tokens) - window_size + 1):
                window = tokens[index : index + window_size]
                discriminative_terms = [term for term in window if self._is_discriminative_query_term(term)]
                if len(discriminative_terms) < 1:
                    continue
                phrase = " ".join(window).strip()
                if len(phrase) < 8 or phrase in seen:
                    continue
                seen.add(phrase)
                phrases.append(phrase)
                if len(phrases) >= 10:
                    return phrases
        return phrases

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
