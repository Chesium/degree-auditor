from __future__ import annotations

from collections import defaultdict
from typing import Any

from degree_auditor.audit import MAJOR_PROGRAMME_ID
from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID, UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.models import AuditResult, ConstraintResult, DegreeAuditConfig, SourceRef
from degree_auditor.ordering import contract_row_key, sort_allocations


COHORT_ID = "nus_ee_ay24_jc"
TOTAL_UNITS = 160

REQUIREMENT_ID_MAP = {
    "EE24JC_TC": "TC_MIN_3",
    "EE24JC_TE": "TE_MIN_2",
    "EE24JC_UE": "UE_40",
    UE_RESIDUAL_REQUIREMENT_ID: "UE_40",
    "EE24JC_MAJOR_DIGITAL_CHOICE": "MAJ_DIGITAL_CHOICE",
    FIXED_MAJOR_CORE_REQUIREMENT_ID: "MAJOR_60",
    MAJOR_PROGRAMME_ID: "MAJOR_60",
    "DEG_TOTAL_160": "DEG_TOTAL_160",
    "CDE_COMMON_CURRICULUM": "CC_CDE_60",
    "UE_40": "UE_40",
    "MAJOR_60": "MAJOR_60",
    "MAJOR_INTERNSHIP": "MAJOR_INTERNSHIP_10",
    "MAJOR_INTERNSHIP_10": "MAJOR_INTERNSHIP_10",
    "CC_GE_GESS": "CC_GE_GESS",
    "CC_GE_GEC": "CC_GE_GEC",
    "CC_GE_GEN": "CC_GE_GEN",
    "CC_GE_ES2631": "CC_GE_ES2631",
    "CC_GE_CS1010E": "CC_GE_CS1010E",
    "CC_GE_GEA1000": "CC_GE_GEA1000",
    "CC_ISK_DTK1234": "CC_ISK_DTK1234",
    "CC_ISK_MAKER": "CC_ISK_MAKER",
    "CC_ISK_ST": "CC_ISK_ST",
    "CC_ISK_AI": "CC_ISK_AI",
    "CC_ISK_SF": "CC_ISK_SF",
    "CC_ISK_CN": "CC_ISK_CN",
    "CC_ISK_PM": "CC_ISK_PM",
    "CC_ISK_CAPSTONE": "CC_CAPSTONE",
    "CC_CAPSTONE": "CC_CAPSTONE",
    "AE_CORE": "AE_CORE",
    "AE_ELECTIVE": "AE_ELECTIVES_MIN_3",
    "AE_ELECTIVES": "AE_ELECTIVES_MIN_3",
    "IND4_CORE": "IND4_CORE",
    "IND4_CORE_CONTROL": "IND4_CORE",
    "IND4_CORE_AUTOMATION": "IND4_CORE",
    "IND4_CORE_DATA": "IND4_CORE",
    "IND4_ELECTIVE": "IND4_ELECTIVES_MIN_3",
    "IND4_ELECTIVES": "IND4_ELECTIVES_MIN_3",
    "IOT_CORE": "IOT_CORE",
    "IOT_ELECTIVE": "IOT_ELECTIVES_MIN_2_OR_8U",
    "IOT_ELECTIVES": "IOT_ELECTIVES_MIN_2_OR_8U",
    "IOT_PROJECT": "IOT_ELECTIVES_MIN_2_OR_8U",
    "IOT_PROJECT_OPTIONS": "IOT_ELECTIVES_MIN_2_OR_8U",
    "MQM_CORE": "MQM_CORE",
    "MQM_ELECTIVE": "MQM_ELECTIVES_MIN_3_OR_12U",
    "MQM_ELECTIVES": "MQM_ELECTIVES_MIN_3_OR_12U",
    "MQM_PROJECT_OPTIONS": "MQM_ELECTIVES_MIN_3_OR_12U",
    "RBT_BASKET": "RBT_PATH1_CAPSTONE",
    "RBT_ELECTIVES_12_UNITS": "RBT_PATH1_CAPSTONE",
    "RBT_ELECTIVES_20_UNITS": "RBT_PATH2_COURSEWORK",
    "RBT_CAPSTONE": "RBT_PATH1_CAPSTONE",
    "SET_CORE": "SET_CORE",
    "SET_ELECTIVE": "SET_ELECTIVES_MIN_2",
    "SET_ELECTIVES": "SET_ELECTIVES_MIN_2",
    "SPT_CORE": "SPT_CORE",
    "SPT_ELECTIVE": "SPT_ELECTIVES_MIN_2",
    "SPT_ELECTIVES": "SPT_ELECTIVES_MIN_2",
    "SPT_SATELLITE_CAPSTONE": "SPT_CORE",
    "SPT_IDP_REPLACEMENT_ELECTIVES": "SPT_IDP_PATH",
    "CDE_CAPSTONE": "CC_CAPSTONE",
}

CONSTRAINT_ID_MAP = {
    "EE24JC_TC_TE_MUTUAL_EXCLUSION": "TC_NOT_TE",
    "EE24JC_TE_SEP_ONE_NUS": "SEP_TE_ONE_NUS",
    "EE24JC_TE_SEP_MAX_ONE": "SEP_TE_MAX_ONE_MAPPED",
    "EE_SPEC_SEP_NO_REUSE": "SEP_SPEC_NO_REUSE",
    "TE_EXCLUDE_NON_EE": "TE_EXCLUDE_NON_EE",
    "TC_EFFECTIVE_DATE_EE3033": "TC_EFFECTIVE_DATE_EE3033",
    "ALIAS_DUPLICATE_CREDIT": "ALIAS_DUPLICATE_CREDIT",
    "MANUAL_ALLOC_INELIGIBLE": "MANUAL_ALLOC_INELIGIBLE",
    "CDE4301_NO_SPEC_IF_IDP": "CDE4301_NO_SPEC_IF_IDP",
    "SEP_RESIDENCY_50": "SEP_RESIDENCY_50",
    "SEP_PROGRAMME_60": "SEP_PROGRAMME_60",
    "SEP_MAY_MAP_TC": "SEP_MAY_MAP_TC",
}

SPECIALISATION_FAILURE_MAP = {
    "CAPSTONE_LOCK": "CAP_LOCK",
    "SEP_FORBIDDEN_WITH_CAPSTONE": "SEP_CAPSTONE_FORBIDS_SEP",
    "SEP_MAX_8_UNITS": "SEP_SPEC_MAX_8",
    "SEP_NO_REUSE": "SEP_SPEC_NO_REUSE",
    "GLOBAL_POLICY": "SPEC_MAX_OVERLAP_8",
}


def to_contract_result(config: DegreeAuditConfig, result: AuditResult) -> dict[str, Any]:
    constraints = _contract_constraints(result)
    failed_constraints = [item["id"] for item in constraints if item["status"] == "FAIL"]
    requirements = _contract_requirements(config, result)
    specialisations = sorted(
        [_contract_specialisation(item) for item in result.specialisation_results],
        key=lambda item: item["id"],
    )
    return {
        "pass": result.overall_status == "PASS",
        "cohort": COHORT_ID,
        "total_units": TOTAL_UNITS,
        "requirements": requirements,
        "failed_requirements": [item["id"] for item in requirements if item["status"] == "FAIL"],
        "constraints": constraints,
        "failed_constraints": failed_constraints,
        "warnings": sorted(dict.fromkeys(result.warnings)),
        "specialisations": specialisations,
        "allocations": [
            {
                "course_code": allocation.course_code,
                "requirement_id": map_requirement_id(allocation.requirement_id),
                "units": allocation.units,
                "allocation_role": allocation.allocation_role.value,
                "manual": allocation.manual,
            }
            for allocation in sort_allocations(result.allocations)
        ],
    }


def map_requirement_id(requirement_id: str) -> str:
    if requirement_id.startswith("SPECIALISATION_"):
        return requirement_id
    return REQUIREMENT_ID_MAP.get(requirement_id, requirement_id)


def map_constraint_id(constraint_id: str) -> str:
    return CONSTRAINT_ID_MAP.get(constraint_id, constraint_id)


def _contract_requirements(config: DegreeAuditConfig, result: AuditResult) -> list[dict[str, Any]]:
    units_by_requirement: dict[str, int] = defaultdict(int)
    courses_by_requirement: dict[str, list[str]] = defaultdict(list)
    seen_by_requirement: dict[str, set[str]] = defaultdict(set)
    for allocation in result.allocations:
        mapped_id = map_requirement_id(allocation.requirement_id)
        if allocation.course_code in seen_by_requirement[mapped_id]:
            continue
        seen_by_requirement[mapped_id].add(allocation.course_code)
        units_by_requirement[mapped_id] += allocation.units
        courses_by_requirement[mapped_id].append(allocation.course_code)

    rows: list[dict[str, Any]] = []
    for internal_id, status in result.requirement_statuses.items():
        mapped_id = map_requirement_id(internal_id)
        rows.append(
            {
                "id": mapped_id,
                "status": status,
                "units_done": units_by_requirement.get(mapped_id, 0),
                "units_required": _units_required(config, internal_id, mapped_id),
                "satisfied_by": sorted(courses_by_requirement.get(mapped_id, [])),
                "source_ref": _source_ref(config, internal_id),
            }
        )
    existing = {row["id"] for row in rows}
    for specialisation in result.specialisation_results:
        for internal_id in specialisation.failed_requirements:
            mapped_id = map_requirement_id(internal_id)
            if mapped_id in existing:
                continue
            rows.append(
                {
                    "id": mapped_id,
                    "status": "FAIL",
                    "units_done": units_by_requirement.get(mapped_id, 0),
                    "units_required": _units_required(config, internal_id, mapped_id),
                    "satisfied_by": sorted(courses_by_requirement.get(mapped_id, [])),
                    "source_ref": _source_ref(config, internal_id),
                }
            )
            existing.add(mapped_id)
    return sorted(rows, key=contract_row_key)


def _contract_constraints(result: AuditResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in result.constraint_results:
        mapped_ids = _mapped_constraint_ids(item)
        for mapped_id in mapped_ids:
            rows.append(
                {
                    "id": mapped_id,
                    "status": "PASS" if item.passed else "FAIL",
                    "message": item.message,
                    "source_ref": _dump_source_ref(item.source_ref),
                    "affected_courses": sorted(item.affected_courses),
                }
            )
    for specialisation in result.specialisation_results:
        for failure in specialisation.failed_requirements:
            mapped_id = _map_specialisation_failure(failure)
            if mapped_id is None:
                continue
            rows.append(
                {
                    "id": mapped_id,
                    "status": "FAIL",
                    "message": "; ".join(specialisation.messages) or failure,
                    "source_ref": None,
                    "affected_courses": [],
                }
            )
    return sorted(_dedupe_constraint_rows(rows), key=contract_row_key)


def _mapped_constraint_ids(item: ConstraintResult) -> list[str]:
    if item.constraint_id == "EE24JC_TE_ELIGIBILITY" and not item.passed:
        mapped = []
        if "EE3031" in item.affected_courses:
            mapped.append("TE_EXCLUDE_EE3031")
        if "EE3033" in item.affected_courses:
            mapped.append("TE_EXCLUDE_EE3033")
        return mapped or [item.constraint_id]
    return [map_constraint_id(item.constraint_id)]


def _contract_specialisation(item) -> dict[str, Any]:
    return {
        "id": item.specialisation_id,
        "status": item.status,
        "overlap_used": item.overlap_units,
        "overlap_budget": 8,
        "distinct_units": item.distinct_units,
        "sep_mapped_units": _sep_mapped_units(item.messages),
        "capstone_lock": any("Capstone lock active" in message for message in item.messages),
    }


def _units_required(config: DegreeAuditConfig, internal_id: str, mapped_id: str) -> int:
    if mapped_id == "UE_40":
        return 40
    if mapped_id == "MAJOR_60":
        return 60
    requirement = config.requirement_by_id(internal_id)
    if requirement is None:
        return 0
    if requirement.units is not None:
        return requirement.units
    if requirement.min_count is not None:
        return requirement.min_count * 4
    if requirement.courses:
        return len(requirement.courses) * 4
    return 0


def _source_ref(config: DegreeAuditConfig, internal_id: str) -> dict[str, Any] | None:
    if internal_id == MAJOR_PROGRAMME_ID:
        requirement = config.requirement_by_id(FIXED_MAJOR_CORE_REQUIREMENT_ID)
    else:
        requirement = config.requirement_by_id(internal_id)
    return _dump_source_ref(requirement.source_ref) if requirement else None


def _dump_source_ref(source_ref: SourceRef | None) -> dict[str, Any] | None:
    return source_ref.model_dump(mode="json") if source_ref else None


def _map_specialisation_failure(failure_id: str) -> str | None:
    for suffix, mapped_id in SPECIALISATION_FAILURE_MAP.items():
        if failure_id.endswith(suffix):
            return mapped_id
    return None


def _sep_mapped_units(messages: list[str]) -> int:
    for message in messages:
        if "SEP unit" not in message:
            continue
        parts = message.split()
        for index, part in enumerate(parts):
            if part == "maps" and index + 1 < len(parts):
                try:
                    return int(parts[index + 1])
                except ValueError:
                    return 0
    return 0


def _dedupe_constraint_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for row in rows:
        key = (row["id"], row["status"], tuple(row["affected_courses"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
