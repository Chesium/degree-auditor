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
from degree_auditor.eligibility import expand_eligibility
from degree_auditor.models import CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


def test_non_ee_alias_matches_specialisation_not_te() -> None:
    config = load_config([CONFIG])

    expanded = expand_eligibility(config, [CourseAttempt(course_code="ME3243")])
    choices = allocation_choices_for_course(config, CourseAttempt(course_code="ME3243"))

    assert "EE24JC_TE" not in expanded["ME3243"]
    assert "RBT_ELECTIVES_20_UNITS" in {choice.requirement_id for choice in choices}


@pytest.mark.parametrize(
    "case_id, expected_constraint, expected_warning",
    [
        (
            "non_ee_course_not_te_fail",
            "TE_EXCLUDE_NON_EE",
            "ME3243 is a non-EE course; it counts toward UE only, not the EE TE rule",
        ),
        (
            "alias_ee3306_me3163_double_count_fail",
            "ALIAS_DUPLICATE_CREDIT",
            "EE3306 and ME3163 are the same course; only one may be credited",
        ),
        (
            "ee3033_tc_before_effective_date_warn",
            "TC_EFFECTIVE_DATE_EE3033",
            "EE3033 is TC-eligible only from Semester 2 AY2025/26; attempt term precedes this",
        ),
    ],
)
def test_catalog_failures_surface_contract_ids(tmp_path: Path, case_id: str, expected_constraint: str, expected_warning: str) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is False
    assert expected_constraint in payload["failed_constraints"]
    assert expected_warning in payload["warnings"]
    failed_row = next(
        constraint
        for constraint in payload["constraints"]
        if constraint["id"] == expected_constraint and constraint["status"] == "FAIL"
    )
    assert failed_row["source_ref"]["document"]


@pytest.mark.parametrize("case_id", ["cg3207_te_ay24_pass", "ee3305_te_ay24_pass", "ee3033_tc_on_effective_date_pass"])
def test_catalog_pass_cases(tmp_path: Path, case_id: str) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is True
    assert payload["failed_constraints"] == []


def test_me3142_maps_for_industry4_but_not_te(tmp_path: Path) -> None:
    config = load_config([CONFIG])
    choices = allocation_choices_for_course(config, CourseAttempt(course_code="ME3142"))
    assert "IND4_CORE_CONTROL" in {choice.requirement_id for choice in choices}

    transcript = tmp_path / "me3142.yaml"
    transcript.write_text(
        yaml.safe_dump({"courses": [{"course_code": "ME3142"}, {"course_code": "EE4302"}]}, sort_keys=False),
        encoding="utf-8",
    )
    allocation = tmp_path / "me3142_allocation.yaml"
    allocation.write_text(
        yaml.safe_dump(
            {
                "allocations": [
                    {"course_code": "ME3142", "requirement_id": "EE24JC_TE"},
                    {"course_code": "EE4302", "requirement_id": "EE24JC_TE"},
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
            str(allocation),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert "TE_EXCLUDE_NON_EE" in json.loads(result.output)["failed_constraints"]


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
