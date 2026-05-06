from pathlib import Path

from application.service.RuntimeConfig import (
    AppRuntimeConfig,
    EmbeddingRuntimeConfig,
    GenerationRuntimeConfig,
    RagRuntimeConfig,
    RetrievalRuntimeConfig,
    SplitterRuntimeConfig,
)
from benchmark import GridRun
from benchmark.questions import BenchmarkQuestion


def make_runtime_config() -> AppRuntimeConfig:
    return AppRuntimeConfig(
        ufc_model_name="llama3.1:8b",
        embedding=EmbeddingRuntimeConfig(
            model_name="BAAI/bge-m3",
            device="cpu",
            quantization="int8",
            batch_size=2,
            max_length=1024,
        ),
        splitter=SplitterRuntimeConfig(
            chunk_size=800,
            chunk_overlap=150,
            separators=("\n\n", "\n", " "),
        ),
        retrieval=RetrievalRuntimeConfig(
            base_search_k=12,
            base_fetch_k=30,
            base_lambda_mult=0.2,
            lexical_limit=12,
            candidate_pool_limit=30,
            llm_selection_limit=8,
            llm_selector_enabled=True,
        ),
        rag=RagRuntimeConfig(
            agent_mode="crewai",
            strict_grounding=True,
            min_evidence_score=0.5,
        ),
        generation=GenerationRuntimeConfig(
            temperature=0.0,
            top_p=0.9,
            repeat_penalty=1.05,
            seed=None,
            num_ctx=None,
        ),
    )


def test_grid_config_override_preserves_base_config_except_splitter_values() -> None:
    base_config = make_runtime_config()

    grid_config = GridRun._build_grid_config(
        base_config,
        chunk_size=500,
        chunk_overlap=100,
    )

    assert base_config.splitter.chunk_size == 800
    assert base_config.splitter.chunk_overlap == 150
    assert grid_config.splitter.chunk_size == 500
    assert grid_config.splitter.chunk_overlap == 100
    assert grid_config.splitter.separators == base_config.splitter.separators
    assert grid_config.embedding == base_config.embedding
    assert grid_config.retrieval == base_config.retrieval
    assert grid_config.rag == base_config.rag
    assert grid_config.ufc_model_name == base_config.ufc_model_name


def test_grid_run_label_uses_embedding_model_leaf() -> None:
    runtime_config = make_runtime_config()

    label = GridRun._build_run_label(
        runtime_config,
        chunk_size=800,
        chunk_overlap=150,
    )

    assert label == "bge-m3-800chunk-150overlap"


def test_extract_llm_model_candidates_reads_active_and_commented_models(capsys) -> None:
    config_text = """
[model]
# Tested alternatives:
#   "qwen2.5:14b"
#   "cow/gemma2_tools:2b"
#   "qwen3:8b
ufc_model_name = "gpt-oss:20b"

[generation]
temperature = 0.2
"""

    models = GridRun._extract_llm_model_candidates(config_text)

    assert models == ["qwen2.5:14b", "cow/gemma2_tools:2b", "gpt-oss:20b"]
    assert "Skipping malformed commented model candidate" in capsys.readouterr().out


def test_extract_llm_model_candidates_deduplicates_in_config_order() -> None:
    config_text = """
[model]
#   "gpt-oss:20b"
#   "qwen2.5:14b"
#   "gpt-oss:20b"
ufc_model_name = "qwen2.5:14b"
"""

    assert GridRun._extract_llm_model_candidates(config_text) == [
        "gpt-oss:20b",
        "qwen2.5:14b",
    ]


def test_model_slug_removes_colons_and_keeps_path_context() -> None:
    assert GridRun._slug_model_name("gpt-oss:20b") == "gpt-oss20b"
    assert GridRun._slug_model_name("cow/gemma2_tools:2b") == "cow_gemma2_tools2b"


def test_model_config_override_preserves_base_config_except_model_name() -> None:
    base_config = make_runtime_config()

    model_config = GridRun._build_model_config(base_config, model_name="gpt-oss:20b")

    assert base_config.ufc_model_name == "llama3.1:8b"
    assert model_config.ufc_model_name == "gpt-oss:20b"
    assert model_config.embedding == base_config.embedding
    assert model_config.splitter == base_config.splitter
    assert model_config.retrieval == base_config.retrieval
    assert model_config.rag == base_config.rag
    assert model_config.generation == base_config.generation


def test_run_grid_dispatches_one_output_directory_per_detected_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    base_config = make_runtime_config()
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Question 1?",
            expected_answer="Answer 1",
        ),
        BenchmarkQuestion(
            id="q2",
            collection="google_drive_rag",
            question="Question 2?",
            expected_answer="Answer 2",
        ),
    ]
    calls: list[dict[str, object]] = []

    class FakeBenchmarkRunner:
        def __init__(
            self,
            *,
            service_cls,
            runtime_config_loader,
            retrieval_mode_command,
            progress_callback=None,
            progress_context=None,
        ):
            self.service_cls = service_cls
            self.runtime_config_loader = runtime_config_loader
            self.retrieval_mode_command = retrieval_mode_command
            self.progress_callback = progress_callback
            self.progress_context = dict(progress_context or {})

        def run(self, run_questions, *, questions_path: Path) -> dict[str, object]:
            import service.RuntimeConfig as runtime_config_module

            snapshot_config = self.runtime_config_loader()
            patched_config = runtime_config_module.get_runtime_config()
            calls.append(
                {
                    "service_cls": self.service_cls,
                    "retrieval_mode_command": self.retrieval_mode_command,
                    "question_ids": [question.normalized_id for question in run_questions],
                    "questions_path": questions_path,
                    "snapshot_model_name": snapshot_config.ufc_model_name,
                    "patched_model_name": patched_config.ufc_model_name,
                    "patched_chunk_size": patched_config.splitter.chunk_size,
                    "progress_callback": self.progress_callback,
                    "progress_context": self.progress_context,
                }
            )
            return {
                "run_id": f"run_{GridRun._slug_model_name(patched_config.ufc_model_name)}",
                "generated_at": "2026-04-24T00:00:00+00:00",
                "questions_file": str(questions_path),
                "collections": ["google_drive_rag"],
                "config_snapshot": {"ufc_model_name": "wrong-model"},
                "results": [],
            }

    stale_json = tmp_path / "gpt-oss20b" / "latest_diagnostics.json"
    stale_json.parent.mkdir(parents=True)
    stale_json.write_text("stale", encoding="utf-8")

    def fake_write_outputs(
        run_payload: dict[str, object],
        *,
        output_dir: Path,
        write_latest: bool = True,
    ):
        assert write_latest is False
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{run_payload['run_id']}_study.md"
        json_path = output_dir / f"{run_payload['run_id']}_diagnostics.json"
        markdown_path.write_text(str(run_payload["run_id"]), encoding="utf-8")
        json_path.write_text("{}", encoding="utf-8")
        return markdown_path, json_path

    monkeypatch.setattr(GridRun, "get_runtime_config", lambda: base_config)
    monkeypatch.setattr(GridRun, "get_rag_service_class", lambda: "FakeService")
    monkeypatch.setattr(GridRun, "get_retrieval_mode_command", lambda: "BUSCAR")
    monkeypatch.setattr(GridRun, "load_questions", lambda questions_path: questions)
    monkeypatch.setattr(
        GridRun,
        "_read_llm_model_candidates",
        lambda: ["gpt-oss:20b", "cow/gemma2_tools:2b"],
    )
    monkeypatch.setattr(GridRun, "BenchmarkRunner", FakeBenchmarkRunner)
    monkeypatch.setattr(GridRun, "_write_outputs", fake_write_outputs)

    outputs = GridRun.run_grid(
        questions_path=Path("benchmark/questions.json"),
        output_root=tmp_path,
        question_ids=["q2"],
        show_progress=False,
    )

    assert [output.label for output in outputs] == [
        "gpt-oss20b",
        "cow_gemma2_tools2b",
    ]
    assert [output.output_dir for output in outputs] == [
        tmp_path / "gpt-oss20b",
        tmp_path / "cow_gemma2_tools2b",
    ]
    assert [call["question_ids"] for call in calls] == [["q2"], ["q2"]]
    assert [call["snapshot_model_name"] for call in calls] == [
        "gpt-oss:20b",
        "cow/gemma2_tools:2b",
    ]
    assert [call["patched_model_name"] for call in calls] == [
        "gpt-oss:20b",
        "cow/gemma2_tools:2b",
    ]
    assert [call["patched_chunk_size"] for call in calls] == [800, 800]
    assert [call["progress_callback"] for call in calls] == [None, None]
    assert all(call["service_cls"] == "FakeService" for call in calls)
    assert all(call["retrieval_mode_command"] == "BUSCAR" for call in calls)
    assert all(output.markdown_path.exists() for output in outputs)
    assert all(output.json_path.exists() for output in outputs)
    assert outputs[0].markdown_path == tmp_path / "gpt-oss20b" / "gpt-oss20b_study.md"
    assert outputs[0].json_path == tmp_path / "gpt-oss20b" / "gpt-oss20b_diagnostics.json"
    assert not stale_json.exists()


def test_run_grid_progress_path_updates_grid_and_question_tasks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    base_config = make_runtime_config()
    questions = [
        BenchmarkQuestion(
            id="q1",
            collection="google_drive_rag",
            question="Question 1?",
            expected_answer="Answer 1",
        )
    ]

    class FakeProgress:
        def __init__(self) -> None:
            self.added_tasks: list[dict[str, object]] = []
            self.updates: list[dict[str, object]] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def add_task(self, description: str, **kwargs):
            task_id = len(self.added_tasks) + 1
            self.added_tasks.append(
                {"task_id": task_id, "description": description, **kwargs}
            )
            return task_id

        def update(self, task_id, **kwargs) -> None:
            self.updates.append({"task_id": task_id, **kwargs})

    class FakeBenchmarkRunner:
        def __init__(
            self,
            *,
            service_cls,
            runtime_config_loader,
            retrieval_mode_command,
            progress_callback=None,
            progress_context=None,
        ):
            self.runtime_config_loader = runtime_config_loader
            self.progress_callback = progress_callback
            self.progress_context = dict(progress_context or {})

        def run(self, run_questions, *, questions_path: Path) -> dict[str, object]:
            run_config = self.runtime_config_loader()
            assert self.progress_callback is not None
            for index, question in enumerate(run_questions, start=1):
                event_base = {
                    "question_index": index,
                    "question_total": len(run_questions),
                    "question_id": question.normalized_id,
                    "collection": question.collection,
                    "run_context": dict(self.progress_context),
                    **self.progress_context,
                }
                self.progress_callback({"event": "question_started", **event_base})
                self.progress_callback({"event": "question_completed", **event_base})
            return {
                "run_id": f"{run_config.splitter.chunk_size}_{run_config.splitter.chunk_overlap}",
                "generated_at": "2026-04-24T00:00:00+00:00",
                "questions_file": str(questions_path),
                "collections": ["google_drive_rag"],
                "config_snapshot": {},
                "results": [],
            }

    def fake_write_outputs(
        run_payload: dict[str, object],
        *,
        output_dir: Path,
        write_latest: bool = True,
    ):
        assert write_latest is False
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = output_dir / f"{run_payload['run_id']}_study.md"
        json_path = output_dir / f"{run_payload['run_id']}_diagnostics.json"
        markdown_path.write_text(str(run_payload["run_id"]), encoding="utf-8")
        json_path.write_text("{}", encoding="utf-8")
        return markdown_path, json_path

    fake_progress = FakeProgress()
    monkeypatch.setattr(GridRun, "get_runtime_config", lambda: base_config)
    monkeypatch.setattr(GridRun, "get_rag_service_class", lambda: "FakeService")
    monkeypatch.setattr(GridRun, "get_retrieval_mode_command", lambda: "BUSCAR")
    monkeypatch.setattr(GridRun, "load_questions", lambda questions_path: questions)
    monkeypatch.setattr(GridRun, "_read_llm_model_candidates", lambda: ["gpt-oss:20b"])
    monkeypatch.setattr(GridRun, "BenchmarkRunner", FakeBenchmarkRunner)
    monkeypatch.setattr(GridRun, "_write_outputs", fake_write_outputs)
    monkeypatch.setattr(GridRun, "_create_progress", lambda: fake_progress)

    outputs = GridRun.run_grid(
        questions_path=Path("benchmark/questions.json"),
        output_root=tmp_path,
        show_progress=True,
    )

    assert [output.label for output in outputs] == ["gpt-oss20b"]
    assert fake_progress.added_tasks[0]["description"] == "Grid runs"
    assert fake_progress.added_tasks[1]["description"] == "Questions"
    assert any(
        update.get("task_id") == 1
        and "running gpt-oss20b" in str(update.get("status"))
        for update in fake_progress.updates
    )
    assert any(
        update.get("task_id") == 2
        and update.get("completed") == 0
        and update.get("visible") is True
        for update in fake_progress.updates
    )
    assert any(
        update.get("task_id") == 2
        and update.get("completed") == 1
        and "completed question q1 | google_drive_rag" == update.get("status")
        for update in fake_progress.updates
    )
    assert any(
        update.get("task_id") == 1 and update.get("advance") == 1
        for update in fake_progress.updates
    )
