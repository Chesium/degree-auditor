from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from degree_auditor.audit import MAJOR_PROGRAMME_ID
from degree_auditor.eligibility import MAJOR_CHOICE_REQUIREMENT_ID, TC_REQUIREMENT_ID, TE_REQUIREMENT_ID
from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID
from degree_auditor.models import AuditResult, DegreeAuditConfig, SourceRef
from degree_auditor.ordering import sort_allocations, sort_constraints, sort_specialisations


def render_audit_report(
    config: DegreeAuditConfig,
    result: AuditResult,
    *,
    console: Console | None = None,
) -> None:
    target = console or Console()
    title = config.title or config.programme_id or "Degree Audit"
    target.print(
        Panel.fit(
            f"{title}\nOverall status: {result.overall_status}",
            title="NUS EE AY24 JC Degree Audit",
        )
    )
    _print_overall_status(target, result)
    _print_requirement_summary(target, result)
    _print_allocation_sections(target, result)
    _print_missing_requirements(target, result)
    _print_specialisations(target, result)
    _print_sep_status(target, result)
    _print_warnings(target, result)
    _print_failed_constraints(target, result)
    _print_source_refs(target, result)


def _print_overall_status(console: Console, result: AuditResult) -> None:
    table = Table(title="Overall Status")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Overall", result.overall_status)
    table.add_row("Failed requirements", ", ".join(sorted(result.failed_requirements)) or "-")
    table.add_row(
        "Failed constraints",
        ", ".join(sorted(item.constraint_id for item in result.constraint_results if not item.passed)) or "-",
    )
    console.print(table)


def _print_requirement_summary(console: Console, result: AuditResult) -> None:
    table = Table(title="Requirement Status")
    table.add_column("Area")
    table.add_column("Requirement")
    table.add_column("Status")
    rows = [
        ("Major Programme", MAJOR_PROGRAMME_ID),
        ("Major Core", FIXED_MAJOR_CORE_REQUIREMENT_ID),
        ("Digital/Microcontroller Choice", MAJOR_CHOICE_REQUIREMENT_ID),
        ("Technical Courses", TC_REQUIREMENT_ID),
        ("Technical Electives", TE_REQUIREMENT_ID),
    ]
    for label, requirement_id in rows:
        table.add_row(label, requirement_id, result.requirement_statuses.get(requirement_id, "-"))
    for requirement_id in sorted(
        key for key in result.requirement_statuses if key.startswith(("DEG_", "CC_", "UE_", "MAJOR_INTERNSHIP"))
    ):
        table.add_row("Supporting Requirement", requirement_id, result.requirement_statuses.get(requirement_id, "-"))
    console.print(table)


def _print_allocation_sections(console: Console, result: AuditResult) -> None:
    groups = [
        ("EE Major", {FIXED_MAJOR_CORE_REQUIREMENT_ID, MAJOR_CHOICE_REQUIREMENT_ID}),
        ("Technical Courses", {TC_REQUIREMENT_ID}),
        ("Technical Electives", {TE_REQUIREMENT_ID}),
    ]
    for title, requirement_ids in groups:
        table = Table(title=title)
        table.add_column("Course")
        table.add_column("Requirement")
        table.add_column("Units")
        table.add_column("Role")
        rows = [allocation for allocation in sort_allocations(result.allocations) if allocation.requirement_id in requirement_ids]
        for allocation in rows:
            table.add_row(
                allocation.course_code,
                allocation.requirement_id,
                str(allocation.units),
                allocation.allocation_role,
            )
        if not rows:
            table.add_row("-", "-", "-", "-")
        console.print(table)


def _print_missing_requirements(console: Console, result: AuditResult) -> None:
    table = Table(title="Missing Courses and Units")
    table.add_column("Rule")
    table.add_column("Affected Courses")
    table.add_column("Message", overflow="fold")
    failed = [item for item in sort_constraints(result.constraint_results) if not item.passed]
    missing = [
        item
        for item in failed
        if item.affected_courses
        or "missing" in item.message.lower()
        or "requires" in item.message.lower()
        or "Needs " in item.message
    ]
    if not missing:
        table.add_row("-", "-", "No missing courses or units.")
    for item in missing:
        table.add_row(item.constraint_id, ", ".join(sorted(item.affected_courses)) or "-", item.message)
    for specialisation in sort_specialisations(result.specialisation_results):
        for message in sorted(specialisation.messages):
            if "missing" in message.lower() or "requires" in message.lower() or "Needs " in message:
                table.add_row(f"SPECIALISATION_{specialisation.specialisation_id}", "-", message)
    console.print(table)


def _print_specialisations(console: Console, result: AuditResult) -> None:
    table = Table(title="Selected Specialisations")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Path")
    table.add_column("Units")
    table.add_column("Overlap Budget")
    table.add_column("Distinct Units")
    table.add_column("SEP Mapped Units")
    table.add_column("Capstone Lock")
    table.add_column("Failures", overflow="fold")
    table.add_column("Messages", overflow="fold")
    if not result.specialisation_results:
        table.add_row("-", "-", "-", "-", "-", "-", "-", "-", "-", "No selected specialisations.")
    for item in sort_specialisations(result.specialisation_results):
        table.add_row(
            item.specialisation_id,
            item.status,
            item.selected_path_id or "-",
            str(item.units_counted),
            f"{item.overlap_units} / 8",
            str(item.distinct_units),
            str(_sep_mapped_units(item.messages)),
            "YES" if any("Capstone lock active" in message for message in item.messages) else "NO",
            ", ".join(sorted(item.failed_requirements)) or "-",
            " | ".join(sorted(item.messages)) or "-",
        )
    console.print(table)


def _print_sep_status(console: Console, result: AuditResult) -> None:
    table = Table(title="SEP Status")
    table.add_column("Rule")
    table.add_column("Status")
    table.add_column("Message", overflow="fold")
    sep_results = [item for item in result.constraint_results if "SEP" in item.constraint_id]
    sep_messages = [
        (item.specialisation_id, message)
        for item in result.specialisation_results
        for message in item.messages
        if "SEP" in message
    ]
    if not sep_results and not sep_messages:
        table.add_row("-", "-", "No SEP rules triggered.")
    for item in sort_constraints(sep_results):
        table.add_row(item.constraint_id, "PASS" if item.passed else "FAIL", item.message)
    for specialisation_id, message in sorted(sep_messages):
        table.add_row(f"SPECIALISATION_{specialisation_id}", "-", message)
    console.print(table)


def _print_warnings(console: Console, result: AuditResult) -> None:
    console.print("Warnings and Manual Notes")
    table = Table(title="Warnings and Manual Notes")
    table.add_column("Message", overflow="fold")
    messages = sorted(dict.fromkeys(result.warnings))
    for item in sort_constraints(result.constraint_results):
        if item.constraint_id == "MANUAL_ALLOC_INELIGIBLE" and not item.passed:
            messages.append(item.message)
    messages = sorted(dict.fromkeys(messages))
    if not messages:
        table.add_row("No warnings.")
    for message in messages:
        table.add_row(message)
    console.print(table)


def _print_failed_constraints(console: Console, result: AuditResult) -> None:
    table = Table(title="Failed Constraints")
    table.add_column("Constraint")
    table.add_column("Affected Courses")
    table.add_column("Message", overflow="fold")
    failed = [item for item in sort_constraints(result.constraint_results) if not item.passed]
    if not failed:
        table.add_row("-", "-", "No failed constraints.")
    for item in failed:
        table.add_row(item.constraint_id, ", ".join(sorted(item.affected_courses)) or "-", item.message)
    console.print(table)


def _print_source_refs(console: Console, result: AuditResult) -> None:
    table = Table(title="Source References")
    table.add_column("Rule")
    table.add_column("Source", overflow="fold")
    important = [
        item
        for item in result.constraint_results
        if not item.passed or "SEP" in item.constraint_id or item.constraint_id.startswith("EE24JC_")
    ]
    seen: set[tuple[str, str]] = set()
    for item in sort_constraints(important):
        source = _format_source(item.source_ref)
        key = (item.constraint_id, source)
        if key in seen:
            continue
        seen.add(key)
        table.add_row(item.constraint_id, source)
    if not seen:
        table.add_row("-", "-")
    console.print(table)


def _format_source(source_ref: SourceRef | None) -> str:
    if source_ref is None:
        return "-"
    source = source_ref.document
    if source_ref.page is not None:
        source = f"{source}:p{source_ref.page}"
    if source_ref.section:
        source = f"{source} ({source_ref.section})"
    return source


def _sep_mapped_units(messages: list[str]) -> int:
    for message in messages:
        if "SEP unit" not in message:
            continue
        parts = message.split()
        for index, part in enumerate(parts):
            if part == "maps" and index + 1 < len(parts):
                try:
                    return int(parts[index + 1])
                except ValueError:
                    return 0
    return 0
