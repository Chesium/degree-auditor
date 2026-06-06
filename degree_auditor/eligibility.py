from __future__ import annotations

import re

from degree_auditor.models import Allocation, CourseAttempt, CoursePool, DegreeAuditConfig


MAJOR_CHOICE_REQUIREMENT_ID = "EE24JC_MAJOR_DIGITAL_CHOICE"
TC_REQUIREMENT_ID = "EE24JC_TC"
TE_REQUIREMENT_ID = "EE24JC_TE"


def expand_eligibility(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation] | None = None,
) -> dict[str, list[str]]:
    return {
        course.course_code: eligible_requirement_ids(config, course, allocations or [])
        for course in courses
    }


def eligible_requirement_ids(
    config: DegreeAuditConfig,
    course: CourseAttempt,
    allocations: list[Allocation],
) -> list[str]:
    eligible: list[str] = []
    canonical_code = canonical_course_code(config, course)
    if canonical_code in {"EE2026", "EE2028"}:
        eligible.append(MAJOR_CHOICE_REQUIREMENT_ID)
    if is_tc_eligible(config, canonical_code, allocations):
        eligible.append(TC_REQUIREMENT_ID)
    if is_te_eligible(config, canonical_code, original_code=course.course_code):
        eligible.append(TE_REQUIREMENT_ID)
    return eligible


def is_tc_eligible(config: DegreeAuditConfig, course_code: str, allocations: list[Allocation]) -> bool:
    normalized = canonical_code(config, course_code)
    pool = config.pool_by_id("EE24JC_TC_POOL")
    if pool is None or not course_in_pool(normalized, pool):
        return False
    if normalized in {"EE2026", "EE2028"}:
        major_choice = major_choice_course(allocations)
        return major_choice is None or normalized != major_choice
    return True


def is_te_eligible(config: DegreeAuditConfig, course_code: str, original_code: str | None = None) -> bool:
    if original_code is not None and is_non_ee_te_excluded(original_code):
        return False
    pool = config.pool_by_id("EE24JC_TE_POOL")
    return course_in_pool(canonical_code(config, course_code), pool) if pool else False


def is_non_ee_te_excluded(course_code: str) -> bool:
    normalized = course_code.upper().strip()
    return (
        normalized.startswith("ME")
        or normalized.startswith("RB")
        or re.match(r"^CS\d{4}DE$", normalized) is not None
        or normalized in {"CS3237", "CS3244", "CS4222"}
    )


def canonical_course_code(config: DegreeAuditConfig, course: CourseAttempt) -> str:
    return canonical_code(config, course.effective_code)


def canonical_code(config: DegreeAuditConfig, course_code: str) -> str:
    normalized = course_code.upper().strip()
    alias = config.alias_for(normalized)
    return alias.canonical.upper().strip() if alias else normalized


def course_in_pool(course_code: str, pool: CoursePool) -> bool:
    normalized = course_code.upper().strip()
    if any(_pattern_matches(pattern, normalized) for pattern in pool.excludes):
        return False
    return any(_pattern_matches(pattern, normalized) for pattern in pool.includes)


def major_choice_course(allocations: list[Allocation]) -> str | None:
    for allocation in allocations:
        if allocation.requirement_id == MAJOR_CHOICE_REQUIREMENT_ID and allocation.allocation_role != "ignored":
            return allocation.course_code
    return None


def _pattern_matches(pattern: str, course_code: str) -> bool:
    normalized = pattern.upper().strip()
    if "X" not in normalized:
        return normalized == course_code
    regex = "^" + "".join(r"\d" if char == "X" else re.escape(char) for char in normalized) + "$"
    return re.match(regex, course_code) is not None
