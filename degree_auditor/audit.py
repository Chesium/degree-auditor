from __future__ import annotations

from degree_auditor.constraints import evaluate_constraints
from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
    is_tc_eligible,
    is_te_eligible,
)
from degree_auditor.models import Allocation, AuditResult, CourseAttempt, DegreeAuditConfig


FIXED_MAJOR_CORE = {"EE1111A", "EE2111A", "EE2012", "EE2022", "EE2023", "EE2027", "PC2020"}


def audit(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    manual_allocations: list[Allocation] | None = None,
) -> AuditResult:
    allocations = manual_allocations if manual_allocations is not None else greedy_allocate(config, courses)
    constraint_results = evaluate_constraints(config, courses, allocations)
    failed_constraints = [result for result in constraint_results if not result.passed]

    satisfied_requirements: list[str] = []
    failed_requirements: list[str] = []
    for requirement_id in (TC_REQUIREMENT_ID, TE_REQUIREMENT_ID):
        related_failures = [
            result
            for result in failed_constraints
            if requirement_id in result.message or requirement_id in result.description
        ]
        if related_failures:
            failed_requirements.append(requirement_id)
        else:
            satisfied_requirements.append(requirement_id)

    return AuditResult(
        overall_status="FAIL" if failed_constraints else "PASS",
        satisfied_requirements=satisfied_requirements,
        failed_requirements=failed_requirements,
        allocations=allocations,
        constraint_results=constraint_results,
    )


def greedy_allocate(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[Allocation]:
    allocations: list[Allocation] = []
    course_codes = [course.effective_code for course in courses]

    for course_code in course_codes:
        if course_code in FIXED_MAJOR_CORE:
            allocations.append(Allocation(course_code=course_code, requirement_id="EE24JC_MAJOR_CORE"))

    for choice in ("EE2028", "EE2026"):
        if choice in course_codes:
            allocations.append(Allocation(course_code=choice, requirement_id=MAJOR_CHOICE_REQUIREMENT_ID))
            break

    for course_code in course_codes:
        if _count_allocations(allocations, TC_REQUIREMENT_ID) >= 3:
            break
        if is_tc_eligible(config, course_code, allocations):
            allocations.append(Allocation(course_code=course_code, requirement_id=TC_REQUIREMENT_ID))

    for course_code in course_codes:
        if _count_allocations(allocations, TE_REQUIREMENT_ID) >= 2:
            break
        if any(allocation.course_code == course_code and allocation.requirement_id == TC_REQUIREMENT_ID for allocation in allocations):
            continue
        if is_te_eligible(config, course_code):
            allocations.append(Allocation(course_code=course_code, requirement_id=TE_REQUIREMENT_ID))

    return allocations


def _count_allocations(allocations: list[Allocation], requirement_id: str) -> int:
    return sum(1 for allocation in allocations if allocation.requirement_id == requirement_id)

