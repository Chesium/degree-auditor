from __future__ import annotations

from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID, plan_allocations
from degree_auditor.constraints import evaluate_constraints
from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
)
from degree_auditor.models import Allocation, AuditResult, CourseAttempt, DegreeAuditConfig
from degree_auditor.specialisations import evaluate_specialisations


MAJOR_PROGRAMME_ID = "EE24JC_MAJOR"


def audit(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    manual_allocations: list[Allocation] | None = None,
    student_flags: list[str] | None = None,
) -> AuditResult:
    allocations = manual_allocations if manual_allocations is not None else plan_allocations(config, courses)
    constraint_results = evaluate_constraints(config, courses, allocations)
    specialisation_results = evaluate_specialisations(config, courses, allocations, student_flags or [])
    failed_constraints = [result for result in constraint_results if not result.passed]
    failed_specialisations = [result for result in specialisation_results if result.status == "FAIL"]

    requirement_statuses = _requirement_statuses(failed_constraints)
    for result in specialisation_results:
        requirement_statuses[f"SPECIALISATION_{result.specialisation_id}"] = result.status
    satisfied_requirements = [
        requirement_id
        for requirement_id, status in requirement_statuses.items()
        if status == "PASS" and requirement_id != MAJOR_PROGRAMME_ID
    ]
    failed_requirements = [
        requirement_id
        for requirement_id, status in requirement_statuses.items()
        if status == "FAIL" and requirement_id != MAJOR_PROGRAMME_ID
    ]

    return AuditResult(
        overall_status="FAIL" if failed_constraints or failed_specialisations else "PASS",
        requirement_statuses=requirement_statuses,
        satisfied_requirements=satisfied_requirements,
        failed_requirements=failed_requirements,
        allocations=allocations,
        constraint_results=constraint_results,
        specialisation_results=specialisation_results,
    )


def greedy_allocate(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[Allocation]:
    return plan_allocations(config, courses)


def _requirement_statuses(failed_constraints: list) -> dict[str, str]:
    status_by_requirement = {
        FIXED_MAJOR_CORE_REQUIREMENT_ID: "PASS",
        MAJOR_CHOICE_REQUIREMENT_ID: "PASS",
        TC_REQUIREMENT_ID: "PASS",
        TE_REQUIREMENT_ID: "PASS",
    }
    constraint_requirements = {
        "EE24JC_MAJOR_CORE_COMPLETE": [FIXED_MAJOR_CORE_REQUIREMENT_ID],
        "EE24JC_MAJOR_CHOICE_EXACTLY_ONE": [MAJOR_CHOICE_REQUIREMENT_ID],
        "EE24JC_TC_MIN_3": [TC_REQUIREMENT_ID],
        "EE24JC_TC_ELIGIBILITY": [TC_REQUIREMENT_ID],
        "EE24JC_TE_MIN_2": [TE_REQUIREMENT_ID],
        "EE24JC_TE_ELIGIBILITY": [TE_REQUIREMENT_ID],
        "EE24JC_TC_TE_MUTUAL_EXCLUSION": [TC_REQUIREMENT_ID, TE_REQUIREMENT_ID],
    }

    for failure in failed_constraints:
        for requirement_id in constraint_requirements.get(failure.constraint_id, []):
            status_by_requirement[requirement_id] = "FAIL"

    major_parts = [
        status_by_requirement[FIXED_MAJOR_CORE_REQUIREMENT_ID],
        status_by_requirement[MAJOR_CHOICE_REQUIREMENT_ID],
        status_by_requirement[TE_REQUIREMENT_ID],
    ]
    status_by_requirement[MAJOR_PROGRAMME_ID] = "PASS" if all(status == "PASS" for status in major_parts) else "FAIL"
    return status_by_requirement
