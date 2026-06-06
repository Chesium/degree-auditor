from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from degree_auditor.allocation import plan_allocations
from degree_auditor.audit import audit
from degree_auditor.config_loader import ConfigLoadError, load_allocations, load_config, load_student_flags, load_transcript
from degree_auditor.contract import to_contract_result
from degree_auditor.eligibility import expand_eligibility
from degree_auditor.interactive_allocation import (
    allocations_for_selection,
    choices_for_transcript,
    parse_selection,
    write_commented_allocation_yaml,
)
from degree_auditor.manual_validation import ManualAllocationValidationError, validate_manual_allocations
from degree_auditor.ordering import sort_allocations
from degree_auditor.reporting import render_audit_report


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
    payload = {"allocations": [allocation.model_dump(mode="json") for allocation in sort_allocations(allocations)]}
    out.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    console.print(f"[green]Wrote allocation plan[/green]: {out}")


@app.command("interactive-allocate")
def interactive_allocate_command(
    config: ConfigOption,
    transcript: Annotated[Path, typer.Option("--transcript", "-t")],
    out: Annotated[Path, typer.Option("--out", "-o")],
    run_audit: Annotated[bool, typer.Option("--audit", help="Run audit after writing the allocation YAML.")] = False,
    audit_format: Annotated[str, typer.Option("--audit-format", help="Audit output format: text, json, or yaml.")] = "text",
) -> None:
    loaded = load_config(config)
    courses = load_transcript(transcript)
    student_flags = load_student_flags(transcript)
    choices_by_course = choices_for_transcript(loaded, courses)
    allocations_by_course = {}
    selected_allocations = []

    for course in courses:
        choices = choices_by_course[course.course_code]
        table = Table(title=f"{course.course_code} ({course.effective_code}, {course.units} units)")
        table.add_column("#")
        table.add_column("Requirement")
        table.add_column("Description")
        for index, choice in enumerate(choices, start=1):
            table.add_row(str(index), choice.requirement_id, choice.description)
        console.print(table)

        while True:
            raw_selection = typer.prompt("Choose allocation number(s), comma-separated; blank = UE_RESIDUAL", default="")
            try:
                selected_numbers = parse_selection(raw_selection, choices)
            except ValueError as exc:
                console.print(f"[red]{exc}[/]")
                continue
            break

        allocations = allocations_for_selection(course, choices, selected_numbers)
        allocations_by_course[course.course_code] = allocations
        selected_allocations.extend(allocations)

    write_commented_allocation_yaml(out, courses, choices_by_course, allocations_by_course)
    console.print(f"[green]Wrote interactive allocation[/green]: {out}")

    if run_audit:
        result = audit(loaded, courses, selected_allocations, student_flags=student_flags)
        _emit_audit_result(loaded, result, audit_format)


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
    try:
        loaded = load_config(config)
        courses = load_transcript(transcript)
        student_flags = load_student_flags(transcript)
        allocations = load_allocations(allocation) if allocation else None
        if allocations is not None:
            validate_manual_allocations(loaded, courses, allocations)
    except (ConfigLoadError, ManualAllocationValidationError, ValidationError, ValueError) as exc:
        typer.echo(f"Invalid input: {exc}", err=True)
        raise typer.Exit(1) from exc
    result = audit(loaded, courses, allocations, student_flags=student_flags)
    _emit_audit_result(loaded, result, output_format)


def _emit_audit_result(loaded, result, output_format: str) -> None:
    contract = to_contract_result(loaded, result)
    if output_format == "json":
        typer.echo(json.dumps(contract, indent=2))
    elif output_format == "yaml":
        typer.echo(yaml.safe_dump(contract, sort_keys=False))
    elif output_format == "text":
        render_audit_report(loaded, result, console=console)
    else:
        raise typer.BadParameter("format must be text, json, or yaml")

    if not contract["pass"]:
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
