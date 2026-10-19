"""Regression controls; no model downloads, secrets or real generation."""

from decimal import Decimal
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from application.service.rag.v2.Models import (
    Chunk,
    EvidenceUnit,
    QueryPlan,
    QuestionContract,
    AnswerRequirement,
    Scope,
    ReasoningResult,
    AnswerDraft,
    VerificationResult,
    CalculationRequest,
    Claim,
    RetrievalOccurrence,
    Fact,
    SupportQuote,
    ClaimVerification,
    EvidenceConflict,
    GlobalVerification,
    RetrievalQuery,
)
from application.service.rag.v2.Planning import DocumentResolver, explicit_entities
from application.service.rag.v2.Decision import next_action
from application.service.rag.v2.Grounding import (
    validate_verification,
    validate_support_quotes,
    validate_entity_constraints,
    useful_claims,
    answer_status,
)
from application.service.rag.v2.Tables import (
    decimal_value,
    textual_operands,
    calculate,
    calculation_matches_claim,
)
from application.service.rag.v2.Flow import RAGFlow
from application.service.rag.v2.Config import V2Config
from application.service.rag.v2.Coverage import evidence_batches


def contract(*texts):
    return QuestionContract(
        original_question="Pergunta original",
        resolved_question="Pergunta resolvida",
        requirements=[
            AnswerRequirement(requirement_id=f"R{i}", text=t)
            for i, t in enumerate(texts or ("nome do coordenador",), 1)
        ],
    )


def unit(text, eid="E1", parent="p", score=1, hop=1):
    return EvidenceUnit(
        evidence_id=eid,
        document_id="d",
        document_name="Ata.pdf",
        chunk_id=eid,
        parent_id=parent,
        text=text,
        excerpt=text,
        context=text,
        occurrences=[
            RetrievalOccurrence(
                retrieval_query="query", hop_id=hop, reranker_score=score
            )
        ],
    )


def test_original_question_is_immutable():
    with pytest.raises(ValidationError):
        contract().original_question = "Outro assunto"


@pytest.mark.parametrize(
    "kind,ids",
    [
        ("explicit_single_document", []),
        ("explicit_single_document", ["a", "b"]),
        ("explicit_multi_document", ["a", "a"]),
    ],
)
def test_invalid_scope_cardinality(kind, ids):
    with pytest.raises(ValidationError):
        Scope(kind=kind, document_ids=ids)


def resolver():
    chunks = [
        Chunk(
            chunk_id="a",
            parent_id="pa",
            document_id="a",
            document_name="Ata.pdf",
            section_title="Reunião realizada em 13 de julho de 2022.",
            text="Decisão aprovada. Assinado em 19/08/2022.",
        ),
        Chunk(
            chunk_id="b",
            parent_id="pb",
            document_id="b",
            document_name="Ata agosto.pdf",
            section_title="Reunião realizada em 19 de agosto de 2022.",
            text="Tutor Fernando.",
        ),
    ]
    return DocumentResolver(
        [
            {"document_id": c.document_id, "document_name": c.document_name}
            for c in chunks
        ],
        chunks,
    )


def test_meeting_date_not_signature_and_short_refs():
    r = resolver()
    plan = QueryPlan(
        resolved_question="Qual decisão?",
        scope=Scope(kind="explicit_single_document", document_ids=["D2"]),
    )
    c = r.contract("Na reunião de 13/07/2022, qual decisão?", [], plan)
    assert c.mandatory_document_ids == ["a"]
    assert plan.scope.document_ids == ["a"]
    assert r.resolve("Na ata de 19/08/2022?")["ids"] == ["b"]
    assert r.records[0]["date_provenance"][0]["chunk_id"] == "a"


def test_inferred_candidate_not_mandatory_and_unknown_refs_rejected():
    r = resolver()
    plan = QueryPlan(
        resolved_question="Quem coordena Rack Build?",
        scope=Scope(kind="explicit_single_document", document_ids=["D1"]),
    )
    c = r.contract(plan.resolved_question, [], plan)
    assert c.candidate_document_ids == ["a"] and c.mandatory_document_ids == []
    assert plan.scope.kind == "collection_wide"
    with pytest.raises(ValueError):
        r.translate(["D999"])


def test_followup_contract_preserves_banca_and_uses_latest_topic():
    r = resolver()
    plan = QueryPlan(resolved_question="De qual instituição é o presidente da banca?")
    c = r.contract(
        "De qual instituição é o presidente dela?",
        [
            {"role": "user", "content": "Ata de 13/07/2022."},
            {"role": "user", "content": "Banca aprovada na reunião de 19/08/2022."},
        ],
        plan,
    )
    assert "Banca" in c.contextual_reference
    assert c.mandatory_document_ids == ["b"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"unanswerable": True, "requires_additional_retrieval": True},
        {"next_action": "abstain", "unanswerable": True},
        {"next_action": "answer", "requires_additional_retrieval": True},
        {"next_action": "answer", "missing_requirement_ids": ["R1"]},
    ],
)
def test_conflicting_or_unfounded_stop_continues_discovery(kwargs):
    assert next_action(ReasoningResult(**kwargs), contract(), 1, 3)[0] == "retrieve"
    assert next_action(ReasoningResult(**kwargs), contract(), 3, 3) == (
        "abstain",
        "max_hops",
    )


def draft():
    return AnswerDraft(
        claims=[
            Claim(
                claim_id="C1",
                text="Pessoa A coordena Atlas.",
                evidence_ids=["E1"],
                requirement_ids=["R1"],
            )
        ]
    )


def verdict(**kwargs):
    return VerificationResult(
        claims=[{"claim_id": "C1", "status": "SUPPORTED", "reason": "literal"}],
        central_question_supported=True,
        coverage=[{"requirement_id": "R1", "claim_ids": ["C1"], "covered": True}],
        **kwargs,
    )


def test_coverage_not_boolean_or_and_partial_identifies_missing():
    c, d = contract("nome", "instituição"), draft()
    v = validate_verification(verdict(), d, c, {"E1"})
    assert not v.central_question_supported
    assert answer_status(c, v, useful_claims(d, v)) == ("partial", ["instituição"])


def test_true_but_unrelated_claim_not_delivered():
    d = draft()
    d.claims[0].requirement_ids = []
    v = validate_verification(verdict(), d, contract(), {"E1"})
    assert useful_claims(d, v) == []


def test_global_conflict_invalidates_coverage_even_with_supported_claim():
    v = verdict(
        conflicts=[
            {
                "requirement_ids": ["R1"],
                "evidence_ids": ["E1", "E2"],
                "reason": "Coordenadores incompatíveis",
            }
        ]
    )
    v = validate_verification(v, draft(), contract(), {"E1", "E2"})
    assert not v.central_question_supported and not useful_claims(draft(), v)


def test_missing_or_wrong_citation_cannot_be_supported():
    v = validate_verification(verdict(), draft(), contract(), set())
    assert v.claims[0].status == "UNSUPPORTED"
    assert not v.central_question_supported


class Tokenizer:
    def encode(self, text, **kwargs):
        return text.split()


def flow():
    return RAGFlow(
        SimpleNamespace(),
        SimpleNamespace(chunks=[]),
        {},
        [],
        V2Config(child_tokens=32, parent_tokens=64, context_tokens=128),
        Tokenizer(),
    )


def test_recomposition_preserves_facts_and_replaces_stale_context():
    f = flow()
    f.state.current_hop = 2
    f.state.found_evidence = [
        unit("fact " * 30),
        unit("old " * 90, "E2", "p2", score=20),
        unit("new " * 90, "E3", "p3", score=1, hop=2),
    ]
    f.state.established_facts = [Fact(text="Known fact", evidence_ids=["E1"])]
    f.select_context()
    assert [e.evidence_id for e in f.state.evidence] == ["E1", "E3"]
    assert len(f.state.found_evidence) == 3
    assert f.diagnostics["context_selection"][0]["reason"] == "token_budget"


def test_prepared_batches_are_not_processed_or_complete():
    f = flow()
    f.state.plan = QueryPlan(resolved_question="Resumo")
    f.retriever.chunks = [
        Chunk(
            chunk_id="a",
            parent_id="pa",
            document_id="a",
            document_name="A",
            text="text",
        )
    ]
    f.parents = {"pa": "text"}
    assert len(evidence_batches(f, None)) == 1
    c = f.diagnostics["coverage"]
    assert c["prepared_parents"] == 1 and c["processed_parents"] == 0
    assert not c["complete"] and c["sent_batches"] == c["completed_batches"] == 0


@pytest.mark.parametrize(
    "value,expected",
    [
        ("10.800", "10800"),
        ("R$ 6.150,04", "6150.04"),
        (6150.04, "6150.04"),
        (Decimal("0.10"), "0.10"),
        ("0,10", "0.10"),
    ],
)
def test_typed_numbers_and_brazilian_strings(value, expected):
    assert str(decimal_value(value)) == expected


@pytest.mark.parametrize("value", ["", None, "1.23", "1,2,3", "nan"])
def test_empty_and_ambiguous_cells_rejected(value):
    with pytest.raises(ValueError):
        decimal_value(value)


def test_t04_source_total_diff_and_repair_cannot_replace_arithmetic():
    e = unit(
        "| Item | Horas |\n| --- | --- |\n| A | 10.800 |\n| B | 8.400 |\n| C | 1.920 |\n| TOTAL | 21.200 |"
    )
    operands = textual_operands([e])
    assert len(operands) == 4
    request = CalculationRequest(
        calculation_id="K1",
        requirement_ids=["R1"],
        operation="sum",
        operand_ids=[o["operand_id"] for o in operands[:3]],
        printed_total_id=operands[3]["operand_id"],
    )
    result = calculate(request, operands, [e], ["R1"])
    assert (result["result"], result["printed_total"], result["difference"]) == (
        "21120",
        "21200",
        "80",
    )
    c = Claim(
        claim_id="C1",
        text="10.800 + 8.400 + 1.920 = 21.120 horas.",
        evidence_ids=["E1"],
        requirement_ids=["R1"],
        calculation_id="K1",
    )
    assert calculation_matches_claim(c, [result])
    c.text = "10.800 + 8.400 + 1.920 = 21.200 horas."
    assert not calculation_matches_claim(c, [result])
    c.calculation_id = None
    assert not calculation_matches_claim(c, [result])


def test_t05_difference_validated_cells_and_provenance():
    e = unit(
        "| Despesa | Março | Abril |\n| --- | --- | --- |\n| RH Direto | R$ 90.779,76 | R$ 84.629,72 |\n| Outros | | |"
    )
    operands = textual_operands([e])
    request = CalculationRequest(
        calculation_id="K1",
        requirement_ids=["R1"],
        operation="difference",
        operand_ids=[o["operand_id"] for o in operands],
    )
    result = calculate(request, operands, [e], ["R1"])
    assert result["result"] == "6150.04" and result["unit"] == "BRL"
    assert all(e.excerpt[o["start"] : o["end"]] == o["literal"] for o in operands)
    operands[0]["literal"] = "Inventado"
    with pytest.raises(ValueError, match="provenance"):
        calculate(request, operands, [e], ["R1"])


def test_unit_mismatch_blocks_calculation():
    e = unit("| Item | Horas | Valor |\n| --- | --- | --- |\n| A | 10 | R$ 20,00 |")
    operands = textual_operands([e])
    request = CalculationRequest(
        calculation_id="K1",
        requirement_ids=["R1"],
        operation="sum",
        operand_ids=[o["operand_id"] for o in operands],
    )
    with pytest.raises(ValueError, match="units"):
        calculate(request, operands, [e], ["R1"])


@pytest.mark.parametrize("quote", ["Texto inventado", "", "PESSOA A"])
def test_support_witness_cannot_be_missing_fabricated_or_paraphrased(quote):
    d, v = draft(), verdict()
    if quote:
        v.claims[0].support_quotes = [SupportQuote(evidence_id="E1", quote=quote)]
    result = validate_support_quotes(v, d, [unit("Pessoa A coordena Atlas.")])
    assert result.claims[0].status == "UNSUPPORTED"


def test_support_quote_accepts_whitespace_but_never_borrows_other_citation():
    d, v = draft(), verdict()
    v.claims[0].support_quotes = [
        SupportQuote(evidence_id="E1", quote="Pessoa A coordena Atlas.")
    ]
    assert (
        validate_support_quotes(v, d, [unit("Pessoa  A\ncoordena Atlas.")])
        .claims[0]
        .status
        == "SUPPORTED"
    )
    v.claims[0].support_quotes[0].evidence_id = "E2"
    assert (
        validate_support_quotes(
            v, d, [unit("irrelevant"), unit("Pessoa A coordena Atlas.", "E2")]
        )
        .claims[0]
        .status
        == "UNSUPPORTED"
    )


def test_multiheader_resource_table_keeps_row_unit_and_printed_total():
    e = unit(
        "| | RH Direto | RH Direto | RH Indireto | Total |\n| --- | --- | --- | --- | --- |\n| Nível | Superior | Médio | Superior | |\n| Total de horas trabalhadas | 10.800 | 8.400 | 1.920 | 21.200 |"
    )
    operands = textual_operands([e])
    assert len(operands) == 4 and {o["unit"] for o in operands} == {"hour"}
    request = CalculationRequest(
        calculation_id="K",
        requirement_ids=["R1"],
        operation="sum",
        operand_ids=[o["operand_id"] for o in operands[:3]],
        printed_total_id=operands[-1]["operand_id"],
    )
    assert calculate(request, operands, [e], ["R1"])["difference"] == "80"


def test_narrative_currency_is_literal_and_mixed_locale_is_not_partial_operand():
    e = unit(
        "Anterior R$ 4.195.352,34; revisado R$ 3.516.108,71. Ambíguo: R$ 964,025.57."
    )
    operands = textual_operands([e])
    assert len(operands) == 2
    request = CalculationRequest(
        calculation_id="K",
        requirement_ids=["R1"],
        operation="difference",
        operand_ids=[o["operand_id"] for o in operands],
    )
    assert calculate(request, operands, [e], ["R1"])["result"] == "679243.63"


def test_named_project_alias_is_proved_in_source_not_planner_guess():
    c = Chunk(
        chunk_id="c",
        parent_id="p",
        document_id="d",
        document_name="RACK.pdf",
        section_title="Projeto",
        text="Projeto\nRack Build Deployment Validation and Provisioning II",
    )
    r = DocumentResolver([{"document_id": "d", "document_name": c.document_name}], [c])
    plan = QueryPlan(
        resolved_question="Quem coordena Rack Build Deployment Validation and Provisioning II?"
    )
    assert r.contract(plan.resolved_question, [], plan).mandatory_document_ids == ["d"]
    assert r.records[0]["alias_provenance"][0]["chunk_id"] == "c"


def test_dependent_temporal_query_does_not_trap_earlier_fact_in_later_ata():
    r = resolver()
    plan = QueryPlan(
        resolved_question="Quem era secretário do Edital 2021 e qual disciplina assumiu em 19/08/2022?",
        requested_facts=[
            "Secretário da comissão do Edital 2021",
            "Disciplina assumida em 19/08/2022",
        ],
        queries=[
            RetrievalQuery(
                text="secretário comissão Edital 2021", requirement_ids=["R1"]
            ),
            RetrievalQuery(
                text="disciplina na ata de 19/08/2022", requirement_ids=["R2"]
            ),
        ],
    )
    c = r.contract(plan.resolved_question, [], plan)
    assert not c.scope_is_exclusive and c.mandatory_document_ids == ["b"]
    searches = r.searches(plan, c)
    assert searches[0].document_ids == [] and searches[1].document_ids == ["b"]
    c = r.contract(
        "Somente na ata de 19/08/2022: secretário de 2021 e disciplina?", [], plan
    )
    assert c.scope_is_exclusive
    assert all(q.document_ids == ["b"] for q in r.searches(plan, c))


def test_global_verification_preserves_cross_batch_conflict_and_never_ors_coverage():
    from application.service.rag.v2.Coverage import global_verification

    f = flow()
    f.state.plan = QueryPlan(resolved_question="Nome?")
    f.state.question_contract = contract()
    f.state.evidence = [unit("Pessoa A."), unit("Pessoa B.", "E2")]
    d = draft()
    local = [
        ClaimVerification(
            claim_id="C1",
            status="SUPPORTED",
            reason="local",
            support_quotes=[SupportQuote(evidence_id="E1", quote="Pessoa A.")],
        )
    ]

    class Team:
        def run(self, role, instruction, payload, schema):
            assert schema is GlobalVerification
            assert "text" not in payload["evidence"][0]
            assert (
                payload["batch_support"][0]["support_quotes"][0]["quote"] == "Pessoa A."
            )
            return schema.model_validate(
                {
                    "coverage": [
                        {"requirement_id": "R1", "claim_ids": ["C1"], "covered": True}
                    ]
                }
            )

    f.team = Team()
    known = EvidenceConflict(
        requirement_ids=["R1"],
        evidence_ids=["E1", "E2"],
        claim_ids=["REJECTED"],
        reason="Incompatible roles",
    )
    v, _ = global_verification(f, d, local, [known])
    assert not v.central_question_supported and v.conflicts[0].claim_ids == []
    with pytest.raises(ValueError, match="completed local"):
        global_verification(f, d, [], [])


def test_duplicate_coverage_goes_through_central_structured_repair():
    from application.service.rag.v2.Providers import ProviderRegistry, Capabilities
    from application.service.rag.v2.Config import LLMConfig
    import json

    class Provider:
        capabilities = Capabilities()

        def __init__(self, *args):
            self.count = 0

        def identity(self):
            return {"provider": "fake", "logical_model": "test"}

        def generate(self, prompt, schema=None):
            self.count += 1
            data = verdict().model_dump()
            if self.count == 1:
                data["coverage"] *= 2
            else:
                assert "One coverage record" in prompt
            return json.dumps(data)

    registry = ProviderRegistry(LLMConfig(provider="fake"))
    registry.factories["fake"] = Provider
    result = registry.structured("verification", "verify", VerificationResult)
    assert len(result.coverage) == 1 and len(registry.calls) == 2


def test_first_batch_failure_never_reports_prepared_parents_as_processed():
    class Team:
        def run(self, role, instruction, payload, schema):
            if role == "planner":
                return schema.model_validate(
                    {"resolved_question": "Resumo", "needs_exhaustive_coverage": True}
                )
            if role == "reasoning":
                return schema.model_validate(
                    {"next_action": "answer", "sufficient": True}
                )
            raise RuntimeError("first batch failed")

    class Retriever:
        chunks = [
            Chunk(
                chunk_id="a",
                parent_id="pa",
                document_id="a",
                document_name="A",
                text="text",
            )
        ]

        def search(self, query, scope, hop):
            return [
                {
                    "position": 0,
                    "chunk_id": "a",
                    "dense_rank": 1,
                    "sparse_rank": 1,
                    "rrf_score": 0.1,
                    "reranker_score": 2,
                }
            ], {"hop_id": hop, "query": query, "stages": {}}

    f = RAGFlow(
        Team(),
        Retriever(),
        {"pa": "text"},
        [{"document_id": "a"}],
        V2Config(),
        Tokenizer(),
    )
    f.state.original_question = "Resumo"
    with pytest.raises(RuntimeError, match="first batch"):
        f.kickoff()
    assert f.diagnostics["coverage"]["prepared_parents"] == 1
    assert f.diagnostics["coverage"]["sent_batches"] == 1
    assert (
        f.diagnostics["coverage"]["processed_parents"]
        == f.diagnostics["coverage"]["completed_batches"]
        == 0
    )
    assert not f.diagnostics["coverage"]["complete"]


def test_valid_literal_quote_of_wrong_project_cannot_cover_explicit_entity():
    # Exact punctuation: this rejection must not depend on the model changing
    # quote marks or whitespace in a witness.
    c = contract("Quem coordena o projeto cujo firmware usa Redfish?")
    c.explicit_entities = ["Redfish"]
    e = unit('O projeto "Educação FNDE" é coordenado por José Macedo.')
    d = AnswerDraft(
        claims=[
            Claim(
                claim_id="C1",
                text="O projeto cujo firmware usa Redfish é coordenado por José Macedo.",
                evidence_ids=["E1"],
                requirement_ids=["R1"],
            )
        ]
    )
    v = verdict()
    v.claims[0].support_quotes = [SupportQuote(evidence_id="E1", quote=e.excerpt)]
    v = validate_support_quotes(v, d, [e])
    assert v.claims[0].status == "SUPPORTED"
    v = validate_entity_constraints(v, d, c, [e], DocumentResolver([], []))
    v = validate_verification(v, d, c, {"E1"})
    assert v.claims[0].status == "UNSUPPORTED" and not useful_claims(d, v)


def test_generic_capitalized_document_label_is_not_a_named_entity():
    entities = explicit_entities("Quem foi secretário da comissão do Edital 13/2025?")
    assert "Edital" not in entities and "Quem" not in entities


def test_named_entities_keep_technical_terms_names_and_acronyms():
    entities = explicit_entities(
        "Quem coordena o projeto via Redfish? Pablo Mayckon Silva Farias usa ASTEF."
    )
    assert "Redfish" in entities
    assert "Pablo Mayckon Silva Farias" in entities
    assert "ASTEF" in entities


def test_missing_calculation_is_not_replaced_by_generative_arithmetic():
    f = flow()
    f.state.plan = QueryPlan(resolved_question="Qual a soma?")
    f.state.question_contract = contract("Soma dos valores")
    f.state.evidence = [unit("A vale 1; B vale 2.")]
    d = AnswerDraft(
        claims=[
            Claim(
                claim_id="C1",
                text="A soma é 4.",
                evidence_ids=["E1"],
                requirement_ids=["R1"],
            )
        ]
    )
    v = verdict()
    v.claims[0].support_quotes = [
        SupportQuote(evidence_id="E1", quote="A vale 1; B vale 2.")
    ]
    f.team = SimpleNamespace(run=lambda *args: v)
    checked = f.verify(d)
    assert (
        checked.claims[0].status == "UNSUPPORTED"
        and not checked.central_question_supported
    )


def test_unrewritten_followup_is_bound_to_explicit_history_not_abandoned():
    r = resolver()
    question = "De qual instituição é o presidente dela?"
    plan = QueryPlan(resolved_question=question)
    c = r.contract(
        question, [{"role": "user", "content": "Banca da reunião de 19/08/2022"}], plan
    )
    assert not c.unresolved_reference
    assert c.original_question == question
    assert "Banca" in c.resolved_question and "19/08/2022" in c.resolved_question
    assert c.mandatory_document_ids == ["b"]


def test_same_named_documents_require_collection_not_arbitrary_first_id():
    chunks = [
        Chunk(
            chunk_id=i,
            parent_id=i,
            document_id=i,
            document_name="DocAlpha.pdf",
            text="source",
        )
        for i in ("a", "b")
    ]
    r = DocumentResolver(
        [
            {
                "document_id": "a",
                "document_name": "DocAlpha.pdf",
                "relative_path": "azul/doc.md",
            },
            {
                "document_id": "b",
                "document_name": "DocAlpha.pdf",
                "relative_path": "verde/doc.md",
            },
        ],
        chunks,
    )
    plan = QueryPlan(resolved_question="Quem consta no DocAlpha?")
    c = r.contract(plan.resolved_question, [], plan)
    assert plan.scope.kind == "ambiguous_document" and c.candidate_document_ids == [
        "a",
        "b",
    ]
    plan = QueryPlan(resolved_question="Quem consta no DocAlpha da coleção azul?")
    assert r.contract(plan.resolved_question, [], plan).mandatory_document_ids == ["a"]
