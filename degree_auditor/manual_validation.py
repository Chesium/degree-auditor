from __future__ import annotations

from collections import defaultdict

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.allocation_choices import IGNORED_REQUIREMENT_ID
from degree_auditor.common_curriculum import EE24JC_UE
from degree_auditor.eligibility import canonical_code
from degree_auditor.internship import MAJOR_INTERNSHIP_SLOT
from degree_auditor.models import Allocation, CourseAttempt, DegreeAuditConfig
from degree_auditor.specialisations import IDP_SECOND_MAJOR_REQUIREMENT_ID, REQUIREMENT_SLOT_ALIASES


class ManualAllocationValidationError(ValueError):
    """Raised when a manual allocation file is structurally invalid."""


def validate_manual_allocations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> None:
    errors: list[str] = []
    known_requirements = _known_requirement_ids(config)
    seen_course_requirement: set[tuple[str, str]] = set()
    units_by_course_requirement: dict[tuple[str, str], int] = defaultdict(int)

    for allocation in allocations:
        attempt = _attempt_for_allocation(config, courses, allocation)
        if attempt is None:
            errors.append(f"Manual allocation references {allocation.course_code} which is not in the transcript")
        if allocation.requirement_id not in known_requirements:
            errors.append(f"Manual allocation references unknown requirement {allocation.requirement_id}")

        key = (allocation.course_code, allocation.requirement_id)
        if key in seen_course_requirement:
            errors.append(
                f"Manual allocation repeats {allocation.course_code} for {allocation.requirement_id}; "
                "a single course instance can be allocated only once to the same requirement"
            )
        seen_course_requirement.add(key)
        units_by_course_requirement[key] += allocation.units
        if attempt is not None and units_by_course_requirement[key] > attempt.units:
            errors.append(
                f"Allocation of {units_by_course_requirement[key]} units exceeds "
                f"{attempt.course_code}'s {attempt.units} available units"
            )

    if errors:
        raise ManualAllocationValidationError("; ".join(dict.fromkeys(errors)))


def _known_requirement_ids(config: DegreeAuditConfig) -> set[str]:
    requirement_ids = {requirement.id for requirement in config.requirements}
    requirement_ids.update({UE_RESIDUAL_REQUIREMENT_ID, EE24JC_UE, IGNORED_REQUIREMENT_ID})
    requirement_ids.update({MAJOR_INTERNSHIP_SLOT, IDP_SECOND_MAJOR_REQUIREMENT_ID})
    requirement_ids.update(REQUIREMENT_SLOT_ALIASES)
    return requirement_ids


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
