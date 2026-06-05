from __future__ import annotations

from collections import defaultdict

from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
    is_tc_eligible,
    is_te_eligible,
    major_choice_course,
)
from degree_auditor.models import Allocation, Constraint, ConstraintResult, CourseAttempt, DegreeAuditConfig, SourceRef


def evaluate_constraints(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    results.append(_evaluate_min_count(config, allocations, TC_REQUIREMENT_ID, "EE24JC_TC_MIN_3", minimum=3))
    results.append(_evaluate_min_count(config, allocations, TE_REQUIREMENT_ID, "EE24JC_TE_MIN_2", minimum=2))
    results.extend(_evaluate_tc_te_mutual_exclusion(config, allocations))
    results.extend(_evaluate_tc_eligibility(config, allocations))
    results.extend(_evaluate_te_eligibility(config, allocations))
    return results


def _evaluate_min_count(
    config: DegreeAuditConfig,
    allocations: list[Allocation],
    requirement_id: str,
    constraint_id: str,
    minimum: int,
) -> ConstraintResult:
    constraint = _constraint(config, constraint_id)
    count = sum(
        1
        for allocation in allocations
        if allocation.requirement_id == requirement_id and allocation.allocation_role != "ignored"
    )
    return _result(
        constraint=constraint,
        passed=count >= minimum,
        message=f"{requirement_id} has {count} allocation(s); requires at least {minimum}.",
    )


def _evaluate_tc_te_mutual_exclusion(
    config: DegreeAuditConfig,
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_TC_TE_MUTUAL_EXCLUSION")
    by_course: dict[str, set[str]] = defaultdict(set)
    for allocation in allocations:
        if allocation.allocation_role == "ignored":
            continue
        if allocation.requirement_id in {TC_REQUIREMENT_ID, TE_REQUIREMENT_ID}:
            by_course[allocation.course_code].add(allocation.requirement_id)

    conflicts = sorted(
        course
        for course, requirement_ids in by_course.items()
        if {TC_REQUIREMENT_ID, TE_REQUIREMENT_ID}.issubset(requirement_ids)
    )
    if not conflicts:
        return [_result(constraint, True, "No course is allocated to both TC and TE.")]
    return [
        _result(
            constraint,
            False,
            "A course cannot be allocated to both TC and TE.",
            affected_courses=conflicts,
        )
    ]


def _evaluate_tc_eligibility(config: DegreeAuditConfig, allocations: list[Allocation]) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_TC_ELIGIBILITY")
    failures: list[str] = []
    choice = major_choice_course(allocations)
    for allocation in allocations:
        if allocation.requirement_id != TC_REQUIREMENT_ID or allocation.allocation_role == "ignored":
            continue
        if not is_tc_eligible(config, allocation.course_code, allocations):
            if allocation.course_code in {"EE2026", "EE2028"} and allocation.course_code == choice:
                failures.append(allocation.course_code)
            else:
                failures.append(allocation.course_code)
    if not failures:
        return [_result(constraint, True, "All TC allocations are eligible.")]
    return [
        _result(
            constraint,
            False,
            "One or more TC allocations are not eligible; EE2026/EE2028 can count as TC only if not used for the major choice.",
            affected_courses=sorted(set(failures)),
        )
    ]


def _evaluate_te_eligibility(config: DegreeAuditConfig, allocations: list[Allocation]) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_TE_ELIGIBILITY")
    failures = sorted(
        {
            allocation.course_code
            for allocation in allocations
            if allocation.requirement_id == TE_REQUIREMENT_ID
            and allocation.allocation_role != "ignored"
            and not is_te_eligible(config, allocation.course_code)
        }
    )
    if not failures:
        return [_result(constraint, True, "All TE allocations are eligible.")]
    return [
        _result(
            constraint,
            False,
            "One or more TE allocations are not eligible; EE3031 and EE3033 cannot fulfil the TE rule.",
            affected_courses=failures,
        )
    ]


def _constraint(config: DegreeAuditConfig, constraint_id: str) -> Constraint | None:
    return config.constraint_by_id(constraint_id)


def _result(
    constraint: Constraint | None,
    passed: bool,
    message: str,
    affected_courses: list[str] | None = None,
) -> ConstraintResult:
    return ConstraintResult(
        constraint_id=constraint.id if constraint else "UNKNOWN",
        passed=passed,
        description=constraint.description if constraint else "Unknown constraint",
        source_ref=constraint.source_ref if constraint else None,
        message=message,
        affected_courses=affected_courses or [],
    )

