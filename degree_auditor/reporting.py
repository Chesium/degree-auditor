from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from degree_auditor.audit import MAJOR_PROGRAMME_ID
from degree_auditor.eligibility import MAJOR_CHOICE_REQUIREMENT_ID, TC_REQUIREMENT_ID, TE_REQUIREMENT_ID
from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID
from degree_auditor.models import AuditResult, DegreeAuditConfig, SourceRef


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
    _print_requirement_summary(target, result)
    _print_allocation_sections(target, result)
    _print_specialisations(target, result)
    _print_sep_status(target, result)
    _print_failed_constraints(target, result)
    _print_source_refs(target, result)


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
        rows = [allocation for allocation in result.allocations if allocation.requirement_id in requirement_ids]
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


def _print_specialisations(console: Console, result: AuditResult) -> None:
    table = Table(title="Selected Specialisations")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Path")
    table.add_column("Units")
    table.add_column("Overlap Budget")
    table.add_column("Distinct Units")
    table.add_column("Failures", overflow="fold")
    table.add_column("Messages", overflow="fold")
    if not result.specialisation_results:
        table.add_row("-", "-", "-", "-", "-", "-", "-", "No selected specialisations.")
    for item in result.specialisation_results:
        table.add_row(
            item.specialisation_id,
            item.status,
            item.selected_path_id or "-",
            str(item.units_counted),
            f"{item.overlap_units} / 8",
            str(item.distinct_units),
            ", ".join(item.failed_requirements) or "-",
            " | ".join(item.messages) or "-",
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
    for item in sep_results:
        table.add_row(item.constraint_id, "PASS" if item.passed else "FAIL", item.message)
    for specialisation_id, message in sep_messages:
        table.add_row(f"SPECIALISATION_{specialisation_id}", "-", message)
    console.print(table)


def _print_failed_constraints(console: Console, result: AuditResult) -> None:
    table = Table(title="Failed Constraints")
    table.add_column("Constraint")
    table.add_column("Affected Courses")
    table.add_column("Message", overflow="fold")
    failed = [item for item in result.constraint_results if not item.passed]
    if not failed:
        table.add_row("-", "-", "No failed constraints.")
    for item in failed:
        table.add_row(item.constraint_id, ", ".join(item.affected_courses) or "-", item.message)
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
    for item in important:
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
