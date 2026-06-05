from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_allocations, load_config, load_transcript
from degree_auditor.eligibility import expand_eligibility


app = typer.Typer(help="Prototype NUS EE degree auditor.")
console = Console()


ConfigOption = Annotated[list[Path], typer.Option("--config", "-c", help="Config file or folder. May be repeated.")]


@app.command("validate-config")
def validate_config(config: ConfigOption) -> None:
    loaded = load_config(config)
    console.print(f"[green]Config valid[/green]: {loaded.title or loaded.programme_id}")


@app.command("expand-eligibility")
def expand_eligibility_command(
    config: ConfigOption,
    transcript: Annotated[Path, typer.Option("--transcript", "-t")],
) -> None:
    loaded = load_config(config)
    courses = load_transcript(transcript)
    expanded = expand_eligibility(loaded, courses)
    table = Table(title="Eligibility")
    table.add_column("Course")
    table.add_column("Eligible Requirements")
    for course_code, requirement_ids in expanded.items():
        table.add_row(course_code, ", ".join(requirement_ids) or "-")
    console.print(table)


@app.command("audit")
def audit_command(
    config: ConfigOption,
    transcript: Annotated[Path, typer.Option("--transcript", "-t")],
    allocation: Annotated[Path | None, typer.Option("--allocation", "-a")] = None,
    output_format: Annotated[str, typer.Option("--format")] = "text",
) -> None:
    loaded = load_config(config)
    courses = load_transcript(transcript)
    allocations = load_allocations(allocation) if allocation else None
    result = audit(loaded, courses, allocations)

    if output_format == "json":
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
        return
    if output_format != "text":
        raise typer.BadParameter("format must be text or json")

    console.print(f"[bold]NUS EE AY24 JC Degree Audit[/bold]")
    console.print(f"Overall status: [{'green' if result.overall_status == 'PASS' else 'red'}]{result.overall_status}[/]")
    table = Table(title="Constraint Results")
    table.add_column("Constraint")
    table.add_column("Status")
    table.add_column("Message")
    for item in result.constraint_results:
        table.add_row(item.constraint_id, "PASS" if item.passed else "FAIL", item.message)
    console.print(table)


if __name__ == "__main__":
    app()
