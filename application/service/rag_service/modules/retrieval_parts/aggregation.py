"""Context aggregation helpers for broader retrieval answers."""

import re


# Este mixin resume a evidencia recuperada antes da resposta final do modelo.
class RetrievalAggregationMixin:
    # Este helper combina um pacote agregado com o contexto bruto selecionado.
    def _build_answer_context(
        self,
        docs,
        *,
        retrieval_intent: str | None = None,
        target_document_name: str | None = None,
        resolved_question: str | None = None,
    ) -> str:
        raw_context = self._format_docs(docs)
        aggregate = self._build_aggregated_evidence_block(
            docs,
            retrieval_intent=retrieval_intent,
            target_document_name=target_document_name,
            resolved_question=resolved_question,
        )
        if not aggregate:
            return raw_context
        if not raw_context:
            return aggregate
        return f"{aggregate}\n\nContexto bruto recuperado:\n{raw_context}".strip()

    # Este bloco sintetiza cobertura de secoes, nomes, fatos e pontos-chave.
    def _build_aggregated_evidence_block(
        self,
        docs,
        *,
        retrieval_intent: str | None = None,
        target_document_name: str | None = None,
        resolved_question: str | None = None,
    ) -> str:
        if not docs:
            return ""

        topics = self._collect_unique_values(
            [
                str(doc.metadata.get("section_title") or "").strip()
                for doc in docs
                if str(doc.metadata.get("section_title") or "").strip()
            ],
            limit=10,
        )
        names = self._collect_unique_values(
            self._collect_metadata_or_text_values(
                docs,
                metadata_key="entity_names",
                extractor=self._extract_name_candidates,
                use_cleaned_text=True,
                fallback_chunk_kinds={"section_detail", "list_block", "row_record", "people_index"},
            ),
            limit=80 if retrieval_intent == "list_extraction" else 24,
        )
        dates = self._collect_unique_values(
            self._collect_metadata_or_text_values(docs, metadata_key="date_values", extractor=self._extract_date_candidates),
            limit=12,
        )
        money_values = self._collect_unique_values(
            self._collect_metadata_or_text_values(docs, metadata_key="money_values", extractor=self._extract_money_candidates),
            limit=12,
        )
        fact_lines = self._collect_unique_values(self._collect_fact_lines(docs), limit=14)
        key_points = self._collect_unique_values(self._collect_key_evidence_lines(docs), limit=10)

        lines = ["Pacote agregado de evidencias"]
        if target_document_name:
            lines.append(f"Documento-alvo consolidado: {target_document_name}")
        if resolved_question:
            lines.append(f"Pergunta contextualizada: {resolved_question}")
        if topics:
            lines.append(f"Secoes ou topicos cobertos: {'; '.join(topics)}")
        if names and retrieval_intent in {"summary", "document_expansion", "list_extraction", "entity_lookup"}:
            lines.append(f"Pessoas ou entidades consolidadas: {'; '.join(names)}")
        if dates:
            lines.append(f"Datas consolidadas: {'; '.join(dates)}")
        if money_values:
            lines.append(f"Valores consolidados: {'; '.join(money_values)}")
        if fact_lines:
            lines.append("Campos rotulados relevantes:")
            lines.extend(f"- {fact}" for fact in fact_lines)
        if key_points and retrieval_intent in {"summary", "document_expansion", "specific_fact"}:
            lines.append("Pontos-chave observados:")
            lines.extend(f"- {point}" for point in key_points)
        return "\n".join(lines).strip()

    # Este helper reaproveita metadados estruturados e cai para regex quando eles faltam.
    def _collect_metadata_or_text_values(
        self,
        docs,
        *,
        metadata_key: str,
        extractor,
        use_cleaned_text: bool = False,
        fallback_chunk_kinds: set[str] | None = None,
    ) -> list[str]:
        values = []
        for doc in docs:
            raw_value = doc.metadata.get(metadata_key)
            if isinstance(raw_value, list):
                values.extend(str(item).strip() for item in raw_value if str(item).strip())
                continue
            if isinstance(raw_value, str) and raw_value.strip():
                values.append(raw_value.strip())
                continue
            chunk_kind = str(doc.metadata.get("chunk_kind") or "").strip()
            if fallback_chunk_kinds is not None and chunk_kind not in fallback_chunk_kinds:
                continue
            source_text = self._strip_retrieval_wrapper(doc.page_content or "") if use_cleaned_text else (doc.page_content or "")
            values.extend(extractor(source_text))
        return values

    # Esta etapa recolhe fatos no formato campo: valor espalhados pelos chunks.
    def _collect_fact_lines(self, docs) -> list[str]:
        facts = []
        for doc in docs:
            raw_facts = doc.metadata.get("labeled_facts")
            if isinstance(raw_facts, list):
                facts.extend(str(fact).strip() for fact in raw_facts if str(fact).strip())
            for label, value in self._extract_labeled_facts(doc.page_content or "", limit=12):
                facts.append(f"{label}: {value}")
        return facts

    # Esta coleta cria um resumo curto por trecho para cobrir mais partes do documento.
    def _collect_key_evidence_lines(self, docs) -> list[str]:
        points = []
        for doc in docs:
            section_title = str(doc.metadata.get("section_title") or "").strip()
            cleaned = self._strip_retrieval_wrapper(doc.page_content or "")
            compact_lines = [re.sub(r"\s+", " ", line).strip(" -") for line in cleaned.splitlines() if line.strip()]
            if section_title:
                points.append(f"Secao {section_title}: {' '.join(compact_lines[:2])[:220].strip()}")
                continue
            if compact_lines:
                points.append(" ".join(compact_lines[:2])[:220].strip())
        return [point for point in points if point]

    # Este helper remove marcadores tecnicos antes de sintetizar a evidencia.
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

    # Esta deduplicacao preserva a ordem natural da leitura.
    def _collect_unique_values(self, values: list[str], limit: int) -> list[str]:
        unique_values = []
        seen = set()
        for value in values:
            compact = re.sub(r"\s+", " ", str(value or "")).strip(" -")
            if not compact:
                continue
            normalized = self._normalize_identifier(compact)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(compact)
            if len(unique_values) >= limit:
                break
        return unique_values
