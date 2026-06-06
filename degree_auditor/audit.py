from __future__ import annotations

from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID, plan_allocations
from degree_auditor.common_curriculum import (
    CC_CAPSTONE,
    CC_GE_GESS,
    CC_ISK_CN,
    CC_ISK_SF,
    CC_ISK_ST,
    EE24JC_UE,
    evaluate_common_curriculum,
    has_common_curriculum_allocation,
)
from degree_auditor.constraints import evaluate_constraints
from degree_auditor.eligibility import (
    MAJOR_CHOICE_REQUIREMENT_ID,
    TC_REQUIREMENT_ID,
    TE_REQUIREMENT_ID,
)
from degree_auditor.models import Allocation, AuditResult, CourseAttempt, DegreeAuditConfig
from degree_auditor.specialisations import evaluate_sep_reuse_constraint, evaluate_specialisations


MAJOR_PROGRAMME_ID = "EE24JC_MAJOR"


def audit(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    manual_allocations: list[Allocation] | None = None,
    student_flags: list[str] | None = None,
) -> AuditResult:
    allocations = manual_allocations if manual_allocations is not None else plan_allocations(config, courses)
    constraint_results = evaluate_constraints(config, courses, allocations)
    cc_results, cc_warnings = evaluate_common_curriculum(config, courses, allocations, student_flags or [])
    constraint_results.extend(cc_results)
    specialisation_results = evaluate_specialisations(config, courses, allocations, student_flags or [])
    constraint_results.extend(evaluate_sep_reuse_constraint(config, courses, allocations))
    if _is_scoped_common_curriculum_audit(manual_allocations):
        constraint_results = [
            result for result in constraint_results if result.constraint_id not in _UNRELATED_CC_SCOPE_CONSTRAINTS
        ]
    failed_constraints = [result for result in constraint_results if not result.passed]
    failed_specialisations = [result for result in specialisation_results if result.status == "FAIL"]

    requirement_statuses = _requirement_statuses(failed_constraints)
    for result in specialisation_results:
        requirement_statuses[f"SPECIALISATION_{result.specialisation_id}"] = result.status
    satisfied_requirements = [
        requirement_id
        for requirement_id, status in requirement_statuses.items()
        if status == "PASS" and requirement_id != MAJOR_PROGRAMME_ID
    ]
    failed_requirements = [
        requirement_id
        for requirement_id, status in requirement_statuses.items()
        if status == "FAIL" and requirement_id != MAJOR_PROGRAMME_ID
    ]

    return AuditResult(
        overall_status="FAIL" if failed_constraints or failed_specialisations else "PASS",
        requirement_statuses=requirement_statuses,
        satisfied_requirements=satisfied_requirements,
        failed_requirements=failed_requirements,
        allocations=allocations,
        constraint_results=constraint_results,
        specialisation_results=specialisation_results,
        warnings=cc_warnings,
    )


def greedy_allocate(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[Allocation]:
    return plan_allocations(config, courses)


def _requirement_statuses(failed_constraints: list) -> dict[str, str]:
    status_by_requirement = {
        FIXED_MAJOR_CORE_REQUIREMENT_ID: "PASS",
        MAJOR_CHOICE_REQUIREMENT_ID: "PASS",
        TC_REQUIREMENT_ID: "PASS",
        TE_REQUIREMENT_ID: "PASS",
        "DEG_TOTAL_160": "PASS",
        "CDE_COMMON_CURRICULUM": "PASS",
        "UE_40": "PASS",
        "MAJOR_60": "PASS",
        CC_GE_GESS: "PASS",
        CC_ISK_ST: "PASS",
        CC_ISK_CN: "PASS",
        CC_ISK_SF: "PASS",
        CC_CAPSTONE: "PASS",
        "CC_ISK_CAPSTONE": "PASS",
    }
    constraint_requirements = {
        "EE24JC_MAJOR_CORE_COMPLETE": [FIXED_MAJOR_CORE_REQUIREMENT_ID],
        "EE24JC_MAJOR_CHOICE_EXACTLY_ONE": [MAJOR_CHOICE_REQUIREMENT_ID],
        "EE24JC_TC_MIN_3": [TC_REQUIREMENT_ID],
        "EE24JC_TC_ELIGIBILITY": [TC_REQUIREMENT_ID],
        "EE24JC_TE_MIN_2": [TE_REQUIREMENT_ID],
        "EE24JC_TE_ELIGIBILITY": [TE_REQUIREMENT_ID],
        "EE24JC_TE_SEP_ONE_NUS": [TE_REQUIREMENT_ID],
        "EE24JC_TE_SEP_MAX_ONE": [TE_REQUIREMENT_ID],
        "EE24JC_TC_TE_MUTUAL_EXCLUSION": [TC_REQUIREMENT_ID, TE_REQUIREMENT_ID],
        "DOUBLE_USE_SINGLE_INSTANCE": [CC_GE_GESS, CC_ISK_SF],
        "PILLAR_OVER_ALLOCATED": [CC_ISK_ST, CC_ISK_CN, CC_ISK_SF],
        "CC_CDE2501_DUAL_ROLE": [CC_GE_GESS, CC_ISK_SF],
        "CC_TC_IN_LIEU_ST": [CC_ISK_ST],
        "CC_TC_IN_LIEU_CN": [CC_ISK_CN],
        "CC_TC_IN_LIEU_SF": [CC_ISK_SF],
        "CC_RC_EXCLUSION": ["CDE_COMMON_CURRICULUM"],
        "DEG_TOTAL_160": ["DEG_TOTAL_160"],
        "CC_CDE_60": ["CDE_COMMON_CURRICULUM"],
        "UE_40": ["UE_40"],
        "MAJOR_60": ["MAJOR_60"],
    }

    for failure in failed_constraints:
        for requirement_id in constraint_requirements.get(failure.constraint_id, []):
            status_by_requirement[requirement_id] = "FAIL"

    major_parts = [
        status_by_requirement[FIXED_MAJOR_CORE_REQUIREMENT_ID],
        status_by_requirement[MAJOR_CHOICE_REQUIREMENT_ID],
        status_by_requirement[TE_REQUIREMENT_ID],
    ]
    status_by_requirement[MAJOR_PROGRAMME_ID] = "PASS" if all(status == "PASS" for status in major_parts) else "FAIL"
    return status_by_requirement


_UNRELATED_CC_SCOPE_CONSTRAINTS = {
    "EE24JC_MAJOR_CORE_COMPLETE",
    "EE24JC_MAJOR_CHOICE_EXACTLY_ONE",
    "EE24JC_TE_MIN_2",
    "EE24JC_TE_ELIGIBILITY",
    "EE24JC_TE_SEP_ONE_NUS",
    "EE24JC_TE_SEP_MAX_ONE",
}


def _is_scoped_common_curriculum_audit(manual_allocations: list[Allocation] | None) -> bool:
    if manual_allocations is None:
        return False
    return has_common_curriculum_allocation(manual_allocations) or any(
        allocation.requirement_id == EE24JC_UE for allocation in manual_allocations
    )
