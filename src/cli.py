"""Command-line interface for the CSV Q&A Agent.

Interactive:
    python -m src.cli --csv data/sales_data.csv

Batch (reproducible reviewer demo):
    python -m src.cli --csv data/sales_data.csv \
        --batch sample_outputs/questions.json \
        --out sample_outputs/answers.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from .agent import CSVQAAgent
from .config import settings
from .exceptions import AgentError, ConfigurationError, DataLoadError
from .models import AnswerMode, QAResult

console = Console()


def print_result(qa: QAResult) -> None:
    console.rule(f"[bold cyan]Q: {qa.question}")
    if qa.mode == AnswerMode.GENERAL_KNOWLEDGE:
        console.print("[dim](not about the dataset — answered from general knowledge, no code run)[/dim]")
        console.print(f"[bold]Answer:[/bold] {qa.explanation}")
        console.print()
        return
    console.print(Syntax(qa.code, "python", theme="monokai", line_numbers=False))
    if qa.success:
        console.print(f"[bold green]Result:[/bold green] {qa.result}")
        console.print(f"[bold]Answer:[/bold] {qa.explanation}")
    else:
        console.print(f"[bold red]FAILED[/bold red] after {qa.attempts} attempt(s): {qa.error}")
    console.print()


def run_batch(agent: CSVQAAgent, questions_path: Path, out_path: Path) -> None:
    questions: list[str] = json.loads(questions_path.read_text())

    results: list[QAResult] = []
    for question in questions:
        qa = agent.ask(question)
        print_result(qa)
        results.append(qa)

    out_path.write_text(json.dumps([r.to_json_dict() for r in results], indent=2))

    table = Table(title="Batch summary")
    table.add_column("Metric")
    table.add_column("Value")
    ok = sum(r.success for r in results)
    table.add_row("Questions answered successfully", f"{ok}/{len(results)}")
    table.add_row("Results written to", str(out_path))
    console.print(table)


def run_interactive(agent: CSVQAAgent) -> None:
    console.print(
        f"[bold green]CSV Q&A Agent ready[/bold green] — loaded {agent.csv_path} "
        f"({len(agent.df)} rows). Type 'exit' to quit.\n"
    )
    while True:
        try:
            question = console.input("[bold]You:[/bold] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye.")
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            console.print("Goodbye.")
            break
        qa = agent.ask(question)
        print_result(qa)


def main() -> None:
    parser = argparse.ArgumentParser(description="CSV / Data Q&A Agent")
    parser.add_argument("--csv", default=str(settings.default_csv_path), help="Path to the CSV file")
    parser.add_argument("--batch", help="Path to a JSON file of questions (list of strings)")
    parser.add_argument("--out", default="sample_outputs/answers.json", help="Where to write batch results")
    args = parser.parse_args()

    try:
        agent = CSVQAAgent(args.csv)
    except (ConfigurationError, DataLoadError) as exc:
        console.print(f"[bold red]Startup failed:[/bold red] {exc}")
        sys.exit(1)

    try:
        if args.batch:
            run_batch(agent, Path(args.batch), Path(args.out))
        else:
            run_interactive(agent)
    except AgentError as exc:
        console.print(f"[bold red]Agent error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
