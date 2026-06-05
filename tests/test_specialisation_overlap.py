from pathlib import Path

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, AllocationRole, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_ae_core_overlap_with_tc_within_budget() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE", allocation_role=AllocationRole.double_count),
            Allocation(course_code="EE3431C", requirement_id="AE_CORE"),
            Allocation(course_code="EE4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
        ],
        extra_courses=["EE3431C", "EE4409", "EE4435", "EE4437"],
    )

    ae = _specialisation(result, "AE")
    assert result.overall_status == "PASS"
    assert result.requirement_statuses["SPECIALISATION_AE"] == "PASS"
    assert ae.units_counted == 20
    assert ae.overlap_units == 4
    assert ae.distinct_units == 16


def test_ae_core_tc_te_conflict() -> None:
    result = _audit_with(
        [
            Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
            Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3408C", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3408C", requirement_id="EE24JC_TE"),
            Allocation(course_code="EE4308", requirement_id="EE24JC_TE"),
            Allocation(course_code="EE3408C", requirement_id="AE_CORE", allocation_role=AllocationRole.double_count),
            Allocation(course_code="EE3431C", requirement_id="AE_CORE"),
            Allocation(course_code="EE4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
        ],
        extra_courses=["EE3431C", "EE4409", "EE4435", "EE4437"],
    )

    mutual_exclusion = next(
        item for item in result.constraint_results if item.constraint_id == "EE24JC_TC_TE_MUTUAL_EXCLUSION"
    )
    assert result.overall_status == "FAIL"
    assert not mutual_exclusion.passed
    assert mutual_exclusion.affected_courses == ["EE3408C"]
    assert _specialisation(result, "AE").status == "PASS"


def test_ue_residual_does_not_consume_overlap() -> None:
    result = _audit_with(
        [
            Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
            Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3033", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE4308", requirement_id="EE24JC_TE"),
            Allocation(course_code="EE4211", requirement_id="EE24JC_TE"),
        ]
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE"),
            Allocation(course_code="EE3431C", requirement_id="AE_CORE"),
            Allocation(course_code="EE4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
            Allocation(
                course_code="EE4437",
                requirement_id="UE_RESIDUAL",
                allocation_role=AllocationRole.residual_ue,
            ),
        ],
        extra_courses=["EE3033", "EE3431C", "EE4409", "EE4435", "EE4437"],
    )

    ae = _specialisation(result, "AE")
    assert result.overall_status == "PASS"
    assert ae.overlap_units == 0
    assert ae.distinct_units == 20


def _audit_with(allocations: list[Allocation], extra_courses: list[str] | None = None):
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    courses.extend(CourseAttempt(course_code=course_code) for course_code in extra_courses or [])
    return audit(config, courses, allocations)


def _base_passing_allocations() -> list[Allocation]:
    return [
        Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
        Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3408C", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE4308", requirement_id="EE24JC_TE"),
        Allocation(course_code="EE4211", requirement_id="EE24JC_TE"),
    ]


def _specialisation(result, specialisation_id: str):
    return next(item for item in result.specialisation_results if item.specialisation_id == specialisation_id)
