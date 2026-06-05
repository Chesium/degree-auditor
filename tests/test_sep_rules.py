from pathlib import Path

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_sep_te_one_nus_one_sep_pass() -> None:
    result = _audit_with(
        _base_passing_allocations(te_courses=["EE4211", "SEP4308"]),
        extra_attempts=[
            CourseAttempt(course_code="SEP4308", source="SEP", mapped_to="EE4308"),
        ],
    )

    assert result.overall_status == "PASS"
    assert _constraint(result, "EE24JC_TE_SEP_ONE_NUS").passed
    assert _constraint(result, "EE24JC_TE_SEP_MAX_ONE").passed


def test_sep_te_all_sep_fail() -> None:
    result = _audit_with(
        _base_passing_allocations(te_courses=["SEP4308", "SEP4211"]),
        extra_attempts=[
            CourseAttempt(course_code="SEP4308", source="SEP", mapped_to="EE4308"),
            CourseAttempt(course_code="SEP4211", source="SEP", mapped_to="EE4211"),
        ],
    )

    one_nus = _constraint(result, "EE24JC_TE_SEP_ONE_NUS")
    max_one = _constraint(result, "EE24JC_TE_SEP_MAX_ONE")
    assert result.overall_status == "FAIL"
    assert not one_nus.passed
    assert not max_one.passed
    assert one_nus.source_ref is not None
    assert one_nus.affected_courses == ["SEP4308", "SEP4211"]


def test_sep_specialisation_max_8_units_pass() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE"),
            Allocation(course_code="SEP3431", requirement_id="AE_CORE"),
            Allocation(course_code="SEP4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
        ],
        extra_courses=["EE4435", "EE4437"],
        extra_attempts=[
            CourseAttempt(course_code="SEP3431", source="SEP", mapped_to="EE3431C"),
            CourseAttempt(course_code="SEP4409", source="SEP", mapped_to="EE4409"),
        ],
    )

    ae = _specialisation(result, "AE")
    assert result.overall_status == "PASS"
    assert ae.status == "PASS"
    assert not any(failure.endswith("SEP_MAX_8_UNITS") for failure in ae.failed_requirements)


def test_sep_specialisation_over_8_units_fail() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE"),
            Allocation(course_code="SEP3431", requirement_id="AE_CORE"),
            Allocation(course_code="SEP4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="SEP4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
        ],
        extra_courses=["EE4437"],
        extra_attempts=[
            CourseAttempt(course_code="SEP3431", source="SEP", mapped_to="EE3431C"),
            CourseAttempt(course_code="SEP4409", source="SEP", mapped_to="EE4409"),
            CourseAttempt(course_code="SEP4435", source="SEP", mapped_to="EE4435"),
        ],
    )

    ae = _specialisation(result, "AE")
    assert result.overall_status == "FAIL"
    assert ae.status == "FAIL"
    assert "AE_SEP_MAX_8_UNITS" in ae.failed_requirements
    assert any("12 SEP unit" in message for message in ae.messages)


def test_sep_same_course_two_specialisations_fail() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="SEP4216", requirement_id="RBT_ELECTIVES_20_UNITS"),
            Allocation(course_code="SEP4216", requirement_id="IOT_ELECTIVES"),
        ],
        extra_attempts=[
            CourseAttempt(course_code="SEP4216", source="SEP", mapped_to="EE4216"),
        ],
    )

    reuse = _constraint(result, "EE_SPEC_SEP_NO_REUSE")
    assert result.overall_status == "FAIL"
    assert not reuse.passed
    assert reuse.affected_courses == ["SEP4216"]
    assert "RBT_SEP_NO_REUSE" in _specialisation(result, "RBT").failed_requirements
    assert "IOT_SEP_NO_REUSE" in _specialisation(result, "IOT").failed_requirements


def test_spt_capstone_sep_forbidden_fail() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3105", requirement_id="SPT_CORE"),
            Allocation(course_code="EE4002R", requirement_id="SPT_SATELLITE_CAPSTONE", units=8),
            Allocation(course_code="SEP3104", requirement_id="SPT_ELECTIVES"),
            Allocation(course_code="EE4101", requirement_id="SPT_ELECTIVES"),
        ],
        extra_courses=["EE3105", "EE4101"],
        extra_attempts=[
            CourseAttempt(course_code="EE4002R", units=8, topic_tags=["satellite"]),
            CourseAttempt(course_code="SEP3104", source="SEP", mapped_to="EE3104C"),
        ],
    )

    spt = _specialisation(result, "SPT")
    assert result.overall_status == "FAIL"
    assert spt.status == "FAIL"
    assert "SPT_SEP_FORBIDDEN_WITH_CAPSTONE" in spt.failed_requirements
    assert any("SEP mapping is forbidden" in message for message in spt.messages)


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


def _base_passing_allocations(te_courses: list[str] | None = None) -> list[Allocation]:
    first_te, second_te = te_courses or ["EE4308", "EE4211"]
    return [
        Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
        Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3408C", requirement_id="EE24JC_TC"),
        Allocation(course_code=first_te, requirement_id="EE24JC_TE"),
        Allocation(course_code=second_te, requirement_id="EE24JC_TE"),
    ]


def _constraint(result, constraint_id: str):
    return next(item for item in result.constraint_results if item.constraint_id == constraint_id)


def _specialisation(result, specialisation_id: str):
    return next(item for item in result.specialisation_results if item.specialisation_id == specialisation_id)
