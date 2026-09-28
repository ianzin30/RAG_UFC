"""Shared-state CrewAI orchestration with bounded retrieval and verification."""

import time
from ..CrewAiTelemetry import disable_crewai_telemetry_by_default

disable_crewai_telemetry_by_default()
from crewai.flow.flow import Flow, start
from .Models import (
    RAGState,
    QueryPlan,
    ReasoningResult,
    ResearchResult,
    AnswerDraft,
    VerificationResult,
    SourceFocusResult,
    EvidenceUnit,
    RetrievalOccurrence,
)


class RAGFlow(Flow[RAGState]):
    def __init__(
        self, team, retriever, parents, catalog, config, tokenizer, callback=None
    ):
        super().__init__(tracing=False, suppress_flow_events=True)
        self.team, self.retriever, self.parents, self.catalog = (
            team,
            retriever,
            parents,
            catalog,
        )
        self.config, self.tokenizer, self.callback = config, tokenizer, callback
        self.diagnostics = {"hops": [], "verification": [], "context_selection": []}

    def status(self, stage):
        if self.callback:
            self.callback(stage)

    def tokens(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def collect(self, query, scope, exhaustive=False, per_document_budget=None):
        try:
            if exhaustive:
                candidates = [
                    {
                        "position": i,
                        "chunk_id": chunk.chunk_id,
                        "dense_rank": None,
                        "sparse_rank": None,
                        "rrf_score": 0.0,
                        "reranker_score": None,
                    }
                    for i, chunk in enumerate(self.retriever.chunks)
                    if scope is None or chunk.document_id in scope
                ]
                diagnostic = {
                    "hop_id": self.state.current_hop,
                    "query": query,
                    "scope": scope,
                    "stages": {"structural_enumeration": candidates},
                }
            else:
                candidates, diagnostic = self.retriever.search(
                    query, scope, self.state.current_hop
                )
        except Exception as exc:
            self.diagnostics["hops"].append(
                {
                    "query": query,
                    "scope": scope,
                    "hop_id": self.state.current_hop,
                    "error": str(exc),
                }
            )
            raise
        self.diagnostics["hops"].append(diagnostic)
        known = {item.parent_id: item for item in self.state.evidence}
        added = 0
        # Budget includes repeated parents only once; evidence child text remains exact.
        used_parents = {item.parent_id for item in self.state.evidence}
        used = sum(self.tokens(self.parents[parent]) for parent in used_parents)
        used_for_document = sum(
            self.tokens(item.context)
            for item in self.state.evidence
            if item.document_id == (scope[0] if scope and len(scope) == 1 else None)
        )
        for candidate in candidates:
            chunk = self.retriever.chunks[candidate["position"]]
            occurrence = RetrievalOccurrence(
                retrieval_query=query,
                hop_id=self.state.current_hop,
                **{
                    key: candidate[key]
                    for key in (
                        "dense_rank",
                        "sparse_rank",
                        "rrf_score",
                        "reranker_score",
                    )
                },
            )
            if chunk.parent_id in known:
                existing = known[chunk.parent_id]
                existing.occurrences.append(occurrence)
                if chunk.chunk_id not in existing.retrieved_chunk_ids:
                    existing.retrieved_chunk_ids.append(chunk.chunk_id)
                continue
            context = self.parents[chunk.parent_id]
            cost = 0 if chunk.parent_id in used_parents else self.tokens(context)
            if (
                used + cost > self.config.context_tokens
                or (
                    per_document_budget is not None
                    and used_for_document + cost > per_document_budget
                )
            ):
                self.diagnostics["context_selection"].append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "reason": (
                            "document_token_budget"
                            if per_document_budget is not None
                            and used_for_document + cost > per_document_budget
                            else "token_budget"
                        ),
                    }
                )
                continue
            used += cost
            used_for_document += cost
            used_parents.add(chunk.parent_id)
            item = EvidenceUnit(
                **{**chunk.model_dump(), "text": context},
                evidence_id=f"E{len(self.state.evidence) + 1}",
                excerpt=context,
                context=context,
                occurrences=[occurrence],
                retrieved_chunk_ids=[chunk.chunk_id],
            )
            self.state.evidence.append(item)
            known[chunk.parent_id] = item
            added += 1
        return added

    def evidence_payload(self, evidence=None):
        return [
            {
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "document_name": item.document_name,
                "section": item.section_title,
                "text": item.text,
            }
            for item in (self.state.evidence if evidence is None else evidence)
        ]

    def verify(self, draft):
        evidence_ids = {item.evidence_id for item in self.state.evidence}
        valid = [
            claim
            for claim in draft.claims
            if claim.evidence_ids and set(claim.evidence_ids) <= evidence_ids
        ]
        invalid = [claim.claim_id for claim in draft.claims if claim not in valid]
        if len({claim.claim_id for claim in draft.claims}) != len(draft.claims):
            raise ValueError("Duplicate claim IDs")
        by_evidence = {item["evidence_id"]: item for item in self.evidence_payload()}
        verification_claims = [
            {
                **claim.model_dump(),
                "cited_evidence": [by_evidence[eid] for eid in claim.evidence_ids],
            }
            for claim in valid
        ]
        result = self.team.run(
            "verification",
            "Verifique cada claim EXCLUSIVAMENTE contra seu cited_evidence e cálculos determinísticos fornecidos. Nunca use evidências de outra claim. Classifique suporte, contradição ou falta. central_question_supported exige resposta à pergunta central; não basta alguma frase verdadeira.",
            {
                "question": self.state.original_question,
                "claims": verification_claims,
                "deterministic_table_calculation": self.diagnostics.get(
                    "table_calculation"
                ),
            },
            VerificationResult,
        )
        from .Models import ClaimVerification

        by_id = {item.claim_id: item for item in result.claims}
        for claim in draft.claims:
            if claim.claim_id in invalid or claim.claim_id not in by_id:
                by_id[claim.claim_id] = ClaimVerification(
                    claim_id=claim.claim_id,
                    status="UNSUPPORTED",
                    reason="Missing/invalid evidence or verification",
                )
        result.claims = [by_id[claim.claim_id] for claim in draft.claims]
        self.diagnostics["verification"].append(result.model_dump())
        return result

    def synthesize(self, evidence, batch_index=0):
        """Bounded synthesis/repair for one context batch; one repair per question."""
        state = self.state
        payload = {
            "question": state.plan.resolved_question,
            "evidence": self.evidence_payload(evidence),
            "deterministic_table_calculation": self.diagnostics.get(
                "table_calculation"
            ),
        }
        self.status("answer")
        draft = self.team.run(
            "answer",
            "Responda em português com claims atômicos e evidence_ids. Use apenas trechos fornecidos. Para 'quem' ou identidade/cargo, a claim deve conter o nome ou valor literal pedido; uma descrição genérica do papel não responde à pergunta. Para comparação, inclua cada lado solicitado. Não acrescente fatos sem evidência. Se os dados não respondem à pergunta, retorne claims vazio.",
            payload,
            AnswerDraft,
        )
        # IDs generated in separate batches must not collide in the shared state.
        for index, claim in enumerate(draft.claims, 1):
            claim.claim_id = f"B{batch_index}C{index}"
        self.status("verification")
        verification = self.verify(draft)
        if (
            any(item.status != "SUPPORTED" for item in verification.claims)
            and state.repair_count == 0
        ):
            state.repair_count += 1
            draft = self.team.run(
                "answer",
                "Repare uma vez: remova ou corrija claims rejeitados usando somente as evidências. Não invente IDs.",
                {
                    **payload,
                    "draft": draft.model_dump(),
                    "verification": verification.model_dump(),
                },
                AnswerDraft,
            )
            for index, claim in enumerate(draft.claims, 1):
                claim.claim_id = f"B{batch_index}C{index}"
            verification = self.verify(draft)
        supported = {
            item.claim_id for item in verification.claims if item.status == "SUPPORTED"
        }
        approved = [claim for claim in draft.claims if claim.claim_id in supported]
        return approved, verification, len(approved) != len(draft.claims)

    def focus_cited_sources(self):
        """Ask once for literal, claim-level focus quotes after verification."""
        if not self.state.claims:
            return
        self.status("source_focus")
        evidence_by_id = {item.evidence_id: item for item in self.state.evidence}
        cited_ids = list(
            dict.fromkeys(
                evidence_id
                for claim in self.state.claims
                for evidence_id in claim.evidence_ids
            )
        )
        sources = []
        for evidence_id in cited_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                continue
            claims = [
                {"claim_id": claim.claim_id, "text": claim.text}
                for claim in self.state.claims
                if evidence_id in claim.evidence_ids
            ]
            sources.append(
                {
                    "evidence_id": evidence_id,
                    "excerpt": evidence.excerpt,
                    "claims": claims,
                }
            )
            self.state.source_focus_status[evidence_id] = "pending"

        batches, current, size = [], [], 0
        for source in sources:
            cost = self.tokens(source["excerpt"])
            if current and size + cost > self.config.context_tokens:
                batches.append(current)
                current, size = [], 0
            # A parent can exceed the safe request budget only in malformed
            # external traces; retain a compact prefix rather than fail answer.
            if cost > self.config.context_tokens:
                source = {**source, "excerpt": source["excerpt"][:8000]}
                cost = self.tokens(source["excerpt"])
            current.append(source)
            size += cost
        if current:
            batches.append(current)

        all_selections = []
        for batch in batches:
            try:
                result = self.team.run(
                    "source_focus",
                    "Para cada claim-evidência, selecione uma citação LITERAL curta que sustente diretamente a claim. quote precisa ocorrer exatamente no excerpt fornecido, com no máximo 240 caracteres. Não parafraseie, não invente e não inclua Markdown.",
                    {"sources": batch},
                    SourceFocusResult,
                )
                all_selections.extend(result.selections)
            except Exception as exc:
                self.diagnostics.setdefault("source_focus", []).append(
                    {"status": "error", "error": str(exc), "evidence_ids": [item["evidence_id"] for item in batch]}
                )
                for item in batch:
                    self.state.source_focus_status[item["evidence_id"]] = "unavailable"

        from .Focus import resolve_focus_spans

        spans = resolve_focus_spans(
            all_selections,
            evidence_by_id,
            [claim.claim_id for claim in self.state.claims],
        )
        for evidence_id in cited_ids:
            if evidence_id in spans:
                self.state.source_focus[evidence_id] = spans[evidence_id]
                self.state.source_focus_status[evidence_id] = "focused"
            elif self.state.source_focus_status.get(evidence_id) != "unavailable":
                self.state.source_focus_status[evidence_id] = "fallback"
        self.diagnostics.setdefault("source_focus", []).append(
            {
                "status": "ok",
                "focused_evidence_ids": sorted(spans),
                "fallback_evidence_ids": [
                    evidence_id
                    for evidence_id in cited_ids
                    if self.state.source_focus_status.get(evidence_id) != "focused"
                ],
            }
        )

    @start()
    def answer(self):
        started = time.perf_counter()
        state = self.state
        state.max_hops = self.config.max_hops
        self.status("planning")
        state.plan = self.team.run(
            "planner",
            "Resolva a pergunta usando histórico, intenção e escopo. Compare A e B implica explicit_multi_document, nunca ambiguidade automática. Use somente document_ids do catálogo; inclua só documentos solicitados, não outros possivelmente relacionados. Perguntas sociais são casual. Para uma pergunta factual simples, produza UMA query e apenas a evidência mínima pedida; não expanda para detalhes de equipe, datas ou tópicos que não foram perguntados. Intenções: single_fact, entity_lookup, list_extraction, summary, document_expansion, comparison, cross_document, multi_hop, aggregation, spreadsheet/table.",
            {
                "question": state.original_question,
                "history": state.history,
                "catalog": self.catalog,
            },
            QueryPlan,
        )
        plan = state.plan
        allowed_ids = {entry["document_id"] for entry in self.catalog}
        if not set(plan.scope.document_ids) <= allowed_ids:
            raise ValueError("Planner returned unknown document IDs")
        if plan.route == "casual":
            state.final_answer = self.team.registry.generate(
                "answer",
                "Responda brevemente em português sem alegar fatos dos documentos: "
                + state.original_question,
            )
            state.status = "casual"
            return state
        if plan.scope.kind == "ambiguous_document":
            state.status = "clarification_required"
            state.final_answer = (
                plan.clarification or "Qual documento você deseja consultar?"
            )
            return state
        scope = (
            None if plan.scope.kind == "collection_wide" else plan.scope.document_ids
        )
        if scope == []:
            state.status, state.stop_reason = "abstained", "insufficient_scope"
            state.final_answer = (
                "Não foi possível identificar o escopo documental solicitado."
            )
            return state
        if plan.aggregation is not None:
            from .Tables import aggregate

            self.diagnostics["table_calculation"] = aggregate(
                self.retriever.chunks, scope, plan.aggregation
            )
        # A planner subquery can be useful for a second hop, but it must not
        # replace the user's resolved wording: structured labels in the corpus
        # (for example, "Coordenador na Instituição") may be present only in
        # that wording.  Preserve deterministic order and deduplicate.
        original_matches_resolved = (
            " ".join(state.original_question.casefold().split())
            == " ".join(plan.resolved_question.casefold().split())
        )
        queries = list(
            dict.fromkeys(
                ([plan.resolved_question] if original_matches_resolved else [])
                + plan.initial_queries
            )
        ) or [plan.resolved_question]
        seen_queries = set()
        for hop in range(1, state.max_hops + 1):
            state.current_hop = hop
            self.status("retrieval")
            new_evidence = 0
            executed = 0
            for query in queries[: self.config.queries_per_hop]:
                key = " ".join(query.casefold().split())
                if not key or key in seen_queries:
                    continue
                seen_queries.add(key)
                executed += 1
                state.retrieval_queries.append(query)
                # Explicit multi-document requests query each partition for coverage.
                scopes = (
                    [[doc_id] for doc_id in scope]
                    if scope and len(scope) > 1
                    else [scope]
                )
                for selected_scope in scopes:
                    new_evidence += self.collect(
                        query,
                        selected_scope,
                        per_document_budget=(
                            self.config.context_tokens // len(scope)
                            if scope and len(scope) > 1
                            else None
                        ),
                    )
            if not executed or not new_evidence:
                state.stop_reason = (
                    "repeated_query" if not executed else "no_new_evidence"
                )
                break
            self.status("reasoning")
            state.reasoning = self.team.run(
                "reasoning",
                "Extraia fatos somente das evidências, cada fato com IDs. Para perguntas de identidade (quem, qual coordenador, responsável), extraia o nome/valor literal, nunca apenas uma descrição do cargo. Em comparações, extraia explicitamente um valor para cada lado solicitado. Identifique lacunas e contradições. sufficient se a pergunta central está respondida. Não invente necessidades além da pergunta. requires_additional_retrieval somente para lacuna indispensável à resposta; nunca para enriquecer detalhes opcionais. Não infira ausência global a partir de top-K.",
                {
                    "question": plan.resolved_question,
                    "expected_evidence": plan.expected_evidence,
                    "evidence": self.evidence_payload(),
                },
                ReasoningResult,
            )
            ids = {item.evidence_id for item in state.evidence}
            if any(
                not fact.evidence_ids or not set(fact.evidence_ids) <= ids
                for fact in state.reasoning.established_facts
            ):
                raise ValueError("Reasoning returned unsupported evidence references")
            if state.reasoning.sufficient or state.reasoning.unanswerable:
                state.stop_reason = (
                    "evidence_sufficient"
                    if state.reasoning.sufficient
                    else "unanswerable"
                )
                break
            if hop == state.max_hops:
                state.stop_reason = "max_hops"
                break
            if (
                not plan.requires_multi_hop
                and not state.reasoning.requires_additional_retrieval
            ):
                state.stop_reason = "single_pass"
                break
            queries = self.team.run(
                "research",
                "Formule novas queries específicas usando os fatos e as lacunas. Não repita queries anteriores.",
                {
                    "question": plan.resolved_question,
                    "reasoning": state.reasoning.model_dump(),
                    "previous_queries": state.retrieval_queries,
                },
                ResearchResult,
            ).queries
        if not state.evidence:
            state.status = "abstained"
            state.final_answer = "Não encontrei evidências suficientes para responder."
            return state
        if (
            plan.intent
            in {"summary", "list_extraction", "document_expansion", "aggregation"}
            or plan.aggregation
        ):
            from .Coverage import evidence_batches

            batches = evidence_batches(self, scope)
        else:
            batches = [state.evidence]
        central_supported, rejected_any, verdicts = False, False, []
        seen_claims = set()
        for batch_index, batch in enumerate(batches):
            claims, verification, rejected = self.synthesize(batch, batch_index)
            verdicts.extend(verification.claims)
            central_supported |= verification.central_question_supported
            rejected_any |= rejected
            for claim in claims:
                key = " ".join(claim.text.casefold().split())
                if key not in seen_claims:
                    state.claims.append(claim)
                    seen_claims.add(key)
        state.verification = VerificationResult(
            claims=verdicts, central_question_supported=central_supported
        )
        if not state.claims:
            state.status = "abstained"
            state.final_answer = "Não encontrei evidências suficientes para responder."
        else:
            partial = (
                not state.verification.central_question_supported
                or rejected_any
                or not self.diagnostics.get("coverage", {}).get("complete", True)
            )
            state.status = "partial" if partial else "answered"
            state.final_answer = (
                "Resposta parcial — faltam evidências para a conclusão completa.\n\n"
                if partial
                else ""
            ) + "\n\n".join(
                claim.text + " " + " ".join(f"[{eid}]" for eid in claim.evidence_ids)
                for claim in state.claims
            )
        self.focus_cited_sources()
        self.diagnostics["total_seconds"] = time.perf_counter() - started
        return state
