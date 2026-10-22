"""Validated shared state and public evidence contracts."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Scope(BaseModel):
    kind: Literal[
        "ambiguous_document",
        "explicit_single_document",
        "explicit_multi_document",
        "collection_wide",
    ] = "collection_wide"
    document_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def cardinality(self):
        if self.kind == "explicit_single_document" and len(set(self.document_ids)) != 1:
            raise ValueError("single document scope requires exactly one ID")
        if self.kind == "explicit_multi_document" and len(set(self.document_ids)) < 2:
            raise ValueError("multi document scope requires at least two IDs")
        return self


class AnswerRequirement(BaseModel):
    requirement_id: str
    text: str


class RequirementDocumentScope(BaseModel):
    requirement_id: str
    document_ids: list[str] = Field(default_factory=list)
    origin: str = "collection_discovery"


class QuestionContract(BaseModel):
    original_question: str = Field(frozen=True)
    resolved_question: str
    requirements: list[AnswerRequirement]
    mandatory_document_ids: list[str] = Field(default_factory=list)
    candidate_document_ids: list[str] = Field(default_factory=list)
    explicit_entities: list[str] = Field(default_factory=list)
    explicit_dates: list[str] = Field(default_factory=list)
    scope_origin: str = "collection_discovery"
    unresolved_reference: bool = False
    contextual_reference: str = ""
    scope_is_exclusive: bool = True
    requirement_scopes: list[RequirementDocumentScope] = Field(default_factory=list)


class RetrievalQuery(BaseModel):
    text: str
    requirement_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)


class QueryPlan(BaseModel):
    resolved_question: str
    route: Literal["retrieval", "casual"] = "retrieval"
    intent: str = "single_fact"
    scope: Scope = Field(default_factory=Scope)
    initial_queries: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    requires_multi_hop: bool = False
    clarification: str = ""
    aggregation: "TableOperation | None" = None
    requested_facts: list[str] = Field(default_factory=list)
    queries: list[RetrievalQuery] = Field(default_factory=list)
    needs_exhaustive_coverage: bool = False


class TableOperation(BaseModel):
    operation: Literal["count", "sum", "mean", "min", "max", "difference"]
    column: str = ""
    equals: dict[str, str] = Field(default_factory=dict)


QueryPlan.model_rebuild()


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    parent_id: str
    text: str
    section_title: str = ""
    chunk_kind: str = "section_detail"
    chunk_order: int = 0
    source: str = ""
    relative_path: str = ""
    provenance: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class RetrievalOccurrence(BaseModel):
    retrieval_query: str
    hop_id: int
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rrf_score: float = 0
    reranker_score: float | None = None


class EvidenceUnit(Chunk):
    evidence_id: str
    excerpt: str
    context: str
    occurrences: list[RetrievalOccurrence] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)


class Fact(BaseModel):
    text: str
    evidence_ids: list[str] = Field(min_length=1)
    requirement_ids: list[str] = Field(default_factory=list)


class CalculationRequest(BaseModel):
    calculation_id: str
    requirement_ids: list[str] = Field(min_length=1)
    operation: Literal["sum", "difference", "mean", "min", "max"]
    operand_ids: list[str] = Field(min_length=1)
    printed_total_id: str | None = None


class ReasoningResult(BaseModel):
    established_facts: list[Fact] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    sufficient: bool = False
    unanswerable: bool = False
    requires_additional_retrieval: bool = False
    next_action: (
        Literal["answer", "retrieve", "revise_scope", "clarify", "abstain"] | None
    ) = None
    missing_requirement_ids: list[str] = Field(default_factory=list)
    calculations: list[CalculationRequest] = Field(default_factory=list)
    impossibility_evidence_ids: list[str] = Field(default_factory=list)
    impossibility_reason: str = ""


class ResearchResult(BaseModel):
    queries: list[str] = Field(default_factory=list)
    searches: list[RetrievalQuery] = Field(default_factory=list)


class Claim(BaseModel):
    claim_id: str
    text: str
    evidence_ids: list[str]
    requirement_ids: list[str] = Field(default_factory=list)
    calculation_id: str | None = None
    calculation_field: Literal["result", "printed_total", "difference"] = "result"


class RequirementCoverage(BaseModel):
    requirement_id: str
    claim_ids: list[str] = Field(default_factory=list)
    covered: bool = False
    reason: str = ""


class EvidenceConflict(BaseModel):
    requirement_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    reason: str


class AnswerDraft(BaseModel):
    claims: list[Claim] = Field(default_factory=list)


class SourceFocusSelection(BaseModel):
    claim_id: str
    evidence_id: str
    quote: str = Field(min_length=1, max_length=240)


class SourceFocusResult(BaseModel):
    selections: list[SourceFocusSelection] = Field(default_factory=list)


class SupportQuote(BaseModel):
    evidence_id: str
    quote: str = Field(min_length=1, max_length=240)


class ClaimVerification(BaseModel):
    claim_id: str
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]
    reason: str
    support_quotes: list[SupportQuote] = Field(default_factory=list)


class VerificationResult(BaseModel):
    claims: list[ClaimVerification]
    central_question_supported: bool = False
    coverage: list[RequirementCoverage] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_references(self):
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("One verification record per claim")
        if len({c.requirement_id for c in self.coverage}) != len(self.coverage):
            raise ValueError("One coverage record per requirement")
        return self


class GlobalVerification(BaseModel):
    coverage: list[RequirementCoverage] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_coverage(self):
        if len({c.requirement_id for c in self.coverage}) != len(self.coverage):
            raise ValueError("One coverage record per requirement")
        return self


class RAGState(BaseModel):
    original_question: str = ""
    history: list[dict] = Field(default_factory=list)
    plan: QueryPlan | None = None
    question_contract: QuestionContract | None = None
    current_hop: int = 0
    max_hops: int = 3
    retrieval_queries: list[str] = Field(default_factory=list)
    evidence: list[EvidenceUnit] = Field(default_factory=list)
    found_evidence: list[EvidenceUnit] = Field(default_factory=list)
    established_facts: list[Fact] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    reasoning: ReasoningResult = Field(default_factory=ReasoningResult)
    claims: list[Claim] = Field(default_factory=list)
    source_focus: dict[str, list[dict]] = Field(default_factory=dict)
    source_focus_status: dict[str, str] = Field(default_factory=dict)
    verification: VerificationResult | None = None
    repair_count: int = 0
    stop_reason: str = ""
    final_answer: str = ""
    status: str = "running"
