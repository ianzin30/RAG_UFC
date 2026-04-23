"""Focused evidence span helpers for factoid retrieval and handoff."""

import re


class RetrievalEvidenceMixin:
    def _extract_company_like_candidates(self, text: str) -> list[str]:
        candidates = []
        seen = set()
        patterns = (
            r"(?:empresa\s+parceira(?:\s+do\s+projeto)?(?:\s*[:\-]|\s+e)?\s*)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
            r"(?:parceria\s+com(?:\s+a)?\s+empresa\s+)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
            r"(?:parceria\s+com(?:\s+a)?\s+)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
            r"(?:empresa\s+)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
            r"(?:conv[eÃª]nio\s+com(?:\s+a)?\s+empresa\s+)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
            r"(?:entre\s+a\s+[A-Z][A-Za-z0-9&./-]*\s+e\s+a\s+)([A-Z][A-Za-z0-9&./-]*(?:\s+[A-Z][A-Za-z0-9&./-]*){0,3})",
        )
        for pattern in patterns:
            for match in re.findall(pattern, text or ""):
                compact = re.sub(r"\s+", " ", str(match or "")).strip(" -:;,.")
                compact = re.split(r"(?<=[A-Za-z0-9])\.(?=\s+[A-Z])", compact, maxsplit=1)[0].strip(" -:;,.")
                normalized = self._normalize_identifier(compact)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                candidates.append(compact)
        return candidates

    def _clean_answer_candidate_text(self, text: str) -> str:
        cleaned = re.sub(r"^Documento:\s.*?\n", "", text or "", flags=re.DOTALL)
        cleaned = re.sub(r"^Secao:\s.*?\n", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^Trecho:\n", "", cleaned, flags=re.DOTALL)
        cleaned_lines = []
        for line in cleaned.splitlines():
            compact = re.sub(r"\s+", " ", line).strip(" -")
            if not compact or compact.startswith("Documento:") or compact.startswith("Secao:"):
                continue
            cleaned_lines.append(compact)
        return "\n".join(cleaned_lines).strip()

    def _infer_short_answer_shape(self, resolved_question: str) -> str:
        normalized_question = self._normalize_identifier(resolved_question or "")
        question_tokens = set(normalized_question.split())

        def has_any_token(*markers: str) -> bool:
            return any(marker in question_tokens for marker in markers)

        def has_any_phrase(*markers: str) -> bool:
            return any(marker in normalized_question for marker in markers)

        if has_any_token("cidade", "pais", "onde", "local", "localidade") or has_any_phrase(
            "em qual cidade",
            "em qual pais",
            "em que cidade",
            "em que pais",
        ):
            return "location"
        if has_any_token("quanto", "valor", "orcamento", "bolsa", "reais", "custo") or has_any_phrase(
            "orcamento total",
            "orcamento previsto",
        ):
            return "money"
        if has_any_token("quando", "data", "dia", "mes", "ano", "periodo", "duracao", "inicio", "fim"):
            return "date"
        if has_any_token("sigla", "acronimo", "acronym", "titulo") or has_any_phrase(
            "nome do projeto",
            "como se chama",
        ):
            return "acronym_or_title"
        if question_tokens & {
            "quem",
            "empresa",
            "parceira",
            "parceria",
            "chefe",
            "coordenador",
            "coordenadora",
            "professor",
            "professora",
            "servidor",
            "subchefe",
            "responsavel",
            "autor",
            "autora",
            "nome",
        }:
            return "person_or_org"
        return "generic_short_fact"

    def _extract_support_spans(self, text: str) -> list[str]:
        cleaned = self._clean_answer_candidate_text(text)
        if not cleaned:
            return []

        raw_spans = re.split(r"(?:\n+|(?<=[\.\?!;:])\s+)", cleaned)
        spans: list[str] = []
        pending = ""
        seen: set[str] = set()
        for raw_span in raw_spans:
            compact = re.sub(r"\s+", " ", raw_span or "").strip(" -")
            if not compact:
                continue
            if pending:
                compact = f"{pending} {compact}".strip()
                pending = ""
            if len(compact) < 28 and not re.search(r"[.!?;:]$", compact):
                pending = compact
                continue

            normalized = self._normalize_identifier(compact)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            spans.append(compact)
            if len(spans) >= 32:
                break

        if pending:
            normalized = self._normalize_identifier(pending)
            if normalized and normalized not in seen:
                spans.append(pending)

        if not spans:
            return [cleaned]
        return spans

    def _count_token_phrase_occurrences(
        self,
        haystack_tokens: list[str],
        needle_tokens: list[str],
    ) -> int:
        if not haystack_tokens or not needle_tokens or len(needle_tokens) > len(haystack_tokens):
            return 0

        count = 0
        window_size = len(needle_tokens)
        for index in range(len(haystack_tokens) - window_size + 1):
            if haystack_tokens[index : index + window_size] == needle_tokens:
                count += 1
        return count

    def _normalize_answer_comparison_text(self, text: str) -> str:
        tokens = self._tokenize_search_text(text)
        if tokens:
            return " ".join(tokens)
        return self._normalize_identifier(text)

    def _candidate_supported_in_span(self, candidate_payload: dict[str, object], span_text: str) -> int:
        comparison_text = str(candidate_payload.get("comparison_normalized") or "")
        if not comparison_text:
            return 0

        needle_tokens = comparison_text.split()
        haystack_tokens = self._normalize_answer_comparison_text(span_text).split()
        return self._count_token_phrase_occurrences(haystack_tokens, needle_tokens)

    def _extract_location_candidates(self, text: str, limit: int | None = None) -> list[str]:
        patterns = (
            r"\b([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+(?:\s+(?:de|da|do|das|dos|e|[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+)){0,4}),\s*([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+)\b",
            r"(?:cidade(?:\s+de)?|pais|pais do evento|ocorreu em|realizado em|realizada em|evento em|na cidade de|no municipio de|no município de)\s+([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+(?:\s+(?:de|da|do|das|dos|e|[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+)){0,5}(?:\s*-\s*[A-Z]{2})?)",
            r"\b([A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+(?:\s+(?:de|da|do|das|dos|e|[A-ZÁÀÃÂÉÊÍÓÔÕÚÇ][A-Za-zÁÀÃÂÉÊÍÓÔÕÚÇáàãâéêíóôõúç]+)){0,4}\s*-\s*[A-Z]{2})\b",
        )
        candidates: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for match in re.findall(pattern, text or ""):
                if isinstance(match, tuple):
                    compact = ", ".join(part.strip() for part in match if str(part).strip())
                else:
                    compact = str(match or "").strip()
                compact = re.sub(r"\s+", " ", compact).strip(" ,;:-")
                normalized = self._normalize_identifier(compact)
                if not normalized or normalized in seen:
                    continue
                if any(token in normalized for token in ("departamento", "prof", "professor", "profa", "universidade")):
                    continue
                seen.add(normalized)
                candidates.append(compact)
                if limit is not None and len(candidates) >= limit:
                    return candidates
        return candidates

    def _candidate_chunk_kind_bonus(self, chunk_kind: str) -> int:
        return {
            "section_detail": 34,
            "entity_index": 18,
            "section_overview": 10,
            "text": 8,
            "list_block": 4,
            "document_profile": 0,
        }.get(str(chunk_kind or "text").strip(), 6)

    def _candidate_chunk_kind_rank(self, chunk_kind: str) -> int:
        return {
            "section_detail": 5,
            "entity_index": 4,
            "section_overview": 3,
            "text": 2,
            "list_block": 1,
            "document_profile": 0,
        }.get(str(chunk_kind or "text").strip(), 1)

    def _score_support_span_alignment(
        self,
        span_text: str,
        *,
        query_profile: dict[str, object],
        answer_shape: str,
        chunk_kind: str,
    ) -> dict[str, object]:
        normalized_span = self._normalize_identifier(span_text)
        query_terms = set(query_profile.get("query_terms") or set())
        exact_overlap = sum(1 for term in query_terms if term in normalized_span)
        phrase_hits = [
            phrase for phrase in list(query_profile.get("query_phrases") or []) if phrase in normalized_span
        ]
        quoted_phrase_hits = [
            phrase for phrase in list(query_profile.get("explicit_phrases") or []) if phrase in normalized_span
        ]
        rare_overlap = sum(1 for term in set(query_profile.get("rare_terms") or set()) if term in normalized_span)
        role_overlap = sum(
            1
            for term in {"chefe", "coordenador", "coordenadora", "professor", "professora", "servidor", "subchefe"}
            if term in normalized_span
        )
        company_cue_hits = sum(
            1
            for cue in ("empresa", "parceira", "parceria", "convenio", "empresa junior", "convenio entre")
            if cue in normalized_span
        )
        date_hits = len(self._extract_date_candidates(span_text, limit=3))
        money_hits = len(self._extract_money_candidates(span_text, limit=3))
        labeled_fact_hits = len(self._extract_labeled_facts(span_text, limit=2))
        location_hits = len(self._extract_location_candidates(span_text, limit=3))
        person_hits = len(self._extract_name_candidates(span_text, limit=4))

        alignment_score = (
            exact_overlap * 8
            + len(phrase_hits[:4]) * 42
            + len(quoted_phrase_hits[:3]) * 34
            + min(rare_overlap, 4) * 14
            + min(role_overlap, 3) * 18
            + min(company_cue_hits, 3) * 20
            + min(date_hits, 2) * 18
            + min(money_hits, 2) * 18
            + min(labeled_fact_hits, 2) * 12
            + min(location_hits, 2) * 24
            + min(person_hits, 3) * 8
        )

        aligned = bool(
            phrase_hits
            or quoted_phrase_hits
            or alignment_score >= 26
            or (answer_shape == "person_or_org" and (company_cue_hits or role_overlap or person_hits) and exact_overlap >= 1)
            or (answer_shape == "location" and location_hits and (exact_overlap >= 1 or rare_overlap >= 1))
            or (answer_shape == "date" and date_hits and (exact_overlap >= 1 or rare_overlap >= 1))
            or (answer_shape == "money" and money_hits and (exact_overlap >= 1 or labeled_fact_hits))
        )

        noise_penalty = 0
        if self._looks_like_noisy_source(span_text):
            noise_penalty += 52
        if chunk_kind in {"document_profile", "list_block"}:
            noise_penalty += 12
        if any(
            marker in normalized_span
            for marker in (
                "documento assinado eletronicamente",
                "autenticidade deste documento",
                "codigo crc",
                "codigo verificador",
            )
        ):
            noise_penalty += 80

        return {
            "aligned": aligned,
            "alignment_score": alignment_score,
            "noise_penalty": noise_penalty,
            "exact_overlap": exact_overlap,
            "phrase_hit_count": len(phrase_hits),
            "quoted_phrase_hit_count": len(quoted_phrase_hits),
            "rare_overlap": rare_overlap,
            "role_overlap": role_overlap,
            "company_cue_hits": company_cue_hits,
            "date_hits": date_hits,
            "money_hits": money_hits,
            "labeled_fact_hits": labeled_fact_hits,
            "location_hits": location_hits,
            "person_hits": person_hits,
        }

    def _get_factoid_evidence_cache(self) -> dict[tuple[int, str, str], dict[str, object]]:
        cache = getattr(self, "_retrieval_evidence_span_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._retrieval_evidence_span_cache = cache
        if len(cache) > 2048:
            cache.clear()
        return cache

    def _build_doc_factoid_evidence_summary(
        self,
        doc,
        *,
        resolved_question: str,
        retrieval_intent: str | None,
    ) -> dict[str, object]:
        cache = self._get_factoid_evidence_cache()
        cache_key = (id(doc), str(retrieval_intent or ""), str(resolved_question or ""))
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        empty_summary = {
            "answer_shape": self._infer_short_answer_shape(resolved_question),
            "top_span_score": 0,
            "top_span_text": None,
            "aligned_span_count": 0,
            "spans": [],
        }
        if not resolved_question or retrieval_intent not in {"specific_fact", "entity_lookup", "document_expansion"}:
            cache[cache_key] = empty_summary
            return empty_summary

        metadata = getattr(doc, "metadata", {}) or {}
        chunk_kind = str(metadata.get("chunk_kind") or "text").strip()
        answer_shape = self._infer_short_answer_shape(resolved_question)
        query_profile = self._build_retrieval_query_profile(resolved_question)
        spans: list[dict[str, object]] = []
        for span_index, span_text in enumerate(self._extract_support_spans(getattr(doc, "page_content", "") or "")):
            alignment = self._score_support_span_alignment(
                span_text,
                query_profile=query_profile,
                answer_shape=answer_shape,
                chunk_kind=chunk_kind,
            )
            if not bool(alignment.get("aligned")):
                continue

            shape_bonus = 0
            if answer_shape == "person_or_org":
                if self._extract_company_like_candidates(span_text) or self._extract_name_candidates(span_text, limit=3):
                    shape_bonus += 18
            elif answer_shape == "location":
                if self._extract_location_candidates(span_text, limit=2):
                    shape_bonus += 34
            elif answer_shape == "date":
                if self._extract_date_candidates(span_text, limit=2):
                    shape_bonus += 26
            elif answer_shape == "money":
                if self._extract_money_candidates(span_text, limit=2):
                    shape_bonus += 26
            elif answer_shape == "acronym_or_title":
                if re.findall(r"\b[A-Z]{2,}[A-Z0-9&./-]{0,10}\b", span_text):
                    shape_bonus += 18

            kind_bonus = self._candidate_chunk_kind_bonus(chunk_kind)
            score = int(alignment.get("alignment_score") or 0) + kind_bonus + shape_bonus - int(
                alignment.get("noise_penalty") or 0
            )
            span_payload = {
                "candidate_id": (
                    self._get_retrieval_candidate_id(doc)
                    if hasattr(self, "_get_retrieval_candidate_id")
                    else None
                ),
                "document_name": str(metadata.get("document_name") or "").strip() or "documento",
                "chunk_kind": chunk_kind,
                "chunk_order": metadata.get("chunk_order") if isinstance(metadata.get("chunk_order"), int) else None,
                "section_title": str(metadata.get("section_title") or "").strip() or None,
                "span_index": span_index,
                "text": span_text,
                "score": score,
                "score_components": {
                    "alignment_score": int(alignment.get("alignment_score") or 0),
                    "kind_bonus": kind_bonus,
                    "shape_bonus": shape_bonus,
                    "noise_penalty": -int(alignment.get("noise_penalty") or 0),
                    "exact_overlap": int(alignment.get("exact_overlap") or 0),
                    "phrase_hit_count": int(alignment.get("phrase_hit_count") or 0),
                    "quoted_phrase_hit_count": int(alignment.get("quoted_phrase_hit_count") or 0),
                    "rare_overlap": int(alignment.get("rare_overlap") or 0),
                    "company_cue_hits": int(alignment.get("company_cue_hits") or 0),
                    "role_overlap": int(alignment.get("role_overlap") or 0),
                    "location_hits": int(alignment.get("location_hits") or 0),
                    "date_hits": int(alignment.get("date_hits") or 0),
                    "money_hits": int(alignment.get("money_hits") or 0),
                },
            }
            spans.append(span_payload)

        spans.sort(
            key=lambda item: (
                -int(item.get("score") or 0),
                str(item.get("document_name") or ""),
                int(item.get("chunk_order") or 0),
                int(item.get("span_index") or 0),
            )
        )
        summary = {
            "answer_shape": answer_shape,
            "top_span_score": int(spans[0]["score"]) if spans else 0,
            "top_span_text": str(spans[0]["text"]) if spans else None,
            "aligned_span_count": len(spans),
            "spans": spans[:4],
        }
        cache[cache_key] = summary
        return summary

    def _collect_selected_evidence_spans(
        self,
        docs,
        *,
        retrieval_intent: str | None,
        resolved_question: str,
        target_document_name: str | None = None,
        limit: int = 6,
    ) -> list[dict[str, object]]:
        if not docs or retrieval_intent not in {"specific_fact", "entity_lookup", "document_expansion"}:
            return []

        spans: list[dict[str, object]] = []
        seen: set[str] = set()
        for doc_rank, doc in enumerate(list(docs or [])[:8]):
            summary = self._build_doc_factoid_evidence_summary(
                doc,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
            )
            if not summary.get("spans"):
                continue

            metadata = getattr(doc, "metadata", {}) or {}
            document_name = str(metadata.get("document_name") or "").strip()
            doc_bonus = max(0, 28 - doc_rank * 4)
            if target_document_name and document_name == target_document_name:
                doc_bonus += 18

            for span in list(summary.get("spans") or [])[:2]:
                normalized_text = self._normalize_identifier(str(span.get("text") or ""))
                unique_key = f"{document_name}:{span.get('chunk_order')}:{normalized_text}"
                if not normalized_text or unique_key in seen:
                    continue
                seen.add(unique_key)
                score_components = {
                    str(key): int(value)
                    for key, value in dict(span.get("score_components") or {}).items()
                    if isinstance(value, (int, float))
                }
                score_components["doc_rank_bonus"] = doc_bonus
                spans.append(
                    {
                        **span,
                        "score": int(span.get("score") or 0) + doc_bonus,
                        "score_components": score_components,
                    }
                )

        spans.sort(
            key=lambda item: (
                -int(item.get("score") or 0),
                str(item.get("document_name") or ""),
                int(item.get("chunk_order") or 0),
                int(item.get("span_index") or 0),
            )
        )
        return spans[:limit]

    def _answer_mentions_candidate_text(self, answer_text: str, candidate_text: str) -> bool:
        answer_normalized = self._normalize_answer_comparison_text(answer_text)
        candidate_normalized = self._normalize_answer_comparison_text(candidate_text)
        if not answer_normalized or not candidate_normalized:
            return False
        return (
            answer_normalized == candidate_normalized
            or candidate_normalized in answer_normalized
            or answer_normalized in candidate_normalized
        )
