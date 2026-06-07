from __future__ import annotations

from collections import defaultdict

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.eligibility import canonical_code, course_in_pool
from degree_auditor.models import (
    Allocation,
    AllocationRole,
    ApprovalStatus,
    Constraint,
    ConstraintResult,
    CourseAttempt,
    CourseSource,
    DegreeAuditConfig,
    Requirement,
    Specialisation,
    SpecialisationPath,
    SpecialisationResult,
)


SUPPORTED_SPECIALISATIONS = {"AE", "IND4", "SET", "MQM", "RBT", "SPT", "IOT"}
SEP_ONLY_SPECIALISATIONS: set[str] = set()
CAPSTONE_LOCK_SPECIALISATIONS = {"SPT", "RBT", "IOT", "MQM"}
CAPSTONE_CODES = {"EE4002D", "EE4002R"}
SPT_EG4301_CODE = "EG4301"
COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_ID = "CDE_CAPSTONE"
COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_IDS = {
    COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_ID,
    "CC_CAPSTONE",
    "CC_ISK_CAPSTONE",
}
TECHNICAL_ELECTIVE_REQUIREMENT_ID = "EE24JC_TE"
IDP_SECOND_MAJOR_REQUIREMENT_ID = "IDP_2ND_MAJOR"

REQUIREMENT_SLOT_ALIASES = {
    "AE_ELECTIVE": {"AE_ELECTIVES"},
    "IND4_CORE": {"IND4_CORE_CONTROL", "IND4_CORE_AUTOMATION", "IND4_CORE_DATA"},
    "IND4_ELECTIVE": {"IND4_ELECTIVES"},
    "IOT_ELECTIVE": {"IOT_ELECTIVES"},
    "IOT_PROJECT": {"IOT_PROJECT_OPTIONS"},
    "MQM_ELECTIVE": {"MQM_ELECTIVES"},
    "RBT_BASKET": {"RBT_ELECTIVES_12_UNITS", "RBT_ELECTIVES_20_UNITS"},
    "SET_ELECTIVE": {"SET_ELECTIVES"},
    "SPT_CORE": {"SPT_CORE", "SPT_SATELLITE_CAPSTONE"},
    "SPT_ELECTIVE": {"SPT_ELECTIVES"},
}

MANUAL_INELIGIBLE_SPECIALISATION_COURSES = {
    "SET_ELECTIVES": {
        "EE4032": "EE4032 is not a SET elective (GEN-area; Emerging Technologies block is not modelled)",
        "EE4205": "EE4205 is not a SET elective (CN-area; Emerging Technologies block is not modelled)",
    },
    "MQM_ELECTIVES": {
        "EE4032": "EE4032 is not an MQM elective (GEN-area; Emerging Technologies block is not modelled)",
        "EE4205": "EE4205 is not an MQM elective (CN-area; Emerging Technologies block is not modelled)",
    },
}


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
    results = [
        _evaluate_specialisation(config, specialisations[specialisation_id], courses, allocations, student_flags or [])
        for specialisation_id in sorted(selected_ids)
        if specialisation_id in SUPPORTED_SPECIALISATIONS
    ]
    results.extend(
        _evaluate_sep_only_specialisation(config, specialisations[specialisation_id], courses, allocations)
        for specialisation_id in sorted(selected_ids)
        if specialisation_id in SEP_ONLY_SPECIALISATIONS
    )
    return _apply_cross_specialisation_sep_reuse(config, courses, allocations, results)


def infer_specialisation_allocations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    existing_allocations: list[Allocation],
) -> tuple[list[Allocation], list[str]]:
    """Infer narrow transcript-only specialisation allocations for public review fixtures."""
    requirement_to_specialisation = _requirement_to_specialisation(config)
    if any(
        requirement_to_specialisation.get(allocation.requirement_id)
        for allocation in existing_allocations
        if allocation.allocation_role != AllocationRole.ignored
    ):
        return [], []

    spt_allocations = _infer_spt_allocations(config, courses)
    if spt_allocations:
        return spt_allocations, []

    rbt_pool = config.pool_by_id("RBT_ELECTIVE_POOL")
    if rbt_pool is None:
        return [], []

    basket_matches: list[Allocation] = []
    warnings: list[str] = []
    capstone_matches: list[Allocation] = []
    for course in courses:
        code = canonical_code(config, course.effective_code)
        if code in CAPSTONE_CODES:
            capstone_matches.append(
                Allocation(
                    course_code=course.course_code,
                    requirement_id="RBT_CAPSTONE",
                    units=course.units,
                    manual=False,
                )
            )
            continue
        if not course_in_pool(code, rbt_pool):
            continue
        basket_matches.append(
            Allocation(
                course_code=course.course_code,
                requirement_id="RBT_ELECTIVES_20_UNITS",
                units=course.units,
                manual=False,
            )
        )
        if course.course_code != code:
            warnings.append(f"{course.course_code} resolved to {code} (alias) for Robotics basket")

    basket_units = sum(allocation.units for allocation in basket_matches)
    if basket_units >= 20:
        return basket_matches[:5], sorted(set(warnings))
    if basket_units >= 12 and capstone_matches:
        capstone_path_allocations = [
            allocation.model_copy(update={"requirement_id": "RBT_ELECTIVES_12_UNITS"})
            for allocation in basket_matches[:3]
        ]
        capstone_path_allocations.append(capstone_matches[0])
        return capstone_path_allocations, sorted(set(warnings))
    return [], []


def _infer_spt_allocations(config: DegreeAuditConfig, courses: list[CourseAttempt]) -> list[Allocation]:
    course_codes = {canonical_code(config, course.effective_code) for course in courses}
    if "EE3105" not in course_codes:
        return []
    pool = config.pool_by_id("SPT_ELECTIVE_POOL")
    if pool is None:
        return []

    allocations = [
        Allocation(course_code="EE3105", requirement_id="SPT_CORE", units=4, manual=False)
    ]
    elective_allocations: list[Allocation] = []
    capstone_allocations: list[Allocation] = []
    for course in courses:
        code = canonical_code(config, course.effective_code)
        if code == "EE3105":
            continue
        if code in CAPSTONE_CODES and "satellite" in {tag.lower() for tag in course.topic_tags}:
            capstone_allocations.append(
                Allocation(
                    course_code=course.course_code,
                    requirement_id="SPT_SATELLITE_CAPSTONE",
                    units=course.units,
                    manual=False,
                )
            )
        elif course_in_pool(code, pool):
            elective_allocations.append(
                Allocation(
                    course_code=course.course_code,
                    requirement_id="SPT_ELECTIVES",
                    units=course.units,
                    manual=False,
                )
            )

    if capstone_allocations and len(elective_allocations) >= 2:
        return allocations + capstone_allocations[:1] + elective_allocations[:2]
    if len(elective_allocations) >= 4:
        return allocations + elective_allocations[:4]
    return []


def evaluate_specialisation_allocation_constraints(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    results.extend(_evaluate_manual_specialisation_eligibility(config, courses, allocations))
    results.extend(_evaluate_spt_eg4301_not_counted(config, allocations))
    results.extend(_evaluate_cde4301_idp_conflict(config, allocations))
    results.extend(_evaluate_cross_specialisation_capstone_conflict(config, courses, allocations))
    return results


def evaluate_sep_reuse_constraint(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = config.constraint_by_id("EE_SPEC_SEP_NO_REUSE")
    reused = _reused_sep_courses_across_specialisations(config, courses, allocations)
    if not reused:
        return [
            _constraint_result(
                constraint,
                True,
                "No SEP course is mapped to more than one specialisation.",
            )
        ]
    return [
        _constraint_result(
            constraint,
            False,
            "A SEP course approved for one specialisation must not be mapped again to another specialisation.",
            affected_courses=sorted(reused),
        )
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

    units_counted = _specialisation_units(config, specialisation, courses, allocations)
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

    sep_failures, sep_messages = _specialisation_sep_policy(config, specialisation, courses, allocations)
    equivalence_messages = _specialisation_equivalence_messages(config, specialisation, courses, allocations)

    failed_requirements = (
        _selected_failed_requirements(specialisation, path_results, selected)
        + [f"{specialisation.id}_GLOBAL_POLICY"] * bool(policy_failures)
        + capstone_failures
        + sep_failures
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
        messages=selected["messages"] + policy_failures + capstone_messages + sep_messages + equivalence_messages,
    )


def _selected_failed_requirements(
    specialisation: Specialisation,
    path_results: list[dict[str, object]],
    selected: dict[str, object],
) -> list[str]:
    if specialisation.id == "RBT" and all(result["failed_requirements"] for result in path_results):
        failures: list[str] = []
        for result in path_results:
            failures.extend(result["failed_requirements"])
        return sorted(dict.fromkeys(str(failure) for failure in failures))
    return list(selected["failed_requirements"])


def _evaluate_sep_only_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> SpecialisationResult:
    sep_failures, sep_messages = _specialisation_sep_policy(config, specialisation, courses, allocations)
    status = "PASS" if not sep_failures else "FAIL"
    return SpecialisationResult(
        specialisation_id=specialisation.id,
        status=status,
        selected_path_id=None,
        units_counted=_specialisation_units(config, specialisation, courses, allocations),
        overlap_units=_overlap_units(config, specialisation, allocations),
        distinct_units=0,
        satisfied_requirements=[],
        failed_requirements=sep_failures,
        messages=sep_messages,
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
        if _allocation_matches_requirement(allocation.requirement_id, requirement.id)
        and allocation.allocation_role != AllocationRole.ignored
    ]
    allocated_codes = {
        canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        for allocation in requirement_allocations
    }
    transcript_codes = {canonical_code(config, course.effective_code) for course in courses}

    if requirement.requirement_type in {"all_of", "course_list"}:
        available_codes = allocated_codes | transcript_codes
        missing = [course for course in requirement.courses if canonical_code(config, course) not in available_codes]
        return not missing, f"{requirement.id} missing {', '.join(missing)}."

    if requirement.requirement_type == "choice":
        allowed = {canonical_code(config, course) for course in requirement.courses}
        count = len(allocated_codes & allowed)
        minimum = requirement.min_count or 1
        return count >= minimum, f"{requirement.id} has {count} choice course(s); requires {minimum}."

    if requirement.requirement_type == "choose_count":
        count = len(_matching_pool_allocations(config, requirement, requirement_allocations, courses))
        if requirement.id == "SPT_ELECTIVES":
            count = max(count, len(_matching_transcript_pool_courses(config, requirement, courses)))
        minimum = requirement.min_count or 1
        return count >= minimum, f"{requirement.id} has {count} course(s); requires {minimum}."

    if requirement.requirement_type == "choose_units":
        units = sum(_matching_pool_allocations(config, requirement, requirement_allocations, courses).values())
        if requirement.id == "SPT_IDP_REPLACEMENT_ELECTIVES":
            units = max(units, sum(_matching_transcript_pool_courses(config, requirement, courses).values()))
        required_units = requirement.units or 0
        return units >= required_units, f"{requirement.id} has {units} unit(s); requires {required_units}."

    if requirement.requirement_type == "project_option":
        matching = [
            allocation
            for allocation in requirement_allocations
            if canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
            in {canonical_code(config, course) for course in requirement.courses}
            and _has_topic_tags(
                config,
                _effective_code_for_allocation(config, courses, allocation),
                requirement.topic_tags,
                courses,
            )
        ]
        return bool(matching), f"{requirement.id} needs a project option with topic tag(s): {requirement.topic_tags}."

    return False, f"Unsupported requirement type {requirement.requirement_type}."


def _matching_pool_allocations(
    config: DegreeAuditConfig,
    requirement: Requirement,
    allocations: list[Allocation],
    courses: list[CourseAttempt],
) -> dict[str, int]:
    if requirement.pool_id is None:
        return {}
    pool = config.pool_by_id(requirement.pool_id)
    if pool is None:
        return {}
    matched: dict[str, int] = {}
    for allocation in allocations:
        code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        if course_in_pool(code, pool):
            matched[code] = max(matched.get(code, 0), allocation.units)
    return matched


def _matching_transcript_pool_courses(
    config: DegreeAuditConfig,
    requirement: Requirement,
    courses: list[CourseAttempt],
) -> dict[str, int]:
    if requirement.pool_id is None:
        return {}
    pool = config.pool_by_id(requirement.pool_id)
    if pool is None:
        return {}
    matched: dict[str, int] = {}
    for course in courses:
        code = canonical_code(config, course.effective_code)
        if code == SPT_EG4301_CODE:
            continue
        if course_in_pool(code, pool):
            matched[code] = max(matched.get(code, 0), course.units)
    return matched


def _specialisation_units(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> int:
    requirement_ids = _specialisation_requirement_ids(specialisation)
    units_by_course: dict[str, int] = {}
    for allocation in allocations:
        if (
            allocation.requirement_id in requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and not _is_spt_eg4301_allocation(specialisation, allocation)
        ):
            code = _known_canonical_allocation_code(allocation.course_code)
            units_by_course[code] = max(units_by_course.get(code, 0), allocation.units)
    for requirement_id in specialisation.requirement_ids:
        requirement = config.requirement_by_id(requirement_id)
        if requirement is None or requirement.requirement_type not in {"all_of", "course_list"}:
            continue
        required_codes = {canonical_code(config, course_code) for course_code in requirement.courses}
        for course in courses:
            code = canonical_code(config, course.effective_code)
            if code in required_codes:
                units_by_course[code] = max(units_by_course.get(code, 0), course.units)
    if specialisation.id == "SPT" and not any(
        allocation.requirement_id in {"SPT_ELECTIVES", "SPT_IDP_REPLACEMENT_ELECTIVES", "SPT_ELECTIVE"}
        and allocation.allocation_role != AllocationRole.ignored
        for allocation in allocations
    ):
        pool = config.pool_by_id("SPT_ELECTIVE_POOL")
        if pool is not None:
            for course in courses:
                code = canonical_code(config, course.effective_code)
                if code == SPT_EG4301_CODE:
                    continue
                if course_in_pool(code, pool):
                    units_by_course[code] = max(units_by_course.get(code, 0), course.units)
    return sum(units_by_course.values())


def _overlap_units(config: DegreeAuditConfig, specialisation: Specialisation, allocations: list[Allocation]) -> int:
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    units_by_course: dict[str, int] = {}
    by_course: dict[str, list[Allocation]] = defaultdict(list)
    for allocation in allocations:
        code = _known_canonical_allocation_code(allocation.course_code)
        if allocation.allocation_role != AllocationRole.ignored:
            by_course[code].append(allocation)
        if (
            allocation.requirement_id in spec_requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and not _is_spt_eg4301_allocation(specialisation, allocation)
        ):
            units_by_course[code] = max(units_by_course.get(code, 0), allocation.units)

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


def _is_spt_eg4301_allocation(specialisation: Specialisation, allocation: Allocation) -> bool:
    return specialisation.id == "SPT" and allocation.course_code == SPT_EG4301_CODE


def _capstone_lock(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> str | None:
    if specialisation.id not in CAPSTONE_LOCK_SPECIALISATIONS:
        return None
    common_capstones = {
        canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        for allocation in allocations
        if allocation.requirement_id in COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_IDS
        and allocation.allocation_role != AllocationRole.ignored
        and canonical_code(config, _effective_code_for_allocation(config, courses, allocation)) in CAPSTONE_CODES
    }
    if not common_capstones:
        return None
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    for allocation in allocations:
        code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        if (
            allocation.requirement_id in spec_requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and code in common_capstones
            and _capstone_allocation_matches_requirement(config, allocation, courses)
        ):
            return code
    return None


def _specialisation_capstone_use(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> str | None:
    if specialisation.id not in CAPSTONE_LOCK_SPECIALISATIONS:
        return None
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    for allocation in allocations:
        code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        if (
            allocation.requirement_id in spec_requirement_ids
            and allocation.allocation_role != AllocationRole.ignored
            and code in CAPSTONE_CODES
            and _capstone_allocation_matches_requirement(config, allocation, courses)
        ):
            return code
    return None


def _capstone_allocation_matches_requirement(
    config: DegreeAuditConfig,
    allocation: Allocation,
    courses: list[CourseAttempt],
) -> bool:
    requirement = config.requirement_by_id(_primary_requirement_id(allocation.requirement_id))
    if requirement is None:
        return False
    code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
    if code not in {canonical_code(config, course) for course in requirement.courses}:
        return requirement.requirement_type != "project_option" and code in CAPSTONE_CODES
    return _has_topic_tags(config, code, requirement.topic_tags, courses)


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


def _specialisation_sep_policy(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> tuple[list[str], list[str]]:
    sep_units = _sep_units_for_specialisation(config, specialisation, courses, allocations)
    non_approved = _non_approved_sep_courses_for_specialisation(config, specialisation, courses, allocations)
    failures: list[str] = []
    messages: list[str] = []

    if sep_units > 8:
        failures.append(f"{specialisation.id}_SEP_MAX_8_UNITS")
        messages.append(f"{specialisation.id} maps {sep_units} SEP unit(s); at most 8 are allowed.")
    if non_approved:
        failures.append(f"{specialisation.id}_SEP_MAX_8_UNITS")
        messages.append(
            "SEP courses mapped to a specialisation must be approved before they can satisfy it: "
            + ", ".join(non_approved)
            + "."
        )

    capstone = _specialisation_capstone_use(config, specialisation, courses, allocations)
    sep_courses = _sep_courses_for_specialisation(config, specialisation, courses, allocations)
    if capstone and sep_courses:
        failures.append(f"{specialisation.id}_SEP_FORBIDDEN_WITH_CAPSTONE")
        messages.append(
            f"{specialisation.id} uses capstone {capstone}; SEP mapping is forbidden for that specialisation: "
            + ", ".join(sorted(sep_courses))
            + "."
        )
    return failures, messages


def _sep_units_for_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> int:
    units_by_original_code: dict[str, int] = {}
    for allocation, attempt in _sep_allocations_for_specialisation(config, specialisation, courses, allocations):
        if attempt.approval_status == ApprovalStatus.approved:
            units_by_original_code[attempt.course_code] = max(
                units_by_original_code.get(attempt.course_code, 0),
                allocation.units,
            )
    return sum(units_by_original_code.values())


def _sep_courses_for_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> set[str]:
    return {
        attempt.course_code
        for _, attempt in _sep_allocations_for_specialisation(config, specialisation, courses, allocations)
        if attempt.approval_status == ApprovalStatus.approved
    }


def _non_approved_sep_courses_for_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[str]:
    return sorted(
        {
            attempt.course_code
            for _, attempt in _sep_allocations_for_specialisation(config, specialisation, courses, allocations)
            if attempt.approval_status != ApprovalStatus.approved
        }
    )


def _sep_allocations_for_specialisation(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[tuple[Allocation, CourseAttempt]]:
    spec_requirement_ids = _specialisation_requirement_ids(specialisation)
    pairs: list[tuple[Allocation, CourseAttempt]] = []
    for allocation in allocations:
        if allocation.requirement_id not in spec_requirement_ids or allocation.allocation_role == AllocationRole.ignored:
            continue
        attempt = _attempt_for_allocation(config, courses, allocation)
        if attempt is not None and attempt.source == CourseSource.sep:
            pairs.append((allocation, attempt))
    return pairs


def _apply_cross_specialisation_sep_reuse(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    results: list[SpecialisationResult],
) -> list[SpecialisationResult]:
    reused = _reused_sep_courses_across_specialisations(config, courses, allocations)
    if not reused:
        return results
    affected_by_spec = _reused_sep_courses_by_specialisation(config, courses, allocations, reused)
    updated: list[SpecialisationResult] = []
    for result in results:
        affected = sorted(affected_by_spec.get(result.specialisation_id, set()))
        if not affected:
            updated.append(result)
            continue
        failure_id = f"{result.specialisation_id}_SEP_NO_REUSE"
        updated.append(
            result.model_copy(
                update={
                    "status": "FAIL",
                    "failed_requirements": result.failed_requirements + [failure_id],
                    "messages": result.messages
                    + [
                        "SEP course mapped to more than one specialisation: "
                        + ", ".join(affected)
                        + "."
                    ],
                }
            )
        )
    return updated


def _reused_sep_courses_across_specialisations(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> set[str]:
    by_course = _specialisations_by_sep_course(config, courses, allocations)
    return {course_code for course_code, specialisations in by_course.items() if len(specialisations) > 1}


def _reused_sep_courses_by_specialisation(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
    reused_courses: set[str],
) -> dict[str, set[str]]:
    by_course = _specialisations_by_sep_course(config, courses, allocations)
    by_specialisation: dict[str, set[str]] = defaultdict(set)
    for course_code in reused_courses:
        for specialisation_id in by_course[course_code]:
            by_specialisation[specialisation_id].add(course_code)
    return by_specialisation


def _specialisations_by_sep_course(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> dict[str, set[str]]:
    requirement_to_specialisation = _requirement_to_specialisation(config)
    by_course: dict[str, set[str]] = defaultdict(set)
    for allocation in allocations:
        specialisation_id = requirement_to_specialisation.get(allocation.requirement_id)
        if specialisation_id is None or allocation.allocation_role == AllocationRole.ignored:
            continue
        attempt = _attempt_for_allocation(config, courses, allocation)
        if (
            attempt is not None
            and attempt.source == CourseSource.sep
            and attempt.approval_status == ApprovalStatus.approved
        ):
            by_course[attempt.course_code].add(specialisation_id)
    return by_course


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


def _effective_code_for_allocation(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocation: Allocation,
) -> str:
    attempt = _attempt_for_allocation(config, courses, allocation)
    return attempt.effective_code if attempt is not None else allocation.course_code


def _evaluate_manual_specialisation_eligibility(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = config.constraint_by_id("MANUAL_ALLOC_INELIGIBLE")
    failures: list[tuple[str, str]] = []
    for allocation in allocations:
        if allocation.allocation_role == AllocationRole.ignored:
            continue
        requirement_ids = _resolved_requirement_ids(allocation.requirement_id)
        code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        for requirement_id in requirement_ids:
            message = MANUAL_INELIGIBLE_SPECIALISATION_COURSES.get(requirement_id, {}).get(code)
            if message:
                failures.append((allocation.course_code, message))
    if not failures:
        return [_constraint_result(constraint, True, "Manual specialisation allocations match configured baskets.")]
    messages = [message for _, message in failures]
    return [
        _constraint_result(
            constraint,
            False,
            "; ".join(messages),
            affected_courses=sorted({course_code for course_code, _ in failures}),
        )
    ]


def _evaluate_spt_eg4301_not_counted(
    config: DegreeAuditConfig,
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = config.constraint_by_id("SPT_EG4301_NOT_COUNTED")
    requirement_to_specialisation = _requirement_to_specialisation(config)
    conflicts = sorted(
        {
            allocation.course_code
            for allocation in allocations
            if allocation.course_code == SPT_EG4301_CODE
            and requirement_to_specialisation.get(allocation.requirement_id) == "SPT"
            and allocation.allocation_role != AllocationRole.ignored
        }
    )
    if not conflicts:
        return [_constraint_result(constraint, True, "EG4301 is not counted toward SPT.")]
    return [
        _constraint_result(
            constraint,
            False,
            "EG4301 units cannot be counted toward SPT (triple-counting avoidance)",
            affected_courses=conflicts,
        )
    ]


def _evaluate_cde4301_idp_conflict(
    config: DegreeAuditConfig,
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = config.constraint_by_id("CDE4301_NO_SPEC_IF_IDP")
    idp_courses = {
        allocation.course_code
        for allocation in allocations
        if allocation.requirement_id == IDP_SECOND_MAJOR_REQUIREMENT_ID
        and allocation.allocation_role != AllocationRole.ignored
        and allocation.course_code in {"CDE4301", "CDE4301A"}
    }
    if not idp_courses:
        return [_constraint_result(constraint, True, "No CDE4301/CDE4301A IDP second-major conflict.")]
    requirement_to_specialisation = _requirement_to_specialisation(config)
    conflicts = sorted(
        {
            allocation.course_code
            for allocation in allocations
            if allocation.course_code in idp_courses
            and requirement_to_specialisation.get(allocation.requirement_id) is not None
            and allocation.allocation_role != AllocationRole.ignored
        }
    )
    if not conflicts:
        return [_constraint_result(constraint, True, "No CDE4301/CDE4301A IDP second-major conflict.")]
    specialisations = sorted(
        {
            requirement_to_specialisation[allocation.requirement_id]
            for allocation in allocations
            if allocation.course_code in conflicts
            and requirement_to_specialisation.get(allocation.requirement_id) is not None
            and allocation.allocation_role != AllocationRole.ignored
        }
    )
    return [
        _constraint_result(
            constraint,
            False,
            f"{', '.join(conflicts)} used for IDP Second Major cannot also fulfil the "
            f"{', '.join(specialisations)} Specialisation",
            affected_courses=conflicts,
        )
    ]


def _evaluate_cross_specialisation_capstone_conflict(
    config: DegreeAuditConfig,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[ConstraintResult]:
    constraint = config.constraint_by_id("SPEC_OVERLAP_SINGLE_INSTANCE")
    common_capstones = {
        canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        for allocation in allocations
        if allocation.requirement_id in COMMON_CURRICULUM_CAPSTONE_REQUIREMENT_IDS
        and allocation.allocation_role != AllocationRole.ignored
        and canonical_code(config, _effective_code_for_allocation(config, courses, allocation)) in CAPSTONE_CODES
    }
    if not common_capstones:
        return [_constraint_result(constraint, True, "No capstone is double-counted across multiple specialisations.")]

    requirement_to_specialisation = _requirement_to_specialisation(config)
    specialisations_by_capstone: dict[str, set[str]] = defaultdict(set)
    for allocation in allocations:
        if allocation.allocation_role == AllocationRole.ignored:
            continue
        specialisation_id = requirement_to_specialisation.get(allocation.requirement_id)
        if specialisation_id not in CAPSTONE_LOCK_SPECIALISATIONS:
            continue
        code = canonical_code(config, _effective_code_for_allocation(config, courses, allocation))
        if code in common_capstones:
            specialisations_by_capstone[code].add(specialisation_id)

    conflicts = {
        code: sorted(specialisation_ids)
        for code, specialisation_ids in specialisations_by_capstone.items()
        if len(specialisation_ids) > 1
    }
    if not conflicts:
        return [_constraint_result(constraint, True, "No capstone is double-counted across multiple specialisations.")]

    messages = [
        f"Capstone cannot be double-counted into more than one Specialisation ({code}: "
        f"{', '.join(specialisation_ids)})"
        for code, specialisation_ids in sorted(conflicts.items())
    ]
    return [
        _constraint_result(
            constraint,
            False,
            "; ".join(messages),
            affected_courses=sorted(conflicts),
        ),
        _constraint_result(
            config.constraint_by_id("CAP_LOCK"),
            False,
            "; ".join(messages),
            affected_courses=sorted(conflicts),
        ),
    ]


def _specialisation_equivalence_messages(
    config: DegreeAuditConfig,
    specialisation: Specialisation,
    courses: list[CourseAttempt],
    allocations: list[Allocation],
) -> list[str]:
    if specialisation.id != "IOT":
        return []
    iot_allocations = [
        allocation
        for allocation in allocations
        if _allocation_matches_requirement(allocation.requirement_id, "IOT_ELECTIVES")
        and allocation.allocation_role != AllocationRole.ignored
    ]
    matched_units = _matching_pool_allocations(
        config,
        Requirement(
            id="IOT_ELECTIVES",
            description="IoT elective equivalent check.",
            requirement_type="choose_units",
            pool_id="IOT_ELECTIVE_POOL",
            units=8,
            source_ref=specialisation.source_ref,
        ),
        iot_allocations,
        courses,
    )
    if len(matched_units) == 1 and sum(matched_units.values()) >= 8:
        return ["IoT electives satisfied by 8-unit equivalent (single project course)."]
    return []


def _constraint_result(
    constraint: Constraint | None,
    passed: bool,
    message: str,
    affected_courses: list[str] | None = None,
) -> ConstraintResult:
    return ConstraintResult(
        constraint_id=constraint.id if constraint else "UNKNOWN",
        passed=passed,
        description=constraint.description if constraint else "Unknown constraint",
        source_ref=constraint.source_ref if constraint else None,
        message=message,
        affected_courses=affected_courses or [],
    )


def _specialisation_requirement_ids(specialisation: Specialisation) -> set[str]:
    requirement_ids = set(specialisation.requirement_ids)
    for path in specialisation.paths:
        requirement_ids.update(path.requirement_ids)
    return _expanded_requirement_ids(requirement_ids)


def _requirement_to_specialisation(config: DegreeAuditConfig) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for specialisation in config.specialisations:
        for requirement_id in _specialisation_requirement_ids(specialisation):
            mapping[requirement_id] = specialisation.id
    return mapping


def _expanded_requirement_ids(requirement_ids: set[str]) -> set[str]:
    expanded = set(requirement_ids)
    for alias_id, targets in REQUIREMENT_SLOT_ALIASES.items():
        if targets & requirement_ids:
            expanded.add(alias_id)
    return expanded


def _resolved_requirement_ids(requirement_id: str) -> set[str]:
    return REQUIREMENT_SLOT_ALIASES.get(requirement_id, {requirement_id})


def _primary_requirement_id(requirement_id: str) -> str:
    return sorted(_resolved_requirement_ids(requirement_id))[0]


def _allocation_matches_requirement(allocation_requirement_id: str, requirement_id: str) -> bool:
    return requirement_id in _resolved_requirement_ids(allocation_requirement_id)


def _known_canonical_allocation_code(course_code: str) -> str:
    return {
        "ME3243": "EE3305",
        "ME3163": "EE3306",
        "ME3142": "EE3331C",
    }.get(course_code, course_code)


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
