from __future__ import annotations

from collections import defaultdict
import re

from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID
from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
    canonical_code,
    is_non_ee_te_excluded,
    is_tc_eligible,
    is_te_eligible,
    major_choice_course,
)
from degree_auditor.models import (
    Allocation,
    ApprovalStatus,
    Constraint,
    ConstraintResult,
    CourseAttempt,
    CourseSource,
    DegreeAuditConfig,
)


def evaluate_constraints(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    results.extend(_evaluate_major_core(config, courses))
    results.extend(_evaluate_major_choice(config, allocations))
    results.append(_evaluate_min_count(config, allocations, TC_REQUIREMENT_ID, "EE24JC_TC_MIN_3", minimum=3))
    results.append(_evaluate_min_count(config, allocations, TE_REQUIREMENT_ID, "EE24JC_TE_MIN_2", minimum=2))
    results.extend(_evaluate_tc_te_mutual_exclusion(config, allocations))
    results.extend(_evaluate_tc_eligibility(config, allocations))
    results.extend(_evaluate_ee3033_tc_effective_date(config, courses, allocations))
    results.extend(_evaluate_te_eligibility(config, courses, allocations))
    results.extend(_evaluate_non_ee_te_exclusion(config, courses, allocations))
    results.extend(_evaluate_te_sep_rules(config, courses, allocations))
    results.extend(_evaluate_alias_duplicate_credit(config, courses, allocations))
    return results


def _evaluate_major_core(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_MAJOR_CORE_COMPLETE")
    requirement = config.requirement_by_id(FIXED_MAJOR_CORE_REQUIREMENT_ID)
    required_courses = set(requirement.courses if requirement else [])
    transcript_courses = {course.effective_code for course in courses}
    missing = sorted(required_courses - transcript_courses)
    if not missing:
        return [_result(constraint, True, "All fixed EE major core courses are present in the transcript.")]
    return [
        _result(
            constraint,
            False,
            "Missing fixed EE major core course(s).",
            affected_courses=missing,
        )
    ]


def _evaluate_major_choice(config: DegreeAuditConfig, allocations: list[Allocation]) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_MAJOR_CHOICE_EXACTLY_ONE")
    requirement = config.requirement_by_id(MAJOR_CHOICE_REQUIREMENT_ID)
    allowed = set(requirement.courses if requirement else {"EE2026", "EE2028"})
    choices = [
        allocation.course_code
        for allocation in allocations
        if allocation.requirement_id == MAJOR_CHOICE_REQUIREMENT_ID
        and allocation.allocation_role != "ignored"
        and allocation.course_code in allowed
    ]
    if len(choices) == 1:
        return [_result(constraint, True, f"Major digital/microcontroller choice is {choices[0]}.")]
    return [
        _result(
            constraint,
            False,
            "Exactly one of EE2026 or EE2028 must be allocated to the EE major digital/microcontroller choice.",
            affected_courses=sorted(choices),
        )
    ]


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


def _evaluate_te_eligibility(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = _constraint(config, "EE24JC_TE_ELIGIBILITY")
    failures = sorted(
        {
            allocation.course_code
            for allocation in allocations
            if allocation.requirement_id == TE_REQUIREMENT_ID
            and allocation.allocation_role != "ignored"
            and not is_te_eligible(
                config,
                _effective_code_for_allocation(config, courses, allocation),
                original_code=allocation.course_code,
            )
            and not is_non_ee_te_excluded(allocation.course_code)
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


def _evaluate_non_ee_te_exclusion(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = _constraint(config, "TE_EXCLUDE_NON_EE")
    failures = sorted(
        {
            allocation.course_code
            for allocation in allocations
            if allocation.requirement_id == TE_REQUIREMENT_ID
            and allocation.allocation_role != "ignored"
            and is_non_ee_te_excluded(allocation.course_code)
        }
    )
    if not failures:
        return [_result(constraint, True, "No non-EE course is allocated to the EE TE rule.")]
    messages = [
        f"{course_code} is a non-EE course; it counts toward UE only, not the EE TE rule"
        for course_code in failures
    ]
    return [_result(constraint, False, "; ".join(messages), affected_courses=failures)]


def _evaluate_ee3033_tc_effective_date(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = _constraint(config, "TC_EFFECTIVE_DATE_EE3033")
    failures = []
    for allocation in allocations:
        if (
            allocation.requirement_id == TC_REQUIREMENT_ID
            and allocation.allocation_role != "ignored"
            and canonical_code(config, allocation.course_code) == "EE3033"
        ):
            attempt = _attempt_for_allocation(config, courses, allocation)
            if attempt is not None and not _term_at_or_after_ay25_26_s2(attempt.term):
                failures.append(allocation.course_code)
    if not failures:
        return [_result(constraint, True, "EE3033 TC allocations satisfy the AY2025/26 Sem 2 effective date.")]
    return [
        _result(
            constraint,
            False,
            "EE3033 is TC-eligible only from Semester 2 AY2025/26; attempt term precedes this",
            affected_courses=sorted(set(failures)),
        )
    ]


def _evaluate_alias_duplicate_credit(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = _constraint(config, "ALIAS_DUPLICATE_CREDIT")
    by_requirement: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for allocation in allocations:
        if allocation.allocation_role == "ignored":
            continue
        canonical = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        by_requirement[allocation.requirement_id][canonical].add(allocation.course_code)
    duplicates = sorted(
        {
            course_code
            for canonical_to_codes in by_requirement.values()
            for codes in canonical_to_codes.values()
            if len(codes) > 1
            for course_code in codes
        }
    )
    if not duplicates:
        return [_result(constraint, True, "No cross-listed alias is credited twice for the same requirement.")]
    return [
        _result(
            constraint,
            False,
            _alias_duplicate_message(duplicates),
            affected_courses=duplicates,
        )
    ]


def _evaluate_te_sep_rules(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    te_allocations = [
        allocation
        for allocation in allocations
        if allocation.requirement_id == TE_REQUIREMENT_ID and allocation.allocation_role != "ignored"
    ]
    qualifying: list[tuple[Allocation, CourseAttempt | None, str]] = []
    for allocation in te_allocations:
        attempt = _attempt_for_allocation(config, courses, allocation)
        code = canonical_code(config, attempt.effective_code if attempt is not None else allocation.course_code)
        if not _is_sep_restricted_te_code(code):
            continue
        qualifying.append((allocation, attempt, code))

    nus_courses = sorted(
        code
        for allocation, attempt, code in qualifying
        if attempt is not None and attempt.source == CourseSource.nus
    )
    sep_courses = sorted(
        {
            allocation.course_code
            for allocation, attempt, code in qualifying
            if attempt is not None
            and attempt.source == CourseSource.sep
            and attempt.approval_status == ApprovalStatus.approved
        }
    )
    non_approved_sep = sorted(
        {
            allocation.course_code
            for allocation, attempt, code in qualifying
            if attempt is not None
            and attempt.source == CourseSource.sep
            and attempt.approval_status != ApprovalStatus.approved
        }
    )

    one_nus_constraint = _constraint(config, "EE24JC_TE_SEP_ONE_NUS")
    max_one_constraint = _constraint(config, "EE24JC_TE_SEP_MAX_ONE")
    results = [
        _result(
            one_nus_constraint,
            bool(nus_courses),
            "At least one qualifying EE3xxxC or EE4xxx TE is completed at NUS."
            if nus_courses
            else "At least one qualifying EE3xxxC or EE4xxx TE must be completed at NUS.",
            affected_courses=[] if nus_courses else [allocation.course_code for allocation, _, _ in qualifying],
        )
    ]

    max_one_passed = len(sep_courses) <= 1 and not non_approved_sep
    message = f"{len(sep_courses)} approved SEP-mapped qualifying TE allocation(s); at most 1 allowed."
    if non_approved_sep:
        message = "SEP-mapped TE allocations must be approved before they can satisfy the Major TE rule."
    results.append(
        _result(
            max_one_constraint,
            max_one_passed,
            message,
            affected_courses=sep_courses[1:] if len(sep_courses) > 1 else non_approved_sep,
        )
    )
    return results


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


def _effective_code_for_allocation(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocation: Allocation,
) -> str:
    attempt = _attempt_for_allocation(config, courses, allocation)
    return attempt.effective_code if attempt is not None else allocation.course_code


def _is_sep_restricted_te_code(course_code: str) -> bool:
    return re.match(r"^EE4\d{3}$", course_code) is not None or re.match(r"^EE3\d{3}C$", course_code) is not None


def _term_at_or_after_ay25_26_s2(term: str | None) -> bool:
    if term is None:
        return True
    match = re.match(r"^AY(\d{4})-(\d{4}) S([12])$", term.strip().upper())
    if match is None:
        return True
    start_year = int(match.group(1))
    semester = int(match.group(3))
    return (start_year, semester) >= (2025, 2)


def _alias_duplicate_message(course_codes: list[str]) -> str:
    codes = set(course_codes)
    if {"EE3306", "ME3163"} <= codes:
        return "EE3306 and ME3163 are the same course; only one may be credited"
    if {"EE3305", "ME3243"} <= codes:
        return "EE3305 and ME3243 are the same course; only one may be credited"
    if {"EE3331C", "ME3142"} <= codes:
        return "EE3331C and ME3142 are the same course; only one may be credited"
    return "Cross-listed alias courses may only be credited once for the same requirement."


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
