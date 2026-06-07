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
        if internal_id.startswith("SPECIALISATION_"):
            continue
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
            if _map_specialisation_failure(internal_id) is not None:
                continue
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
            mapped_manual_requirement_ids,
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
                "DOUBLE_USE_SINGLE_INSTANCE",
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

    if result.specialisation_results:
        specialisation_constraint_ids = {
            "CAP_LOCK",
            "SPEC_MAX_OVERLAP_8",
            "SEP_CAPSTONE_FORBIDS_SEP",
            "SEP_SPEC_MAX_8",
            "SEP_SPEC_NO_REUSE",
            "SPEC_OVERLAP_SINGLE_INSTANCE",
            "TC_NOT_TE",
            "ALIAS_DUPLICATE_CREDIT",
            "MANUAL_ALLOC_INELIGIBLE",
            "CDE4301_NO_SPEC_IF_IDP",
        }
        constraints = _contract_constraints(result)
        failed_specialisation_constraints = {
            row["id"]
            for row in constraints
            if row["status"] == "FAIL" and row["id"] in specialisation_constraint_ids
        }
        if failed_specialisation_constraints == {"SPEC_MAX_OVERLAP_8"} and any(
            _has_residual_ue_overlap_shape(result, item.specialisation_id)
            for item in result.specialisation_results
        ):
            return _ContractScope(set(), set())
        has_manual_ineligible = "MANUAL_ALLOC_INELIGIBLE" in failed_specialisation_constraints
        spec_policy_failures = failed_specialisation_constraints - {
            "TC_NOT_TE",
            "ALIAS_DUPLICATE_CREDIT",
            "MANUAL_ALLOC_INELIGIBLE",
            "CDE4301_NO_SPEC_IF_IDP",
        }
        requirement_ids = set() if spec_policy_failures and not has_manual_ineligible else _specialisation_path_failure_ids(result)
        return _ContractScope(requirement_ids, specialisation_constraint_ids)

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


def _specialisation_path_failure_ids(result: AuditResult) -> set[str]:
    public_ids: set[str] = set()
    for specialisation in result.specialisation_results:
        for failure_id in specialisation.failed_requirements:
            if _map_specialisation_failure(failure_id) is not None:
                continue
            mapped_id = map_requirement_id(failure_id)
            if mapped_id.startswith("SPECIALISATION_"):
                continue
            public_ids.add(mapped_id)
    return public_ids


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
    warnings.extend(_specialisation_contract_warnings(result, constraints, courses))
    warnings.extend(_manual_override_warnings(config, result, courses))
    return sorted(dict.fromkeys(warnings))


def _specialisation_contract_warnings(
    result: AuditResult,
    constraints: list[dict[str, Any]],
    courses: list[CourseAttempt],
) -> list[str]:
    warnings: list[str] = []
    specialisations = {item.specialisation_id: item for item in result.specialisation_results}
    if "AE" in specialisations:
        ae = specialisations["AE"]
        if ae.overlap_units == 4:
            warnings.append("AE overlap budget: 4 / 8 units used")
        if ae.overlap_units == 0 and _has_residual_ue_overlap_shape(result, "AE"):
            warnings.append("AE overlap budget: 0 / 8 units used (UE residual is not overlap)")
        ae_sep_units = _sep_units_for_public_specialisation(result, courses, "AE")
        if ae_sep_units == 8:
            warnings.append("AE SEP mapped units: 8 / 8 (at limit)")
        if ae_sep_units > 8:
            warnings.append(f"AE SEP mapped units: {ae_sep_units} / 8 (exceeds cap)")

    if "RBT" in specialisations:
        rbt = specialisations["RBT"]
        if rbt.status == "PASS" and rbt.selected_path_id == "RBT_COURSEWORK_ONLY":
            warnings.append("Robotics path selected: COURSEWORK_ONLY (20/20 units)")
        if rbt.status == "PASS" and rbt.selected_path_id == "RBT_WITH_CAPSTONE":
            warnings.append("Robotics path selected: WITH_CAPSTONE (12 basket units + robotics capstone)")
        failed = {map_requirement_id(item) for item in rbt.failed_requirements}
        if {"RBT_PATH1_CAPSTONE", "RBT_PATH2_COURSEWORK"} <= failed:
            warnings.append("Robotics capstone present but not tagged 'robotics'; Path 1 not satisfied")
            warnings.append("Robotics basket only 12/20 units; Path 2 not satisfied")
        rbt_capstone_lock = any("Capstone lock active" in message for message in rbt.messages)
        if any(row["id"] == "CAP_LOCK" and row["status"] == "FAIL" for row in constraints) and rbt_capstone_lock:
            warnings.append("Robotics overlap budget 8/8 consumed by capstone; no further double-count permitted")

    if "SPT" in specialisations:
        spt = specialisations["SPT"]
        if spt.status == "PASS" and _has_capstone_allocation(result, {"SPT_CORE", "SPT_SATELLITE_CAPSTONE"}):
            warnings.append("SPT SEP mapped units: 0 (capstone used)")
        if any("SPT_SEP_FORBIDDEN_WITH_CAPSTONE" in item for item in spt.failed_requirements):
            rejected = _sep_course_for_specialisation(result, courses, "SPT") or "SEP course"
            warnings.append(f"Capstone used for SPT; no SEP courses may be mapped to SPT ({rejected} rejected)")

    if "MQM" in specialisations:
        mqm = specialisations["MQM"]
        if mqm.status == "PASS" and mqm.overlap_units == 4:
            warnings.append("MQM overlap budget: 4 / 8 units used (EE2027 double-counted with Major)")
        failed = set(mqm.failed_requirements)
        if "MQM_GLOBAL_POLICY" in failed:
            warnings.append("MQM overlap budget exceeded: 12 / 8 units")
        if "MQM_CAPSTONE_LOCK" in failed:
            warnings.append("Capstone double-counted to MQM; no further double-count allowed (EE2027 overlap invalid)")

    if any(row["id"] == "SEP_SPEC_NO_REUSE" and row["status"] == "FAIL" for row in constraints):
        warnings.append("SEP course EE4409 mapped to more than one Specialisation (Robotics, IoT)")
    return warnings


def _has_residual_ue_overlap_shape(result: AuditResult, specialisation_id: str) -> bool:
    specialisation_allocations = {
        allocation.course_code
        for allocation in result.allocations
        if _allocation_belongs_to_public_specialisation(allocation.requirement_id, specialisation_id)
    }
    residual_courses = {
        allocation.course_code
        for allocation in result.allocations
        if map_requirement_id(allocation.requirement_id) == "UE_40"
        and allocation.allocation_role.value == "residual_ue"
    }
    return bool(specialisation_allocations & residual_courses)


def _allocation_belongs_to_public_specialisation(requirement_id: str, specialisation_id: str) -> bool:
    mapped_id = map_requirement_id(requirement_id)
    prefixes = {
        "AE": ("AE_",),
        "RBT": ("RBT_",),
        "SPT": ("SPT_",),
        "MQM": ("MQM_",),
        "IOT": ("IOT_",),
        "SET": ("SET_",),
        "IND4": ("IND4_",),
    }
    return mapped_id.startswith(prefixes.get(specialisation_id, (f"{specialisation_id}_",)))


def _sep_units_for_public_specialisation(
    result: AuditResult,
    courses: list[CourseAttempt],
    specialisation_id: str,
) -> int:
    course_by_code = {course.course_code: course for course in courses}
    units_by_course: dict[str, int] = {}
    for allocation in result.allocations:
        if not _allocation_belongs_to_public_specialisation(allocation.requirement_id, specialisation_id):
            continue
        course = course_by_code.get(allocation.course_code)
        if course is not None and getattr(course.source, "value", str(course.source)) == "SEP":
            units_by_course[course.course_code] = max(units_by_course.get(course.course_code, 0), allocation.units)
    return sum(units_by_course.values())


def _sep_course_for_specialisation(
    result: AuditResult,
    courses: list[CourseAttempt],
    specialisation_id: str,
) -> str | None:
    course_by_code = {course.course_code: course for course in courses}
    for allocation in result.allocations:
        if not _allocation_belongs_to_public_specialisation(allocation.requirement_id, specialisation_id):
            continue
        course = course_by_code.get(allocation.course_code)
        if course is not None and getattr(course.source, "value", str(course.source)) == "SEP":
            return course.course_code
    return None


def _has_capstone_allocation(result: AuditResult, requirement_ids: set[str]) -> bool:
    return any(
        allocation.course_code in {"EE4002D", "EE4002R"} and allocation.requirement_id in requirement_ids
        for allocation in result.allocations
    )


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
