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
    RetrievalQuery,
    QuestionContract,
    AnswerRequirement,
)
from .Planning import DocumentResolver
from .Decision import next_action
from .Grounding import (
    validate_verification,
    validate_support_quotes,
    validate_entity_constraints,
    useful_claims,
    answer_status,
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
        self.resolver = DocumentResolver(
            catalog, retriever.chunks if retriever is not None else []
        )
        self.diagnostics = {
            "control_version": 3,
            "hops": [],
            "verification": [],
            "context_selection": [],
            "context_tokenizer": "embedding_tokenizer_not_generator_window",
        }

    def contract_payload(self):
        contract = self.state.question_contract
        if contract is None:
            contract = QuestionContract(
                original_question=self.state.original_question,
                resolved_question=self.state.plan.resolved_question,
                requirements=[
                    AnswerRequirement(
                        requirement_id="R1", text=self.state.original_question
                    )
                ],
            )
            self.state.question_contract = contract
        return {
            "question_contract": contract.model_dump(),
            "established_facts": [f.model_dump() for f in self.state.established_facts],
            "missing_facts": self.state.reasoning.missing_facts,
            "known_contradictions": self.state.reasoning.contradictions,
        }

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
        known = {item.parent_id: item for item in self.state.found_evidence}
        added = 0
        # Budget includes repeated parents only once; evidence child text remains exact.
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
            item = EvidenceUnit(
                **{**chunk.model_dump(), "text": context},
                evidence_id=f"E{len(self.state.found_evidence) + 1}",
                excerpt=context,
                context=context,
                occurrences=[occurrence],
                retrieved_chunk_ids=[chunk.chunk_id],
            )
            self.state.found_evidence.append(item)
            known[chunk.parent_id] = item
            added += 1
        return added

    def select_context(self):
        state = self.state
        pinned = {eid for f in state.established_facts for eid in f.evidence_ids}

        def priority(item):
            latest = max((o.hop_id for o in item.occurrences), default=0)
            score = max(
                (
                    o.reranker_score
                    for o in item.occurrences
                    if o.reranker_score is not None
                ),
                default=0,
            )
            return (item.evidence_id not in pinned, -latest, -score, item.chunk_id)

        ordered = sorted(state.found_evidence, key=priority)
        used, selected = 0, []
        for item in ordered:
            cost = self.tokens(item.context)
            if used + cost > self.config.context_tokens:
                self.diagnostics["context_selection"].append(
                    {
                        "chunk_id": item.chunk_id,
                        "evidence_id": item.evidence_id,
                        "hop_id": state.current_hop,
                        "reason": "token_budget",
                        "pinned": item.evidence_id in pinned,
                    }
                )
                continue
            used += cost
            selected.append(item)
        state.evidence = selected
        self.diagnostics.setdefault("active_context", []).append(
            {
                "hop_id": state.current_hop,
                "evidence_ids": [e.evidence_id for e in selected],
                "embedding_tokens": used,
            }
        )

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
        self.contract_payload()
        evidence_ids = {item.evidence_id for item in self.state.evidence}
        valid = [
            claim
            for claim in draft.claims
            if claim.evidence_ids and set(claim.evidence_ids) <= evidence_ids
        ]
        if len({claim.claim_id for claim in draft.claims}) != len(draft.claims):
            raise ValueError("Duplicate claim IDs")
        # Each excerpt is serialized once. Claim citations are authoritative
        # links; other excerpts may reveal a conflict, not repair a wrong link.
        verification_claims = [claim.model_dump() for claim in valid]
        result = self.team.run(
            "verification",
            "Verifique suporte de cada claim SOMENTE nos seus evidence_ids, consultando evidence. SUPPORTED exige support_quotes: citação LITERAL curta por evidência citada, demonstrando a relação pedida; se não existe, UNSUPPORTED. Exija MESMA entidade, cargo, projeto, data e modalidade (previsto não é realizado). Nome de outro projeto ou lista de presentes NÃO responde à pergunta. Outras fontes só revelam conflitos, não justificam citação errada. Preencha coverage para CADA requirement_id somente se todos os fatos pedidos estiverem respondidos. Registre conflicts, nunca escolha entre fontes incompatíveis sem fundamento. Cálculos validados prevalecem. Seja conciso.",
            {
                **self.contract_payload(),
                "question": self.state.original_question,
                "claims": verification_claims,
                "evidence": self.evidence_payload(),
                "deterministic_table_calculation": self.diagnostics.get(
                    "table_calculation"
                ),
            },
            VerificationResult,
        )
        result = validate_support_quotes(result, draft, self.state.evidence)
        result = validate_entity_constraints(
            result,
            draft,
            self.state.question_contract,
            self.state.evidence,
            self.resolver,
        )
        result = validate_verification(
            result, draft, self.state.question_contract, evidence_ids
        )
        from .Tables import calculation_matches_claim, requests_calculation

        math_requirements = {
            r.requirement_id
            for r in self.state.question_contract.requirements
            if requests_calculation(r.text)
        }
        invalid_math = {
            rid
            for error in self.diagnostics.get("calculation_errors", [])
            for rid in error.get("requirement_ids", [])
        }

        for claim in draft.claims:
            numeric_claim = any(char.isdigit() for char in claim.text)
            required = numeric_claim and (
                requests_calculation(claim.text)
                or bool(set(claim.requirement_ids) & (math_requirements | invalid_math))
            )
            if not calculation_matches_claim(
                claim, self.diagnostics.get("calculations", []), required=required
            ):
                for verdict in result.claims:
                    if verdict.claim_id == claim.claim_id:
                        verdict.status, verdict.reason = (
                            "UNSUPPORTED",
                            "Changed/invalid deterministic calculation",
                        )
        by_claim = {c.claim_id: c for c in draft.claims}
        for coverage in result.coverage:
            if coverage.requirement_id in math_requirements and not any(
                by_claim[cid].calculation_id for cid in coverage.claim_ids
            ):
                coverage.covered = False
        result = validate_verification(
            result, draft, self.state.question_contract, evidence_ids
        )
        self.diagnostics["verification"].append(result.model_dump())
        return result

    def synthesize(self, evidence, batch_index=0, defer_coverage=False):
        """Bounded synthesis/repair for one context batch; one repair per question."""
        state = self.state
        payload = {
            **self.contract_payload(),
            "question": state.plan.resolved_question,
            "evidence": self.evidence_payload(evidence),
            "deterministic_table_calculation": self.diagnostics.get(
                "table_calculation"
            ),
            "validated_calculations": self.diagnostics.get("calculations", []),
        }
        self.status("answer")
        draft = self.team.run(
            "answer",
            "Responda em português com claims atômicos, evidence_ids e requirement_ids. Claims calculados exigem calculation_id do cálculo validado e calculation_field: result, printed_total ou difference. Responda somente aos requisitos. Para quem, extraia NOME e relação exigida, nunca atribuições genéricas. Preserve datas, projeto, proposta versus decisão e previsão versus fato realizado. Use somente evidências fornecidas e cálculos validados. Contexto irrelevante produz claims vazio. Se fontes conflitam, não afirme ambas como definitivas. Seja conciso.",
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
            or (not defer_coverage and not verification.central_question_supported)
            or verification.conflicts
        ) and state.repair_count == 0:
            state.repair_count += 1
            draft = self.team.run(
                "answer",
                "Repare uma vez: corrija cobertura, remova claims rejeitados ou conflitantes. Use somente evidências e cálculos validados; preserve calculation_id/field dos resultados numéricos. Não invente IDs.",
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
        if defer_coverage:
            supported = {
                v.claim_id for v in verification.claims if v.status == "SUPPORTED"
            }
            requirements = {
                r.requirement_id for r in state.question_contract.requirements
            }
            approved = [
                c
                for c in draft.claims
                if c.claim_id in supported
                and c.requirement_ids
                and set(c.requirement_ids) <= requirements
            ]
        else:
            approved = useful_claims(draft, verification)
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
                    {
                        "status": "error",
                        "error": str(exc),
                        "evidence_ids": [item["evidence_id"] for item in batch],
                    }
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

    def plan_question(self):
        """Production planning path, also used by isolated controls."""
        state = self.state
        self.status("planning")
        state.plan = self.team.run(
            "planner",
            "Resolva a pergunta usando histórico sem trocar de assunto. Decomponha SOMENTE fatos pedidos em requested_facts. Use referências D do catálogo. Escopo explícito somente se o usuário nomeou os documentos; descoberta fica collection_wide. Compare A e B nunca implica ambiguidade automática. Gere até 3 queries, vinculando documentos somente quando indispensável. Não peça cálculos sobre PDFs como se fossem row_records: interprete a tabela textual recuperada primeiro. Perguntas sociais são casual. Seja conciso.",
            {
                "question": state.original_question,
                "history": state.history,
                "catalog": self.resolver.prompt_catalog(),
                "capabilities": {
                    "calculations": [
                        "sum",
                        "difference",
                        "count",
                        "mean",
                        "min",
                        "max",
                    ],
                    "document_references": "Use D references; unresolved discovery stays collection_wide",
                },
            },
            QueryPlan,
        )
        plan = state.plan
        state.question_contract = self.resolver.contract(
            state.original_question, state.history, plan
        )
        contract = state.question_contract
        self.diagnostics["question_contract"] = contract.model_dump()
        self.diagnostics["document_resolution"] = self.resolver.records
        return plan

    @start()
    def answer(self):
        started = time.perf_counter()
        state = self.state
        state.max_hops = min(3, self.config.max_hops)
        plan = self.plan_question()
        contract = state.question_contract
        if plan.route == "casual":
            state.final_answer = self.team.registry.generate(
                "answer",
                "Responda brevemente em português sem alegar fatos dos documentos: "
                + state.original_question,
            )
            state.status = "casual"
            return state
        if plan.scope.kind == "ambiguous_document" or contract.unresolved_reference:
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
        if plan.aggregation is not None and any(
            c.chunk_kind == "row_record" and (scope is None or c.document_id in scope)
            for c in self.retriever.chunks
        ):
            from .Tables import aggregate

            self.diagnostics["table_calculation"] = aggregate(
                self.retriever.chunks, scope, plan.aggregation
            )
            table_result = self.diagnostics["table_calculation"]
            table_result["calculation_id"] = "TABLE1"
            self.diagnostics["calculations"] = [
                {
                    "calculation_id": "TABLE1",
                    "requirement_ids": [
                        r.requirement_id for r in contract.requirements
                    ],
                    "result": table_result["result"],
                    "evidence_ids": [],
                    "input_chunk_ids": table_result["input_chunk_ids"],
                    "operation": table_result["operation"],
                }
            ]
        # A planner subquery can be useful for a second hop, but it must not
        # replace the user's resolved wording: structured labels in the corpus
        # (for example, "Coordenador na Instituição") may be present only in
        # that wording.  Preserve deterministic order and deduplicate.
        queries = self.resolver.searches(plan, contract)
        requirement_ids = {r.requirement_id for r in contract.requirements}
        seen_queries = set()
        for hop in range(1, state.max_hops + 1):
            state.current_hop = hop
            self.status("retrieval")
            new_evidence = 0
            previous_ids = {e.evidence_id for e in state.found_evidence}
            executed = 0
            for query in queries[: min(3, self.config.queries_per_hop)]:
                if not set(query.requirement_ids) <= requirement_ids:
                    raise ValueError("Search returned unknown requirement IDs")
                selected_scope = query.document_ids or scope
                if (
                    contract.scope_is_exclusive
                    and contract.mandatory_document_ids
                    and not set(selected_scope or ())
                    <= set(contract.mandatory_document_ids)
                ):
                    raise ValueError("Search cannot expand mandatory scope")
                key = (
                    " ".join(query.text.casefold().split()),
                    tuple(sorted(selected_scope or ())),
                )
                if not key[0] or key in seen_queries:
                    continue
                seen_queries.add(key)
                executed += 1
                state.retrieval_queries.append(query.text)
                self.diagnostics.setdefault("search_contracts", []).append(
                    {
                        **query.model_dump(),
                        "hop_id": hop,
                        "effective_scope": selected_scope,
                    }
                )
                new_evidence += self.collect(query.text, selected_scope)
            self.select_context()
            if not executed or not new_evidence:
                state.stop_reason = (
                    "repeated_query" if not executed else "no_new_evidence"
                )
                break
            if not state.evidence:
                state.stop_reason = "context_budget_exhausted"
                break
            if new_evidence and not any(
                e.evidence_id not in previous_ids for e in state.evidence
            ):
                state.stop_reason = "context_budget_no_new_evidence"
                break
            self.status("reasoning")
            from .Tables import textual_operands, calculate

            operands = textual_operands(state.evidence)
            self.diagnostics["numeric_operands"] = operands
            state.reasoning = self.team.run(
                "reasoning",
                "Extraia fatos com evidence_ids e requirement_ids. Escolha next_action: answer, retrieve, revise_scope, clarify ou abstain. Lacunas exigem missing_requirement_ids. Contexto incompleto NÃO prova ausência no corpus. Use fatos estabelecidos para uma busca dependente. Para identidade, extraia NOME e relação exata; preserve proposta versus decisão e previsão versus realizado. Para calcular, selecione somente IDs de numeric_operands cuja linha/cabeçalho atendem à pergunta; proponha calculations com calculation_id, requirement_ids, operation, operand_ids e printed_total_id quando pertinente. Não calcule mentalmente. Seja conciso.",
                {
                    **self.contract_payload(),
                    "question": plan.resolved_question,
                    "expected_evidence": plan.expected_evidence,
                    "evidence": self.evidence_payload(),
                    "numeric_operands": [
                        {
                            "operand_id": o["operand_id"],
                            "literal": o["literal"],
                            "unit": o["unit"],
                            "column": o["header"],
                            "row_label": o["row"][0],
                        }
                        for o in operands
                    ],
                },
                ReasoningResult,
            )
            calculations = []
            for request in state.reasoning.calculations:
                try:
                    calculations.append(
                        calculate(request, operands, state.evidence, requirement_ids)
                    )
                except ValueError as exc:
                    self.diagnostics.setdefault("calculation_errors", []).append(
                        {
                            "hop_id": hop,
                            "error": str(exc),
                            "requirement_ids": request.requirement_ids,
                        }
                    )
            if calculations:
                self.diagnostics["calculations"] = calculations
                self.diagnostics["table_calculation"] = calculations
            ids = {item.evidence_id for item in state.evidence}
            if any(
                not fact.evidence_ids or not set(fact.evidence_ids) <= ids
                for fact in state.reasoning.established_facts
            ):
                raise ValueError("Reasoning returned unsupported evidence references")
            if not set(state.reasoning.missing_requirement_ids) <= requirement_ids:
                raise ValueError("Reasoning returned unknown missing requirements")
            if not set(state.reasoning.impossibility_evidence_ids) <= ids:
                raise ValueError("Invalid impossibility evidence")
            known_facts = {
                (f.text, tuple(f.evidence_ids)) for f in state.established_facts
            }
            for fact in state.reasoning.established_facts:
                if not set(fact.requirement_ids) <= requirement_ids:
                    raise ValueError("Fact returned unknown requirements")
                key = (fact.text, tuple(fact.evidence_ids))
                if key not in known_facts:
                    state.established_facts.append(fact)
                    known_facts.add(key)
            action, reason = next_action(state.reasoning, contract, hop, state.max_hops)
            state.decisions.append({"hop_id": hop, "action": action, "reason": reason})
            if action in {"answer", "abstain", "clarify"}:
                state.stop_reason = reason
                if action == "clarify":
                    state.status = "clarification_required"
                    state.final_answer = "Qual referência você deseja consultar?"
                    return state
                break
            research = self.team.run(
                "research",
                "Formule novas queries específicas usando os fatos e as lacunas. Não repita queries anteriores.",
                {
                    **self.contract_payload(),
                    "question": plan.resolved_question,
                    "reasoning": state.reasoning.model_dump(),
                    "previous_queries": state.retrieval_queries,
                },
                ResearchResult,
            )
            queries = research.searches or [
                RetrievalQuery(
                    text=q,
                    requirement_ids=state.reasoning.missing_requirement_ids
                    or list(requirement_ids),
                )
                for q in research.queries
            ]
            for query in queries:
                query.document_ids = self.resolver.translate(query.document_ids)
                query.requirement_ids = (
                    query.requirement_ids
                    or state.reasoning.missing_requirement_ids
                    or list(requirement_ids)
                )
            queries = self.resolver.searches(
                plan.model_copy(update={"queries": queries}), contract
            )
            if not contract.mandatory_document_ids:
                # Discovery starts collection-wide. A later reference may
                # narrow to a document established by retrieved facts, never
                # merely to a candidate invented by the planner.
                by_id = {e.evidence_id: e.document_id for e in state.found_evidence}
                proved_documents = {
                    by_id[eid]
                    for fact in state.established_facts
                    for eid in fact.evidence_ids
                    if eid in by_id
                }
                for query in queries:
                    discovered = self.resolver.resolve(query.text)["ids"]
                    query.document_ids = [
                        d for d in discovered if d in proved_documents
                    ]
        if not state.evidence:
            state.status = "abstained"
            state.final_answer = "Não encontrei evidências suficientes para responder."
            return state
        if plan.needs_exhaustive_coverage or (
            scope
            and plan.intent in {"summary", "list_extraction", "document_expansion"}
        ):
            from .Coverage import evidence_batches

            batches = evidence_batches(self, scope)
        else:
            batches = [state.evidence]
        rejected_any, last_verification = False, None
        batch_verdicts, batch_conflicts = [], []
        seen_claims = set()
        processed_evidence = {}
        for batch_index, batch in enumerate(batches):
            state.evidence = batch
            coverage = self.diagnostics.get("coverage")
            if coverage is not None:
                coverage["sent_batches"] += 1
            claims, verification, rejected = self.synthesize(
                batch, batch_index, defer_coverage=len(batches) > 1
            )
            last_verification = verification
            batch_verdicts.extend(verification.claims)
            batch_conflicts.extend(verification.conflicts)
            processed_evidence.update({e.evidence_id: e for e in batch})
            if coverage is not None:
                coverage["completed_batches"] += 1
                coverage["processed_parents"] += len(batch)
                coverage["complete"] = (
                    coverage["completed_batches"] == coverage["prepared_batches"]
                    and not coverage["skipped_parent_ids"]
                )
            rejected_any |= rejected
            for claim in claims:
                key = " ".join(claim.text.casefold().split())
                if key not in seen_claims:
                    state.claims.append(claim)
                    seen_claims.add(key)
        state.evidence = list(processed_evidence.values())
        if len(batches) > 1:
            # No OR across batches: coverage and conflicts are evaluated globally.
            combined = AnswerDraft(claims=state.claims)
            from .Coverage import global_verification

            last_verification, global_payload = global_verification(
                self, combined, batch_verdicts, batch_conflicts
            )
            if (
                not last_verification.central_question_supported
                and state.repair_count == 0
            ):
                state.repair_count += 1
                combined = self.team.run(
                    "answer",
                    "Repare cobertura e conflitos globais uma vez usando apenas os fatos já verificados e seus testemunhos literais. Remova conclusões conflitantes, não invente fatos nem altere cálculos validados.",
                    {
                        **global_payload,
                        "draft": combined.model_dump(),
                        "verification": last_verification.model_dump(),
                        "deterministic_table_calculation": self.diagnostics.get(
                            "table_calculation"
                        ),
                    },
                    AnswerDraft,
                )
                all_evidence = state.evidence
                checked, repaired_verdicts = [], []
                for index, claim in enumerate(combined.claims, 1):
                    claim.claim_id = f"G{index}"
                    state.evidence = [
                        e for e in all_evidence if e.evidence_id in claim.evidence_ids
                    ]
                    if (
                        sum(self.tokens(e.context) for e in state.evidence)
                        > self.config.context_tokens
                    ):
                        self.diagnostics.setdefault("global_repair", []).append(
                            {"claim_id": claim.claim_id, "reason": "context_budget"}
                        )
                        continue
                    v = self.verify(AnswerDraft(claims=[claim]))
                    batch_conflicts.extend(v.conflicts)
                    repaired_verdicts.extend(v.claims)
                    if any(item.status == "SUPPORTED" for item in v.claims):
                        checked.append(claim)
                state.evidence = all_evidence
                combined = AnswerDraft(claims=checked)
                last_verification, _ = global_verification(
                    self, combined, repaired_verdicts, batch_conflicts
                )
            state.claims = useful_claims(combined, last_verification)
        state.verification = last_verification or VerificationResult(claims=[])
        if not state.claims:
            state.status = "abstained"
            state.final_answer = (
                "As fontes apresentam um conflito não resolvido; não posso afirmar uma conclusão segura."
                if state.verification.conflicts
                else "Não encontrei evidências suficientes para responder."
            )
            if self.diagnostics.get("calculation_errors"):
                state.final_answer += " Os operandos ou unidades disponíveis não permitem validar o cálculo."
        else:
            state.status, missing = answer_status(
                contract, state.verification, state.claims
            )
            if not self.diagnostics.get("coverage", {}).get("complete", True):
                state.status = "partial"
                missing.append("Cobertura documental completa não concluída")
            state.final_answer = (
                "Resposta parcial — falta: " + "; ".join(missing) + ".\n\n"
                if state.status == "partial"
                else ""
            ) + "\n\n".join(
                claim.text + " " + " ".join(f"[{eid}]" for eid in claim.evidence_ids)
                for claim in state.claims
            )
        self.focus_cited_sources()
        self.diagnostics["total_seconds"] = time.perf_counter() - started
        return state
