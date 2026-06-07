from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


def test_specialisation_contract_overlap_and_path_warnings(tmp_path: Path) -> None:
    ae = _run_case(tmp_path, "ae_core_overlap_with_tc_within_budget")
    rbt_coursework = _run_case(tmp_path, "robotics_coursework_only_pass")
    rbt_untagged = _run_case(tmp_path, "robotics_capstone_untagged_fail")

    assert ae["pass"] is True
    assert "AE overlap budget: 4 / 8 units used" in ae["warnings"]
    assert rbt_coursework["pass"] is True
    assert "Robotics path selected: COURSEWORK_ONLY (20/20 units)" in rbt_coursework["warnings"]
    assert {"RBT_PATH1_CAPSTONE", "RBT_PATH2_COURSEWORK"} <= set(rbt_untagged["failed_requirements"])
    assert "Robotics capstone present but not tagged 'robotics'; Path 1 not satisfied" in rbt_untagged["warnings"]


def test_specialisation_contract_capstone_and_sep_failures(tmp_path: Path) -> None:
    rbt_lock = _run_case(tmp_path, "robotics_capstone_overlap_lock_fail")
    spt_sep = _run_case(tmp_path, "spt_capstone_sep_forbidden_fail")
    mqm_lock = _run_case(tmp_path, "mqm_overlap_exceeds_budget_fail")

    assert "CAP_LOCK" in rbt_lock["failed_constraints"]
    assert "Robotics overlap budget 8/8 consumed by capstone; no further double-count permitted" in rbt_lock["warnings"]
    assert "SEP_CAPSTONE_FORBIDS_SEP" in spt_sep["failed_constraints"]
    assert "Capstone used for SPT; no SEP courses may be mapped to SPT (EE4314 rejected)" in spt_sep["warnings"]
    assert {"SPEC_MAX_OVERLAP_8", "CAP_LOCK"} <= set(mqm_lock["failed_constraints"])
    assert "MQM overlap budget exceeded: 12 / 8 units" in mqm_lock["warnings"]


def test_specialisation_contract_sep_budget_and_reuse(tmp_path: Path) -> None:
    sep_at_limit = _run_case(tmp_path, "sep_specialisation_max_8_units_pass")
    sep_over = _run_case(tmp_path, "sep_specialisation_over_8_units_fail")
    sep_reuse = _run_case(tmp_path, "sep_same_course_two_specialisations_fail")

    assert sep_at_limit["pass"] is True
    assert "AE SEP mapped units: 8 / 8 (at limit)" in sep_at_limit["warnings"]
    assert "SEP_SPEC_MAX_8" in sep_over["failed_constraints"]
    assert "AE SEP mapped units: 12 / 8 (exceeds cap)" in sep_over["warnings"]
    assert "SEP_SPEC_NO_REUSE" in sep_reuse["failed_constraints"]
    assert "SEP course EE4409 mapped to more than one Specialisation (Robotics, IoT)" in sep_reuse["warnings"]


def _run_case(tmp_path: Path, case_id: str) -> dict:
    data = yaml.safe_load(EDGE_CASES.read_text(encoding="utf-8"))
    defaults = data["meta"]["defaults"]
    case = next(item for item in data["cases"] if item["id"] == case_id)
    case_dir = tmp_path / case_id
    case_dir.mkdir()
    transcript = deepcopy(case["transcript"])
    transcript["courses"] = [{**defaults, **course} for course in transcript.get("courses", [])]
    transcript_path = case_dir / "transcript.yaml"
    transcript_path.write_text(yaml.safe_dump(transcript, sort_keys=False), encoding="utf-8")

    args = ["audit", "--config", str(CONFIG), "--transcript", str(transcript_path), "--format", "json"]
    if case.get("manual_allocation"):
        allocation_path = case_dir / "allocations.yaml"
        allocation_path.write_text(yaml.safe_dump(case["manual_allocation"], sort_keys=False), encoding="utf-8")
        args.extend(["--allocation", str(allocation_path)])
    result = CliRunner().invoke(app, args)
    assert result.exit_code in {0, 2}, result.output
    return json.loads(result.output)
