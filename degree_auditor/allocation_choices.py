from __future__ import annotations

from dataclasses import dataclass

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
    canonical_course_code,
    course_in_pool,
    eligible_requirement_ids,
)
from degree_auditor.models import Allocation, CourseAttempt, DegreeAuditConfig, Requirement


IGNORED_REQUIREMENT_ID = "IGNORED"


@dataclass(frozen=True)
class AllocationChoice:
    requirement_id: str
    description: str


def allocation_choices_for_course(
    config: DegreeAuditConfig,
    course: CourseAttempt,
    allocations: list[Allocation] | None = None,
) -> list[AllocationChoice]:
    requirement_ids: list[str] = []
    for requirement_id in eligible_requirement_ids(config, course, allocations or []):
        _append_unique(requirement_ids, requirement_id)

    code = canonical_course_code(config, course)
    tags = {tag.lower() for tag in course.topic_tags}
    for requirement in config.requirements:
        if _requirement_matches(config, requirement, code, tags):
            _append_unique(requirement_ids, requirement.id)

    _append_unique(requirement_ids, UE_RESIDUAL_REQUIREMENT_ID)
    _append_unique(requirement_ids, IGNORED_REQUIREMENT_ID)
    return [
        AllocationChoice(requirement_id=requirement_id, description=_description(config, requirement_id))
        for requirement_id in requirement_ids
    ]


def expand_allocation_choices(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
) -> dict[str, list[AllocationChoice]]:
    return {course.course_code: allocation_choices_for_course(config, course) for course in courses}


def _requirement_matches(
    config: DegreeAuditConfig,
    requirement: Requirement,
    course_code: str,
    topic_tags: set[str],
) -> bool:
    requirement_courses = {course.upper().strip() for course in requirement.courses}
    if requirement.requirement_type in {"course_list", "all_of", "choice"}:
        return course_code in requirement_courses

    if requirement.requirement_type in {"pool_count", "choose_count", "choose_units"}:
        if requirement.pool_id is None:
            return False
        pool = config.pool_by_id(requirement.pool_id)
        return course_in_pool(course_code, pool) if pool else False

    if requirement.requirement_type == "project_option":
        if course_code not in requirement_courses:
            return False
        required_tags = {tag.lower() for tag in requirement.topic_tags}
        return not required_tags or required_tags <= topic_tags

    return False


def _description(config: DegreeAuditConfig, requirement_id: str) -> str:
    if requirement_id == UE_RESIDUAL_REQUIREMENT_ID:
        return "Residual unrestricted elective allocation."
    if requirement_id == IGNORED_REQUIREMENT_ID:
        return "Skip this course in the allocation file."
    requirement = config.requirement_by_id(requirement_id)
    return requirement.description if requirement else requirement_id


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
