from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


@pytest.mark.parametrize(
    "case_id, expected_warning",
    [
        (
            "cc_cde2501_to_gess_no_gess_pass",
            "CDE2501 counted under Singapore Studies (no GESS taken); TC fills Sustainable Futures",
        ),
        (
            "cc_cde2501_to_sf_with_gess_pass",
            "GESS taken; CDE2501 counted under Sustainable Futures; third TC read using UE",
        ),
        (
            "cc_tc_in_lieu_ie2141_pass",
            "Systems Thinking pillar satisfied by TC in lieu of IE2141",
        ),
        (
            "cc_tc_count_not_inflated",
            "3 TCs absorbed by ST/CN/SF pillars; degree total remains 160 units (not inflated)",
        ),
    ],
)
def test_common_curriculum_pass_branches(tmp_path: Path, case_id: str, expected_warning: str) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is True
    assert expected_warning in payload["warnings"]
    assert "DEG_TOTAL_160" in {requirement["id"] for requirement in payload["requirements"]}


@pytest.mark.parametrize(
    "case_id, expected_constraint, expected_warning",
    [
        (
            "cc_double_count_cde2501_fail",
            "DOUBLE_USE_SINGLE_INSTANCE",
            "CDE2501 cannot satisfy both Singapore Studies and Sustainable Futures pillars",
        ),
        (
            "cc_ie2141_and_tc_both_in_st_fail",
            "PILLAR_OVER_ALLOCATED",
            "Systems Thinking pillar already satisfied by IE2141; TC cannot also fill it",
        ),
        (
            "cc_rc4_substitution_not_applicable_warn",
            "CC_RC_EXCLUSION",
            "Standard TC-in-lieu substitution does not apply to RC4/UTCP/NUSC/RVRC/poly students; needs_human_review",
        ),
    ],
)
def test_common_curriculum_failures_surface_contract_ids_and_source_refs(
    tmp_path: Path,
    case_id: str,
    expected_constraint: str,
    expected_warning: str,
) -> None:
    payload = _run_review_case(tmp_path, case_id)

    assert payload["pass"] is False
    assert expected_constraint in payload["failed_constraints"]
    assert expected_warning in payload["warnings"]
    failed_rows = [
        constraint
        for constraint in payload["constraints"]
        if constraint["id"] == expected_constraint and constraint["status"] == "FAIL"
    ]
    assert failed_rows
    assert failed_rows[0]["source_ref"]["document"]


def _run_review_case(tmp_path: Path, case_id: str) -> dict:
    data = yaml.safe_load(EDGE_CASES.read_text(encoding="utf-8"))
    defaults = data["meta"]["defaults"]
    case = next(item for item in data["cases"] if item["id"] == case_id)
    transcript = deepcopy(case["transcript"])
    transcript["courses"] = [{**defaults, **course} for course in transcript.get("courses", [])]
    transcript_path = tmp_path / f"{case_id}_transcript.yaml"
    transcript_path.write_text(yaml.safe_dump(transcript, sort_keys=False), encoding="utf-8")

    allocation_path = tmp_path / f"{case_id}_allocation.yaml"
    allocation_path.write_text(yaml.safe_dump(case["manual_allocation"], sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "audit",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript_path),
            "--allocation",
            str(allocation_path),
            "--format",
            "json",
        ],
    )

    assert result.exit_code in {0, 2}, result.output
    return json.loads(result.output)
