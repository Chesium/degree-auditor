from __future__ import annotations

from collections import defaultdict

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.eligibility import canonical_code, course_in_pool
from degree_auditor.models import (
    Allocation,
    AllocationRole,
    CourseAttempt,
    DegreeAuditConfig,
    Requirement,
    Specialisation,
    SpecialisationPath,
    SpecialisationResult,
)


SUPPORTED_SPECIALISATIONS = {"AE", "IND4", "SET", "MQM", "RBT", "SPT"}
CAPSTONE_LOCK_SPECIALISATIONS = {"SPT", "RBT", "IOT", "MQM"}
CAPSTONE_CODES = {"EE4002D", "EE4002R"}
COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_ID = "CDE_CAPSTONE"
TECHNICAL_ELECTIVE_REQUIREMENT_ID = "EE24JC_TE"


def evaluate_specialisations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    student_flags: list[str] | None = None,
) -> list[SpecialisationResult]:
    requirement_to_specialisation = _requirement_to_specialisation(config)
    selected_ids = {
        requirement_to_specialisation[allocation.requirement_id]
        for allocation in allocations
        if allocation.requirement_id in requirement_to_specialisation
        and allocation.allocation_role != AllocationRole.ignored
    }
    specialisations = {specialisation.id: specialisation for specialisation in config.specialisations}
    return [
        _evaluate_specialisation(config, specialisations[specialisation_id], courses, allocations, student_flags or [])
        for specialisation_id in sorted(selected_ids)
        if specialisation_id in SUPPORTED_SPECIALISATIONS
    ]


def _evaluate_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    student_flags: list[str],
) -> SpecialisationResult:
    available_paths = [
        path
        for path in specialisation.paths
        if set(path.activation_flags) <= {flag.upper() for flag in student_flags}
    ]
    candidate_paths = available_paths or [
        SpecialisationPath(
            id=f"{specialisation.id}_STANDARD",
            description=specialisation.description,
            source_ref=specialisation.source_ref,
            requirement_ids=specialisation.requirement_ids,
        )
    ]

    path_results = [
        _evaluate_path(config, path, courses, allocations, specialisation)
        for path in candidate_paths
    ]
    selected = _best_path_result(path_results)

    units_counted = _specialisation_units(specialisation, allocations)
    generic_overlap_units = _overlap_units(config, specialisation, allocations)
    capstone_lock = _capstone_lock(config, specialisation, courses, allocations)
    overlap_units = specialisation.max_overlap_units if capstone_lock else generic_overlap_units
    distinct_units = max(units_counted - overlap_units, 0)
    policy_failures: list[str] = []
    if units_counted < specialisation.total_units:
        policy_failures.append(f"Needs {specialisation.total_units - units_counted} more specialisation unit(s).")
    if overlap_units > specialisation.max_overlap_units:
        policy_failures.append(
            f"Overlap is {overlap_units} unit(s), above limit of {specialisation.max_overlap_units}."
        )
    if distinct_units < specialisation.min_distinct_units:
        policy_failures.append(
            f"Distinct units are {distinct_units}, below minimum of {specialisation.min_distinct_units}."
        )

    capstone_failures: list[str] = []
    capstone_messages: list[str] = []
    if capstone_lock:
        capstone_messages.append(
            f"Capstone lock active: {capstone_lock} consumes the {specialisation.max_overlap_units}-unit overlap budget."
        )
        te_overlaps = _technical_elective_overlaps_after_capstone_lock(specialisation, allocations, capstone_lock)
        if te_overlaps:
            capstone_failures.append(f"{specialisation.id}_CAPSTONE_LOCK")
            capstone_messages.append(
                "Capstone lock forbids further TE double-counting for this specialisation: "
                + ", ".join(te_overlaps)
                + "."
            )
        if _non_te_overlap_units_excluding_capstone(specialisation, allocations, capstone_lock) > 0:
            capstone_failures.append(f"{specialisation.id}_CAPSTONE_LOCK")
            capstone_messages.append("Capstone lock leaves no overlap budget for additional non-UE overlaps.")

    failed_requirements = (
        selected["failed_requirements"]
        + [f"{specialisation.id}_GLOBAL_POLICY"] * bool(policy_failures)
        + capstone_failures
    )
    status = "PASS" if not failed_requirements else "FAIL"

    return SpecialisationResult(
        specialisation_id=specialisation.id,
        status=status,
        selected_path_id=selected["path_id"],
        units_counted=units_counted,
        overlap_units=overlap_units,
        distinct_units=distinct_units,
        satisfied_requirements=selected["satisfied_requirements"],
        failed_requirements=failed_requirements,
        messages=selected["messages"] + policy_failures + capstone_messages,
    )


def _evaluate_path(
    config: DegreeAuditConfig,
    path: SpecialisationPath,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    specialisation: Specialisation,
) -> dict[str, object]:
    satisfied: list[str] = []
    failed: list[str] = []
    messages: list[str] = []

    for requirement_id in path.requirement_ids:
        requirement = config.requirement_by_id(requirement_id)
        if requirement is None:
            failed.append(requirement_id)
            messages.append(f"Unknown requirement {requirement_id}.")
            continue
        passed, message = _evaluate_requirement(config, requirement, courses, allocations)
        if passed:
            satisfied.append(requirement_id)
        else:
            failed.append(requirement_id)
            messages.append(message)

    return {
        "path_id": path.id,
        "satisfied_requirements": satisfied,
        "failed_requirements": failed,
        "messages": messages,
        "score": (len(failed), -len(satisfied)),
    }


def _evaluate_requirement(
    config: DegreeAuditConfig,
    requirement: Requirement,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> tuple[bool, str]:
    requirement_allocations = [
        allocation
        for allocation in allocations
        if allocation.requirement_id == requirement.id and allocation.allocation_role != AllocationRole.ignored
    ]
    allocated_codes = {canonical_code(config, allocation.course_code) for allocation in requirement_allocations}

    if requirement.requirement_type in {"all_of", "course_list"}:
        missing = [course for course in requirement.courses if canonical_code(config, course) not in allocated_codes]
        return not missing, f"{requirement.id} missing {', '.join(missing)}."

    if requirement.requirement_type == "choice":
        allowed = {canonical_code(config, course) for course in requirement.courses}
        count = len(allocated_codes & allowed)
        minimum = requirement.min_count or 1
        return count >= minimum, f"{requirement.id} has {count} choice course(s); requires {minimum}."

    if requirement.requirement_type == "choose_count":
        count = len(_matching_pool_allocations(config, requirement, requirement_allocations))
        minimum = requirement.min_count or 1
        return count >= minimum, f"{requirement.id} has {count} course(s); requires {minimum}."

    if requirement.requirement_type == "choose_units":
        units = sum(_matching_pool_allocations(config, requirement, requirement_allocations).values())
        required_units = requirement.units or 0
        return units >= required_units, f"{requirement.id} has {units} unit(s); requires {required_units}."

    if requirement.requirement_type == "project_option":
        matching = [
            allocation
            for allocation in requirement_allocations
            if canonical_code(config, allocation.course_code)
            in {canonical_code(config, course) for course in requirement.courses}
            and _has_topic_tags(config, allocation.course_code, requirement.topic_tags, courses)
        ]
        return bool(matching), f"{requirement.id} needs a project option with topic tag(s): {requirement.topic_tags}."

    return False, f"Unsupported requirement type {requirement.requirement_type}."


def _matching_pool_allocations(
    config: DegreeAuditConfig,
    requirement: Requirement,
    allocations: list[Allocation],
) -> dict[str, int]:
    if requirement.pool_id is None:
        return {}
    pool = config.pool_by_id(requirement.pool_id)
    if pool is None:
        return {}
    matched: dict[str, int] = {}
    for allocation in allocations:
        code = canonical_code(config, allocation.course_code)
        if course_in_pool(code, pool):
            matched[code] = max(matched.get(code, 0), allocation.units)
    return matched


def _specialisation_units(specialisation: Specialisation, allocations: list[Allocation]) -> int:
    requirement_ids = _specialisation_requirement_ids(specialisation)
    units_by_course: dict[str, int] = {}
    for allocation in allocations:
        if allocation.requirement_id in requirement_ids and allocation.allocation_role != AllocationRole.ignored:
            units_by_course[allocation.course_code] = max(units_by_course.get(allocation.course_code, 0), allocation.units)
    return sum(units_by_course.values())


def _overlap_units(config: DegreeAuditConfig, specialisation: Specialisation, allocations: list[Allocation]) -> int:
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    units_by_course: dict[str, int] = {}
    by_course: dict[str, list[Allocation]] = defaultdict(list)
    for allocation in allocations:
        if allocation.allocation_role != AllocationRole.ignored:
            by_course[allocation.course_code].append(allocation)
        if allocation.requirement_id in spec_requirement_ids and allocation.allocation_role != AllocationRole.ignored:
            units_by_course[allocation.course_code] = max(units_by_course.get(allocation.course_code, 0), allocation.units)

    overlap = 0
    for course_code, units in units_by_course.items():
        other_allocations = [
            allocation
            for allocation in by_course[course_code]
            if allocation.requirement_id not in spec_requirement_ids
            and allocation.requirement_id != UE_RESIDUAL_REQUIREMENT_ID
            and allocation.allocation_role != AllocationRole.residual_ue
        ]
        if other_allocations:
            overlap += units
    return overlap


def _capstone_lock(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> str | None:
    if specialisation.id not in CAPSTONE_LOCK_SPECIALISATIONS:
        return None
    common_capstones = {
        canonical_code(config, allocation.course_code)
        for allocation in allocations
        if allocation.requirement_id == COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_ID
        and allocation.allocation_role != AllocationRole.ignored
        and canonical_code(config, allocation.course_code) in CAPSTONE_CODES
    }
    if not common_capstones:
        return None
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    for allocation in allocations:
        code = canonical_code(config, allocation.course_code)
        if (
            allocation.requirement_id in spec_requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and code in common_capstones
            and _capstone_allocation_matches_requirement(config, allocation, courses)
        ):
            return code
    return None


def _capstone_allocation_matches_requirement(
    config: DegreeAuditConfig,
    allocation: Allocation,
    courses: list[CourseAttempt],
) -> bool:
    requirement = config.requirement_by_id(allocation.requirement_id)
    if requirement is None:
        return False
    if canonical_code(config, allocation.course_code) not in {canonical_code(config, course) for course in requirement.courses}:
        return requirement.requirement_type != "project_option" and canonical_code(config, allocation.course_code) in CAPSTONE_CODES
    return _has_topic_tags(config, allocation.course_code, requirement.topic_tags, courses)


def _technical_elective_overlaps_after_capstone_lock(
    specialisation: Specialisation,
    allocations: list[Allocation],
    capstone_code: str,
) -> list[str]:
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    spec_courses = {
        allocation.course_code
        for allocation in allocations
        if allocation.requirement_id in spec_requirement_ids
        and allocation.allocation_role != AllocationRole.ignored
        and allocation.course_code != capstone_code
    }
    te_courses = {
        allocation.course_code
        for allocation in allocations
        if allocation.requirement_id == TECHNICAL_ELECTIVE_REQUIREMENT_ID
        and allocation.allocation_role != AllocationRole.ignored
    }
    return sorted(spec_courses & te_courses)


def _non_te_overlap_units_excluding_capstone(
    specialisation: Specialisation,
    allocations: list[Allocation],
    capstone_code: str,
) -> int:
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    units = 0
    spec_units_by_course: dict[str, int] = {}
    by_course: dict[str, list[Allocation]] = defaultdict(list)
    for allocation in allocations:
        if allocation.allocation_role != AllocationRole.ignored:
            by_course[allocation.course_code].append(allocation)
        if (
            allocation.requirement_id in spec_requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and allocation.course_code != capstone_code
        ):
            spec_units_by_course[allocation.course_code] = max(
                spec_units_by_course.get(allocation.course_code, 0),
                allocation.units,
            )
    for course_code, course_units in spec_units_by_course.items():
        has_non_te_overlap = any(
            allocation.requirement_id not in spec_requirement_ids
            and allocation.requirement_id not in {
                UE_RESIDUAL_REQUIREMENT_ID,
                TECHNICAL_ELECTIVE_REQUIREMENT_ID,
            }
            and allocation.allocation_role != AllocationRole.residual_ue
            for allocation in by_course[course_code]
        )
        if has_non_te_overlap:
            units += course_units
    return units


def _specialisation_requirement_ids(specialisation: Specialisation) -> set[str]:
    requirement_ids = set(specialisation.requirement_ids)
    for path in specialisation.paths:
        requirement_ids.update(path.requirement_ids)
    return requirement_ids


def _requirement_to_specialisation(config: DegreeAuditConfig) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for specialisation in config.specialisations:
        for requirement_id in _specialisation_requirement_ids(specialisation):
            mapping[requirement_id] = specialisation.id
    return mapping


def _best_path_result(path_results: list[dict[str, object]]) -> dict[str, object]:
    return sorted(path_results, key=lambda item: item["score"])[0]


def _has_topic_tags(
    config: DegreeAuditConfig,
    course_code: str,
    required_tags: list[str],
    courses: list[CourseAttempt],
) -> bool:
    if not required_tags:
        return True
    canonical = canonical_code(config, course_code)
    for course in courses:
        if canonical_code(config, course.effective_code) == canonical:
            tags = {tag.lower() for tag in course.topic_tags}
            return set(required_tags) <= tags
    return False
