"""Validated shared state and public evidence contracts."""

from typing import Literal
from pydantic import BaseModel, Field


class Scope(BaseModel):
    kind: Literal[
        "ambiguous_document",
        "explicit_single_document",
        "explicit_multi_document",
        "collection_wide",
    ] = "collection_wide"
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


class TableOperation(BaseModel):
    operation: Literal["count", "sum", "mean", "min", "max"]
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


class ReasoningResult(BaseModel):
    established_facts: list[Fact] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    sufficient: bool = False
    unanswerable: bool = False
    requires_additional_retrieval: bool = False


class ResearchResult(BaseModel):
    queries: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    claim_id: str
    text: str
    evidence_ids: list[str]


class AnswerDraft(BaseModel):
    claims: list[Claim] = Field(default_factory=list)


class SourceFocusSelection(BaseModel):
    claim_id: str
    evidence_id: str
    quote: str = Field(min_length=1, max_length=240)


class SourceFocusResult(BaseModel):
    selections: list[SourceFocusSelection] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    claim_id: str
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]
    reason: str


class VerificationResult(BaseModel):
    claims: list[ClaimVerification]
    central_question_supported: bool = False


class RAGState(BaseModel):
    original_question: str = ""
    history: list[dict] = Field(default_factory=list)
    plan: QueryPlan | None = None
    current_hop: int = 0
    max_hops: int = 3
    retrieval_queries: list[str] = Field(default_factory=list)
    evidence: list[EvidenceUnit] = Field(default_factory=list)
    reasoning: ReasoningResult = Field(default_factory=ReasoningResult)
    claims: list[Claim] = Field(default_factory=list)
    source_focus: dict[str, list[dict]] = Field(default_factory=dict)
    source_focus_status: dict[str, str] = Field(default_factory=dict)
    verification: VerificationResult | None = None
    repair_count: int = 0
    stop_reason: str = ""
    final_answer: str = ""
    status: str = "running"
