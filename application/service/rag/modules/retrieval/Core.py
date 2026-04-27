"""Generic retrieval pipeline helpers."""

from __future__ import annotations

import json
import re

from ...Constants import MONTH_NUMBER_TO_NAME


class RetrievalCoreMixin:
    def _get_retrieval_config_value(self, key: str, default):
        retrieval_config = getattr(self, "retrieval_config", None)
        return getattr(retrieval_config, key, default)

    def _normalize_document_shortlist(
        self,
        document_shortlist: list[str] | None = None,
        target_document_name: str | None = None,
    ) -> list[str]:
        normalized = []
        seen = set()
        for document_name in [target_document_name, *(document_shortlist or [])]:
            compact = str(document_name or "").strip()
            if not compact or compact in seen:
                continue
            seen.add(compact)
            normalized.append(compact)
        return normalized

    def _collect_query_signal_phrases(self, question: str) -> list[str]:
        phrases = []
        seen = set()
        normalized_question = self._normalize_identifier(question)
        raw_phrases = [
            *list(self._extract_explicit_query_phrases(question) or []),
            *list(self._extract_query_signal_phrases(normalized_question) or []),
        ]
        for phrase in raw_phrases:
            normalized_phrase = self._normalize_identifier(phrase)
            if len(normalized_phrase.split()) < 2 or normalized_phrase in seen:
                continue
            seen.add(normalized_phrase)
            phrases.append(normalized_phrase)
        return phrases

    def _get_retrieval_doc_pool(
        self,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        docs = list(self._get_vector_store_documents())
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        if not shortlist:
            return docs
        allowed = set(shortlist)
        return [
            doc
            for doc in docs
            if str((getattr(doc, "metadata", {}) or {}).get("document_name") or "").strip() in allowed
        ]

    def _retrieve_docs(
        self,
        question: str,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        document_shortlist: list[str] | None = None,
    ):
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        candidate_pool_limit = int(self._get_retrieval_config_value("candidate_pool_limit", 30))
        lexical_limit = int(self._get_retrieval_config_value("lexical_limit", candidate_pool_limit))

        dense_docs = self._retrieve_dense_mmr_docs(
            question,
            target_document_name=target_document_name,
            document_shortlist=shortlist,
            limit=candidate_pool_limit,
        )
        self._record_retrieval_stage("dense_mmr", dense_docs)

        lexical_docs = self._retrieve_lexical_docs(
            question,
            target_document_name=target_document_name,
            document_shortlist=shortlist,
            retrieval_intent=retrieval_intent,
            limit=lexical_limit,
        )
        self._record_retrieval_stage("lexical", lexical_docs)

        self._last_retrieval_dense_docs = list(dense_docs or [])
        self._last_retrieval_lexical_docs = list(lexical_docs or [])
        candidate_pool = self._merge_dense_lexical_candidates(
            dense_docs,
            lexical_docs,
            candidate_pool_limit=candidate_pool_limit,
            lexical_limit=lexical_limit,
        )
        self._record_retrieval_stage("candidate_pool", candidate_pool)
        return candidate_pool

    def _retrieve_dense_mmr_docs(
        self,
        question: str,
        *,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
        limit: int,
    ) -> list:
        if not question:
            return []

        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        filter_payload = {"document_name": shortlist[0]} if len(shortlist) == 1 else None
        fetch_k = max(
            int(self._get_retrieval_config_value("base_fetch_k", 60)),
            limit * 2,
        )
        lambda_mult = float(self._get_retrieval_config_value("base_lambda_mult", 0.2))
        docs = []

        vector_store = getattr(self, "vector_store", None)
        if vector_store is not None and hasattr(vector_store, "max_marginal_relevance_search"):
            search_kwargs = {
                "k": limit,
                "fetch_k": fetch_k,
                "lambda_mult": lambda_mult,
            }
            if filter_payload:
                search_kwargs["filter"] = filter_payload
            try:
                docs = vector_store.max_marginal_relevance_search(question, **search_kwargs)
            except TypeError:
                docs = vector_store.max_marginal_relevance_search(question, k=limit)
        elif getattr(self, "retriever", None) is not None:
            docs = self.retriever.invoke(question)

        if len(shortlist) > 1:
            allowed = set(shortlist)
            docs = [
                doc
                for doc in docs
                if str((getattr(doc, "metadata", {}) or {}).get("document_name") or "").strip() in allowed
            ]
        return list(docs or [])[:limit]

    def _retrieve_lexical_docs(
        self,
        question: str,
        *,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
        retrieval_intent: str | None = None,
        limit: int = 30,
    ) -> list:
        query_text = self._expand_query_for_lexical_search(question)
        query_terms = set(self._tokenize_search_text(query_text))
        query_phrases = self._collect_query_signal_phrases(query_text)
        query_dates = set(self._extract_normalized_full_dates(question))
        if not query_terms and not query_phrases and not query_dates:
            return []

        candidates: list[tuple[int, str, int, object]] = []
        for doc in self._get_retrieval_doc_pool(target_document_name, document_shortlist):
            score = self._score_lexical_retrieval_candidate(
                doc,
                query_terms=query_terms,
                query_phrases=query_phrases,
                query_dates=query_dates,
            )
            if score <= 0:
                continue
            metadata = getattr(doc, "metadata", {}) or {}
            candidates.append(
                (
                    score,
                    str(metadata.get("document_name") or ""),
                    int(metadata.get("chunk_order") or 0),
                    doc,
                )
            )

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [doc for _, _, _, doc in candidates[:limit]]

    def _score_lexical_retrieval_candidate(
        self,
        doc,
        *,
        query_terms: set[str],
        query_phrases: list[str],
        query_dates: set[str],
    ) -> int:
        metadata = getattr(doc, "metadata", {}) or {}
        text_parts = [
            getattr(doc, "page_content", "") or "",
            str(metadata.get("document_name") or ""),
            str(metadata.get("section_title") or metadata.get("sheet_name") or ""),
            str(metadata.get("search_text_normalized") or ""),
            " ".join(str(value) for value in list(metadata.get("entity_names") or [])),
            " ".join(str(value) for value in list(metadata.get("date_values") or [])),
            " ".join(str(value) for value in list(metadata.get("money_values") or [])),
            " ".join(str(value) for value in list(metadata.get("labeled_facts") or [])),
        ]
        combined_text = " ".join(part for part in text_parts if part)
        normalized_text = self._normalize_identifier(combined_text)
        if not normalized_text:
            return 0

        candidate_terms = set(normalized_text.split())
        exact_overlap = len(query_terms & candidate_terms)
        phrase_hits = sum(1 for phrase in query_phrases if phrase and phrase in normalized_text)
        date_hits = 0
        if query_dates:
            candidate_dates = set(self._extract_normalized_full_dates(combined_text))
            candidate_dates.update(str(value) for value in list(metadata.get("date_values") or []) if str(value).strip())
            date_hits = len(query_dates & candidate_dates)

        if exact_overlap <= 0 and phrase_hits <= 0 and date_hits <= 0:
            return 0

        chunk_kind = str(metadata.get("chunk_kind") or "text").strip()
        kind_bonus = {
            "section_detail": 18,
            "row_record": 14,
            "entity_index": 12,
            "people_index": 12,
            "list_block": 8,
            "section_overview": 6,
            "document_profile": 2,
            "summary": 2,
            "sheet_summary": 2,
        }.get(chunk_kind, 4)
        return exact_overlap * 12 + phrase_hits * 44 + date_hits * 72 + kind_bonus

    def _expand_query_for_lexical_search(self, question: str) -> str:
        parts = [str(question or "")]
        for normalized_date in self._extract_normalized_full_dates(question):
            year, month, day = normalized_date.split("-", 2)
            month_name = MONTH_NUMBER_TO_NAME.get(month, "")
            parts.extend(
                [
                    normalized_date,
                    f"{day}/{month}/{year}",
                    f"{int(day)} {month_name} {year}".strip(),
                    f"{int(day)} de {month_name} de {year}".strip(),
                    year,
                    month_name,
                ]
            )
        return " ".join(part for part in parts if part).strip()

    def _merge_unique_docs(self, *doc_groups) -> list:
        merged = []
        seen = set()
        for group in doc_groups:
            for doc in group or []:
                unique_key = self._doc_unique_key(doc)
                if unique_key in seen:
                    continue
                seen.add(unique_key)
                merged.append(doc)
        return merged

    def _doc_unique_key(self, doc) -> tuple:
        metadata = getattr(doc, "metadata", {}) or {}
        return (
            metadata.get("document_name"),
            metadata.get("chunk_kind"),
            metadata.get("chunk_order"),
            re.sub(r"\s+", " ", getattr(doc, "page_content", "") or "").strip()[:220],
        )

    def _merge_dense_lexical_candidates(
        self,
        dense_docs,
        lexical_docs,
        *,
        candidate_pool_limit: int,
        lexical_limit: int,
    ) -> list:
        limit = max(0, int(candidate_pool_limit or 0))
        if limit <= 0:
            return []

        lexical_quota = min(max(0, int(lexical_limit or 0)), limit)
        dense_quota = max(limit - lexical_quota, 0)
        dense_items = list(dense_docs or [])
        lexical_items = list(lexical_docs or [])
        merged = []
        seen = set()

        def add_from(group, quota: int | None = None) -> None:
            nonlocal merged, seen
            for doc in group:
                if len(merged) >= limit:
                    return
                if quota is not None and quota <= 0:
                    return
                unique_key = self._doc_unique_key(doc)
                if unique_key in seen:
                    continue
                seen.add(unique_key)
                merged.append(doc)
                if quota is not None:
                    quota -= 1

        add_from(dense_items, dense_quota)
        add_from(lexical_items, lexical_quota)
        add_from(dense_items)
        add_from(lexical_items)
        return merged[:limit]

    def _select_docs_for_context(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        candidates = list(docs or [])
        if not candidates:
            self._record_retrieval_stage("llm_selected", [])
            return []

        limit = int(self._get_retrieval_config_value("llm_selection_limit", 8))
        llm_selected_docs = self._select_docs_with_llm(
            resolved_question or "",
            candidates,
            limit=limit,
            target_document_name=target_document_name,
        )
        self._record_retrieval_stage("llm_selected", llm_selected_docs)
        return self._build_final_context_selection(
            resolved_question or "",
            candidates,
            llm_selected_docs,
            limit=limit,
            target_document_name=target_document_name,
        )

    def _select_docs_with_llm(
        self,
        question: str,
        candidates: list,
        *,
        limit: int,
        target_document_name: str | None = None,
    ) -> list:
        if not bool(self._get_retrieval_config_value("llm_selector_enabled", True)):
            return list(candidates or [])[:limit]
        if not getattr(self, "llm_client", None):
            return list(candidates or [])[:limit]

        payloads = self._build_llm_selector_candidate_payloads(candidates, question=question)
        id_to_doc = {str(payload["candidate_id"]): doc for payload, doc in zip(payloads, candidates)}
        prompt = self._build_llm_selector_prompt(
            question=question,
            candidate_payloads=payloads,
            limit=limit,
            target_document_name=target_document_name,
        )
        try:
            raw_response = self.llm_client.invoke(prompt)
        except Exception:
            return list(candidates or [])[:limit]

        selected_ids = self._parse_llm_selector_response(
            raw_response,
            valid_ids=list(id_to_doc),
            limit=limit,
        )
        if not selected_ids:
            return list(candidates or [])[:limit]

        selected = []
        seen = set()
        for candidate_id in selected_ids:
            if candidate_id in seen or candidate_id not in id_to_doc:
                continue
            seen.add(candidate_id)
            selected.append(id_to_doc[candidate_id])
            if len(selected) >= limit:
                break
        return selected or list(candidates or [])[:limit]

    def _build_final_context_selection(
        self,
        question: str,
        candidates: list,
        llm_selected_docs: list,
        *,
        limit: int,
        target_document_name: str | None = None,
    ) -> list:
        selected = []
        seen = set()

        def add(doc) -> None:
            if doc is None or len(selected) >= limit:
                return
            unique_key = self._doc_unique_key(doc)
            if unique_key in seen:
                return
            seen.add(unique_key)
            selected.append(doc)

        for doc in self._select_protected_context_docs(
            question,
            candidates,
            limit=limit,
            target_document_name=target_document_name,
        ):
            add(doc)
        for doc in llm_selected_docs or []:
            add(doc)
        for doc in candidates or []:
            add(doc)
        return selected[:limit]

    def _select_protected_context_docs(
        self,
        question: str,
        candidates: list,
        *,
        limit: int,
        target_document_name: str | None = None,
    ) -> list:
        candidate_keys = {self._doc_unique_key(doc) for doc in candidates or []}
        protected = []
        seen = set()
        protected_limit = max(1, min(limit, 4))

        def add(doc) -> None:
            if doc is None or len(protected) >= protected_limit:
                return
            unique_key = self._doc_unique_key(doc)
            if unique_key not in candidate_keys or unique_key in seen:
                return
            seen.add(unique_key)
            protected.append(doc)

        for doc in list(getattr(self, "_last_retrieval_dense_docs", []) or [])[:2]:
            add(doc)
        for doc in list(getattr(self, "_last_retrieval_lexical_docs", []) or [])[:2]:
            add(doc)

        scored_candidates = [
            (
                self._score_selector_candidate_signal(
                    doc,
                    question,
                    target_document_name=target_document_name,
                ),
                index,
                doc,
            )
            for index, doc in enumerate(candidates or [])
        ]
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))
        for score, _, doc in scored_candidates:
            if score < 50:
                continue
            add(doc)
        return protected

    def _score_selector_candidate_signal(
        self,
        doc,
        question: str,
        *,
        target_document_name: str | None = None,
    ) -> int:
        query_text = self._expand_query_for_lexical_search(question)
        query_terms = set(self._tokenize_search_text(query_text))
        query_phrases = self._collect_query_signal_phrases(query_text)
        query_dates = set(self._extract_normalized_full_dates(question))
        if not query_terms and not query_phrases and not query_dates:
            return 0

        score = self._score_lexical_retrieval_candidate(
            doc,
            query_terms=query_terms,
            query_phrases=query_phrases,
            query_dates=query_dates,
        )
        metadata = getattr(doc, "metadata", {}) or {}
        if target_document_name and str(metadata.get("document_name") or "").strip() == target_document_name:
            score += 20
        return score

    def _build_llm_selector_candidate_payloads(
        self,
        candidates: list,
        *,
        question: str = "",
    ) -> list[dict[str, object]]:
        payloads = []
        for doc in candidates or []:
            metadata = getattr(doc, "metadata", {}) or {}
            text = self._build_query_aware_selector_excerpt(
                getattr(doc, "page_content", "") or "",
                question,
            )
            candidate_id = self._resolve_selector_candidate_id(doc)
            payloads.append(
                {
                    "candidate_id": candidate_id,
                    "document_name": str(metadata.get("document_name") or "").strip(),
                    "chunk_kind": str(metadata.get("chunk_kind") or "text").strip(),
                    "chunk_order": metadata.get("chunk_order") if isinstance(metadata.get("chunk_order"), int) else None,
                    "section_title": str(metadata.get("section_title") or metadata.get("sheet_name") or "").strip(),
                    "text": text,
                }
            )
        return payloads

    def _build_query_aware_selector_excerpt(
        self,
        text: str,
        question: str,
        *,
        max_chars: int = 1200,
    ) -> str:
        compact_text = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(compact_text) <= max_chars:
            return compact_text

        signals = self._build_selector_query_signals(question)
        if not signals:
            return f"{compact_text[: max_chars - 3].rstrip()}..."

        raw_segments = re.split(r"(?<=[\.\?!;:])\s+|\n+", str(text or ""))
        scored_segments = []
        for index, segment in enumerate(raw_segments):
            compact_segment = re.sub(r"\s+", " ", segment).strip()
            if not compact_segment:
                continue
            normalized_segment = self._normalize_identifier(compact_segment)
            score = 0
            for signal in signals:
                if not signal:
                    continue
                if " " in signal and signal in normalized_segment:
                    score += 12
                elif signal in normalized_segment.split():
                    score += 3
                elif len(signal) >= 4 and signal in normalized_segment:
                    score += 2
            if score <= 0:
                continue
            scored_segments.append((score, index, compact_segment))

        if not scored_segments:
            return f"{compact_text[: max_chars - 3].rstrip()}..."

        selected_segments = []
        used_indexes = set()
        for _, index, segment in sorted(scored_segments, key=lambda item: (-item[0], item[1]))[:4]:
            if index in used_indexes:
                continue
            used_indexes.add(index)
            selected_segments.append(
                self._shorten_selector_segment_around_signal(segment, signals)
            )

        ordered = [
            segment
            for _, index, segment in sorted(
                (item for item in scored_segments if item[1] in used_indexes),
                key=lambda item: item[1],
            )
        ]
        if ordered:
            selected_segments = [
                self._shorten_selector_segment_around_signal(segment, signals)
                for segment in ordered
            ]

        excerpt = " [...] ".join(selected_segments)
        if len(excerpt) > max_chars:
            excerpt = f"{excerpt[: max_chars - 3].rstrip()}..."
        return excerpt or f"{compact_text[: max_chars - 3].rstrip()}..."

    def _build_selector_query_signals(self, question: str) -> list[str]:
        signals = []
        seen = set()
        normalized_question = self._normalize_identifier(question)
        raw_values = [
            *self._collect_query_signal_phrases(question),
            *self._tokenize_search_text(question),
            *self._extract_normalized_full_dates(question),
            *self._extract_date_candidates(question, limit=8),
            *self._extract_name_candidates(question, limit=8),
            *re.findall(r"\b[A-Z]{2,}(?:[-_/][A-Z0-9]+)*\b", question or ""),
            *re.findall(r"\b\d+(?:[.,]\d+)?\b", question or ""),
        ]
        for value in raw_values:
            normalized_value = self._normalize_identifier(value)
            if not normalized_value or normalized_value in seen:
                continue
            if len(normalized_value) < 2:
                continue
            if normalized_value in normalized_question or " " in normalized_value:
                seen.add(normalized_value)
                signals.append(normalized_value)
        return signals[:32]

    def _shorten_selector_segment_around_signal(
        self,
        segment: str,
        signals: list[str],
        *,
        window_chars: int = 520,
    ) -> str:
        compact_segment = re.sub(r"\s+", " ", segment).strip()
        if len(compact_segment) <= window_chars:
            return compact_segment

        normalized_segment = self._normalize_identifier(compact_segment)
        for signal in signals:
            if not signal:
                continue
            match_index = normalized_segment.find(signal)
            if match_index < 0:
                continue
            ratio = match_index / max(len(normalized_segment), 1)
            center = int(ratio * len(compact_segment))
            start = max(0, center - window_chars // 2)
            end = min(len(compact_segment), start + window_chars)
            start = max(0, end - window_chars)
            excerpt = compact_segment[start:end].strip()
            if start > 0:
                excerpt = f"...{excerpt}"
            if end < len(compact_segment):
                excerpt = f"{excerpt}..."
            return excerpt
        return f"{compact_segment[: window_chars - 3].rstrip()}..."

    def _resolve_selector_candidate_id(self, doc) -> str:
        if hasattr(self, "_get_retrieval_candidate_id"):
            return self._get_retrieval_candidate_id(doc)
        metadata = getattr(doc, "metadata", {}) or {}
        seed = "|".join(
            [
                str(metadata.get("document_name") or ""),
                str(metadata.get("chunk_kind") or ""),
                str(metadata.get("chunk_order") or ""),
                re.sub(r"\s+", " ", getattr(doc, "page_content", "") or "").strip()[:80],
            ]
        )
        return f"cand_{abs(hash(seed))}"

    def _build_llm_selector_prompt(
        self,
        *,
        question: str,
        candidate_payloads: list[dict[str, object]],
        limit: int,
        target_document_name: str | None = None,
    ) -> str:
        candidates_json = json.dumps(candidate_payloads, ensure_ascii=False, indent=2)
        return (
            "Voce seleciona evidencias para um sistema RAG.\n"
            "Use apenas os candidatos fornecidos. Nao responda a pergunta.\n"
            "Priorize recall: se um candidato talvez contenha a resposta, inclua-o.\n"
            "Use o limite disponivel quando varios candidatos forem plausiveis.\n"
            "Preserve trechos com nomes, datas, numeros, empresas, cargos, projetos ou siglas exatas da pergunta.\n"
            "Escolha evidencias diretas e tambem contexto forte que ajude a responder sem chute.\n"
            "Retorne somente JSON valido no formato:\n"
            '{"selected_candidate_ids":["cand_id_1"],"maybe_candidate_ids":["cand_id_2"]}\n\n'
            f"Limite maximo de IDs: {limit}\n"
            f"Documento explicitamente solicitado: {target_document_name or 'nenhum'}\n"
            f"Pergunta: {question}\n\n"
            f"Candidatos:\n{candidates_json}"
        )

    def _parse_llm_selector_response(
        self,
        raw_response: str | None,
        *,
        valid_ids: list[str],
        limit: int,
    ) -> list[str]:
        text = str(raw_response or "").strip()
        valid_set = set(valid_ids)
        if not text or not valid_set:
            return []

        candidates = [
            re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip(),
        ]
        object_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if object_match:
            candidates.append(object_match.group(0).strip())
        array_match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if array_match:
            candidates.append(array_match.group(0).strip())

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except (TypeError, json.JSONDecodeError):
                continue
            selected = self._extract_selector_ids_from_payload(payload)
            normalized = [candidate_id for candidate_id in selected if candidate_id in valid_set]
            if normalized:
                return list(dict.fromkeys(normalized))[:limit]

        fallback_ids = [candidate_id for candidate_id in valid_ids if candidate_id in text]
        return list(dict.fromkeys(fallback_ids))[:limit]

    def _extract_selector_ids_from_payload(self, payload: object) -> list[str]:
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = []
            for key in (
                "selected_candidate_ids",
                "selected_ids",
                "candidate_ids",
                "ids",
                "selection",
                "selected",
                "maybe_candidate_ids",
                "maybe_ids",
                "maybe",
            ):
                value = payload.get(key)
                if value:
                    items.extend(value if isinstance(value, list) else [value])
        else:
            items = []

        selected = []
        for item in items:
            if isinstance(item, dict):
                item = item.get("candidate_id") or item.get("id")
            compact = str(item or "").strip()
            if compact:
                selected.append(compact)
        return selected

    def _score_retrieval_evidence(
        self,
        resolved_question: str,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> float:
        selected_docs = list(docs or [])
        if not selected_docs:
            return 0.0

        query_terms = set(self._tokenize_search_text(resolved_question))
        context_text = " ".join(getattr(doc, "page_content", "") or "" for doc in selected_docs)
        context_terms = set(self._tokenize_search_text(context_text))
        overlap_ratio = len(query_terms & context_terms) / max(len(query_terms), 1)
        score = 0.34 + min(0.44, overlap_ratio * 0.60)
        if self._extract_normalized_full_dates(resolved_question) and self._extract_normalized_full_dates(context_text):
            score += 0.10
        if target_document_name and any(
            str((getattr(doc, "metadata", {}) or {}).get("document_name") or "").strip() == target_document_name
            for doc in selected_docs
        ):
            score += 0.08
        if len(selected_docs) >= 2:
            score += 0.04
        return round(min(score, 1.0), 4)

    def _prioritize_retrieved_docs(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        return list(docs or [])

    def _build_abstain_answer(self) -> str:
        return (
            "Nao ha evidencias suficientes nos trechos recuperados para responder com seguranca. "
            "Informe um arquivo, data ou trecho mais especifico."
        )

    def _build_document_refinement_answer(
        self,
        matched_documents: list[str],
        invalid_selection: int | None = None,
    ) -> str:
        document_lines = "\n".join(
            f"{index}. {document_name}" for index, document_name in enumerate(matched_documents, start=1)
        )
        if invalid_selection is None:
            intro = "Identifiquei mais de um arquivo citado e nao vou misturar evidencias."
        else:
            intro = f"O numero {invalid_selection} nao corresponde a nenhum arquivo desta lista."
        return (
            f"{intro}\n\n"
            f"Arquivos encontrados:\n{document_lines}\n\n"
            "Responda apenas com o numero do arquivo na proxima mensagem, por exemplo: 1, 2 ou 3."
        )
