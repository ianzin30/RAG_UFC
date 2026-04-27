"""CLI entrypoint for the retrieval benchmark study."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .bootstrap import (
    PROJECT_ROOT,
    bootstrap_python_path,
    get_rag_service_class,
    get_retrieval_mode_command,
    get_runtime_config,
)
from .orchestrator import BenchmarkRunner
from .questions import load_questions
from .reporting import render_markdown_report
from .ui import get_ui
from .warnings_filter import suppress_noisy_warnings


def _progress_handler(event: dict[str, object], ui) -> None:
    """Handle progress events from the benchmark runner."""
    event_type = str(event.get("event") or "").strip()

    if event_type == "question_started":
        question_id = str(event.get("question_id") or "?")
        question_index = int(event.get("question_index") or 0)
        question_total = int(event.get("question_total") or 0)
        ui.update_question(question_id, question_index, question_total)

    elif event_type == "question_completed":
        ui.advance_progress()


def _resolve_user_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _write_outputs(
    run_payload: dict[str, object],
    *,
    output_dir: Path,
    write_latest: bool = True,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(run_payload.get("run_id") or "benchmark_run")
    markdown_path = output_dir / f"{run_id}_study.md"
    json_path = output_dir / f"{run_id}_diagnostics.json"
    latest_markdown_path = output_dir / "latest_study.md"
    latest_json_path = output_dir / "latest_diagnostics.json"

    markdown_report = render_markdown_report(run_payload)
    markdown_path.write_text(markdown_report, encoding="utf-8")
    json_path.write_text(
        json.dumps(run_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if write_latest:
        shutil.copyfile(markdown_path, latest_markdown_path)
        shutil.copyfile(json_path, latest_json_path)
    return markdown_path, json_path


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retrieval benchmark diagnostics.")
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
        "--output-dir",
        default="benchmark/results",
        help="Directory where Markdown and JSON reports will be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # Suppress non-critical warnings early
    suppress_noisy_warnings()

    bootstrap_python_path()
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    questions_path = _resolve_user_path(args.questions)
    output_dir = _resolve_user_path(args.output_dir)
    questions = load_questions(questions_path)

    if args.question_ids:
        normalized_ids = {str(question_id).strip() for question_id in args.question_ids if str(question_id).strip()}
        questions = [
            question for question in questions if question.normalized_id in normalized_ids
        ]
        if not questions:
            parser.error("No benchmark questions matched the provided --question-id filter.")

    # Initialize UI
    ui = get_ui()
    ui.show_header("Benchmark: RAG Evaluation")

    # Setup steps
    ui.step_setup("Loading configuration")
    try:
        runtime_config = get_runtime_config()
        ui.step_complete("Configuration loaded")
    except Exception as exc:
        ui.step_error("Configuration", str(exc))
        return 1

    ui.step_setup("Initializing service")
    try:
        service_cls = get_rag_service_class()
        ui.step_complete("Service initialized")
    except Exception as exc:
        ui.step_error("Service initialization", str(exc))
        return 1

    ui.step_setup("Setting up retrieval mode")
    try:
        retrieval_mode = get_retrieval_mode_command()
        ui.step_complete("Retrieval mode ready")
    except Exception as exc:
        ui.step_error("Retrieval mode setup", str(exc))
        return 1

    # Create runner with progress callback
    runner = BenchmarkRunner(
        service_cls=service_cls,
        runtime_config_loader=get_runtime_config,
        retrieval_mode_command=retrieval_mode,
        progress_callback=lambda event: _progress_handler(event, ui),
    )

    # Start progress tracking and run benchmark
    progress_bar = ui.start_progress(len(questions))
    start_time = datetime.now()

    try:
        run_payload = runner.run(questions, questions_path=questions_path)
    finally:
        ui.stop_progress()

    elapsed = datetime.now() - start_time

    # Write outputs
    markdown_path, json_path = _write_outputs(run_payload, output_dir=output_dir)

    # Display results
    ui.show_results_summary(len(questions), run_payload)
    results = list(run_payload.get("results") or [])
    ui.show_results_table(results)
    ui.show_file_output(markdown_path, json_path)
    ui.show_completion(elapsed)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
