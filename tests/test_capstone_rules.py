from pathlib import Path

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_robotics_capstone_overlap_lock_fail() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE4002D", requirement_id="CDE_CAPSTONE", units=8),
            Allocation(course_code="EE4212", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4216", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4308", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4002D", requirement_id="RBT_CAPSTONE", units=8),
        ],
        extra_courses=["EE4212", "EE4216"],
        extra_attempts=[CourseAttempt(course_code="EE4002D", units=8, topic_tags=["robotics"])],
    )

    robotics = _specialisation(result, "RBT")
    assert result.overall_status == "FAIL"
    assert robotics.status == "FAIL"
    assert robotics.overlap_units == 8
    assert "RBT_CAPSTONE_LOCK" in robotics.failed_requirements
    assert any("Capstone lock active" in message for message in robotics.messages)
    assert any("EE4308" in message for message in robotics.messages)


def test_spt_standard_pass() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3105", requirement_id="SPT_CORE"),
            Allocation(course_code="EE4002R", requirement_id="SPT_SATELLITE_CAPSTONE", units=8),
            Allocation(course_code="EE3104C", requirement_id="SPT_ELECTIVES"),
            Allocation(course_code="EE4101", requirement_id="SPT_ELECTIVES"),
        ],
        extra_courses=["EE3105", "EE3104C", "EE4101"],
        extra_attempts=[CourseAttempt(course_code="EE4002R", units=8, topic_tags=["satellite"])],
    )

    spt = _specialisation(result, "SPT")
    assert result.overall_status == "PASS"
    assert spt.status == "PASS"
    assert spt.selected_path_id == "SPT_STANDARD"
    assert spt.units_counted == 20


def test_mqm_overlap_exceeds_budget_fail() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE2027", requirement_id="EE24JC_MAJOR_CORE"),
            Allocation(course_code="EE2027", requirement_id="MQM_CORE"),
            Allocation(course_code="MLE2105", requirement_id="MQM_CORE"),
            Allocation(course_code="EE3431C", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="EE4409", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="EE4002D", requirement_id="CDE_CAPSTONE", units=8),
            Allocation(course_code="EE4002D", requirement_id="MQM_ELECTIVES", units=8),
        ],
        extra_courses=["MLE2105", "EE3431C", "EE4409"],
        extra_attempts=[CourseAttempt(course_code="EE4002D", units=8, topic_tags=["mqm"])],
    )

    mqm = _specialisation(result, "MQM")
    assert result.overall_status == "FAIL"
    assert mqm.status == "FAIL"
    assert mqm.overlap_units == 8
    assert "MQM_CAPSTONE_LOCK" in mqm.failed_requirements
    assert any("no overlap budget" in message for message in mqm.messages)


def test_spt_idp_replacement_requires_flag() -> None:
    allocations = _base_passing_allocations() + [
        Allocation(course_code="EE3105", requirement_id="SPT_CORE"),
        Allocation(course_code="EE3104C", requirement_id="SPT_IDP_REPLACEMENT_ELECTIVES"),
        Allocation(course_code="EE3131C", requirement_id="SPT_IDP_REPLACEMENT_ELECTIVES"),
        Allocation(course_code="EE4101", requirement_id="SPT_IDP_REPLACEMENT_ELECTIVES"),
        Allocation(course_code="EE4218", requirement_id="SPT_IDP_REPLACEMENT_ELECTIVES"),
    ]
    extra_courses = ["EE3105", "EE3104C", "EE3131C", "EE4101", "EE4218"]

    without_idp = _audit_with(allocations, extra_courses=extra_courses)
    with_idp = _audit_with(allocations, extra_courses=extra_courses, student_flags=["IDP"])

    assert _specialisation(without_idp, "SPT").status == "FAIL"
    assert _specialisation(without_idp, "SPT").selected_path_id == "SPT_STANDARD"
    assert _specialisation(with_idp, "SPT").status == "PASS"
    assert _specialisation(with_idp, "SPT").selected_path_id == "SPT_IDP_REPLACEMENT"


def _audit_with(
    allocations: list[Allocation],
    extra_courses: list[str] | None = None,
    extra_attempts: list[CourseAttempt] | None = None,
    student_flags: list[str] | None = None,
):
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    courses.extend(CourseAttempt(course_code=course_code) for course_code in extra_courses or [])
    courses.extend(extra_attempts or [])
    return audit(config, courses, allocations, student_flags=student_flags)


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
