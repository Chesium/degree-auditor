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
    if course.effective_code in {"EE2026", "EE2028"}:
        eligible.append(MAJOR_CHOICE_REQUIREMENT_ID)
    if is_tc_eligible(config, course.effective_code, allocations):
        eligible.append(TC_REQUIREMENT_ID)
    if is_te_eligible(config, course.effective_code):
        eligible.append(TE_REQUIREMENT_ID)
    return eligible


def is_tc_eligible(config: DegreeAuditConfig, course_code: str, allocations: list[Allocation]) -> bool:
    normalized = course_code.upper().strip()
    pool = config.pool_by_id("EE24JC_TC_POOL")
    if pool is None or not course_in_pool(normalized, pool):
        return False
    if normalized in {"EE2026", "EE2028"}:
        major_choice = major_choice_course(allocations)
        return major_choice is None or normalized != major_choice
    return True


def is_te_eligible(config: DegreeAuditConfig, course_code: str) -> bool:
    pool = config.pool_by_id("EE24JC_TE_POOL")
    return course_in_pool(course_code.upper().strip(), pool) if pool else False


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
    regex = "^" + re.escape(normalized).replace("X", r"\d") + "$"
    return re.match(regex, course_code) is not None

