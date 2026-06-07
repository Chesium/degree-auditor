from __future__ import annotations

from collections import defaultdict

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.allocation_choices import IGNORED_REQUIREMENT_ID
from degree_auditor.common_curriculum import EE24JC_UE
from degree_auditor.constraints import manual_allocation_eligibility_errors
from degree_auditor.eligibility import canonical_code
from degree_auditor.id_registry import PUBLIC_SLOT_IDS, normalize_slot_id
from degree_auditor.internship import MAJOR_INTERNSHIP_SLOT
from degree_auditor.models import Allocation, CourseAttempt, DegreeAuditConfig
from degree_auditor.specialisations import (
    IDP_SECOND_MAJOR_REQUIREMENT_ID,
    REQUIREMENT_SLOT_ALIASES,
    manual_specialisation_eligibility_errors,
)


class ManualAllocationValidationError(ValueError):
    """Raised when a manual allocation file is structurally invalid."""


def validate_manual_allocations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> None:
    invalid_errors: list[str] = []
    known_requirements = _known_requirement_ids(config)
    seen_course_requirement: set[tuple[str, str]] = set()
    units_by_course_requirement: dict[tuple[str, str], int] = defaultdict(int)

    for allocation in allocations:
        attempt = _attempt_for_allocation(config, courses, allocation)
        if attempt is None:
            invalid_errors.append(f"Manual allocation references {allocation.course_code} which is not in the transcript")
        if allocation.requirement_id not in known_requirements:
            invalid_errors.append(f"Manual allocation references unknown requirement {allocation.requirement_id}")

        key = (allocation.course_code, allocation.requirement_id)
        if key in seen_course_requirement:
            invalid_errors.append(
                f"Manual allocation repeats {allocation.course_code} for {allocation.requirement_id}; "
                "a single course instance can be allocated only once to the same requirement"
            )
        seen_course_requirement.add(key)
        units_by_course_requirement[key] += allocation.units
        if attempt is not None and units_by_course_requirement[key] > attempt.units:
            invalid_errors.append(
                f"Allocation of {units_by_course_requirement[key]} units exceeds "
                f"{attempt.course_code}'s {attempt.units} available units"
            )

    errors = [f"MANUAL_ALLOC_INVALID: {message}" for message in dict.fromkeys(invalid_errors)]
    if not invalid_errors:
        ineligible = manual_allocation_eligibility_errors(config, courses, allocations)
        ineligible.extend(manual_specialisation_eligibility_errors(config, courses, allocations))
        errors.extend(
            f"MANUAL_ALLOC_INELIGIBLE: {message}"
            for allocation, message in _ineligible_errors_with_allocations(config, courses, allocations, ineligible)
            if not _is_audit_context_conflict(allocation, allocations)
        )

    if errors:
        raise ManualAllocationValidationError("; ".join(dict.fromkeys(errors)))


def _known_requirement_ids(config: DegreeAuditConfig) -> set[str]:
    requirement_ids = {requirement.id for requirement in config.requirements}
    requirement_ids.update({UE_RESIDUAL_REQUIREMENT_ID, EE24JC_UE, IGNORED_REQUIREMENT_ID})
    requirement_ids.update({MAJOR_INTERNSHIP_SLOT, IDP_SECOND_MAJOR_REQUIREMENT_ID})
    requirement_ids.update(REQUIREMENT_SLOT_ALIASES)
    requirement_ids.update(PUBLIC_SLOT_IDS)
    requirement_ids.update(normalize_slot_id(slot_id) for slot_id in PUBLIC_SLOT_IDS)
    return requirement_ids


def _ineligible_errors_with_allocations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    ineligible: list[tuple[str, str]],
) -> list[tuple[Allocation, str]]:
    remaining = list(dict.fromkeys(ineligible))
    resolved: list[tuple[Allocation, str]] = []
    eligible_allocations = [
        allocation
        for allocation in allocations
        if allocation.allocation_role != "ignored"
        and allocation.manual
        and _attempt_for_allocation(config, courses, allocation) is not None
    ]
    for item in remaining:
        course_code, message = item
        candidates = [allocation for allocation in eligible_allocations if allocation.course_code == course_code]
        if not candidates:
            continue
        allocation = next((candidate for candidate in candidates if _is_audit_context_conflict(candidate, allocations)), candidates[0])
        resolved.append((allocation, message))
    return resolved


def _is_audit_context_conflict(allocation: Allocation, allocations: list[Allocation]) -> bool:
    if allocation.course_code in {"EE2026", "EE2028"} and allocation.requirement_id == "EE24JC_TC":
        return any(
            other.course_code == allocation.course_code
            and other.requirement_id == "EE24JC_MAJOR_DIGITAL_CHOICE"
            and other.allocation_role != "ignored"
            for other in allocations
        )
    if allocation.course_code in {"CDE4301", "CDE4301A"}:
        has_idp = any(
            other.course_code == allocation.course_code
            and other.requirement_id == IDP_SECOND_MAJOR_REQUIREMENT_ID
            and other.allocation_role != "ignored"
            for other in allocations
        )
        return has_idp and allocation.requirement_id != IDP_SECOND_MAJOR_REQUIREMENT_ID
    return False


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
