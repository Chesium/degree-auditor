from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.audit import audit
from degree_auditor.cli import app
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, AllocationRole, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_major_choice_tc_single_instance_double_use_fail() -> None:
    result = _audit_with(
        [
            Allocation(course_code="EE2026", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
            Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
        ],
        courses=[CourseAttempt(course_code="EE2026")],
    )

    failure = _failed_constraint(result, "DOUBLE_USE_SINGLE_INSTANCE")
    assert failure.affected_courses == ["EE2026"]
    assert "EE2026 cannot fulfil both Major digital choice and TC" in failure.message
    assert failure.source_ref is not None


def test_major_choice_tc_distinct_courses_pass() -> None:
    result = _audit_with(
        _base_passing_allocations(),
        courses=load_transcript(TRANSCRIPT),
    )

    single_instance = next(item for item in result.constraint_results if item.constraint_id == "DOUBLE_USE_SINGLE_INSTANCE")
    assert single_instance.passed
    assert result.overall_status == "PASS"


def test_ae_tc_overlap_still_allowed() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE", allocation_role=AllocationRole.double_count),
            Allocation(course_code="EE3431C", requirement_id="AE_CORE"),
            Allocation(course_code="EE4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
        ],
        courses=load_transcript(TRANSCRIPT)
        + [
            CourseAttempt(course_code="EE3431C"),
            CourseAttempt(course_code="EE4409"),
            CourseAttempt(course_code="EE4435"),
            CourseAttempt(course_code="EE4437"),
        ],
    )

    assert result.overall_status == "PASS"
    assert next(item for item in result.constraint_results if item.constraint_id == "DOUBLE_USE_SINGLE_INSTANCE").passed
    ae = next(item for item in result.specialisation_results if item.specialisation_id == "AE")
    assert ae.overlap_units == 4


def test_spec_capstone_two_specialisations_fail(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.yaml"
    transcript.write_text(
        yaml.safe_dump(
            {
                "courses": [
                    {"course_code": "EE4002D", "units": 8, "topic_tags": ["robotics", "iot"]},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    allocations = tmp_path / "allocations.yaml"
    allocations.write_text(
        yaml.safe_dump(
            {
                "allocations": [
                    {"course_code": "EE4002D", "requirement_id": "CC_CAPSTONE", "units": 8},
                    {"course_code": "EE4002D", "requirement_id": "RBT_CAPSTONE", "units": 8, "allocation_role": "double_count"},
                    {"course_code": "EE4002D", "requirement_id": "IOT_ELECTIVE", "units": 8, "allocation_role": "double_count"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "audit",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--allocation",
            str(allocations),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert {"CAP_LOCK", "SPEC_OVERLAP_SINGLE_INSTANCE"} <= set(payload["failed_constraints"])
    assert any("Capstone cannot be double-counted into more than one Specialisation" in warning for warning in payload["warnings"])
    failed = next(item for item in payload["constraints"] if item["id"] == "SPEC_OVERLAP_SINGLE_INSTANCE")
    assert failed["source_ref"]["document"] == "ECE_Specialisations_AY2025_7July2025.pdf"


def test_ue_residual_still_not_overlap_conflict() -> None:
    result = _audit_with(
        _base_passing_allocations()
        + [
            Allocation(course_code="EE3408C", requirement_id="AE_CORE"),
            Allocation(course_code="EE3431C", requirement_id="AE_CORE"),
            Allocation(course_code="EE4409", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4435", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4437", requirement_id="UE_RESIDUAL", allocation_role=AllocationRole.residual_ue),
        ],
        courses=load_transcript(TRANSCRIPT)
        + [
            CourseAttempt(course_code="EE3431C"),
            CourseAttempt(course_code="EE4409"),
            CourseAttempt(course_code="EE4435"),
            CourseAttempt(course_code="EE4437"),
        ],
    )

    assert next(item for item in result.constraint_results if item.constraint_id == "DOUBLE_USE_SINGLE_INSTANCE").passed
    assert not any(
        item.constraint_id == "SPEC_OVERLAP_SINGLE_INSTANCE" and not item.passed
        for item in result.constraint_results
    )


def _audit_with(allocations: list[Allocation], courses: list[CourseAttempt]):
    return audit(load_config([CONFIG]), courses, allocations)


def _base_passing_allocations() -> list[Allocation]:
    return [
        Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
        Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE3408C", requirement_id="EE24JC_TC"),
        Allocation(course_code="EE4308", requirement_id="EE24JC_TE"),
        Allocation(course_code="EE4211", requirement_id="EE24JC_TE"),
    ]


def _failed_constraint(result, constraint_id: str):
    return next(item for item in result.constraint_results if item.constraint_id == constraint_id and not item.passed)
