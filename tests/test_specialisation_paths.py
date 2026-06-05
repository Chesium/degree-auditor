from pathlib import Path

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_robotics_coursework_only_pass() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE4211", requirement_id="RBT_ELECTIVES_20_UNITS"),
            Allocation(course_code="EE4212", requirement_id="RBT_ELECTIVES_20_UNITS"),
            Allocation(course_code="EE4216", requirement_id="RBT_ELECTIVES_20_UNITS"),
            Allocation(course_code="EE4218", requirement_id="RBT_ELECTIVES_20_UNITS"),
            Allocation(course_code="EE4308", requirement_id="RBT_ELECTIVES_20_UNITS"),
        ],
        extra_courses=["EE4212", "EE4216", "EE4218"],
    )

    robotics = _specialisation(result, "RBT")
    assert result.overall_status == "PASS"
    assert robotics.status == "PASS"
    assert robotics.selected_path_id == "RBT_COURSEWORK_ONLY"
    assert robotics.units_counted == 20


def test_robotics_capstone_path_pass() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE4212", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4216", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4218", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4002D", requirement_id="RBT_CAPSTONE", units=8),
        ],
        extra_courses=["EE4212", "EE4216", "EE4218"],
        extra_attempts=[CourseAttempt(course_code="EE4002D", units=8, topic_tags=["robotics"])],
    )

    robotics = _specialisation(result, "RBT")
    assert result.overall_status == "PASS"
    assert robotics.status == "PASS"
    assert robotics.selected_path_id == "RBT_WITH_CAPSTONE"
    assert robotics.units_counted == 20


def test_mqm_ee2027_overlap_budget() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE2027", requirement_id="EE24JC_MAJOR_CORE"),
            Allocation(course_code="EE2027", requirement_id="MQM_CORE"),
            Allocation(course_code="MLE2105", requirement_id="MQM_CORE"),
            Allocation(course_code="EE3431C", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="EE4409", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="MQM_ELECTIVES"),
        ],
        extra_courses=["MLE2105", "EE3431C", "EE4409", "EE4435"],
    )

    mqm = _specialisation(result, "MQM")
    assert result.overall_status == "PASS"
    assert mqm.status == "PASS"
    assert mqm.overlap_units == 4
    assert mqm.distinct_units == 16


def _audit_with(
    allocations: list[Allocation],
    extra_courses: list[str] | None = None,
    extra_attempts: list[CourseAttempt] | None = None,
):
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    courses.extend(CourseAttempt(course_code=course_code) for course_code in extra_courses or [])
    courses.extend(extra_attempts or [])
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
