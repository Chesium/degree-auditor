from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from degree_auditor.allocation import plan_allocations
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


@app.command("plan-allocation")
def plan_allocation_command(
    config: ConfigOption,
    transcript: Annotated[Path, typer.Option("--transcript", "-t")],
    out: Annotated[Path, typer.Option("--out", "-o")],
) -> None:
    loaded = load_config(config)
    courses = load_transcript(transcript)
    allocations = plan_allocations(loaded, courses)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"allocations": [allocation.model_dump(mode="json") for allocation in allocations]}
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    console.print(f"[green]Wrote allocation plan[/green]: {out}")


@app.command("list-requirements")
def list_requirements_command(config: ConfigOption) -> None:
    loaded = load_config(config)
    table = Table(title="Requirements")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Description")
    table.add_column("Source")
    for requirement in loaded.requirements:
        source = requirement.source_ref.document
        if requirement.source_ref.page is not None:
            source = f"{source}:p{requirement.source_ref.page}"
        table.add_row(requirement.id, requirement.requirement_type, requirement.description, source)
    console.print(table)


@app.command("list-specialisations")
def list_specialisations_command(config: ConfigOption) -> None:
    loaded = load_config(config)
    table = Table(title="Specialisations")
    table.add_column("ID")
    table.add_column("Description")
    table.add_column("Units")
    table.add_column("Overlap")
    table.add_column("Distinct")
    table.add_column("Paths")
    table.add_column("Source")
    for specialisation in loaded.specialisations:
        source = specialisation.source_ref.document
        if specialisation.source_ref.page is not None:
            source = f"{source}:p{specialisation.source_ref.page}"
        table.add_row(
            specialisation.id,
            specialisation.description,
            str(specialisation.total_units),
            str(specialisation.max_overlap_units),
            str(specialisation.min_distinct_units),
            ", ".join(path.id for path in specialisation.paths) or "-",
            source,
        )
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
