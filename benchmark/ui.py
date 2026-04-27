"""Rich-based terminal UI for benchmark execution.

Provides a clean, structured terminal interface with:
- Progress bars and spinners
- Status panels
- Result tables
- Formatted output for benchmark steps
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()


class BenchmarkUI:
    """Terminal UI for benchmark execution with progress tracking and results display."""

    def __init__(self) -> None:
        self.console = console
        self.progress_bar = None
        self.question_task = None
        self.start_time: datetime | None = None
        self.step_messages: list[str] = []

    def show_header(self, title: str = "Benchmark: RAG Evaluation") -> None:
        """Display benchmark header."""
        self.console.print()
        self.console.print(f"[bold cyan]{title}[/bold cyan]")
        self.console.print("[dim]" + "-" * 60 + "[/dim]")

    def start_progress(self, total_questions: int) -> Progress:
        """Create and start a progress bar for question processing."""
        self.start_time = datetime.now()
        self.progress_bar = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )
        self.progress_bar.start()
        self.question_task = self.progress_bar.add_task(
            "[cyan]Processing questions...",
            total=total_questions,
        )
        return self.progress_bar

    def step_setup(self, step: str) -> None:
        """Show a setup step being executed."""
        symbol = "..."
        self.console.print(f"[yellow]{symbol}[/yellow] {step}...", end=" ", soft_wrap=True)

    def step_complete(self, step: str) -> None:
        """Mark a setup step as complete."""
        self.console.print("[green][OK][/green]")
        self.step_messages.append(step)

    def step_error(self, step: str, error: str) -> None:
        """Mark a setup step as failed."""
        self.console.print(f"[red][FAIL][/red] [red]{error}[/red]")

    def update_question(self, question_id: str, index: int, total: int) -> None:
        """Update progress bar with current question."""
        if self.question_task is not None and self.progress_bar is not None:
            self.progress_bar.update(
                self.question_task,
                description=f"[cyan]Processing [{index}/{total}]: {question_id}",
            )

    def advance_progress(self) -> None:
        """Advance the progress bar by one question."""
        if self.question_task is not None and self.progress_bar is not None:
            self.progress_bar.advance(self.question_task)

    def stop_progress(self) -> None:
        """Stop the progress bar."""
        if self.progress_bar is not None:
            self.progress_bar.stop()
            self.progress_bar = None

    def show_results_summary(
        self,
        total_questions: int,
        results: dict[str, Any],
    ) -> None:
        """Display a summary of benchmark results."""
        self.console.print()
        self.console.print("[bold]Results Summary[/bold]")
        self.console.print("[dim]" + "-" * 60 + "[/dim]")

        # Extract summary stats
        stats = results.get("summary", {})
        correct = stats.get("correct", 0)
        total = stats.get("total", total_questions)
        accuracy = (correct / total * 100) if total > 0 else 0

        # Create summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("Total Questions:", f"[cyan]{total}[/cyan]")
        table.add_row("Correct Answers:", f"[green]{correct}[/green]")
        table.add_row("Accuracy:", f"[cyan]{accuracy:.1f}%[/cyan]")

        # Failure breakdown if available
        failures = stats.get("failure_counts", {})
        if failures:
            table.add_row()
            table.add_row("Failure Breakdown:", "")
            for failure_type, count in sorted(failures.items()):
                table.add_row(f"  • {failure_type}:", f"[yellow]{count}[/yellow]")

        self.console.print(table)

    def show_results_table(self, results: list[dict[str, Any]]) -> None:
        """Display detailed results in a table format."""
        if not results:
            return

        self.console.print()
        self.console.print("[bold]Detailed Results[/bold]")
        self.console.print("[dim]" + "─" * 120 + "[/dim]")

        table = Table(title=None, box=None)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Question", style="white", width=40)
        table.add_column("Status", style="magenta")
        table.add_column("Correctness", style="yellow")
        table.add_column("Grounding", style="blue")

        for result in results[:25]:  # Limit to first 25 for readability
            question_data = result.get("question_data", {})
            question_id = question_data.get("question_id", "?")
            question_text = question_data.get("question", "")[:35]

            agent_grading = result.get("agent_grading", {})
            correctness = agent_grading.get("correctness", "unknown")
            grounding = agent_grading.get("grounding_status", "unknown")
            failure = agent_grading.get("failure_classification", "unknown")

            # Color code correctness
            if correctness == "correct":
                correctness_display = f"[green]{correctness}[/green]"
            elif correctness == "partially_correct":
                correctness_display = f"[yellow]{correctness}[/yellow]"
            else:
                correctness_display = f"[red]{correctness}[/red]"

            # Color code grounding
            if grounding == "grounded":
                grounding_display = f"[green]{grounding}[/green]"
            elif grounding == "weakly_grounded":
                grounding_display = f"[yellow]{grounding}[/yellow]"
            else:
                grounding_display = f"[red]{grounding}[/red]"

            table.add_row(
                question_id,
                question_text,
                failure,
                correctness_display,
                grounding_display,
            )

        self.console.print(table)
        if len(results) > 25:
            self.console.print(f"[dim](showing first 25 of {len(results)} results)[/dim]")

    def show_file_output(self, markdown_path: Path, json_path: Path) -> None:
        """Display output file locations."""
        self.console.print()
        self.console.print("[bold]Output Files[/bold]")
        self.console.print("[dim]" + "-" * 60 + "[/dim]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[cyan]Study Report:[/cyan]", f"[green]{markdown_path}[/green]")
        table.add_row("[cyan]Diagnostics:[/cyan]", f"[green]{json_path}[/green]")

        self.console.print(table)

    def show_completion(self, elapsed: timedelta | None = None) -> None:
        """Show benchmark completion message."""
        self.console.print()
        msg = "[bold green][DONE] Benchmark completed successfully[/bold green]"
        if elapsed:
            msg += f" [dim](elapsed: {elapsed})[/dim]"
        self.console.print(msg)
        self.console.print()

    def show_error(self, title: str, message: str) -> None:
        """Display an error message."""
        self.console.print()
        self.console.print(f"[bold red][ERROR] {title}[/bold red]")
        self.console.print(f"[red]{message}[/red]")
        self.console.print()

    def show_warning(self, message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[yellow][WARN] {message}[/yellow]")


# Global UI instance
_ui: BenchmarkUI | None = None


def get_ui() -> BenchmarkUI:
    """Get or create the global benchmark UI instance."""
    global _ui
    if _ui is None:
        _ui = BenchmarkUI()
    return _ui
