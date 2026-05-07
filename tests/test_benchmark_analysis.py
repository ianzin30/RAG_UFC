from __future__ import annotations

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
    chunk_kind: str = "text",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "document_name": document_name,
        "source": f"data/collections/google_drive_rag/{document_name}",
        "source_name": document_name,
        "chunk_kind": chunk_kind,
        "chunk_order": 1,
        "section_title": None,
        "excerpt": text[:120],
        "text": text,
        "priority_score": None,
        "priority_score_components": None,
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
    evidence_score: float = 0.7,
    resolver_status: str = "collection_wide",
    resolver_selection_mode: str | None = "collection_wide",
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
        "answer_context": "",
        "selected_evidence_spans": [],
        "focused_evidence_context_built": False,
        "resolver_status": resolver_status,
        "resolver_confidence": 0.0,
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


def make_question() -> BenchmarkQuestion:
    return BenchmarkQuestion(
        id="q1",
        collection="google_drive_rag",
        question="Qual empresa e parceira do projeto?",
        expected_answer="Dell",
        source_document="RACK.pdf",
    )


def test_currency_structured_matching_accepts_equivalent_formats() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)

    assert analyzer._text_support_level("Bolsa aprovada: R$ 5.500,00.", ["5500,00"]) == "implicit"
    assert analyzer._text_support_level("Bolsa aprovada: 5.500,00 reais.", ["R$ 5.500,00"]) == "implicit"


def test_currency_structured_matching_rejects_different_amounts() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)

    assert analyzer._text_support_level("Bolsa aprovada: R$ 7.000,00.", ["R$ 5.500,00"]) == "not_found"


def test_range_structured_matching_preserves_regime_qualifiers() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    expected = ["Minima de 13 e maxima de 18 horas semanais para o regime de 40 horas."]

    wrong_regime_text = (
        "Carga horaria minima de 08 e maxima de 12 horas semanais "
        "para quem concorre a vaga no regime de 20 horas."
    )
    right_regime_text = (
        "Carga horaria minima de 08 e maxima de 12 horas semanais para o regime de 20 horas; "
        "e minima de 13 e maxima de 18 horas semanais para o regime de 40 horas."
    )

    assert analyzer._text_support_level(wrong_regime_text, expected) == "not_found"
    assert analyzer._text_support_level(right_regime_text, expected) in {"explicit", "implicit"}


def test_runtime_candidate_support_counts_when_corpus_id_differs() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    corpus_relevant = make_candidate(
        "corpus_id",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
    )
    runtime_relevant = {
        **make_candidate(
            "runtime_id",
            document_name="RACK.pdf",
            text="A empresa parceira do projeto e a Dell.",
        ),
        "chunk_order": 99,
    }
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nA empresa parceira e a Dell.",
        candidate_catalog={runtime_relevant["candidate_id"]: runtime_relevant},
        stages={
            "dense_mmr": [runtime_relevant["candidate_id"]],
            "lexical": [],
            "candidate_pool": [runtime_relevant["candidate_id"]],
            "llm_selected": [runtime_relevant["candidate_id"]],
            "selected_context": [runtime_relevant["candidate_id"]],
        },
    )

    result = analyzer.build_question_result(make_question(), trace, [corpus_relevant])

    assert result["failure"]["classification"] == "no_failure"
    assert result["retrieval"]["metrics"]["expected_answer_in_pool"] is True
    assert result["retrieval"]["metrics"]["expected_answer_in_context"] is True


def test_wrong_generated_answer_with_supported_context_is_generation_failure() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    question = BenchmarkQuestion(
        id="q_money",
        collection="google_drive_rag",
        question="Qual o valor da bolsa?",
        expected_answer="R$ 5.500,00",
        accepted_answers=("5500,00", "5.500,00"),
        source_document="RACK.pdf",
    )
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A bolsa do coordenador foi aprovada no valor de R$ 5.500,00.",
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nA bolsa aprovada foi de R$ 7.000,00.",
        candidate_catalog={relevant["candidate_id"]: relevant},
        stages={
            "dense_mmr": [relevant["candidate_id"]],
            "lexical": [],
            "candidate_pool": [relevant["candidate_id"]],
            "llm_selected": [relevant["candidate_id"]],
            "selected_context": [relevant["candidate_id"]],
        },
    )

    result = analyzer.build_question_result(question, trace, [relevant])

    assert result["failure"]["classification"] == "generation_failure"
    assert result["grounding"]["generated_answer_support"] == "not_found"


@pytest.mark.parametrize(
    ("expected_classification", "trace_builder"),
    [
        (
            "retrieval_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={distractor["candidate_id"]: distractor},
                stages={
                    "dense_mmr": [distractor["candidate_id"]],
                    "lexical": [],
                    "candidate_pool": [distractor["candidate_id"]],
                    "llm_selected": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
        (
            "selection_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={
                    relevant["candidate_id"]: relevant,
                    distractor["candidate_id"]: distractor,
                },
                stages={
                    "dense_mmr": [relevant["candidate_id"], distractor["candidate_id"]],
                    "lexical": [],
                    "candidate_pool": [relevant["candidate_id"], distractor["candidate_id"]],
                    "llm_selected": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
            ),
        ),
        (
            "generation_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nNao sei responder.",
                candidate_catalog={relevant["candidate_id"]: relevant},
                stages={
                    "dense_mmr": [relevant["candidate_id"]],
                    "lexical": [],
                    "candidate_pool": [relevant["candidate_id"]],
                    "llm_selected": [relevant["candidate_id"]],
                    "selected_context": [relevant["candidate_id"]],
                },
            ),
        ),
        (
            "document_resolution_failure",
            lambda relevant, distractor: make_trace(
                generated_answer="**RETRIEVAL**\n\nResposta errada",
                candidate_catalog={distractor["candidate_id"]: distractor},
                stages={
                    "dense_mmr": [distractor["candidate_id"]],
                    "lexical": [],
                    "candidate_pool": [distractor["candidate_id"]],
                    "llm_selected": [distractor["candidate_id"]],
                    "selected_context": [distractor["candidate_id"]],
                },
                resolver_status="single_match",
                resolver_selection_mode="explicit_reference",
                target_document_name="OUTRO.pdf",
                matched_documents=["OUTRO.pdf"],
                document_shortlist=["OUTRO.pdf"],
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
    )
    distractor = make_candidate(
        "cand_distractor",
        document_name="OUTRO.pdf",
        text="Trecho irrelevante sem a resposta.",
    )
    trace = trace_builder(relevant, distractor)

    result = analyzer.build_question_result(make_question(), trace, [relevant, distractor])

    assert result["failure"]["classification"] == expected_classification


def test_non_explicit_miss_is_not_document_resolution_failure() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
    )
    distractor = make_candidate(
        "cand_distractor",
        document_name="OUTRO.pdf",
        text="Trecho irrelevante sem a resposta.",
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nResposta errada",
        candidate_catalog={distractor["candidate_id"]: distractor},
        stages={
            "dense_mmr": [distractor["candidate_id"]],
            "lexical": [],
            "candidate_pool": [distractor["candidate_id"]],
            "llm_selected": [distractor["candidate_id"]],
            "selected_context": [distractor["candidate_id"]],
        },
        resolver_status="collection_wide",
        resolver_selection_mode="collection_wide",
    )

    result = analyzer.build_question_result(make_question(), trace, [relevant, distractor])

    assert result["failure"]["classification"] == "retrieval_failure"


def test_retriever_first_metrics_are_reported() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nA empresa parceira e a Dell.",
        candidate_catalog={relevant["candidate_id"]: relevant},
        stages={
            "dense_mmr": [relevant["candidate_id"]],
            "lexical": [],
            "candidate_pool": [relevant["candidate_id"]],
            "llm_selected": [relevant["candidate_id"]],
            "selected_context": [relevant["candidate_id"]],
        },
    )

    result = analyzer.build_question_result(make_question(), trace, [relevant])

    assert result["failure"]["classification"] == "no_failure"
    assert result["retrieval"]["metrics"]["source_document_rank"] == 1
    assert result["retrieval"]["metrics"]["source_document_in_pool"] is True
    assert result["retrieval"]["metrics"]["expected_answer_in_pool"] is True
    assert result["retrieval"]["metrics"]["expected_answer_in_context"] is True
    assert result["retrieval"]["metrics"]["context_hit_rate"] == 1.0


def test_report_includes_retriever_metrics_and_selection_failures() -> None:
    analyzer = BenchmarkAnalyzer(normalize_text=normalize_text, tokenize_text=tokenize_text)
    relevant = make_candidate(
        "cand_relevant",
        document_name="RACK.pdf",
        text="A empresa parceira do projeto e a Dell.",
    )
    distractor = make_candidate(
        "cand_distractor",
        document_name="OUTRO.pdf",
        text="Trecho irrelevante sem a resposta.",
    )
    trace = make_trace(
        generated_answer="**RETRIEVAL**\n\nResposta errada",
        candidate_catalog={
            relevant["candidate_id"]: relevant,
            distractor["candidate_id"]: distractor,
        },
        stages={
            "dense_mmr": [relevant["candidate_id"], distractor["candidate_id"]],
            "lexical": [],
            "candidate_pool": [relevant["candidate_id"], distractor["candidate_id"]],
            "llm_selected": [distractor["candidate_id"]],
            "selected_context": [distractor["candidate_id"]],
        },
    )
    result = analyzer.build_question_result(make_question(), trace, [relevant, distractor])
    report = render_markdown_report(
        {
            "run_id": "test-run",
            "generated_at": "2026-04-22T00:00:00+00:00",
            "questions_file": "benchmark/questions.json",
            "collections": ["google_drive_rag"],
            "config_snapshot": {
                "ufc_model_name": "llama3.1:8b",
                "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
            },
            "abstained_count": 0,
            "results": [result],
        }
    )

    assert "Documento-fonte no pool" in report
    assert "Resposta esperada no contexto" in report
    assert "Avaliacao por agente" in report
    assert "selection_failure" in report
    assert "pool=1" in report
