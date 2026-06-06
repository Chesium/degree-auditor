from __future__ import annotations

from typing import Any

from degree_auditor.models import Allocation, ConstraintResult, SpecialisationResult


REQUIREMENT_PRIORITY = {
    "EE24JC_MAJOR_CORE": 10,
    "EE24JC_MAJOR_DIGITAL_CHOICE": 20,
    "CDE_CAPSTONE": 30,
    "EE24JC_TC": 40,
    "EE24JC_TE": 50,
    "CC_GE_GESS": 60,
    "CC_ISK_ST": 61,
    "CC_ISK_CN": 62,
    "CC_ISK_SF": 63,
    "MAJOR_INTERNSHIP_10": 70,
    "MAJOR_INTERNSHIP": 70,
    "UE_RESIDUAL": 900,
    "EE24JC_UE": 900,
}


def allocation_sort_key(allocation: Allocation) -> tuple[int, str, str, str]:
    return (
        REQUIREMENT_PRIORITY.get(allocation.requirement_id, 500),
        allocation.course_code,
        allocation.requirement_id,
        allocation.allocation_role.value,
    )


def sort_allocations(allocations: list[Allocation]) -> list[Allocation]:
    return sorted(allocations, key=allocation_sort_key)


def constraint_sort_key(item: ConstraintResult) -> tuple[int, str, str]:
    return (0 if not item.passed else 1, item.constraint_id, ",".join(sorted(item.affected_courses)))


def sort_constraints(constraints: list[ConstraintResult]) -> list[ConstraintResult]:
    return sorted(constraints, key=constraint_sort_key)


def sort_specialisations(results: list[SpecialisationResult]) -> list[SpecialisationResult]:
    return sorted(results, key=lambda item: item.specialisation_id)


def sorted_unique(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values))


def contract_row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("id", "")),
        str(row.get("status", "")),
        ",".join(str(item) for item in row.get("affected_courses", [])),
    )
