from __future__ import annotations

import re

from degree_auditor.common_curriculum import EE24JC_UE
from degree_auditor.eligibility import canonical_code
from degree_auditor.models import (
    Allocation,
    Constraint,
    ConstraintResult,
    CourseAttempt,
    CourseSource,
    DegreeAuditConfig,
)


MAJOR_INTERNSHIP_SLOT = "MAJOR_INTERNSHIP"
MAJOR_INTERNSHIP_REQUIREMENT_ID = "MAJOR_INTERNSHIP_10"
VALID_INTERNSHIP_CODES = {
    "EG3611A",
    "EG3612",
    "CFG2101",
    "CDE2605",
    "CDE2605R",
    "ETP3201",
    "ETP3205",
    "ETP3206",
    "ETP3207",
    "EG3611P",
}
CEG_ONLY_CODES = {"CP3880", "CP3200", "CP3202"}
UROP_CODES = {"CDE2605", "CDE2605R"}
LEVEL_1000_EXCLUDED_PREFIXES = ("POY190", "DYOC")
LEVEL_1000_EXCLUDED_CODES = {"CFG1010", "ES1103", "CFG1002"}


def evaluate_internship_and_level1000(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    student_flags: list[str],
) -> tuple[list[ConstraintResult], list[str]]:
    results: list[ConstraintResult] = []
    warnings: list[str] = []
    internship_allocations = [
        allocation
        for allocation in allocations
        if allocation.requirement_id in {MAJOR_INTERNSHIP_SLOT, MAJOR_INTERNSHIP_REQUIREMENT_ID}
        and allocation.allocation_role != "ignored"
    ]
    poly_student = "POLY" in {flag.upper().strip() for flag in student_flags}

    ceg_only = sorted(
        allocation.course_code
        for allocation in internship_allocations
        if canonical_code(config, allocation.course_code) in CEG_ONLY_CODES
    )
    results.append(
        _result(
            _constraint(config, "MAJOR_INTERNSHIP_CEG_ONLY"),
            not ceg_only,
            f"{ceg_only[0]} (ATAP/SIP) is CEG-only and not valid for the EE-major internship"
            if ceg_only
            else "No CEG-only internship course is allocated to the EE major internship.",
            affected_courses=ceg_only,
        )
    )
    if ceg_only:
        warnings.append(f"{ceg_only[0]} (ATAP/SIP) is CEG-only and not valid for the EE-major internship")

    valid_major_units = 0
    urop_units = 0
    alias_used = False
    for allocation in internship_allocations:
        code = canonical_code(config, allocation.course_code)
        attempt = _attempt_for_allocation(config, courses, allocation)
        if allocation.course_code.upper().strip() == "EG2605" and code == "CDE2605":
            alias_used = True
        if code not in VALID_INTERNSHIP_CODES:
            continue
        if code == "EG3611P" and not (poly_student or (attempt is not None and attempt.source == CourseSource.apc)):
            continue
        units = allocation.units
        if code in UROP_CODES:
            urop_units += units
        valid_major_units += units

    urop_passed = urop_units <= 4
    if not urop_passed:
        warnings.append("At most 4 units of UROP/UREx count toward the major internship; excess goes to UE")
    results.append(
        _result(
            _constraint(config, "MAJOR_INTERNSHIP_UROP_CAP"),
            urop_passed,
            "At most 4 units of UROP/UREx count toward the major internship; excess goes to UE"
            if not urop_passed
            else "UROP/UREx internship units are within the 4-unit major cap.",
            affected_courses=[
                allocation.course_code
                for allocation in internship_allocations
                if canonical_code(config, allocation.course_code) in UROP_CODES
            ]
            if not urop_passed
            else [],
        )
    )

    combo_passed = valid_major_units >= 10 and not ceg_only and urop_passed
    if not combo_passed and internship_allocations and not ceg_only and urop_passed:
        warnings.append(f"Major internship: {valid_major_units} / 10 units; combination is short of 10")
    results.append(
        _result(
            _constraint(config, "MAJOR_INTERNSHIP_COMBO"),
            combo_passed or not internship_allocations,
            f"Major internship: {valid_major_units} / 10 units; combination is short of 10"
            if internship_allocations and not combo_passed and not ceg_only and urop_passed
            else f"Major internship has {min(valid_major_units, 10)} / 10 valid allocated unit(s).",
            affected_courses=[allocation.course_code for allocation in internship_allocations]
            if internship_allocations and not combo_passed
            else [],
        )
    )

    poly_allocations = [
        allocation
        for allocation in internship_allocations
        if canonical_code(config, allocation.course_code) == "EG3611P"
    ]
    poly_passed = not poly_allocations or poly_student or any(
        (attempt := _attempt_for_allocation(config, courses, allocation)) is not None
        and attempt.source == CourseSource.apc
        for allocation in poly_allocations
    )
    results.append(
        _result(
            _constraint(config, "MAJOR_INTERNSHIP_POLY_APC"),
            poly_passed,
            "EG3611P may satisfy internship only for poly-direct-entry APC students."
            if not poly_passed
            else "No invalid EG3611P APC internship allocation.",
            affected_courses=[allocation.course_code for allocation in poly_allocations] if not poly_passed else [],
        )
    )

    overflow = [
        allocation
        for allocation in allocations
        if allocation.requirement_id in {EE24JC_UE, "UE_RESIDUAL"}
        and canonical_code(config, allocation.course_code) in VALID_INTERNSHIP_CODES
    ]
    results.append(
        _result(
            _constraint(config, "MAJOR_INTERNSHIP_UE_OVERFLOW"),
            True,
            "Internship overflow allocations to UE are valid.",
            affected_courses=[allocation.course_code for allocation in overflow],
        )
    )
    for allocation in overflow:
        warnings.append(f"Internship units beyond 10 ({allocation.course_code}: {allocation.units}u) counted toward UE")
    if alias_used:
        warnings.append("EG2605 resolved to CDE2605 (UROP); counts as 4 units (within UROP cap)")

    level1000_units = _level1000_units(config, courses)
    level1000_passed = level1000_units <= 60
    results.append(
        _result(
            _constraint(config, "LVL1000_MAX_60"),
            level1000_passed,
            f"Level-1000 units {level1000_units} exceed the 60-unit cap; {level1000_units - 60} units will not count toward graduation"
            if not level1000_passed
            else f"Level-1000 units {level1000_units} are within the 60-unit cap.",
        )
    )
    if not level1000_passed:
        warnings.append(
            f"Level-1000 units {level1000_units} exceed the 60-unit cap; {level1000_units - 60} units will not count toward graduation"
        )

    return results, warnings


def has_internship_allocation(allocations: list[Allocation]) -> bool:
    return any(
        allocation.requirement_id in {MAJOR_INTERNSHIP_SLOT, MAJOR_INTERNSHIP_REQUIREMENT_ID}
        for allocation in allocations
    )


def _attempt_for_allocation(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocation: Allocation,
) -> CourseAttempt | None:
    allocation_code = canonical_code(config, allocation.course_code)
    for course in courses:
        if allocation_code == canonical_code(config, course.course_code):
            return course
    for course in courses:
        if allocation_code == canonical_code(config, course.effective_code):
            return course
    return None


def _level1000_units(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> int:
    total = 0
    for course in courses:
        code = canonical_code(config, course.effective_code)
        if code in LEVEL_1000_EXCLUDED_CODES or code.startswith(LEVEL_1000_EXCLUDED_PREFIXES):
            continue
        if re.match(r"^[A-Z]{2,4}1\d{3}[A-Z]*$", code):
            total += max(course.units, 4)
    return total


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
