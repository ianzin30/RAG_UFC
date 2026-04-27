import json
import re
from pathlib import Path

from benchmark.orchestrator import BenchmarkRunner
from benchmark.questions import BenchmarkQuestion
from benchmark.run import _write_outputs


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def tokenize_text(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if token]


class FakeService:
    instances = []

    def __init__(self) -> None:
        self.loaded_collections: list[str] = []
        self.calls: list[tuple[str, object]] = []
        self.last_retrieval_focus = {"dirty": True}
        self._corpus_candidate = {
            "candidate_id": "cand_relevant",
            "document_name": "RACK.pdf",
            "source": "data/collections/google_drive_rag/88_RACK.md",
            "source_name": "88_RACK.md",
            "chunk_kind": "text",
            "chunk_order": 1,
            "section_title": None,
            "excerpt": "A empresa parceira do projeto e a Dell.",
            "text": "A empresa parceira do projeto e a Dell.",
            "priority_score": 90,
            "entity_names": [],
            "date_values": [],
            "money_values": [],
            "labeled_facts": [],
        }
        FakeService.instances.append(self)

    def load_collection(self, collection_name: str) -> None:
        self.loaded_collections.append(collection_name)
        self.calls.append(("load_collection", collection_name))
        progress_callback = getattr(self, "_benchmark_progress_callback", None)
        if callable(progress_callback):
            progress_callback(
                {
                    "event": "collection_cache_restored",
                    "collection": collection_name,
                    "completed": 1,
                    "total": 1,
                }
            )

    def ask_question_with_trace(self, question: str, chat_history=None) -> dict[str, object]:
        self.calls.append(("ask_question_with_trace", question))
        return {
            "route": "retrieval",
            "answer_text": "**RETRIEVAL**\n\nModo retrieval ativado.",
            "resolved_question": question,
            "matched_documents": [],
            "needs_document_refinement": False,
            "sources": [],
        }

    def ask_question_with_diagnostics(self, question: str, chat_history=None) -> dict[str, object]:
        self.calls.append(("ask_question_with_diagnostics", {"question": question, "focus": self.last_retrieval_focus}))
        self.last_retrieval_focus = {"locked": question}
        return {
            "route": "retrieval",
            "answer_text": "**RETRIEVAL**\n\nA resposta e Dell.",
            "resolved_question": question,
            "matched_documents": ["RACK.pdf"],
            "needs_document_refinement": False,
            "sources": [
                {
                    "document_name": "RACK.pdf",
                    "chunk_kind": "text",
                    "excerpt": "A empresa parceira do projeto e a Dell.",
                }
            ],
            "retrieval_intent": "specific_fact",
            "target_document_name": "RACK.pdf",
            "evidence_score": 0.82,
            "abstained": False,
            "answer_context": "A empresa parceira do projeto e a Dell.",
            "retrieval_stages": {
                "dense_mmr": {"candidate_ids": ["cand_relevant"]},
                "lexical": {"candidate_ids": []},
                "candidate_pool": {"candidate_ids": ["cand_relevant"]},
                "llm_selected": {"candidate_ids": ["cand_relevant"]},
                "selected_context": {"candidate_ids": ["cand_relevant"]},
            },
            "retrieval_stage_order": ["dense_mmr", "lexical", "candidate_pool", "llm_selected", "selected_context"],
            "candidate_catalog": {"cand_relevant": dict(self._corpus_candidate)},
            "resolver_status": "single_match",
            "resolver_confidence": 0.93,
            "resolver_selection_mode": "explicit_reference",
            "document_shortlist": ["RACK.pdf"],
            "matched_aliases": [],
            "document_scores": [],
            "recovery_search_performed": False,
            "recovery_matched_documents": [],
            "extraction_diagnostics": [],
            "answer_repair_applied": False,
            "answer_repair_reason": None,
            "final_answer_origin": "llm",
        }

    def _get_vector_store_documents(self) -> list[object]:
        return ["doc1"]

    def _build_retrieval_candidate_payload(self, doc) -> dict[str, object]:
        return dict(self._corpus_candidate)

    def _normalize_identifier(self, text: str) -> str:
        return normalize_text(text)

    def _tokenize_search_text(self, text: str) -> list[str]:
        return tokenize_text(text)


class AgentGradingService(FakeService):
    def _invoke_benchmark_grading_agent(self, grading_payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("benchmark_grading", grading_payload))
        return {
            "status": "graded",
            "parsed": {
                "correctness": "incorrect",
                "grounding_status": "unsupported",
                "failure_classification": "generation_failure",
                "evidence_support": "none",
                "confidence": 0.91,
                "rationale": "A resposta gerada nao deve ser aceita pelo avaliador semantico.",
            },
            "raw_response": '{"correctness":"incorrect"}',
        }


class InvalidAgentGradingService(FakeService):
    def _invoke_benchmark_grading_agent(self, grading_payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("benchmark_grading", grading_payload))
        return {
            "status": "graded",
            "parsed": {
                "correctness": "wrong-label",
                "grounding_status": "unsupported",
                "failure_classification": "generation_failure",
                "evidence_support": "none",
                "confidence": 0.91,
                "rationale": "Invalid label should force fallback.",
            },
        }


def test_runner_resets_focus_and_starts_each_question_in_retrieval_mode() -> None:
    FakeService.instances = []
    runner = BenchmarkRunner(
        service_cls=FakeService,
        runtime_config_loader=lambda: {
            "ufc_model_name": "fake-model",
            "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
        },
        retrieval_mode_command="BUSCAR",
    )
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Qual empresa e parceira do projeto?",
            expected_answer="Dell",
        ),
        BenchmarkQuestion(
            id="q2",
            collection="google_drive_rag",
            question="Quem coordena o projeto?",
            expected_answer="Paulo Rego",
            source_document="RACK.pdf",
        ),
    ]

    payload = runner.run(questions, questions_path=Path("benchmark/questions.json"))

    assert payload["collections"] == ["google_drive_rag"]
    assert len(FakeService.instances) == 1
    service = FakeService.instances[0]
    assert service.loaded_collections == ["google_drive_rag"]
    assert [call[1] for call in service.calls if call[0] == "ask_question_with_trace"] == ["BUSCAR", "BUSCAR"]

    diagnostic_calls = [
        call[1]
        for call in service.calls
        if call[0] == "ask_question_with_diagnostics"
    ]
    assert diagnostic_calls[0]["focus"] is None
    assert diagnostic_calls[1]["focus"] is None


def test_runner_emits_question_progress_events_with_context() -> None:
    FakeService.instances = []
    progress_events: list[dict[str, object]] = []
    runner = BenchmarkRunner(
        service_cls=FakeService,
        runtime_config_loader=lambda: {
            "ufc_model_name": "fake-model",
            "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
        },
        retrieval_mode_command="BUSCAR",
        progress_callback=progress_events.append,
        progress_context={
            "run_label": "bge-m3-800chunk-150overlap",
            "chunk_size": 800,
            "chunk_overlap": 150,
        },
    )
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Qual empresa e parceira do projeto?",
            expected_answer="Dell",
        ),
        BenchmarkQuestion(
            id="q2",
            collection="google_drive_rag",
            question="Quem coordena o projeto?",
            expected_answer="Paulo Rego",
            source_document="RACK.pdf",
        ),
    ]

    runner.run(questions, questions_path=Path("benchmark/questions.json"))

    collection_events = [
        event for event in progress_events if event["event"] == "collection_cache_restored"
    ]
    assert len(collection_events) == 1
    assert collection_events[0]["collection"] == "google_drive_rag"
    assert collection_events[0]["run_label"] == "bge-m3-800chunk-150overlap"
    completed_events = [
        event for event in progress_events if event["event"] == "question_completed"
    ]
    assert [event["question_index"] for event in completed_events] == [1, 2]
    assert [event["question_total"] for event in completed_events] == [2, 2]
    assert [event["question_id"] for event in completed_events] == ["q1", "q2"]
    assert [event["collection"] for event in completed_events] == [
        "google_drive_rag",
        "google_drive_rag",
    ]
    assert completed_events[0]["run_label"] == "bge-m3-800chunk-150overlap"
    assert completed_events[0]["run_context"] == {
        "run_label": "bge-m3-800chunk-150overlap",
        "chunk_size": 800,
        "chunk_overlap": 150,
    }


def test_agent_grading_becomes_official_benchmark_verdict() -> None:
    FakeService.instances = []
    runner = BenchmarkRunner(
        service_cls=AgentGradingService,
        runtime_config_loader=lambda: {
            "ufc_model_name": "fake-model",
            "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
        },
        retrieval_mode_command="BUSCAR",
    )
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Qual empresa e parceira do projeto?",
            expected_answer="Dell",
            source_document="RACK.pdf",
        )
    ]

    payload = runner.run(questions, questions_path=Path("benchmark/questions.json"))
    result = payload["results"][0]

    assert payload["failure_counts"] == {"generation_failure": 1}
    assert payload["grounding_counts"] == {"unsupported": 1}
    assert result["failure"]["classification"] == "generation_failure"
    assert result["grounding"]["grounding_status"] == "unsupported"
    assert result["auto_correctness"] == "incorrect"
    assert result["agent_grading"]["status"] == "graded"
    assert result["deterministic_evaluation"]["failure"]["classification"] == "no_failure"
    assert result["deterministic_evaluation"]["retrieval_metrics"]["expected_answer_in_context"] is True


def test_invalid_agent_grading_falls_back_to_deterministic_verdict() -> None:
    FakeService.instances = []
    runner = BenchmarkRunner(
        service_cls=InvalidAgentGradingService,
        runtime_config_loader=lambda: {
            "ufc_model_name": "fake-model",
            "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
        },
        retrieval_mode_command="BUSCAR",
    )
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Qual empresa e parceira do projeto?",
            expected_answer="Dell",
            source_document="RACK.pdf",
        )
    ]

    payload = runner.run(questions, questions_path=Path("benchmark/questions.json"))
    result = payload["results"][0]

    assert payload["failure_counts"] == {"no_failure": 1}
    assert payload["grounding_counts"] == {"grounded": 1}
    assert result["failure"]["classification"] == "no_failure"
    assert result["agent_grading"]["status"] == "fallback"
    assert result["agent_grading"]["reason"] == "invalid_agent_grading_payload"
    assert result["deterministic_evaluation"]["grounding"]["grounding_status"] == "grounded"


def test_write_outputs_creates_run_and_latest_files(tmp_path: Path) -> None:
    payload = {
        "run_id": "20260422T120000Z",
        "generated_at": "2026-04-22T12:00:00+00:00",
        "questions_file": "benchmark/questions.json",
        "collections": ["google_drive_rag"],
        "config_snapshot": {
            "ufc_model_name": "fake-model",
            "rag": {"strict_grounding": True, "min_evidence_score": 0.5},
        },
        "abstained_count": 0,
        "results": [],
    }

    markdown_path, json_path = _write_outputs(payload, output_dir=tmp_path)

    assert markdown_path.exists()
    assert json_path.exists()
    assert (tmp_path / "latest_study.md").exists()
    assert (tmp_path / "latest_diagnostics.json").exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["run_id"] == "20260422T120000Z"


def test_write_outputs_can_skip_latest_aliases(tmp_path: Path) -> None:
    payload = {
        "run_id": "20260422T120000Z",
        "generated_at": "2026-04-22T12:00:00+00:00",
        "questions_file": "benchmark/questions.json",
        "collections": ["google_drive_rag"],
        "config_snapshot": {},
        "abstained_count": 0,
        "results": [],
    }

    markdown_path, json_path = _write_outputs(
        payload,
        output_dir=tmp_path,
        write_latest=False,
    )

    assert markdown_path.exists()
    assert json_path.exists()
    assert not (tmp_path / "latest_study.md").exists()
    assert not (tmp_path / "latest_diagnostics.json").exists()
