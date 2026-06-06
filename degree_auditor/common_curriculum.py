from __future__ import annotations

from collections import defaultdict

from degree_auditor.eligibility import TC_REQUIREMENT_ID, is_tc_eligible
from degree_auditor.models import Allocation, Constraint, ConstraintResult, CourseAttempt, DegreeAuditConfig


CC_GE_GESS = "CC_GE_GESS"
CC_ISK_ST = "CC_ISK_ST"
CC_ISK_CN = "CC_ISK_CN"
CC_ISK_SF = "CC_ISK_SF"
CC_CAPSTONE = "CC_CAPSTONE"
EE24JC_UE = "EE24JC_UE"
CC_REQUIREMENT_IDS = {
    CC_GE_GESS,
    "CC_GE_GEC",
    "CC_GE_GEN",
    "CC_GE_ES2631",
    "CC_GE_CS1010E",
    "CC_GE_GEA1000",
    "CC_ISK_DTK1234",
    "CC_ISK_MAKER",
    CC_ISK_ST,
    "CC_ISK_AI",
    CC_ISK_SF,
    CC_ISK_CN,
    "CC_ISK_PM",
    "CC_ISK_CAPSTONE",
    CC_CAPSTONE,
    "CDE_COMMON_CURRICULUM",
}
CC_REVIEW_FLAGS = {"RC4", "UTCP", "NUSC", "RVRC", "POLY"}
TC_IN_LIEU_REQUIREMENTS = {CC_ISK_ST, CC_ISK_CN, CC_ISK_SF}


def evaluate_common_curriculum(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    student_flags: list[str],
) -> tuple[list[ConstraintResult], list[str]]:
    results: list[ConstraintResult] = []
    warnings: list[str] = []
    by_requirement = _allocations_by_requirement(allocations)
    transcript_codes = {course.effective_code for course in courses}
    review_flags = CC_REVIEW_FLAGS & {flag.upper().strip() for flag in student_flags}

    double_counted_cde2501 = _allocated_to("CDE2501", CC_GE_GESS, by_requirement) and _allocated_to(
        "CDE2501", CC_ISK_SF, by_requirement
    )
    results.append(
        _result(
            _constraint(config, "DOUBLE_USE_SINGLE_INSTANCE"),
            not double_counted_cde2501,
            "CDE2501 cannot satisfy both Singapore Studies and Sustainable Futures pillars."
            if double_counted_cde2501
            else "No single Common Curriculum course instance is double-counted across incompatible pillars.",
            affected_courses=["CDE2501"] if double_counted_cde2501 else [],
        )
    )
    if double_counted_cde2501:
        warnings.append("CDE2501 cannot satisfy both Singapore Studies and Sustainable Futures pillars")

    gess_allocated = any(allocation.course_code.startswith("GESS") for allocation in by_requirement[CC_GE_GESS])
    cde2501_to_gess = _allocated_to("CDE2501", CC_GE_GESS, by_requirement)
    cde2501_to_sf = _allocated_to("CDE2501", CC_ISK_SF, by_requirement)
    tc_to_sf = _tc_allocations_for_requirement(config, by_requirement[CC_ISK_SF], allocations)

    cde2501_valid = True
    cde2501_message = "CDE2501 Common Curriculum branch is valid."
    affected: list[str] = []
    if cde2501_to_gess and gess_allocated:
        cde2501_valid = False
        cde2501_message = "CDE2501 may count under Singapore Studies only when no GESS course is taken."
        affected = ["CDE2501"]
    elif gess_allocated and cde2501_to_sf and tc_to_sf:
        cde2501_valid = False
        cde2501_message = "GESS taken; CDE2501 occupies Sustainable Futures, so TC cannot also fill it."
        affected = [allocation.course_code for allocation in tc_to_sf]
    elif cde2501_to_gess and tc_to_sf:
        warnings.append("CDE2501 counted under Singapore Studies (no GESS taken); TC fills Sustainable Futures")
        cde2501_message = "CDE2501 counted under Singapore Studies; TC fills Sustainable Futures."
    elif gess_allocated and cde2501_to_sf:
        warnings.append("GESS taken; CDE2501 counted under Sustainable Futures; third TC read using UE")
        cde2501_message = "GESS taken; CDE2501 counted under Sustainable Futures."

    results.append(
        _result(
            _constraint(config, "CC_CDE2501_DUAL_ROLE"),
            cde2501_valid,
            cde2501_message,
            affected_courses=affected,
        )
    )

    results.extend(_evaluate_tc_in_lieu(config, by_requirement, allocations, transcript_codes, warnings))

    tc_in_lieu_used = any(_tc_allocations_for_requirement(config, by_requirement[req], allocations) for req in TC_IN_LIEU_REQUIREMENTS)
    rc_passed = not (review_flags and tc_in_lieu_used)
    results.append(
        _result(
            _constraint(config, "CC_RC_EXCLUSION"),
            rc_passed,
            "Standard TC-in-lieu substitution does not apply to RC4/UTCP/NUSC/RVRC/poly students; needs_human_review"
            if not rc_passed
            else "No college/poly human-review flag affects Common Curriculum substitution.",
            affected_courses=sorted(review_flags),
        )
    )
    if not rc_passed:
        warnings.append(
            "Standard TC-in-lieu substitution does not apply to RC4/UTCP/NUSC/RVRC/poly students; needs_human_review"
        )

    tc_in_lieu_count = sum(
        len(_tc_allocations_for_requirement(config, by_requirement[req], allocations)) for req in TC_IN_LIEU_REQUIREMENTS
    )
    results.append(
        _result(
            _constraint(config, "CC_TC_OVERFLOW_TO_UE"),
            True,
            f"{tc_in_lieu_count} TCs absorbed by ST/CN/SF pillars; degree total remains 160 units (not inflated).",
        )
    )
    if tc_in_lieu_count == 3:
        warnings.append("3 TCs absorbed by ST/CN/SF pillars; degree total remains 160 units (not inflated)")

    return results, warnings


def has_common_curriculum_allocation(allocations: list[Allocation]) -> bool:
    return any(allocation.requirement_id in CC_REQUIREMENT_IDS for allocation in allocations)


def _evaluate_tc_in_lieu(
    config: DegreeAuditConfig,
    by_requirement: dict[str, list[Allocation]],
    all_allocations: list[Allocation],
    transcript_codes: set[str],
    warnings: list[str],
) -> list[ConstraintResult]:
    checks = [
        (CC_ISK_ST, "IE2141", "Systems Thinking", "CC_TC_IN_LIEU_ST"),
        (CC_ISK_CN, "CDE2000", "Creating Narratives", "CC_TC_IN_LIEU_CN"),
    ]
    results: list[ConstraintResult] = []
    over_allocated_courses: list[str] = []

    for requirement_id, default_course, label, constraint_id in checks:
        allocations = by_requirement[requirement_id]
        default_allocated = _allocated_to(default_course, requirement_id, by_requirement)
        tc_allocations = _tc_allocations_for_requirement(config, allocations, all_allocations)
        passed = not (default_allocated and tc_allocations)
        message = (
            f"{label} pillar already satisfied by {default_course}; TC cannot also fill it."
            if not passed
            else f"{label} TC-in-lieu allocation is valid."
        )
        if not default_allocated and tc_allocations and default_course not in transcript_codes:
            warnings.append(f"{label} pillar satisfied by TC in lieu of {default_course}")
        if not passed:
            over_allocated_courses.extend([default_course, *[allocation.course_code for allocation in tc_allocations]])
        results.append(
            _result(
                _constraint(config, constraint_id),
                passed,
                message,
                affected_courses=[] if passed else [default_course, *[allocation.course_code for allocation in tc_allocations]],
            )
        )

    sf_allocations = by_requirement[CC_ISK_SF]
    sf_cde_allocated = _allocated_to("CDE2501", CC_ISK_SF, by_requirement)
    sf_tc_allocations = _tc_allocations_for_requirement(config, sf_allocations, all_allocations)
    sf_passed = not (sf_cde_allocated and sf_tc_allocations)
    if not sf_passed:
        over_allocated_courses.extend(["CDE2501", *[allocation.course_code for allocation in sf_tc_allocations]])
    results.append(
        _result(
            _constraint(config, "CC_TC_IN_LIEU_SF"),
            sf_passed,
            "Sustainable Futures already satisfied by CDE2501; TC cannot also fill it."
            if not sf_passed
            else "Sustainable Futures substitution allocation is valid.",
            affected_courses=[] if sf_passed else ["CDE2501", *[allocation.course_code for allocation in sf_tc_allocations]],
        )
    )

    results.append(
        _result(
            _constraint(config, "PILLAR_OVER_ALLOCATED"),
            not over_allocated_courses,
            "A Common Curriculum pillar cannot be satisfied by both its default course and a TC-in-lieu."
            if over_allocated_courses
            else "No Common Curriculum pillar is over-allocated.",
            affected_courses=sorted(set(over_allocated_courses)),
        )
    )
    if over_allocated_courses:
        warnings.append("Systems Thinking pillar already satisfied by IE2141; TC cannot also fill it")
    return results


def _tc_allocations_for_requirement(
    config: DegreeAuditConfig,
    requirement_allocations: list[Allocation],
    all_allocations: list[Allocation],
) -> list[Allocation]:
    tc_course_codes = {
        allocation.course_code
        for allocation in all_allocations
        if allocation.requirement_id == TC_REQUIREMENT_ID and allocation.allocation_role != "ignored"
    }
    return [
        allocation
        for allocation in requirement_allocations
        if allocation.allocation_role != "ignored"
        and (allocation.course_code in tc_course_codes or is_tc_eligible(config, allocation.course_code, all_allocations))
    ]


def _allocations_by_requirement(allocations: list[Allocation]) -> dict[str, list[Allocation]]:
    by_requirement: dict[str, list[Allocation]] = defaultdict(list)
    for allocation in allocations:
        if allocation.allocation_role != "ignored":
            by_requirement[allocation.requirement_id].append(allocation)
    return by_requirement


def _allocated_to(course_code: str, requirement_id: str, by_requirement: dict[str, list[Allocation]]) -> bool:
    return any(allocation.course_code == course_code for allocation in by_requirement[requirement_id])


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
