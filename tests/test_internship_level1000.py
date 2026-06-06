from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from degree_auditor.allocation_choices import allocation_choices_for_course
from degree_auditor.cli import app
from degree_auditor.config_loader import load_config
from degree_auditor.models import CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


@pytest.mark.parametrize(
    "case_id, expected_warning",
    [
        ("internship_ia_full_pass", None),
        ("internship_via_plus_vip_pass", None),
        ("internship_overflow_to_ue_pass", "Internship units beyond 10 (EG3612: 6u) counted toward UE"),
        ("internship_poly_apc_pass", None),
        ("internship_eg2605_alias_pass", "EG2605 resolved to CDE2605 (UROP); counts as 4 units (within UROP cap)"),
    ],
)
def test_internship_pass_cases(tmp_path: Path, case_id: str, expected_warning: str | None) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is True
    assert "MAJOR_INTERNSHIP_10" not in payload["failed_requirements"]
    if expected_warning:
        assert expected_warning in payload["warnings"]


@pytest.mark.parametrize(
    "case_id, expected_constraint, expected_warning",
    [
        ("internship_short_combo_fail", None, "Major internship: 8 / 10 units; combination is short of 10"),
        (
            "internship_urop_cap_fail",
            "MAJOR_INTERNSHIP_UROP_CAP",
            "At most 4 units of UROP/UREx count toward the major internship; excess goes to UE",
        ),
        (
            "internship_ceg_only_course_fail",
            "MAJOR_INTERNSHIP_CEG_ONLY",
            "CP3200 (ATAP/SIP) is CEG-only and not valid for the EE-major internship",
        ),
    ],
)
def test_internship_failures(tmp_path: Path, case_id: str, expected_constraint: str | None, expected_warning: str) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is False
    assert "MAJOR_INTERNSHIP_10" in payload["failed_requirements"]
    assert expected_warning in payload["warnings"]
    if expected_constraint:
        assert expected_constraint in payload["failed_constraints"]
        failed_rows = [
            constraint
            for constraint in payload["constraints"]
            if constraint["id"] == expected_constraint and constraint["status"] == "FAIL"
        ]
        assert failed_rows
        assert failed_rows[0]["source_ref"]["document"]


def test_level1000_cap_exceeded_surfaces_contract_id_and_source_ref(tmp_path: Path) -> None:
    payload = _run_review_case(tmp_path, "level1000_cap_exceeded_warn")

    assert payload["pass"] is False
    assert "LVL1000_MAX_60" in payload["failed_constraints"]
    assert "Level-1000 units 64 exceed the 60-unit cap; 4 units will not count toward graduation" in payload["warnings"]
    failed_row = next(
        constraint
        for constraint in payload["constraints"]
        if constraint["id"] == "LVL1000_MAX_60" and constraint["status"] == "FAIL"
    )
    assert failed_row["source_ref"]["document"] == "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf"


def test_allocation_choices_include_major_internship() -> None:
    config = load_config([CONFIG])
    choices = allocation_choices_for_course(config, CourseAttempt(course_code="EG3612", units=6))

    assert "MAJOR_INTERNSHIP_10" in {choice.requirement_id for choice in choices}


def _run_review_case(tmp_path: Path, case_id: str) -> dict:
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

    result = CliRunner().invoke(app, args)

    assert result.exit_code in {0, 2}, result.output
    return json.loads(result.output)
