"""Core retrieval and ranking helpers."""

import re


# Este mixin recupera, pontua e seleciona os trechos usados na resposta final.
class RetrievalCoreMixin:
    # Esta busca tenta primeiro o caminho estruturado das planilhas e depois o vetor store geral.
    def _retrieve_docs(
        self,
        question: str,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
    ):
        if self._is_spreadsheet_document_name(target_document_name):
            structured_docs = self._retrieve_spreadsheet_chunks(question, target_document_name)
            if structured_docs:
                return structured_docs

        if target_document_name:
            focused_question = f"{target_document_name} {question}".strip()
            docs = self.vector_store.max_marginal_relevance_search(
                focused_question,
                k=6,
                fetch_k=100,
                lambda_mult=0.2,
                filter={"document_name": target_document_name},
            )
            fallback_docs = self.vector_store.similarity_search(
                target_document_name,
                k=6,
                fetch_k=100,
                filter={"document_name": target_document_name},
            )
            lexical_docs = self._retrieve_lexical_docs(question, target_document_name=target_document_name, limit=12)
            docs = self._merge_unique_docs(docs, fallback_docs, lexical_docs)
            if self._is_coverage_oriented_intent(retrieval_intent):
                docs = self._merge_unique_docs(
                    docs,
                    self._retrieve_document_coverage_docs(
                        question,
                        target_document_name=target_document_name,
                        retrieval_intent=retrieval_intent,
                    ),
                )
            if docs:
                return docs

        dense_docs = self.retriever.invoke(question)
        lexical_docs = self._retrieve_lexical_docs(question, target_document_name=target_document_name, limit=12)
        return self._merge_unique_docs(dense_docs, lexical_docs)

    # Esta busca lexical complementa o embedding com termos exatos e metadados estruturados.
    def _retrieve_lexical_docs(
        self,
        question: str,
        *,
        target_document_name: str | None = None,
        limit: int = 10,
    ) -> list:
        query_terms = self._tokenize_search_text(question)
        if not query_terms:
            return []

        query_fragments = self._build_query_fragments(query_terms)
        candidates = []
        for doc in self._get_retrieval_doc_pool(target_document_name):
            search_text = doc.metadata.get("search_text_normalized") or self._normalize_identifier(doc.page_content)
            overlap = sum(1 for term in query_terms if term in search_text)
            fragment_overlap = sum(1 for fragment in query_fragments if fragment in search_text)
            if overlap <= 0 and fragment_overlap <= 0:
                continue

            score = overlap * 24 + fragment_overlap * 10
            if target_document_name and doc.metadata.get("document_name") == target_document_name:
                score += 30
            chunk_kind = str(doc.metadata.get("chunk_kind") or "text").strip()
            if chunk_kind in {"entity_index", "list_block"}:
                score += 12
            if chunk_kind == "section_overview":
                score += 8
            chunk_order = doc.metadata.get("chunk_order")
            if isinstance(chunk_order, int):
                score += max(0, 8 - min(chunk_order, 8))
            candidates.append((score, str(doc.metadata.get("document_name") or ""), int(chunk_order or 0), doc))

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [doc for _, _, _, doc in candidates[:limit]]

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
        preferred_kinds = (
            "document_profile",
            "section_overview",
            "entity_index",
            "list_block",
            "section_detail",
        )
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
    def _get_retrieval_doc_pool(self, target_document_name: str | None = None) -> list:
        docs = list(self._get_vector_store_documents())
        if not target_document_name:
            return docs
        return [doc for doc in docs if str(doc.metadata.get("document_name") or "").strip() == target_document_name]

    # Esta pontuacao mede se a evidencia recuperada sustenta uma resposta confiavel.
    def _score_retrieval_evidence(self, resolved_question: str, docs, target_document_name: str | None = None) -> float:
        if not docs:
            return 0.0

        query_terms = self._tokenize_search_text(resolved_question)
        if not query_terms:
            return 0.0

        best_score = 0.0
        for doc in docs[:6]:
            search_text = doc.metadata.get("search_text_normalized")
            if not search_text:
                search_text = self._normalize_identifier(doc.page_content)

            overlap = sum(1 for term in query_terms if term in search_text)
            lexical_score = overlap / max(len(query_terms), 1)
            score = lexical_score

            document_name = (doc.metadata.get("document_name") or "").strip()
            if target_document_name and document_name and document_name == target_document_name:
                score += 0.18
            if doc.metadata.get("chunk_kind"):
                score += 0.05
            if any(char.isdigit() for char in resolved_question) and any(char.isdigit() for char in doc.page_content):
                score += 0.05

            best_score = max(best_score, min(score, 1.0))
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
    ) -> int:
        metadata = doc.metadata or {}
        document_name = str(metadata.get("document_name") or "").strip()
        chunk_kind = str(metadata.get("chunk_kind") or "text").strip()
        page_content = re.sub(r"\s+", " ", doc.page_content or "").strip()
        normalized = self._normalize_identifier(page_content)

        score = 0
        if target_document_name and document_name == target_document_name:
            score += 120

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
        score += kind_scores.get(chunk_kind, 30)

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
            score += 14
        chunk_order = metadata.get("chunk_order")
        if isinstance(chunk_order, int):
            score += max(0, 12 - min(chunk_order, 12))
        if self._looks_like_noisy_source(page_content):
            score -= 50
        if len(page_content) < 40:
            score -= 20

        query_terms = self._tokenize_search_text(resolved_question or "")
        if query_terms:
            search_text = metadata.get("search_text_normalized") or normalized
            overlap = sum(1 for term in query_terms if term in search_text)
            score += overlap * 8

        if retrieval_intent == "summary":
            if chunk_kind == "document_profile":
                score += 120
            if chunk_kind == "section_overview":
                score += 75
            if chunk_kind == "entity_index":
                score += 36
            if isinstance(chunk_order, int):
                if chunk_order <= 2:
                    score += 45 - chunk_order * 10
                elif chunk_order >= 10:
                    score -= 20
            if any(marker in normalized for marker in ("perfil do documento", "descricao inicial", "realizada em")):
                score += 35
            if self._looks_numeric_heavy_source(page_content):
                score -= 28
        elif retrieval_intent == "document_expansion":
            if chunk_kind == "document_profile":
                score += 90
            if chunk_kind == "section_overview":
                score += 70
            if chunk_kind in {"entity_index", "list_block"}:
                score += 55
            if metadata.get("section_title"):
                score += 16
        elif retrieval_intent == "list_extraction":
            score += self._count_name_like_mentions(page_content) * 6
            if chunk_kind in {"entity_index", "list_block"}:
                score += 55
            if any(marker in normalized for marker in ("titular", "suplente", "representante", "professor", "professora")):
                score += 18
        elif retrieval_intent == "entity_lookup":
            score += self._count_name_like_mentions(page_content) * 5
            if chunk_kind == "entity_index":
                score += 48
            if any(marker in normalized for marker in ("coorden", "respons", "autor", "presidente", "chefe", "professor")):
                score += 20
        elif retrieval_intent == "specific_fact" and query_terms:
            search_text = metadata.get("search_text_normalized") or normalized
            exact_overlap = sum(1 for term in query_terms if term in search_text)
            score += exact_overlap * 10
        return score

    # Esta selecao final escolhe quantos trechos entram no contexto entregue ao modelo.
    def _select_docs_for_context(
        self,
        docs,
        target_document_name: str | None = None,
        retrieval_intent: str | None = None,
        resolved_question: str | None = None,
    ) -> list:
        ranked_docs = self._prioritize_retrieved_docs(
            docs,
            target_document_name,
            retrieval_intent=retrieval_intent,
            resolved_question=resolved_question,
        )
        if not ranked_docs:
            return []
        if retrieval_intent == "list_extraction":
            return self._select_diverse_context_docs(ranked_docs, limit=8)
        if retrieval_intent == "document_expansion":
            return self._select_diverse_context_docs(ranked_docs, limit=8)
        if retrieval_intent == "summary":
            return self._select_diverse_context_docs(ranked_docs, limit=6)
        return ranked_docs[:6]

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
