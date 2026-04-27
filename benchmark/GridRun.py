"""Lightweight benchmark grid runner for splitter experiments."""

from __future__ import annotations

import argparse
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator, Sequence

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from .bootstrap import (
    bootstrap_python_path,
    get_rag_service_class,
    get_retrieval_mode_command,
    get_runtime_config,
)
from .orchestrator import BenchmarkRunner
from .questions import BenchmarkQuestion, load_questions
from .run import _resolve_user_path, _write_outputs


GRID: tuple[tuple[int, int], ...] = (
    (1600, 300),
    (1000, 200),
    (1200, 200),
    (800, 150),
    (500, 100),
    (200, 50),
    (100, 20),
    (50, 10),

)


@dataclass(frozen=True)
class GridRunOutput:
    label: str
    output_dir: Path
    markdown_path: Path
    json_path: Path


@dataclass(frozen=True)
class _ProgressTasks:
    progress: Progress
    grid_task: TaskID
    question_task: TaskID
    index_task: TaskID


def _build_grid_config(base_config, *, chunk_size: int, chunk_overlap: int):
    splitter_config = replace(
        base_config.splitter,
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
    )
    return replace(base_config, splitter=splitter_config)


def _embedding_model_slug(runtime_config) -> str:
    embedding_config = getattr(runtime_config, "embedding", None)
    model_name = str(
        getattr(embedding_config, "model_name", "")
        or getattr(runtime_config, "ufc_model_name", "")
        or "model"
    ).strip()
    model_leaf = model_name.replace("\\", "/").rstrip("/").split("/")[-1] or "model"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model_leaf).strip("-._")
    return slug or "model"


def _build_run_label(runtime_config, *, chunk_size: int, chunk_overlap: int) -> str:
    return f"{_embedding_model_slug(runtime_config)}-{int(chunk_size)}chunk-{int(chunk_overlap)}overlap"


def _filter_questions(
    questions: list[BenchmarkQuestion],
    question_ids: Sequence[str] | None,
) -> list[BenchmarkQuestion]:
    normalized_ids = {
        str(question_id).strip()
        for question_id in list(question_ids or [])
        if str(question_id).strip()
    }
    if not normalized_ids:
        return questions
    return [
        question for question in questions if question.normalized_id in normalized_ids
    ]


def _clear_grid_output_reports(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    for pattern in ("*_study.md", "*_diagnostics.json", "latest_study.md", "latest_diagnostics.json"):
        for output_file in output_dir.glob(pattern):
            if output_file.is_file():
                output_file.unlink()


def _create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        TextColumn("[dim]{task.fields[status]}"),
    )


@contextmanager
def _progress_tasks(
    *,
    enabled: bool,
    total_grid_runs: int,
    total_questions: int,
) -> Iterator[_ProgressTasks | None]:
    if not enabled:
        yield None
        return

    with _create_progress() as progress:
        grid_task = progress.add_task(
            "Grid runs",
            total=total_grid_runs,
            status="starting",
        )
        question_task = progress.add_task(
            "Questions",
            total=total_questions,
            visible=False,
            status="waiting for first run",
        )
        index_task = progress.add_task(
            "Index",
            total=1,
            visible=False,
            status="waiting for first run",
        )
        yield _ProgressTasks(
            progress=progress,
            grid_task=grid_task,
            question_task=question_task,
            index_task=index_task,
        )


def _update_question_progress(
    progress_tasks: _ProgressTasks | None,
    event: dict[str, object],
) -> None:
    if progress_tasks is None:
        return

    event_name = str(event.get("event") or "")
    if event_name.startswith("collection_") or event_name.startswith("index_"):
        _update_index_progress(progress_tasks, event)
        return

    question_index = int(event.get("question_index") or 0)
    question_id = str(event.get("question_id") or "?")
    collection = str(event.get("collection") or "?")
    run_label = str(event.get("run_label") or "run")
    status = f"question {question_id} | {collection}"

    if event_name == "question_started":
        progress_tasks.progress.update(
            progress_tasks.question_task,
            description=f"Questions ({run_label})",
            status=f"running {status}",
        )
        return

    if event_name == "question_completed":
        progress_tasks.progress.update(
            progress_tasks.question_task,
            completed=question_index,
            description=f"Questions ({run_label})",
            status=f"completed {status}",
        )


def _update_index_progress(
    progress_tasks: _ProgressTasks,
    event: dict[str, object],
) -> None:
    event_name = str(event.get("event") or "")
    run_label = str(event.get("run_label") or "run")
    collection = str(event.get("collection") or "collection")
    completed = int(event.get("completed") or 0)
    total = max(1, int(event.get("total") or 1))
    chunk_count = int(event.get("chunk_count") or 0)
    file_count = int(event.get("file_count") or 0)
    document_count = int(event.get("document_count") or 0)

    status_by_event = {
        "collection_load_started": f"preparing {collection}",
        "collection_fingerprint_ready": f"fingerprint ready ({file_count} files)",
        "collection_cache_restore_started": "restoring cached FAISS index",
        "collection_cache_restored": "cached FAISS index restored",
        "collection_index_build_started": f"building new FAISS index ({file_count} files)",
        "collection_documents_loaded": f"loaded {document_count} documents",
        "index_chunking_started": "chunking documents",
        "index_chunking_progress": f"chunking documents ({chunk_count} chunks)",
        "index_embedding_started": f"embedding {total} chunks",
        "index_embedding_progress": f"embedding chunks ({completed}/{total})",
        "index_faiss_build_started": f"building FAISS from {chunk_count} embeddings",
        "index_faiss_build_completed": "FAISS index built",
        "collection_cache_write_started": "writing FAISS cache",
        "collection_cache_written": "FAISS cache written",
    }
    status = status_by_event.get(event_name, event_name)

    progress_tasks.progress.update(
        progress_tasks.index_task,
        completed=completed,
        total=total,
        visible=True,
        description=f"Index ({run_label})",
        status=status,
    )


@contextmanager
def _patched_runtime_config(runtime_config) -> Iterator[None]:
    bootstrap_python_path()
    import service.RuntimeConfig as runtime_config_module

    original_runtime_loader = runtime_config_module.get_runtime_config
    bootstrap_module = sys.modules.get("service.rag.parts.Bootstrap")
    original_bootstrap_loader = (
        getattr(bootstrap_module, "get_runtime_config", None)
        if bootstrap_module is not None
        else None
    )

    def runtime_loader():
        return runtime_config

    runtime_config_module.get_runtime_config = runtime_loader
    if bootstrap_module is not None:
        bootstrap_module.get_runtime_config = runtime_loader

    try:
        yield
    finally:
        runtime_config_module.get_runtime_config = original_runtime_loader
        if bootstrap_module is not None and original_bootstrap_loader is not None:
            bootstrap_module.get_runtime_config = original_bootstrap_loader


def run_grid(
    *,
    questions_path: Path,
    output_root: Path,
    question_ids: Sequence[str] | None = None,
    grid: Sequence[tuple[int, int]] = GRID,
    show_progress: bool = True,
) -> list[GridRunOutput]:
    bootstrap_python_path()
    questions = _filter_questions(load_questions(questions_path), question_ids)
    if not questions:
        raise ValueError("No benchmark questions matched the provided --question-id filter.")

    base_config = get_runtime_config()
    service_cls = get_rag_service_class()
    retrieval_mode_command = get_retrieval_mode_command()
    outputs: list[GridRunOutput] = []

    with _progress_tasks(
        enabled=show_progress,
        total_grid_runs=len(grid),
        total_questions=len(questions),
    ) as progress_tasks:
        for chunk_size, chunk_overlap in grid:
            run_config = _build_grid_config(
                base_config,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            label = _build_run_label(
                run_config,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            output_dir = output_root / label
            if progress_tasks is not None:
                progress_tasks.progress.update(
                    progress_tasks.grid_task,
                    status=f"running {label} -> {output_dir}",
                )
                progress_tasks.progress.update(
                    progress_tasks.question_task,
                    completed=0,
                    total=len(questions),
                    visible=True,
                    description=f"Questions ({label})",
                    status=f"waiting for index | chunk={chunk_size}, overlap={chunk_overlap}",
                )
                progress_tasks.progress.update(
                    progress_tasks.index_task,
                    completed=0,
                    total=1,
                    visible=True,
                    description=f"Index ({label})",
                    status=f"chunk={chunk_size}, overlap={chunk_overlap}",
                )

            runner = BenchmarkRunner(
                service_cls=service_cls,
                runtime_config_loader=lambda current_config=run_config: current_config,
                retrieval_mode_command=retrieval_mode_command,
                progress_callback=(
                    (lambda event, tasks=progress_tasks: _update_question_progress(tasks, event))
                    if progress_tasks is not None
                    else None
                ),
                progress_context={
                    "run_label": label,
                    "chunk_size": int(chunk_size),
                    "chunk_overlap": int(chunk_overlap),
                    "output_dir": str(output_dir),
                },
            )
            with _patched_runtime_config(run_config):
                run_payload = runner.run(questions, questions_path=questions_path)

            _clear_grid_output_reports(output_dir)
            markdown_path, json_path = _write_outputs(
                run_payload,
                output_dir=output_dir,
                write_latest=False,
            )
            outputs.append(
                GridRunOutput(
                    label=label,
                    output_dir=output_dir,
                    markdown_path=markdown_path,
                    json_path=json_path,
                )
            )
            if progress_tasks is not None:
                progress_tasks.progress.update(
                    progress_tasks.grid_task,
                    advance=1,
                    status=f"finished {label}",
                )

    return outputs


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run benchmark diagnostics over a parameter grid.")
    parser.add_argument(
        "--questions",
        default="benchmark/questions.json",
        help="Path to the benchmark questions file.",
    )
    parser.add_argument(
        "--question-id",
        action="append",
        dest="question_ids",
        help="Filter to one or more benchmark question ids.",
    )
    parser.add_argument(
        "--output-root",
        default="benchmark/results",
        help="Root directory where one folder per grid run will be written.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_false",
        dest="show_progress",
        default=True,
        help="Disable live progress bars for logs or redirected output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    try:
        outputs = run_grid(
            questions_path=_resolve_user_path(args.questions),
            output_root=_resolve_user_path(args.output_root),
            question_ids=args.question_ids,
            show_progress=args.show_progress,
        )
    except ValueError as exc:
        parser.error(str(exc))

    for output in outputs:
        print(f"Grid run {output.label}")
        print(f"  Benchmark study written to: {output.markdown_path}")
        print(f"  Benchmark diagnostics written to: {output.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
