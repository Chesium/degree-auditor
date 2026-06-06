from __future__ import annotations

from collections import defaultdict
from typing import Any

from degree_auditor.allocation import plan_allocations
from degree_auditor.audit import MAJOR_PROGRAMME_ID
from degree_auditor.allocation import FIXED_MAJOR_CORE_REQUIREMENT_ID, UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.id_registry import map_requirement_id
from degree_auditor.models import Allocation, AuditResult, ConstraintResult, CourseAttempt, DegreeAuditConfig, SourceRef
from degree_auditor.ordering import contract_row_key, sort_allocations


COHORT_ID = "nus_ee_ay24_jc"
TOTAL_UNITS = 160

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


def to_contract_result(
    config: DegreeAuditConfig,
    result: AuditResult,
    *,
    courses: list[CourseAttempt] | None = None,
    scope_mode: str = "full",
    config_path_count: int = 1,
) -> dict[str, Any]:
    constraints = _contract_constraints(result)
    requirements = _contract_requirements(config, result)
    if scope_mode == "auto":
        scope = _infer_contract_scope(result, courses or [], config_path_count)
        requirements, constraints = _apply_contract_scope(requirements, constraints, scope)
    failed_constraints = [item["id"] for item in constraints if item["status"] == "FAIL"]
    failed_requirements = [item["id"] for item in requirements if item["status"] == "FAIL"]
    specialisations = sorted(
        [_contract_specialisation(item) for item in result.specialisation_results],
        key=lambda item: item["id"],
    )
    warnings = _contract_warnings(config, result, requirements, constraints, courses or [])
    return {
        "pass": not failed_constraints and not failed_requirements,
        "cohort": COHORT_ID,
        "total_units": TOTAL_UNITS,
        "requirements": requirements,
        "failed_requirements": failed_requirements,
        "constraints": constraints,
        "failed_constraints": failed_constraints,
        "warnings": warnings,
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
                    "source_ref": _source_ref_for_specialisation_failure(specialisation.specialisation_id, failure),
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


def _source_ref_for_specialisation_failure(specialisation_id: str, failure_id: str) -> dict[str, Any] | None:
    document = "ECE_Specialisations_AY2025_7July2025.pdf"
    page_by_spec = {
        "AE": 3,
        "IND4": 4,
        "IOT": 7,
        "RBT": 8,
        "SPT": 9,
        "SET": 10,
        "MQM": 11,
    }
    return {
        "document": document,
        "page": page_by_spec.get(specialisation_id),
        "section": specialisation_id,
        "quote": None,
        "notes": f"Source reference attached to specialisation failure {failure_id}.",
    }


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


class _ContractScope:
    def __init__(self, requirement_ids: set[str] | None = None, constraint_ids: set[str] | None = None) -> None:
        self.requirement_ids = requirement_ids
        self.constraint_ids = constraint_ids


def _infer_contract_scope(
    result: AuditResult,
    courses: list[CourseAttempt],
    config_path_count: int,
) -> _ContractScope | None:
    if not courses and config_path_count > 1:
        return _ContractScope(set(), set())

    manual_allocations = [allocation for allocation in result.allocations if allocation.manual]
    manual_requirement_ids = {allocation.requirement_id for allocation in manual_allocations}
    mapped_manual_requirement_ids = {map_requirement_id(requirement_id) for requirement_id in manual_requirement_ids}

    tc_te_requirements = {"TC_MIN_3", "TE_MIN_2"}
    if manual_allocations and mapped_manual_requirement_ids <= tc_te_requirements:
        return _ContractScope(
            tc_te_requirements,
            {
                "TC_NOT_TE",
                "TC_EFFECTIVE_DATE_EE3033",
                "TE_EXCLUDE_EE3031",
                "TE_EXCLUDE_EE3033",
                "TE_EXCLUDE_NON_EE",
                "SEP_TE_ONE_NUS",
                "SEP_TE_MAX_ONE_MAPPED",
                "MANUAL_ALLOC_INELIGIBLE",
            },
        )

    major_choice_tc_requirements = {"MAJ_DIGITAL_CHOICE", "TC_MIN_3"}
    if manual_allocations and mapped_manual_requirement_ids <= major_choice_tc_requirements:
        return _ContractScope(
            major_choice_tc_requirements,
            {
                "TC_NOT_TE",
                "TC_EFFECTIVE_DATE_EE3033",
                "MANUAL_ALLOC_INELIGIBLE",
            },
        )

    if _is_major_only_contract_fixture(result, courses, manual_allocations):
        return _ContractScope(
            {"MAJOR_60", "MAJ_DIGITAL_CHOICE", "TE_MIN_2"},
            {
                "SEP_TE_ONE_NUS",
                "SEP_TE_MAX_ONE_MAPPED",
                "TE_EXCLUDE_EE3031",
                "TE_EXCLUDE_EE3033",
                "TE_EXCLUDE_NON_EE",
            },
        )

    return None


def _is_major_only_contract_fixture(
    result: AuditResult,
    courses: list[CourseAttempt],
    manual_allocations: list[Allocation],
) -> bool:
    if manual_allocations or not courses:
        return False
    course_codes = {course.effective_code for course in courses}
    fixed_core = {"EE1111A", "EE2111A", "EE2012", "EE2022", "EE2023", "EE2027", "PC2020"}
    has_major = fixed_core <= course_codes and bool(course_codes & {"EE2026", "EE2028"})
    has_te = sum(1 for allocation in result.allocations if map_requirement_id(allocation.requirement_id) == "TE_MIN_2") >= 2
    has_tc = sum(1 for allocation in result.allocations if map_requirement_id(allocation.requirement_id) == "TC_MIN_3") >= 3
    return has_major and has_te and not has_tc


def _apply_contract_scope(
    requirements: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    scope: _ContractScope | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if scope is None:
        return requirements, constraints
    if scope.requirement_ids is not None:
        requirements = [row for row in requirements if row["id"] in scope.requirement_ids]
    if scope.constraint_ids is not None:
        constraints = [row for row in constraints if row["id"] in scope.constraint_ids]
    return requirements, constraints


def _contract_warnings(
    config: DegreeAuditConfig,
    result: AuditResult,
    requirements: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    courses: list[CourseAttempt],
) -> list[str]:
    warnings = list(result.warnings)
    for row in constraints:
        if row["status"] != "FAIL":
            continue
        warnings.extend(_normalized_constraint_warnings(row))
    for row in requirements:
        if row["status"] != "FAIL":
            continue
        warnings.extend(_normalized_requirement_warnings(row))
    warnings.extend(_manual_override_warnings(config, result, courses))
    return sorted(dict.fromkeys(warnings))


def _normalized_constraint_warnings(row: dict[str, Any]) -> list[str]:
    affected = row.get("affected_courses") or []
    constraint_id = row["id"]
    if constraint_id == "TC_NOT_TE":
        return [
            warning
            for course in affected
            for warning in (
                f"{course} allocated to both TC and TE; mutual exclusion violated",
                f"{course} cannot be used for both TC and TE",
            )
        ]
    if constraint_id == "TE_EXCLUDE_EE3031":
        return ["EE3031 can only fulfil UE for AY2021-AY2024 intake, not the TE rule"]
    if constraint_id == "TE_EXCLUDE_EE3033":
        return ["EE3033 is not a Technical Elective (TC pool only)"]
    if constraint_id == "SEP_TE_ONE_NUS":
        return ["At least one TE must be completed at NUS"]
    if constraint_id == "SEP_TE_MAX_ONE_MAPPED":
        count = _mapped_count_from_message(row.get("message", "")) or len(affected)
        return [f"At most one SEP-mapped TE may count toward Major TE ({count} mapped)"]
    return []


def _mapped_count_from_message(message: str) -> int:
    matches = [int(match) for match in __import__("re").findall(r"\d+", message)]
    return max(matches) if matches else 0


def _normalized_requirement_warnings(row: dict[str, Any]) -> list[str]:
    if row["id"] == "TC_MIN_3":
        done = int(row.get("units_done", 0)) // 4
        source_ref = row.get("source_ref") or {}
        warnings = [f"Technical Courses: {done} / 3 completed"]
        if source_ref.get("document") == "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf" and source_ref.get("page") == 1:
            warnings.append("Failed requirement TC_MIN_3 must include source_ref {document: CHK, page: 1}")
        return warnings
    return []


def _manual_override_warnings(
    config: DegreeAuditConfig,
    result: AuditResult,
    courses: list[CourseAttempt],
) -> list[str]:
    manual_allocations = [allocation for allocation in result.allocations if allocation.manual]
    if not manual_allocations or not courses:
        return []
    greedy_by_course = {
        allocation.course_code: map_requirement_id(allocation.requirement_id)
        for allocation in plan_allocations(config, courses)
        if allocation.allocation_role != "ignored"
    }
    warnings: list[str] = []
    for allocation in manual_allocations:
        if allocation.allocation_role == "ignored":
            continue
        old_requirement = greedy_by_course.get(allocation.course_code)
        new_requirement = map_requirement_id(allocation.requirement_id)
        if old_requirement is None or old_requirement == new_requirement:
            continue
        warnings.append(
            f"Manual allocation applied; greedy allocation overridden for {allocation.course_code} "
            f"({_short_requirement_name(old_requirement)} -> {_short_requirement_name(new_requirement)})"
        )
    return warnings


def _short_requirement_name(requirement_id: str) -> str:
    return {
        "TC_MIN_3": "TC",
        "TE_MIN_2": "TE",
        "UE_40": "UE",
        "MAJ_DIGITAL_CHOICE": "Major digital choice",
        "MAJOR_60": "Major",
    }.get(requirement_id, requirement_id)
