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


SUPPORTED_SPECIALISATIONS = {"AE", "IND4", "SET", "MQM", "RBT"}


def evaluate_specialisations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
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
        _evaluate_specialisation(config, specialisations[specialisation_id], courses, allocations)
        for specialisation_id in sorted(selected_ids)
        if specialisation_id in SUPPORTED_SPECIALISATIONS
    ]


def _evaluate_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> SpecialisationResult:
    candidate_paths = specialisation.paths or [
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
    overlap_units = _overlap_units(config, specialisation, allocations)
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

    failed_requirements = selected["failed_requirements"] + [f"{specialisation.id}_GLOBAL_POLICY"] * bool(policy_failures)
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
        messages=selected["messages"] + policy_failures,
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

