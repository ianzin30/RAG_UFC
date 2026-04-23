"""Core retrieval and ranking helpers."""
# Simple: Search and rank most relevant document sections

import re


# Este mixin recupera, pontua e seleciona os trechos usados na resposta final.
class RetrievalCoreMixin:
    def _get_retrieval_config_value(self, key: str, default):
        retrieval_config = getattr(self, "retrieval_config", None)
        return getattr(retrieval_config, key, default)

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

    def _is_explicit_evidence_intent(
        self,
        retrieval_intent: str | None,
        *,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> bool:
        if retrieval_intent in {"specific_fact", "entity_lookup"}:
            return True
        if retrieval_intent != "document_expansion":
            return False
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        return bool(target_document_name or len(shortlist) == 1)

    def _build_retrieval_query_profile(self, question: str) -> dict[str, object]:
        raw_text = str(question or "")
        normalized_text = self._normalize_identifier(raw_text)
        query_terms = set(self._tokenize_search_text(raw_text))
        query_phrases = self._collect_query_signal_phrases(raw_text)
        explicit_phrases = [
            phrase
            for phrase in list(self._extract_explicit_query_phrases(raw_text) or [])
            if self._normalize_identifier(phrase)
        ]
        name_terms = set()
        for name in self._extract_name_candidates(raw_text, limit=8):
            for token in self._tokenize_search_text(name):
                if token:
                    name_terms.add(token)
        acronyms = {
            self._normalize_identifier(match)
            for match in re.findall(r"\b[A-Z]{2,}[A-Z0-9/-]{0,10}\b", raw_text or "")
            if self._normalize_identifier(match)
        }
        year_terms = {term for term in query_terms if re.fullmatch(r"\d{4}", term)}
        rare_terms = {
            term
            for term in query_terms
            if len(term) >= 4 and self._is_discriminative_query_term(term)
        }
        normalized_tokens = set(normalized_text.split())
        return {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "query_terms": query_terms,
            "query_phrases": query_phrases,
            "explicit_phrases": explicit_phrases,
            "name_terms": name_terms,
            "acronyms": acronyms,
            "year_terms": year_terms,
            "rare_terms": rare_terms,
            "company_question": (
                "empresa" in normalized_text
                or any(marker in normalized_text for marker in ("parceira", "parceria", "convenio"))
            ),
            "person_question": bool(
                normalized_tokens
                & {"quem", "chefe", "coordenador", "coordenadora", "professor", "professora", "servidor", "subchefe"}
            ),
        }

    def _build_doc_evidence_profile(
        self,
        doc,
        query_profile: dict[str, object] | None,
    ) -> dict[str, object]:
        metadata = getattr(doc, "metadata", {}) or {}
        raw_text = getattr(doc, "page_content", "") or ""
        normalized_page = self._normalize_identifier(raw_text)
        normalized_search_text = str(metadata.get("search_text_normalized") or normalized_page).strip()
        entity_values = [
            str(value).strip()
            for value in list(metadata.get("entity_names") or [])
            if str(value).strip()
        ]
        date_values = [
            str(value).strip()
            for value in list(metadata.get("date_values") or [])
            if str(value).strip()
        ]
        fact_values = [
            str(value).strip()
            for value in list(
                metadata.get("labeled_facts")
                or metadata.get("fact_lines")
                or []
            )
            if str(value).strip()
        ]
        metadata_text = self._normalize_identifier(" ".join([*entity_values, *date_values, *fact_values]))
        combined_text = " ".join(part for part in [normalized_search_text, metadata_text] if part).strip()
        profile = query_profile or {}
        query_terms = set(profile.get("query_terms") or set())
        query_phrases = list(profile.get("query_phrases") or [])
        explicit_phrases = list(profile.get("explicit_phrases") or [])
        exact_overlap = sum(1 for term in query_terms if term in combined_text)
        phrase_hits = [phrase for phrase in query_phrases if phrase in combined_text]
        quoted_phrase_hits = [phrase for phrase in explicit_phrases if phrase in combined_text]
        name_overlap = sum(
            1
            for term in set(profile.get("name_terms") or set())
            if term in combined_text
        )
        acronym_overlap = sum(
            1
            for term in set(profile.get("acronyms") or set())
            if term in combined_text
        )
        date_overlap = sum(
            1
            for term in set(profile.get("year_terms") or set())
            if term in combined_text
        )
        role_overlap = sum(
            1
            for term in {"chefe", "coordenador", "coordenadora", "professor", "professora", "servidor", "subchefe"}
            if term in combined_text
        )
        company_cue_hits = sum(
            1
            for cue in ("empresa", "parceria", "parceira", "convenio", "convenio entre", "empresa junior")
            if cue in combined_text
        )
        rare_overlap = sum(
            1
            for term in set(profile.get("rare_terms") or set())
            if term in combined_text
        )
        detail_specificity = (
            len(phrase_hits[:4]) * 32
            + len(quoted_phrase_hits[:3]) * 28
            + min(name_overlap, 4) * 16
            + min(acronym_overlap, 3) * 16
            + min(date_overlap, 3) * 12
            + min(role_overlap, 3) * 18
            + min(company_cue_hits, 3) * 18
            + min(rare_overlap, 5) * 10
        )
        strong_explicit = bool(
            phrase_hits
            or quoted_phrase_hits
            or name_overlap >= 2
            or (acronym_overlap and exact_overlap >= 2)
            or (date_overlap and exact_overlap >= 2)
            or (profile.get("company_question") and company_cue_hits >= 2 and (phrase_hits or rare_overlap >= 1))
            or (profile.get("person_question") and role_overlap >= 1 and name_overlap >= 1)
            or (rare_overlap >= 2 and exact_overlap >= 3)
        )
        return {
            "combined_text": combined_text,
            "exact_overlap": exact_overlap,
            "phrase_hits": phrase_hits,
            "quoted_phrase_hits": quoted_phrase_hits,
            "name_overlap": name_overlap,
            "acronym_overlap": acronym_overlap,
            "date_overlap": date_overlap,
            "role_overlap": role_overlap,
            "company_cue_hits": company_cue_hits,
            "rare_overlap": rare_overlap,
            "detail_specificity": detail_specificity,
            "strong_explicit": strong_explicit,
        }

    # Esta etapa resume a forca dos spans alinhados para perguntas factuais.
    def _build_factoid_span_summary(
        self,
        doc,
        *,
        resolved_question: str,
        retrieval_intent: str | None,
    ) -> dict[str, object]:
        return self._build_doc_factoid_evidence_summary(
            doc,
            resolved_question=resolved_question,
            retrieval_intent=retrieval_intent,
        )

    # Esta pontuacao lexical agora combina termo, frase e suporte por span.
    def _build_lexical_candidate_payload(
        self,
        doc,
        *,
        question: str,
        query_terms: list[str],
        query_fragments: set[str],
        query_profile: dict[str, object],
        explicit_intent: bool,
        target_document_name: str | None,
        document_shortlist: list[str] | None,
        retrieval_intent: str | None,
    ) -> dict[str, object] | None:
        search_text = doc.metadata.get("search_text_normalized") or self._normalize_identifier(doc.page_content)
        evidence = self._build_doc_evidence_profile(doc, query_profile)
        overlap = sum(1 for term in query_terms if term in search_text)
        fragment_overlap = sum(1 for fragment in query_fragments if fragment in search_text)
        phrase_hits = list(evidence["phrase_hits"])
        quoted_phrase_hits = list(evidence["quoted_phrase_hits"])
        span_summary = self._build_factoid_span_summary(
            doc,
            resolved_question=question,
            retrieval_intent=retrieval_intent,
        )
        top_span_score = int(span_summary.get("top_span_score") or 0)
        aligned_span_count = int(span_summary.get("aligned_span_count") or 0)
        if overlap <= 0 and fragment_overlap <= 0 and not phrase_hits and not quoted_phrase_hits and top_span_score <= 0:
            return None

        score = (
            overlap * 24
            + fragment_overlap * 6
            + len(phrase_hits[:4]) * 72
            + len(quoted_phrase_hits[:3]) * 44
        )
        document_name = str(doc.metadata.get("document_name") or "").strip()
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        if target_document_name and document_name == target_document_name:
            score += 30
        if shortlist and document_name in shortlist:
            score += max(12, 28 - shortlist.index(document_name) * 6)

        chunk_kind = str(doc.metadata.get("chunk_kind") or "text").strip()
        if chunk_kind in {"entity_index", "list_block"}:
            score += 12 if not explicit_intent else 2
        if chunk_kind == "section_overview":
            score += 8 if not explicit_intent else 1

        if explicit_intent and chunk_kind == "section_detail":
            score += 18
            score += min(112, int(evidence["detail_specificity"]))
            score += min(144, top_span_score)
            score += min(40, aligned_span_count * 10)
            score += int(evidence["company_cue_hits"]) * 24
            score += int(evidence["role_overlap"]) * 18
            if evidence["strong_explicit"]:
                score += 24
        elif explicit_intent and chunk_kind in {
            "document_profile",
            "section_overview",
            "entity_index",
            "list_block",
        }:
            if evidence["strong_explicit"]:
                score += min(42, int(evidence["detail_specificity"]) // 2)
                score += min(64, top_span_score // 2)
            elif fragment_overlap > overlap and not phrase_hits and not quoted_phrase_hits:
                score -= 16
            if query_profile.get("company_question") and not int(evidence["company_cue_hits"]):
                score -= 18
            if top_span_score <= 0:
                score -= 12

        chunk_order = doc.metadata.get("chunk_order")
        if isinstance(chunk_order, int):
            score += max(0, 8 - min(chunk_order, 8))

        return {
            "score": score,
            "document_name": document_name,
            "chunk_order": int(chunk_order or 0),
            "doc": doc,
            "chunk_kind": chunk_kind,
            "fragment_only": (
                fragment_overlap > 0
                and overlap < 2
                and not phrase_hits
                and not quoted_phrase_hits
                and not evidence["strong_explicit"]
                and top_span_score <= 0
            ),
            "has_full_detail_hit": (
                chunk_kind == "section_detail"
                and (phrase_hits or quoted_phrase_hits or evidence["strong_explicit"] or top_span_score >= 72)
            ),
        }

    # Esta busca tenta primeiro o caminho estruturado das planilhas e depois o vetor store geral.
    def _retrieve_docs(
        self,
        question: str,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        document_shortlist: list[str] | None = None,
    ):
        normalized_shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        primary_document_name = target_document_name
        if primary_document_name is None and normalized_shortlist and retrieval_intent in {"specific_fact", "entity_lookup"}:
            primary_document_name = normalized_shortlist[0]

        if self._is_spreadsheet_document_name(primary_document_name):
            structured_docs = self._retrieve_spreadsheet_chunks(question, primary_document_name)
            if structured_docs:
                self._record_retrieval_stage("merged", structured_docs)
                return structured_docs

        if primary_document_name:
            docs = self._retrieve_focused_docs_for_document(
                question,
                primary_document_name,
                retrieval_intent=retrieval_intent,
            )
            if docs:
                self._record_retrieval_stage("merged", docs)
                return docs

        if normalized_shortlist:
            shortlist_docs = []
            shortlist_limit = 3 if self._is_coverage_oriented_intent(retrieval_intent) else 2
            for document_name in normalized_shortlist[:shortlist_limit]:
                shortlist_docs.append(
                    self._retrieve_focused_docs_for_document(
                        question,
                        document_name,
                        retrieval_intent=retrieval_intent,
                    )
                )
            docs = self._merge_unique_docs(*shortlist_docs)
            self._record_retrieval_stage("merged", docs)
            return docs

        dense_docs = self.retriever.invoke(question)
        self._record_retrieval_stage("dense_mmr", dense_docs)
        lexical_docs = self._retrieve_lexical_docs(
            question,
            target_document_name=primary_document_name,
            document_shortlist=normalized_shortlist,
            retrieval_intent=retrieval_intent,
            limit=int(self._get_retrieval_config_value("lexical_limit", 12)),
        )
        self._record_retrieval_stage("lexical", lexical_docs)
        merged_docs = self._merge_unique_docs(dense_docs, lexical_docs)
        self._record_retrieval_stage("merged", merged_docs)
        return merged_docs

    def _retrieve_focused_docs_for_document(
        self,
        question: str,
        document_name: str,
        *,
        retrieval_intent: str | None = None,
    ) -> list:
        focused_question = f"{document_name} {question}".strip()
        focused_search_k = int(self._get_retrieval_config_value("focused_search_k", 6))
        focused_fetch_k = int(self._get_retrieval_config_value("focused_fetch_k", 100))
        focused_lambda_mult = float(self._get_retrieval_config_value("focused_lambda_mult", 0.2))
        lexical_limit = int(self._get_retrieval_config_value("lexical_limit", 12))
        coverage_limit = int(self._get_retrieval_config_value("coverage_limit", 10))
        docs = self.vector_store.max_marginal_relevance_search(
            focused_question,
            k=focused_search_k,
            fetch_k=focused_fetch_k,
            lambda_mult=focused_lambda_mult,
            filter={"document_name": document_name},
        )
        self._record_retrieval_stage("dense_mmr", docs)
        fallback_docs = self.vector_store.similarity_search(
            document_name,
            k=focused_search_k,
            fetch_k=focused_fetch_k,
            filter={"document_name": document_name},
        )
        self._record_retrieval_stage("similarity_fallback", fallback_docs)
        lexical_docs = self._retrieve_lexical_docs(
            question,
            target_document_name=document_name,
            document_shortlist=[document_name],
            retrieval_intent=retrieval_intent,
            limit=lexical_limit,
        )
        self._record_retrieval_stage("lexical", lexical_docs)
        docs = self._merge_unique_docs(docs, fallback_docs, lexical_docs)
        if self._is_coverage_oriented_intent(retrieval_intent):
            coverage_docs = self._retrieve_document_coverage_docs(
                question,
                target_document_name=document_name,
                retrieval_intent=retrieval_intent,
                limit=coverage_limit,
            )
            self._record_retrieval_stage("coverage", coverage_docs)
            docs = self._merge_unique_docs(
                docs,
                coverage_docs,
            )
        return docs

    # Esta busca lexical complementa o embedding com termos exatos e metadados estruturados.
    def _retrieve_lexical_docs(
        self,
        question: str,
        *,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
        retrieval_intent: str | None = None,
        limit: int = 10,
    ) -> list:
        query_terms = self._tokenize_search_text(question)
        if not query_terms:
            return []

        query_fragments = self._build_query_fragments(query_terms)
        query_profile = self._build_retrieval_query_profile(question)
        explicit_intent = self._is_explicit_evidence_intent(
            retrieval_intent,
            target_document_name=target_document_name,
            document_shortlist=document_shortlist,
        )
        candidates = []
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        for doc in self._get_retrieval_doc_pool(target_document_name, shortlist):
            candidate = self._build_lexical_candidate_payload(
                doc,
                question=question,
                query_terms=query_terms,
                query_fragments=query_fragments,
                query_profile=query_profile,
                explicit_intent=explicit_intent,
                target_document_name=target_document_name,
                document_shortlist=shortlist,
                retrieval_intent=retrieval_intent,
            )
            if candidate is None:
                continue
            candidates.append(candidate)

        if any(candidate["has_full_detail_hit"] for candidate in candidates):
            for candidate in candidates:
                if candidate["chunk_kind"] != "section_detail" and candidate["fragment_only"]:
                    candidate["score"] -= 28

        candidates.sort(
            key=lambda item: (-int(item["score"]), str(item["document_name"]), int(item["chunk_order"]))
        )
        return [candidate["doc"] for candidate in candidates[:limit]]

    # Esta selecao amplia a cobertura do documento escolhendo secoes diferentes do mesmo arquivo.
    def _retrieve_document_coverage_docs(
        self,
        question: str,
        *,
        target_document_name: str,
        retrieval_intent: str | None = None,
        limit: int = 10,
    ) -> list:
        pool = self._get_retrieval_doc_pool(target_document_name)
        if not pool:
            return []

        ranked_docs = self._prioritize_retrieved_docs(
            pool,
            target_document_name=target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=question,
        )
        preferred_kinds = self._get_coverage_preferred_kinds(retrieval_intent)
        selected = []
        seen_doc_ids = set()
        seen_groups = set()

        for kind in preferred_kinds:
            for doc in ranked_docs:
                if id(doc) in seen_doc_ids or str(doc.metadata.get("chunk_kind") or "").strip() != kind:
                    continue
                selected.append(doc)
                seen_doc_ids.add(id(doc))
                seen_groups.add(self._build_coverage_group_key(doc))
                break

        for doc in ranked_docs:
            if id(doc) in seen_doc_ids:
                continue
            if self._looks_like_noisy_source(doc.page_content or "") and len(selected) >= 3:
                continue
            if retrieval_intent == "summary" and self._should_skip_summary_doc(doc):
                continue

            group_key = self._build_coverage_group_key(doc)
            chunk_kind = str(doc.metadata.get("chunk_kind") or "").strip()
            if group_key in seen_groups and chunk_kind not in {"entity_index", "list_block"} and len(selected) >= 4:
                continue
            selected.append(doc)
            seen_doc_ids.add(id(doc))
            seen_groups.add(group_key)
            if len(selected) >= limit:
                break
        return selected[:limit]

    def _get_coverage_preferred_kinds(self, retrieval_intent: str | None) -> tuple[str, ...]:
        if retrieval_intent == "summary":
            return ("document_profile", "section_overview", "section_detail")
        if retrieval_intent == "list_extraction":
            return ("entity_index", "list_block", "section_overview", "section_detail")
        return (
            "document_profile",
            "section_overview",
            "entity_index",
            "list_block",
            "section_detail",
        )

    # Este agrupamento evita gastar todo o contexto em muitos trechos da mesma secao.
    def _build_coverage_group_key(self, doc) -> str:
        metadata = doc.metadata or {}
        section_key = str(metadata.get("section_key") or "").strip()
        if section_key:
            return section_key
        chunk_order = metadata.get("chunk_order")
        if isinstance(chunk_order, int):
            return f"order-{chunk_order // 2}"
        return f"kind-{metadata.get('chunk_kind') or 'text'}"

    # Este helper filtra o docstore local antes de aplicar novas heuristicas de busca.
    def _get_retrieval_doc_pool(
        self,
        target_document_name: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        docs = list(self._get_vector_store_documents())
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        if shortlist:
            shortlist_set = set(shortlist)
            return [
                doc
                for doc in docs
                if str(doc.metadata.get("document_name") or "").strip() in shortlist_set
            ]
        if not target_document_name:
            return docs
        return [doc for doc in docs if str(doc.metadata.get("document_name") or "").strip() == target_document_name]

    # Esta pontuacao mede se a evidencia recuperada sustenta uma resposta confiavel.
    def _score_retrieval_evidence(
        self,
        resolved_question: str,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> float:
        if not docs:
            return 0.0

        query_terms = self._tokenize_search_text(resolved_question)
        if not query_terms:
            return 0.0

        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        best_score = 0.0
        document_hits: dict[str, int] = {}
        for doc in docs[:6]:
            search_text = doc.metadata.get("search_text_normalized")
            if not search_text:
                search_text = self._normalize_identifier(doc.page_content)

            overlap = sum(1 for term in query_terms if term in search_text)
            lexical_score = overlap / max(len(query_terms), 1)
            score = lexical_score
            span_summary = self._build_factoid_span_summary(
                doc,
                resolved_question=resolved_question,
                retrieval_intent=retrieval_intent,
            )
            score += min(0.22, float(span_summary.get("top_span_score") or 0) / 500.0)

            document_name = (doc.metadata.get("document_name") or "").strip()
            if document_name:
                document_hits[document_name] = document_hits.get(document_name, 0) + 1
            if target_document_name and document_name and document_name == target_document_name:
                score += 0.18
            elif shortlist and document_name in shortlist:
                score += max(0.04, 0.12 - shortlist.index(document_name) * 0.03)
            if doc.metadata.get("chunk_kind"):
                score += 0.05
            if any(char.isdigit() for char in resolved_question) and any(char.isdigit() for char in doc.page_content):
                score += 0.05

            best_score = max(best_score, min(score, 1.0))

        if document_hits:
            dominant_hits = max(document_hits.values())
            dominant_ratio = dominant_hits / max(sum(document_hits.values()), 1)
            if target_document_name:
                target_hits = document_hits.get(target_document_name, 0)
                if target_hits:
                    best_score += 0.14 * (target_hits / max(sum(document_hits.values()), 1))
                else:
                    best_score -= 0.12
            elif retrieval_intent in {"specific_fact", "entity_lookup"}:
                if len(document_hits) == 1:
                    best_score += 0.12
                else:
                    best_score -= 0.18 * max(0.0, 0.65 - dominant_ratio)
            elif shortlist and dominant_ratio >= 0.55:
                best_score += 0.06
        return round(best_score, 4)

    # Esta fusao evita repetir o mesmo trecho quando juntamos estrategias diferentes de busca.
    def _merge_unique_docs(self, *doc_groups) -> list:
        merged = []
        seen = set()
        for group in doc_groups:
            for doc in group or []:
                unique_key = (
                    doc.metadata.get("document_name"),
                    doc.metadata.get("chunk_kind"),
                    re.sub(r"\s+", " ", doc.page_content or "").strip()[:160],
                )
                if unique_key in seen:
                    continue
                seen.add(unique_key)
                merged.append(doc)
        return merged

    # Esta ordenacao reaplica o ranking final ja considerando intencao e documento-alvo.
    def _prioritize_retrieved_docs(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        ranked_docs = []
        for doc in docs or []:
            ranked_docs.append(
                (
                    self._score_source_priority(
                        doc,
                        target_document_name,
                        retrieval_intent=retrieval_intent,
                        resolved_question=resolved_question,
                        document_shortlist=document_shortlist,
                    ),
                    doc,
                )
            )
        ranked_docs.sort(key=lambda item: (-item[0], str(item[1].metadata.get("document_name") or "")))
        return [doc for _, doc in ranked_docs]

    # Esta funcao concentra as heuristicas que promovem ou penalizam cada fonte.
    def _score_source_priority(
        self,
        doc,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> int:
        score, _ = self._score_source_priority_details(
            doc,
            target_document_name=target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
        )
        return score

    def _build_priority_component_seed(
        self,
        *,
        doc,
        target_document_name: str | None,
        document_shortlist: list[str] | None,
    ) -> tuple[dict[str, int], dict[str, object]]:
        metadata = doc.metadata or {}
        document_name = str(metadata.get("document_name") or "").strip()
        chunk_kind = str(metadata.get("chunk_kind") or "text").strip()
        page_content = re.sub(r"\s+", " ", doc.page_content or "").strip()
        normalized = self._normalize_identifier(page_content)
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        chunk_order = metadata.get("chunk_order")

        components = {
            "target_bonus": 0,
            "base_kind_score": 0,
            "structure_bonus": 0,
            "chunk_order_bonus": 0,
            "noise_penalty": 0,
            "length_penalty": 0,
            "exact_overlap_bonus": 0,
            "phrase_hit_bonus": 0,
            "detail_specificity_bonus": 0,
            "span_support_bonus": 0,
            "intent_bonus": 0,
        }
        if target_document_name and document_name == target_document_name:
            components["target_bonus"] += 120
        elif shortlist and document_name in shortlist:
            components["target_bonus"] += max(36, 82 - shortlist.index(document_name) * 18)
        elif shortlist:
            components["target_bonus"] -= 48

        kind_scores = {
            "document_profile": 90,
            "section_overview": 82,
            "entity_index": 76,
            "list_block": 70,
            "summary": 75,
            "sheet_summary": 65,
            "people_index": 55,
            "text": 45,
            "section_detail": 45,
            "row_record": 25,
            "column_profile": 20,
        }
        components["base_kind_score"] += kind_scores.get(chunk_kind, 30)

        if any(
            marker in normalized
            for marker in (
                "descricao inicial",
                "ata da reuniao",
                "realizada em",
                "projeto",
                "resumo da secao",
                "pessoas ou entidades",
                "lista ou enumeracao detectada",
            )
        ):
            components["structure_bonus"] += 14
        if isinstance(chunk_order, int):
            components["chunk_order_bonus"] += max(0, 12 - min(chunk_order, 12))
        if self._looks_like_noisy_source(page_content):
            components["noise_penalty"] -= 50
        if len(page_content) < 40:
            components["length_penalty"] -= 20

        return components, {
            "metadata": metadata,
            "document_name": document_name,
            "chunk_kind": chunk_kind,
            "page_content": page_content,
            "normalized": normalized,
            "shortlist": shortlist,
            "chunk_order": chunk_order,
        }

    def _apply_intent_priority_components(
        self,
        components: dict[str, int],
        *,
        retrieval_intent: str | None,
        chunk_kind: str,
        page_content: str,
        normalized: str,
        chunk_order,
        metadata: dict[str, object],
        evidence: dict[str, object],
        query_terms: list[str],
        phrase_hits: list[str],
    ) -> None:
        if retrieval_intent == "summary":
            if chunk_kind == "document_profile":
                components["intent_bonus"] += 120
            if chunk_kind == "section_overview":
                components["intent_bonus"] += 75
            if chunk_kind == "section_detail":
                components["intent_bonus"] += 28
            if chunk_kind in {"entity_index", "list_block"}:
                components["intent_bonus"] -= 38
            if isinstance(chunk_order, int):
                if chunk_order <= 2:
                    components["intent_bonus"] += 45 - chunk_order * 10
                elif chunk_order >= 10:
                    components["intent_bonus"] -= 20
            if any(marker in normalized for marker in ("perfil do documento", "descricao inicial", "realizada em")):
                components["intent_bonus"] += 35
            if self._looks_numeric_heavy_source(page_content):
                components["intent_bonus"] -= 28
            if metadata.get("section_is_header_metadata") and chunk_kind != "document_profile":
                components["intent_bonus"] -= 36
            return

        if retrieval_intent == "document_expansion":
            if chunk_kind == "document_profile":
                components["intent_bonus"] += 90
            if chunk_kind == "section_overview":
                components["intent_bonus"] += 70
            if chunk_kind in {"entity_index", "list_block"}:
                components["intent_bonus"] += 55
            if metadata.get("section_title"):
                components["intent_bonus"] += 16
            return

        if retrieval_intent == "list_extraction":
            components["intent_bonus"] += self._count_name_like_mentions(page_content) * 6
            if chunk_kind in {"entity_index", "list_block"}:
                components["intent_bonus"] += 55
            if any(marker in normalized for marker in ("titular", "suplente", "representante", "professor", "professora")):
                components["intent_bonus"] += 18
            return

        if retrieval_intent == "entity_lookup":
            components["intent_bonus"] += self._count_name_like_mentions(page_content) * 5
            if chunk_kind == "entity_index":
                components["intent_bonus"] += 48
            if any(marker in normalized for marker in ("coorden", "respons", "autor", "presidente", "chefe", "professor")):
                components["intent_bonus"] += 20
            if query_terms:
                components["exact_overlap_bonus"] += int(evidence["exact_overlap"]) * 8
                components["phrase_hit_bonus"] += len(list(evidence["phrase_hits"])[:3]) * 28
                if chunk_kind == "section_detail" and phrase_hits:
                    components["detail_specificity_bonus"] += 18
            return

        if retrieval_intent == "specific_fact" and query_terms:
            components["exact_overlap_bonus"] += int(evidence["exact_overlap"]) * 10
            components["phrase_hit_bonus"] += len(list(evidence["phrase_hits"])[:4]) * 42
            if chunk_kind == "section_detail":
                components["detail_specificity_bonus"] += 28 if phrase_hits else 14
            elif chunk_kind == "entity_index":
                components["intent_bonus"] += 12 if phrase_hits else -26
            elif chunk_kind in {"section_overview", "document_profile"} and not phrase_hits and evidence["exact_overlap"] < 3:
                components["intent_bonus"] -= 16

    def _apply_explicit_factoid_priority_components(
        self,
        components: dict[str, int],
        *,
        chunk_kind: str,
        evidence: dict[str, object],
        span_summary: dict[str, object],
        query_profile: dict[str, object],
    ) -> None:
        top_span_score = int(span_summary.get("top_span_score") or 0)
        aligned_span_count = int(span_summary.get("aligned_span_count") or 0)
        components["phrase_hit_bonus"] += len(list(evidence["quoted_phrase_hits"])[:3]) * 24
        if chunk_kind == "section_detail":
            components["detail_specificity_bonus"] += min(160, int(evidence["detail_specificity"]))
            components["detail_specificity_bonus"] += int(evidence["company_cue_hits"]) * 30
            components["detail_specificity_bonus"] += int(evidence["role_overlap"]) * 20
            if evidence["strong_explicit"]:
                components["detail_specificity_bonus"] += 42
            components["span_support_bonus"] += min(160, top_span_score)
            components["span_support_bonus"] += min(36, aligned_span_count * 9)
        elif evidence["strong_explicit"]:
            components["detail_specificity_bonus"] += min(64, int(evidence["detail_specificity"]) // 2)
            components["span_support_bonus"] += min(72, top_span_score // 2)
        elif chunk_kind in {"document_profile", "section_overview", "entity_index", "list_block"}:
            components["detail_specificity_bonus"] -= 22
            if query_profile.get("company_question") and not int(evidence["company_cue_hits"]):
                components["detail_specificity_bonus"] -= 18
            if top_span_score <= 0:
                components["span_support_bonus"] -= 16

    def _score_source_priority_details(
        self,
        doc,
        *,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> tuple[int, dict[str, int]]:
        components, context = self._build_priority_component_seed(
            doc=doc,
            target_document_name=target_document_name,
            document_shortlist=document_shortlist,
        )
        metadata = context["metadata"]
        chunk_kind = str(context["chunk_kind"])
        page_content = str(context["page_content"])
        normalized = str(context["normalized"])
        chunk_order = context["chunk_order"]
        query_terms = self._tokenize_search_text(resolved_question or "")
        query_profile = self._build_retrieval_query_profile(resolved_question or "")
        evidence = self._build_doc_evidence_profile(doc, query_profile)
        phrase_hits = list(evidence["phrase_hits"])
        span_summary = self._build_factoid_span_summary(
            doc,
            resolved_question=resolved_question or "",
            retrieval_intent=retrieval_intent,
        )
        explicit_intent = self._is_explicit_evidence_intent(
            retrieval_intent,
            target_document_name=target_document_name,
            document_shortlist=document_shortlist,
        )
        if query_terms:
            components["exact_overlap_bonus"] += int(evidence["exact_overlap"]) * 8

        self._apply_intent_priority_components(
            components,
            retrieval_intent=retrieval_intent,
            chunk_kind=chunk_kind,
            page_content=page_content,
            normalized=normalized,
            chunk_order=chunk_order,
            metadata=metadata,
            evidence=evidence,
            query_terms=query_terms,
            phrase_hits=phrase_hits,
        )

        if explicit_intent and query_terms:
            self._apply_explicit_factoid_priority_components(
                components,
                chunk_kind=chunk_kind,
                evidence=evidence,
                span_summary=span_summary,
                query_profile=query_profile,
            )

        score = sum(int(value) for value in components.values())
        return score, components

    def _ensure_ranked_doc_in_selection(
        self,
        selected_docs,
        required_doc,
        *,
        ranked_docs,
        limit: int,
    ) -> list:
        updated = list(selected_docs or [])
        if required_doc is None:
            return updated[:limit]
        if any(id(doc) == id(required_doc) for doc in updated):
            return updated[:limit]

        if len(updated) < limit:
            updated.append(required_doc)
        else:
            replace_index = None
            for index in range(len(updated) - 1, -1, -1):
                candidate = updated[index]
                candidate_kind = str((candidate.metadata or {}).get("chunk_kind") or "text").strip()
                if candidate_kind in {"document_profile", "section_overview", "entity_index", "list_block"}:
                    replace_index = index
                    break
            if replace_index is None:
                replace_index = len(updated) - 1
            updated[replace_index] = required_doc

        rank_lookup = {id(doc): index for index, doc in enumerate(ranked_docs or [])}
        updated.sort(key=lambda doc: rank_lookup.get(id(doc), 10_000))
        deduped = []
        seen_ids = set()
        for doc in updated:
            doc_id = id(doc)
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            deduped.append(doc)
            if len(deduped) >= limit:
                break
        return deduped

    def _find_adjacent_supporting_detail_doc(
        self,
        anchor_doc,
        ranked_docs,
        *,
        query_profile: dict[str, object],
    ):
        anchor_metadata = getattr(anchor_doc, "metadata", {}) or {}
        anchor_document_name = str(anchor_metadata.get("document_name") or "").strip()
        anchor_section_title = str(anchor_metadata.get("section_title") or "").strip()
        anchor_order = anchor_metadata.get("chunk_order")
        if not isinstance(anchor_order, int):
            return None

        candidates = []
        for doc in ranked_docs or []:
            if id(doc) == id(anchor_doc):
                continue
            metadata = getattr(doc, "metadata", {}) or {}
            if str(metadata.get("document_name") or "").strip() != anchor_document_name:
                continue
            if str(metadata.get("chunk_kind") or "text").strip() != "section_detail":
                continue
            candidate_order = metadata.get("chunk_order")
            if not isinstance(candidate_order, int) or abs(candidate_order - anchor_order) > 2:
                continue
            if anchor_section_title and str(metadata.get("section_title") or "").strip() not in {"", anchor_section_title}:
                continue
            evidence = self._build_doc_evidence_profile(doc, query_profile)
            span_summary = self._build_factoid_span_summary(
                doc,
                resolved_question=str(query_profile.get("raw_text") or ""),
                retrieval_intent="specific_fact",
            )
            support_score = (
                max(0, 30 - abs(candidate_order - anchor_order) * 8)
                + int(evidence["detail_specificity"]) // 3
                + min(90, int(span_summary.get("top_span_score") or 0))
                + int(evidence["company_cue_hits"]) * 30
                + int(evidence["role_overlap"]) * 18
                + int(evidence["exact_overlap"]) * 8
            )
            if support_score < 42:
                continue
            candidates.append((support_score, doc))

        candidates.sort(key=lambda item: -item[0])
        return candidates[0][1] if candidates else None

    def _select_explicit_evidence_context_docs(
        self,
        selected_docs,
        ranked_docs,
        *,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
        limit: int,
    ) -> list:
        if not self._is_explicit_evidence_intent(
            retrieval_intent,
            target_document_name=target_document_name,
            document_shortlist=document_shortlist,
        ):
            return list(selected_docs or [])[:limit]

        selected_spans = self._collect_selected_evidence_spans(
            ranked_docs,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question or "",
            target_document_name=target_document_name,
            limit=4,
        )
        if not selected_spans:
            return list(selected_docs or [])[:limit]

        top_detail = None
        for span in selected_spans:
            if str(span.get("chunk_kind") or "").strip() != "section_detail":
                continue
            for doc in ranked_docs or []:
                metadata = getattr(doc, "metadata", {}) or {}
                if (
                    str(metadata.get("document_name") or "").strip() == str(span.get("document_name") or "").strip()
                    and str(metadata.get("chunk_kind") or "").strip() == "section_detail"
                    and metadata.get("chunk_order") == span.get("chunk_order")
                ):
                    top_detail = doc
                    break
            if top_detail is not None:
                break

        if top_detail is None:
            return list(selected_docs or [])[:limit]

        query_profile = self._build_retrieval_query_profile(resolved_question or "")
        updated = self._ensure_ranked_doc_in_selection(
            selected_docs,
            top_detail,
            ranked_docs=ranked_docs,
            limit=limit,
        )
        adjacent_detail = self._find_adjacent_supporting_detail_doc(
            top_detail,
            ranked_docs,
            query_profile=query_profile,
        )
        return self._ensure_ranked_doc_in_selection(
            updated,
            adjacent_detail,
            ranked_docs=ranked_docs,
            limit=limit,
        )

    # Esta selecao final escolhe quantos trechos entram no contexto entregue ao modelo.
    def _select_docs_for_context(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
        document_shortlist: list[str] | None = None,
    ) -> list:
        ranked_docs = self._prioritize_retrieved_docs(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
        )
        if not ranked_docs:
            return []
        shortlist = self._normalize_document_shortlist(document_shortlist, target_document_name)
        selected = None
        if shortlist and not target_document_name:
            if retrieval_intent == "summary":
                selected = self._select_shortlist_context_docs(
                    ranked_docs,
                    shortlist,
                    limit=int(self._get_retrieval_config_value("context_summary_limit", 6)),
                    retrieval_intent=retrieval_intent,
                )
            elif retrieval_intent in {"list_extraction", "document_expansion"}:
                selected = self._select_shortlist_context_docs(
                    ranked_docs,
                    shortlist,
                    limit=int(self._get_retrieval_config_value("context_diverse_limit", 8)),
                    retrieval_intent=retrieval_intent,
                )
            else:
                selected = self._select_shortlist_context_docs(
                    ranked_docs,
                    shortlist,
                    limit=int(self._get_retrieval_config_value("context_default_limit", 6)),
                    retrieval_intent=retrieval_intent,
                )
        elif retrieval_intent == "list_extraction":
            selected = self._select_diverse_context_docs(
                ranked_docs,
                limit=int(self._get_retrieval_config_value("context_diverse_limit", 8)),
            )
        elif retrieval_intent == "document_expansion":
            selected = self._select_diverse_context_docs(
                ranked_docs,
                limit=int(self._get_retrieval_config_value("context_diverse_limit", 8)),
            )
        elif retrieval_intent == "summary":
            selected = self._select_summary_context_docs(
                ranked_docs,
                limit=int(self._get_retrieval_config_value("context_summary_limit", 6)),
            )
        else:
            selected = ranked_docs[: int(self._get_retrieval_config_value("context_default_limit", 6))]

        limit = len(selected) if selected else int(self._get_retrieval_config_value("context_default_limit", 6))
        return self._select_explicit_evidence_context_docs(
            selected,
            ranked_docs,
            target_document_name=target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
            document_shortlist=document_shortlist,
            limit=limit,
        )

    def _select_summary_context_docs(self, ranked_docs, limit: int) -> list:
        selected = []
        seen_doc_ids = set()
        seen_groups = set()

        for kind in ("document_profile", "section_overview", "section_detail"):
            for doc in ranked_docs:
                if id(doc) in seen_doc_ids:
                    continue
                if str(doc.metadata.get("chunk_kind") or "").strip() != kind:
                    continue
                if self._should_skip_summary_doc(doc):
                    continue
                group_key = self._build_coverage_group_key(doc)
                if group_key in seen_groups and kind != "document_profile":
                    continue
                selected.append(doc)
                seen_doc_ids.add(id(doc))
                seen_groups.add(group_key)
                if len(selected) >= limit:
                    return selected

        for doc in ranked_docs:
            if id(doc) in seen_doc_ids or self._should_skip_summary_doc(doc):
                continue
            chunk_kind = str(doc.metadata.get("chunk_kind") or "").strip()
            if chunk_kind in {"entity_index", "list_block"}:
                continue

            group_key = self._build_coverage_group_key(doc)
            if group_key in seen_groups and chunk_kind != "document_profile":
                continue
            selected.append(doc)
            seen_doc_ids.add(id(doc))
            seen_groups.add(group_key)
            if len(selected) >= limit:
                break
        return selected or ranked_docs[:limit]

    def _select_shortlist_context_docs(
        self,
        ranked_docs,
        document_shortlist: list[str],
        *,
        limit: int,
        retrieval_intent: str | None = None,
    ) -> list:
        selected = []
        seen_ids = set()
        per_document_counts = {document_name: 0 for document_name in document_shortlist}
        per_document_limit = 2 if retrieval_intent in {"summary", "list_extraction", "document_expansion"} else 3

        for document_name in document_shortlist:
            for doc in ranked_docs:
                if id(doc) in seen_ids:
                    continue
                if str(doc.metadata.get("document_name") or "").strip() != document_name:
                    continue
                if retrieval_intent == "summary" and self._should_skip_summary_doc(doc):
                    continue
                selected.append(doc)
                seen_ids.add(id(doc))
                per_document_counts[document_name] += 1
                if len(selected) >= limit:
                    return selected
                break

        for doc in ranked_docs:
            if id(doc) in seen_ids:
                continue
            document_name = str(doc.metadata.get("document_name") or "").strip()
            if document_name not in per_document_counts:
                continue
            if retrieval_intent == "summary" and self._should_skip_summary_doc(doc):
                continue
            if per_document_counts[document_name] >= per_document_limit and len(selected) >= len(document_shortlist):
                continue
            selected.append(doc)
            seen_ids.add(id(doc))
            per_document_counts[document_name] += 1
            if len(selected) >= limit:
                break
        return selected or ranked_docs[:limit]

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

    def _should_skip_summary_doc(self, doc) -> bool:
        metadata = doc.metadata or {}
        chunk_kind = str(metadata.get("chunk_kind") or "").strip()
        if chunk_kind in {"entity_index", "list_block"}:
            return True
        if metadata.get("section_is_header_metadata") and chunk_kind != "document_profile":
            return True
        return self._looks_like_noisy_source(doc.page_content or "")

    # Esta diversificacao preserva recall em documentos longos ao cobrir secoes diferentes.
    def _select_diverse_context_docs(self, ranked_docs, limit: int) -> list:
        selected = []
        seen_doc_ids = set()
        seen_groups = set()

        preferred_kinds = ("document_profile", "section_overview", "entity_index", "list_block")
        for kind in preferred_kinds:
            for doc in ranked_docs:
                if id(doc) in seen_doc_ids:
                    continue
                if str(doc.metadata.get("chunk_kind") or "").strip() != kind:
                    continue
                selected.append(doc)
                seen_doc_ids.add(id(doc))
                seen_groups.add(self._build_coverage_group_key(doc))
                break

        for doc in ranked_docs:
            if id(doc) in seen_doc_ids:
                continue
            page_content = doc.page_content or ""
            chunk_kind = str(doc.metadata.get("chunk_kind") or "").strip()
            group_key = self._build_coverage_group_key(doc)
            if self._looks_like_noisy_source(page_content) and len(selected) >= max(2, limit // 3):
                continue
            if group_key in seen_groups and chunk_kind not in {"document_profile", "entity_index", "list_block"}:
                continue
            if self._looks_numeric_heavy_source(page_content) and len(selected) >= max(3, limit // 2):
                continue
            selected.append(doc)
            seen_doc_ids.add(id(doc))
            seen_groups.add(group_key)
            if len(selected) >= limit:
                break
        return selected or ranked_docs[:limit]

    # Esta resposta explicita que o sistema preferiu nao inventar quando a evidencia ficou fraca.
    def _build_abstain_answer(self) -> str:
        return (
            "Nao ha evidencias suficientes nos trechos recuperados para responder com seguranca. "
            "Informe um arquivo, data ou trecho mais especifico."
        )

    # Esta resposta lista os arquivos empatados quando ainda falta escolha do usuario.
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
