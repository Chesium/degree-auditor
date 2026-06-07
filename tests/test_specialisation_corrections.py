from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.audit import audit
from degree_auditor.cli import app
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


def test_iot_full_pass_with_core_plus_two_electives() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE4204", requirement_id="IOT_ELECTIVES"),
            Allocation(course_code="EE4216", requirement_id="IOT_ELECTIVES"),
        ],
        extra_courses=["CS3237", "EE4409", "EE4204", "EE4216"],
    )

    iot = _specialisation(result, "IOT")
    assert result.overall_status == "PASS"
    assert iot.status == "PASS"
    assert iot.selected_path_id == "IOT_STANDARD"
    assert iot.units_counted == 20


def test_iot_project_equivalent_passes_review_contract(tmp_path: Path) -> None:
    payload = _run_review_case(tmp_path, "iot_electives_units_equivalent_pass")

    assert payload["pass"] is True
    assert payload["failed_constraints"] == []
    assert any("IoT electives satisfied by 8-unit equivalent" in warning for warning in payload["warnings"])


def test_robotics_me3243_alias_passes_review_contract(tmp_path: Path) -> None:
    payload = _run_review_case(tmp_path, "alias_ee3305_me3243_robotics_basket")

    assert payload["pass"] is True
    assert payload["failed_constraints"] == []
    assert "ME3243 resolved to EE3305 (alias) for Robotics basket" in payload["warnings"]


def test_set_rejects_emerging_tech_elective(tmp_path: Path) -> None:
    result = _run_review_case_raw(tmp_path, "emerging_tech_not_set_elective_fail")

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INELIGIBLE" in result.stderr
    assert "EE4032 is not a SET elective" in result.stderr


def test_cde4301_idp_second_major_conflict(tmp_path: Path) -> None:
    payload = _run_review_case(tmp_path, "cde4301_spec_idp_conflict_fail")

    assert payload["pass"] is False
    assert "CDE4301_NO_SPEC_IF_IDP" in payload["failed_constraints"]
    assert any("CDE4301 used for IDP Second Major cannot also fulfil the SPT Specialisation" in warning for warning in payload["warnings"])


def test_spt_corrected_basket_accepts_ee4115_and_ee4314() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3105", requirement_id="SPT_CORE"),
            Allocation(course_code="EE4002R", requirement_id="SPT_SATELLITE_CAPSTONE", units=8),
            Allocation(course_code="EE4115", requirement_id="SPT_ELECTIVES"),
            Allocation(course_code="EE4314", requirement_id="SPT_ELECTIVES"),
        ],
        extra_courses=["EE3105", "EE4115", "EE4314"],
        extra_attempts=[CourseAttempt(course_code="EE4002R", units=8, topic_tags=["satellite"])],
    )

    spt = _specialisation(result, "SPT")
    assert result.overall_status == "PASS"
    assert spt.status == "PASS"


def test_mqm_accepts_mle4207_and_ee4436_as_electives() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE2027", requirement_id="MQM_CORE"),
            Allocation(course_code="MLE2105", requirement_id="MQM_CORE"),
            Allocation(course_code="MLE4207", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="EE4436", requirement_id="MQM_ELECTIVES"),
            Allocation(course_code="MLE4101B", requirement_id="MQM_ELECTIVES"),
        ],
        extra_courses=["MLE2105", "MLE4207", "EE4436", "MLE4101B"],
    )

    mqm = _specialisation(result, "MQM")
    assert result.overall_status == "PASS"
    assert mqm.status == "PASS"
    assert mqm.units_counted == 20


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


def _run_review_case(tmp_path: Path, case_id: str) -> dict:
    result = _run_review_case_raw(tmp_path, case_id)

    assert result.exit_code in {0, 2}, result.output
    return json.loads(result.output)


def _run_review_case_raw(tmp_path: Path, case_id: str):
    data = yaml.safe_load(EDGE_CASES.read_text(encoding="utf-8"))
    defaults = data["meta"]["defaults"]
    case = next(item for item in data["cases"] if item["id"] == case_id)
    transcript = deepcopy(case["transcript"])
    transcript["courses"] = [{**defaults, **course} for course in transcript.get("courses", [])]
    transcript_path = tmp_path / f"{case_id}_transcript.yaml"
    transcript_path.write_text(yaml.safe_dump(transcript, sort_keys=False), encoding="utf-8")

    args = [
        "audit",
        "--config",
        str(CONFIG),
        "--transcript",
        str(transcript_path),
        "--format",
        "json",
    ]
    if "manual_allocation" in case:
        allocation_path = tmp_path / f"{case_id}_allocation.yaml"
        allocation_path.write_text(yaml.safe_dump(case["manual_allocation"], sort_keys=False), encoding="utf-8")
        args.extend(["--allocation", str(allocation_path)])

    return CliRunner().invoke(app, args)
