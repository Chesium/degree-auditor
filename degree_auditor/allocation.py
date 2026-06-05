from __future__ import annotations

from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
    is_tc_eligible,
    is_te_eligible,
)
from degree_auditor.models import Allocation, AllocationRole, CourseAttempt, DegreeAuditConfig


FIXED_MAJOR_CORE_REQUIREMENT_ID = "EE24JC_MAJOR_CORE"
UE_RESIDUAL_REQUIREMENT_ID = "UE_RESIDUAL"
FIXED_MAJOR_CORE = {"EE1111A", "EE2111A", "EE2012", "EE2022", "EE2023", "EE2027", "PC2020"}


def plan_allocations(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[Allocation]:
    allocations: list[Allocation] = []
    course_codes = [course.effective_code for course in courses]

    for course_code in course_codes:
        if course_code in FIXED_MAJOR_CORE:
            allocations.append(Allocation(course_code=course_code, requirement_id=FIXED_MAJOR_CORE_REQUIREMENT_ID))

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
        if _has_allocation(allocations, course_code, TC_REQUIREMENT_ID):
            continue
        if is_te_eligible(config, course_code):
            allocations.append(Allocation(course_code=course_code, requirement_id=TE_REQUIREMENT_ID))

    for course in courses:
        course_code = course.effective_code
        if not any(allocation.course_code == course_code for allocation in allocations):
            allocations.append(
                Allocation(
                    course_code=course_code,
                    requirement_id=UE_RESIDUAL_REQUIREMENT_ID,
                    units=course.units,
                    allocation_role=AllocationRole.residual_ue,
                )
            )

    return allocations


def _count_allocations(allocations: list[Allocation], requirement_id: str) -> int:
    return sum(
        1
        for allocation in allocations
        if allocation.requirement_id == requirement_id and allocation.allocation_role != AllocationRole.ignored
    )


def _has_allocation(allocations: list[Allocation], course_code: str, requirement_id: str) -> bool:
    return any(
        allocation.course_code == course_code
        and allocation.requirement_id == requirement_id
        and allocation.allocation_role != AllocationRole.ignored
        for allocation in allocations
    )

