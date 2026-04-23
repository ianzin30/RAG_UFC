import re

import pytest

from benchmark.analysis import BenchmarkAnalyzer
from benchmark.questions import BenchmarkQuestion
from benchmark.reporting import render_markdown_report


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def tokenize_text(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if token]


def make_candidate(
    candidate_id: str,
    *,
    document_name: str,
    text: str,
    priority_score: int,
    chunk_kind: str = "text",
    priority_score_components: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "document_name": document_name,
        "source": None,
        "source_name": None,
        "chunk_kind": chunk_kind,
        "chunk_order": 1,
        "section_title": None,
        "excerpt": text[:120],
        "text": text,
        "priority_score": priority_score,
        "priority_score_components": dict(priority_score_components or {}),
        "entity_names": [],
        "date_values": [],
        "money_values": [],
        "labeled_facts": [],
    }


def make_trace(
    *,
    generated_answer: str,
    candidate_catalog: dict[str, dict[str, object]],
    stages: dict[str, list[str]],
    answer_context: str = "",
    evidence_score: float = 0.7,
    resolver_status: str = "single_match",
    resolver_selection_mode: str | None = "top_ranked_single",
    document_shortlist: list[str] | None = None,
    matched_documents: list[str] | None = None,
    target_document_name: str | None = None,
) -> dict[str, object]:
    return {
        "answer_text": generated_answer,
        "resolved_question": "Pergunta resolvida",
        "candidate_catalog": candidate_catalog,
        "retrieval_stages": {
            stage_name: {"candidate_ids": candidate_ids}
            for stage_name, candidate_ids in stages.items()
        },
        "retrieval_stage_order": list(stages.keys()),
        "sources": [],
        "retrieval_intent": "specific_fact",
        "target_document_name": target_document_name,
        "evidence_score": evidence_score,
        "abstained": False,
        "answer_context": answer_context,
        "selected_evidence_spans": [],
        "focused_evidence_context_built": False,
        "resolver_status": resolver_status,
        "resolver_confidence": 0.88,
        "resolver_selection_mode": resolver_selection_mode,
        "document_shortlist": list(document_shortlist or []),
        "matched_documents": list(matched_documents or []),
        "matched_aliases": [],
        "document_scores": [],
        "recovery_search_performed": False,
        "recovery_matched_documents": [],
        "extraction_diagnostics": [],
        "explicit_answer_candidates": [],
        "answer_matches_top_evidence_span": None,
        "answer_ignored_top_evidence_span": False,
        "answer_repair_applied": False,
        "answer_repair_reason": None,
        "final_answer_origin": "llm",
    }


@pytest.mark.parametrize(
    ("expected_classification", "trace_builder"),
    [
        (
            "semantic_search_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={distractor["candidate_id"]: distractor},
                stages={
                    "merged": [distractor["candidate_id"]],
                    "prioritized": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
        (
            "reranking_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={
                    relevant["candidate_id"]: relevant,
                    distractor["candidate_id"]: distractor,
                },
                stages={
                    "merged": [relevant["candidate_id"], distractor["candidate_id"]],
                    "prioritized": [distractor["candidate_id"], relevant["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
        (
            "context_assembly_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={
                    relevant["candidate_id"]: relevant,
                    distractor["candidate_id"]: distractor,
                },
                stages={
                    "merged": [relevant["candidate_id"], distractor["candidate_id"]],
                    "prioritized": [relevant["candidate_id"], distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
        (
            "chunking_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={distractor["candidate_id"]: distractor},
                stages={
                    "merged": [distractor["candidate_id"]],
                    "prioritized": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
                target_document_name="RACK.pdf",
                matched_documents=["RACK.pdf"],
                document_shortlist=["RACK.pdf"],
            ),
        ),
        (
            "generation_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nNao sei responder.",
                candidate_catalog={relevant["candidate_id"]: relevant},
                stages={
                    "merged": [relevant["candidate_id"]],
                    "prioritized": [relevant["candidate_id"]],
                    "selected_context": [relevant["candidate_id"]],
                },
                answer_context=relevant["text"],
                target_document_name="RACK.pdf",
                matched_documents=["RACK.pdf"],
                document_shortlist=["RACK.pdf"],
            ),
        ),
        (
            "benchmark_data_mismatch",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={distractor["candidate_id"]: distractor},
                stages={
                    "merged": [distractor["candidate_id"]],
                    "prioritized": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
    ],
)
def test_failure_classification_scenarios(expected_classification: str, trace_builder) -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
        priority_score=95,
    )
    distractor = make_candidate(
        "cand_distractor",
        document_name="OUTRO.pdf",
        text="Trecho irrelevante sem a resposta.",
        priority_score=99,
    )
    trace = trace_builder(relevant, distractor)
    question = BenchmarkQuestion(
        id="q1",
        collection="google_drive_rag",
        question="Qual empresa e parceira do projeto?",
        expected_answer="Dell",
    )
    corpus_entries = [] if expected_classification == "benchmark_data_mismatch" else [relevant, distractor]

    if expected_classification == "chunking_failure":
        distractor["document_name"] = "RACK.pdf"

    result = analyzer.build_question_result(question, trace, corpus_entries)

    assert result["failure"]["classification"] == expected_classification


def test_report_includes_missed_evidence_section() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
        priority_score=95,
    )
    distractor = make_candidate(
        "cand_distractor",
        document_name="OUTRO.pdf",
        text="Trecho irrelevante sem a resposta.",
        priority_score=99,
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nResposta errada",
        candidate_catalog={
            relevant["candidate_id"]: relevant,
            distractor["candidate_id"]: distractor,
        },
        stages={
            "merged": [relevant["candidate_id"], distractor["candidate_id"]],
            "prioritized": [distractor["candidate_id"], relevant["candidate_id"]],
            "selected_context": [distractor["candidate_id"]],
        },
    )
    question = BenchmarkQuestion(
        id="q2",
        collection="google_drive_rag",
        question="Qual empresa e parceira do projeto?",
        expected_answer="Dell",
    )
    result = analyzer.build_question_result(question, trace, [relevant, distractor])
    report = render_markdown_report(
        {
            "run_id": "test-run",
            "generated_at": "2026-04-22T00:00:00+00:00",
            "questions_file": "benchmark/questions.json",
            "collections": ["google_drive_rag"],
            "config_snapshot": {"ufc_model_name": "llama3.1:8b", "rag": {"strict_grounding": True, "min_evidence_score": 0.5}},
            "abstained_count": 0,
            "results": [result],
        }
    )

    assert "A empresa parceira do projeto e a Dell" in report
    assert "reranking_failure" in report


def test_generation_consensus_diagnostics_are_preserved() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
        priority_score=95,
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nA Dell",
        candidate_catalog={relevant["candidate_id"]: relevant},
        stages={
            "merged": [relevant["candidate_id"]],
            "prioritized": [relevant["candidate_id"]],
            "selected_context": [relevant["candidate_id"]],
        },
        answer_context=relevant["text"],
    )
    trace.update(
        {
            "answer_shape": "person_or_org",
            "consensus_dominant_candidate": {
                "text": "Dell",
                "consensus_score": 182,
                "mention_count": 3,
            },
            "candidate_consensus_details": [
                {
                    "text": "Dell",
                    "consensus_score": 182,
                    "mention_count": 3,
                    "question_alignment_score": 92,
                }
            ],
            "explicit_answer_candidates": [
                {
                    "text": "Dell",
                    "consensus_score": 182,
                    "mention_count": 3,
                    "question_alignment_score": 92,
                }
            ],
            "answer_repair_applied": True,
            "answer_repair_reason": "lower_consensus_prefix_variant",
            "final_answer_origin": "grounded_repair",
        }
    )
    question = BenchmarkQuestion(
        id="q3",
        collection="google_drive_rag",
        question="Qual empresa e parceira do projeto?",
        expected_answer="Dell",
    )

    result = analyzer.build_question_result(question, trace, [relevant])

    assert result["generation"]["answer_shape"] == "person_or_org"
    assert result["generation"]["consensus_dominant_candidate"]["text"] == "Dell"
    assert result["generation"]["candidate_consensus_details"][0]["question_alignment_score"] == 92
    assert result["generation"]["answer_repair_reason"] == "lower_consensus_prefix_variant"


def test_report_includes_generation_diagnostics_and_priority_components() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="01-2022_Ata_de_Reuniao.pdf",
        text="A empresa parceira do projeto e a Dell.",
        priority_score=118,
        chunk_kind="section_detail",
        priority_score_components={
            "base_kind_score": 45,
            "target_bonus": 120,
            "exact_overlap_bonus": 24,
            "phrase_hit_bonus": 72,
            "detail_specificity_bonus": 58,
        },
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nDell",
        candidate_catalog={relevant["candidate_id"]: relevant},
        stages={
            "prioritized": [relevant["candidate_id"]],
            "selected_context": [relevant["candidate_id"]],
        },
        answer_context=relevant["text"],
        target_document_name="01-2022_Ata_de_Reuniao.pdf",
        matched_documents=["01-2022_Ata_de_Reuniao.pdf"],
        document_shortlist=["01-2022_Ata_de_Reuniao.pdf"],
    )
    trace["explicit_answer_candidates"] = [
        {"text": "Dell", "score": 92, "mentions": 2, "source_kinds": ["organization_pattern"]}
    ]
    trace["selected_evidence_spans"] = [
        {
            "document_name": "01-2022_Ata_de_Reuniao.pdf",
            "chunk_kind": "section_detail",
            "section_title": "Projetos",
            "text": 'O projeto "AI for Customer Support" ocorreu em parceria com a empresa Dell.',
            "score_components": {"alignment_score": 88, "shape_bonus": 18},
        }
    ]
    trace["focused_evidence_context_built"] = True
    trace["answer_matches_top_evidence_span"] = True
    trace["answer_repair_applied"] = True
    trace["answer_repair_reason"] = "truncated_prefix_match"
    trace["final_answer_origin"] = "grounded_repair"
    question = BenchmarkQuestion(
        id="q3",
        collection="google_drive_rag",
        question='Qual empresa e a parceira do projeto "AI for Customer Support"?',
        expected_answer="Dell",
    )

    result = analyzer.build_question_result(question, trace, [relevant])
    report = render_markdown_report(
        {
            "run_id": "test-run",
            "generated_at": "2026-04-22T00:00:00+00:00",
            "questions_file": "benchmark/questions.json",
            "collections": ["google_drive_rag"],
            "config_snapshot": {"ufc_model_name": "llama3.1:8b", "rag": {"strict_grounding": True, "min_evidence_score": 0.5}},
            "abstained_count": 0,
            "results": [result],
        }
    )

    assert "Consenso da resposta" in report
    assert "Origem final" in report
    assert "Evidencia focalizada" in report
    assert "Seguiu evidencia focalizada" in report
    assert "detail_specificity_bonus=58" in report
