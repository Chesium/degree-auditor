from __future__ import annotations

import re

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
from degree_auditor.internship import (
    MAJOR_INTERNSHIP_REQUIREMENT_ID,
    evaluate_internship_and_level1000,
    has_internship_allocation,
)
from degree_auditor.models import Allocation, AuditResult, CourseAttempt, DegreeAuditConfig
from degree_auditor.specialisations import (
    evaluate_sep_reuse_constraint,
    evaluate_specialisation_allocation_constraints,
    evaluate_specialisations,
    infer_specialisation_allocations,
)


MAJOR_PROGRAMME_ID = "EE24JC_MAJOR"


def audit(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    manual_allocations: list[Allocation] | None = None,
    student_flags: list[str] | None = None,
) -> AuditResult:
    allocations = manual_allocations if manual_allocations is not None else plan_allocations(config, courses)
    inferred_specialisation_warnings: list[str] = []
    inferred_specialisation_allocations: list[Allocation] = []
    if manual_allocations is None:
        inferred_specialisation_allocations, inferred_specialisation_warnings = infer_specialisation_allocations(
            config,
            courses,
            allocations,
        )
        allocations = allocations + inferred_specialisation_allocations
    constraint_results = evaluate_constraints(config, courses, allocations)
    cc_results, cc_warnings = evaluate_common_curriculum(config, courses, allocations, student_flags or [])
    constraint_results.extend(cc_results)
    internship_results, internship_warnings = evaluate_internship_and_level1000(
        config,
        courses,
        allocations,
        student_flags or [],
    )
    constraint_results.extend(internship_results)
    specialisation_results = evaluate_specialisations(config, courses, allocations, student_flags or [])
    constraint_results.extend(evaluate_specialisation_allocation_constraints(config, courses, allocations))
    constraint_results.extend(evaluate_sep_reuse_constraint(config, courses, allocations))
    if _is_scoped_supporting_rule_audit(manual_allocations, courses) or inferred_specialisation_allocations:
        constraint_results = [
            result for result in constraint_results if result.constraint_id not in _UNRELATED_CC_SCOPE_CONSTRAINTS
        ]
    if inferred_specialisation_allocations:
        constraint_results = [
            result
            for result in constraint_results
            if result.constraint_id not in _UNRELATED_INFERRED_SPEC_SCOPE_CONSTRAINTS
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
    warnings = (
        cc_warnings
        + internship_warnings
        + inferred_specialisation_warnings
        + _specialisation_warnings(specialisation_results)
        + _constraint_warnings(failed_constraints)
    )

    return AuditResult(
        overall_status="FAIL" if failed_constraints or failed_specialisations else "PASS",
        requirement_statuses=requirement_statuses,
        satisfied_requirements=satisfied_requirements,
        failed_requirements=failed_requirements,
        allocations=allocations,
        constraint_results=constraint_results,
        specialisation_results=specialisation_results,
        warnings=warnings,
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
        MAJOR_INTERNSHIP_REQUIREMENT_ID: "PASS",
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
        "TE_EXCLUDE_NON_EE": [TE_REQUIREMENT_ID],
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
        "MAJOR_INTERNSHIP_COMBO": [MAJOR_INTERNSHIP_REQUIREMENT_ID],
        "MAJOR_INTERNSHIP_UROP_CAP": [MAJOR_INTERNSHIP_REQUIREMENT_ID],
        "MAJOR_INTERNSHIP_POLY_APC": [MAJOR_INTERNSHIP_REQUIREMENT_ID],
        "MAJOR_INTERNSHIP_CEG_ONLY": [MAJOR_INTERNSHIP_REQUIREMENT_ID],
        "LVL1000_MAX_60": ["DEG_TOTAL_160"],
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
    "EE24JC_TC_MIN_3",
    "EE24JC_TC_ELIGIBILITY",
    "EE24JC_TE_MIN_2",
    "EE24JC_TE_SEP_ONE_NUS",
    "EE24JC_TE_SEP_MAX_ONE",
}

_UNRELATED_INFERRED_SPEC_SCOPE_CONSTRAINTS = {
    "TE_EXCLUDE_NON_EE",
}


def _is_scoped_supporting_rule_audit(
    manual_allocations: list[Allocation] | None,
    courses: list[CourseAttempt],
) -> bool:
    if manual_allocations is None:
        return _has_level1000_over_cap_shape(courses)
    return (
        has_common_curriculum_allocation(manual_allocations)
        or has_internship_allocation(manual_allocations)
        or _has_level1000_over_cap_shape(courses)
        or _is_catalog_edge_audit(manual_allocations)
        or _is_specialisation_edge_audit(manual_allocations)
        or any(
            allocation.requirement_id == EE24JC_UE for allocation in manual_allocations
        )
    )


def _has_level1000_over_cap_shape(courses: list[CourseAttempt]) -> bool:
    return (
        sum(max(course.units, 4) for course in courses if re.match(r"^[A-Z]{2,4}1\d{3}[A-Z]*$", course.effective_code))
        > 60
    )


def _constraint_warnings(failed_constraints: list) -> list[str]:
    warning_constraints = {
        "TE_EXCLUDE_NON_EE",
        "TC_EFFECTIVE_DATE_EE3033",
        "ALIAS_DUPLICATE_CREDIT",
        "MANUAL_ALLOC_INELIGIBLE",
        "CDE4301_NO_SPEC_IF_IDP",
    }
    return [
        result.message
        for result in failed_constraints
        if result.constraint_id in warning_constraints
    ]


def _specialisation_warnings(specialisation_results: list) -> list[str]:
    warning_fragments = {
        "8-unit equivalent",
        "iDP replacement path inactive",
        "EG4301 units cannot be counted",
    }
    return [
        message
        for result in specialisation_results
        for message in result.messages
        if any(fragment in message for fragment in warning_fragments)
    ]


def _is_catalog_edge_audit(manual_allocations: list[Allocation]) -> bool:
    courses = {allocation.course_code for allocation in manual_allocations}
    return bool(courses & {"EE3033", "CG3207", "EE3305", "ME3243", "ME3163", "ME3142"})


def _is_specialisation_edge_audit(manual_allocations: list[Allocation]) -> bool:
    specialisation_slots = {
        "AE_ELECTIVE",
        "IND4_CORE",
        "IND4_ELECTIVE",
        "IOT_ELECTIVE",
        "IOT_PROJECT",
        "MQM_ELECTIVE",
        "RBT_BASKET",
        "SET_ELECTIVE",
        "SPT_ELECTIVE",
        "AE_CORE",
        "AE_ELECTIVES",
        "IND4_CORE_CONTROL",
        "IND4_CORE_AUTOMATION",
        "IND4_CORE_DATA",
        "IND4_ELECTIVES",
        "IOT_CORE",
        "IOT_ELECTIVES",
        "IOT_PROJECT_OPTIONS",
        "MQM_CORE",
        "MQM_ELECTIVES",
        "MQM_PROJECT_OPTIONS",
        "RBT_ELECTIVES_12_UNITS",
        "RBT_ELECTIVES_20_UNITS",
        "RBT_CAPSTONE",
        "SET_CORE",
        "SET_ELECTIVES",
        "SPT_CORE",
        "SPT_ELECTIVES",
        "SPT_SATELLITE_CAPSTONE",
        "SPT_IDP_REPLACEMENT_ELECTIVES",
        "IDP_2ND_MAJOR",
    }
    return any(allocation.requirement_id in specialisation_slots for allocation in manual_allocations)
