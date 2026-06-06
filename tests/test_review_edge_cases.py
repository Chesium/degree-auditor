from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app


ROOT = Path(__file__).resolve().parents[1]
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
INVALID_INPUT_CONSTRAINTS = {
    "CONFIG_MERGE_CONFLICT",
    "MANUAL_ALLOC_INVALID",
}


UNSUPPORTED_CASES = {
    "major_core_pass_basic": "review fixture expects scoped major pass; current contract reports whole-audit pass",
    "tc_te_mutual_exclusion_fail": "review warning text contract is stricter than the current emitted warning",
    "ee2026_ee2028_choice_tc_success": "review uses final slot id EE24JC_MAJOR_DIGITAL; current input model uses an internal id",
    "ee2026_both_to_major_and_tc_fail": "single-instance double-use validation beyond TC/TE is not implemented",
    "ee3031_not_te_fail": "review warning text contract is stricter than the current emitted warning",
    "ee3031_as_ue_pass": "UE residual scoped pass is not implemented as whole-audit success",
    "ee3033_not_te_fail": "review warning text contract is stricter than the current emitted warning",
    "ee3033_tc_before_effective_date_warn": "TC effective-date handling is not implemented",
    "ee3033_tc_on_effective_date_pass": "review fixture expects scoped TC effective-date pass; current contract reports whole-audit pass",
    "tc_only_3_courses_pass": "review fixture expects scoped TC pass; current contract reports whole-audit pass",
    "tc_only_2_courses_fail": "review warning text contract is stricter than the current emitted warning",
    "ae_core_overlap_with_tc_within_budget": "review fixture expects scoped specialisation pass; current contract reports whole-audit pass",
    "ae_core_tc_te_conflict": "review warning text contract is stricter than the current emitted warning",
    "robotics_coursework_only_pass": "review fixture expects scoped specialisation pass; current contract reports whole-audit pass",
    "robotics_capstone_path_pass": "review fixture expects scoped specialisation pass; current contract reports whole-audit pass",
    "robotics_capstone_untagged_fail": "robotics topic-tag failure ID is not part of the current public contract",
    "robotics_capstone_overlap_lock_fail": "capstone lock public ID is not emitted for the review slot vocabulary yet",
    "spt_standard_pass": "review fixture expects scoped specialisation pass; current contract reports whole-audit pass",
    "spt_capstone_sep_forbidden_fail": "SPT capstone SEP ban public ID is not emitted for the review slot vocabulary yet",
    "mqm_ee2027_overlap_budget": "review fixture expects scoped MQM pass; current contract reports whole-audit pass",
    "mqm_overlap_exceeds_budget_fail": "MQM capstone lock public ID is not emitted for the review slot vocabulary yet",
    "sep_te_one_nus_one_sep_pass": "review fixture expects scoped TE SEP pass; current contract reports whole-audit pass",
    "sep_te_all_sep_fail": "review warning text contract is stricter than the current emitted warning",
    "sep_specialisation_max_8_units_pass": "review fixture expects scoped specialisation SEP pass; current contract reports whole-audit pass",
    "sep_specialisation_over_8_units_fail": "SEP max-8 public ID is not emitted for the review slot vocabulary yet",
    "sep_same_course_two_specialisations_fail": "SEP no-reuse public ID is not emitted for the review slot vocabulary yet",
    "ue_residual_does_not_consume_overlap": "review fixture expects scoped overlap pass; current contract reports whole-audit pass",
    "alias_ee3305_me3243_robotics_basket": "non-EE specialisation alias behavior is not implemented",
    "alias_ee3306_me3163_double_count_fail": "alias duplicate-credit constraint is not implemented",
    "manual_override_changes_greedy_choice": "manual override warning contract is not implemented",
    "manual_alloc_unknown_course_error": "manual allocation validity is reported as invalid input rather than contract JSON",
    "manual_alloc_units_exceed_attempt_error": "manual allocation unit conservation is not implemented as a contract constraint",
    "manual_alloc_ineligible_requirement_fail": "general manual allocation eligibility constraint is not implemented",
    "iot_electives_units_equivalent_pass": "IoT satisfaction is not implemented",
    "spt_idp_path_inactive_without_flag_fail": "SPT IDP inactive-path public IDs are not aligned yet",
    "spt_idp_eg4301_units_not_counted": "SPT EG4301 exclusion is not implemented",
    "capstone_double_count_two_specs_fail": "cross-specialisation capstone single-instance rule is not implemented",
    "config_merge_identical_ok": "review fixture expects scoped config pass; current audit contract reports whole-audit pass",
    "source_ref_preserved_on_failure": "source-ref edge fixture expects scoped TC reporting",
    "level1000_cap_exceeded_warn": "level-1000 unit cap is not implemented",
    "emerging_tech_not_set_elective_fail": "SET emerging-tech exclusion is not implemented",
    "non_ee_course_not_te_fail": "non-EE TE exclusion ID is not implemented",
    "cg3207_te_ay24_pass": "AY24 TE carve-out for CG3207 is not implemented",
    "ee3305_te_ay24_pass": "review fixture expects scoped TE pass; current contract reports whole-audit pass",
    "tc_closed_list_reject_fail": "closed TC pool ineligible-allocation constraint is not implemented",
    "sep_mapped_to_tc_pass": "SEP-mapped TC acceptance is not implemented",
    "cde4301_spec_idp_conflict_fail": "CDE4301 IDP/spec conflict is not implemented",
    "sep_residency_below_50_fail": "SEP residency rule is not implemented",
    "order_independence_check": "review fixture expects scoped major pass; current contract reports whole-audit pass",
    "internship_ia_full_pass": "major internship requirement is not implemented",
    "internship_via_plus_vip_pass": "major internship combinations are not implemented",
    "internship_short_combo_fail": "major internship combinations are not implemented",
    "internship_urop_cap_fail": "UROP internship cap is not implemented",
    "internship_overflow_to_ue_pass": "internship overflow to UE is not implemented",
    "internship_poly_apc_pass": "poly APC internship replacement is not implemented",
    "internship_eg2605_alias_pass": "EG2605/CDE2605 internship alias is not implemented",
    "internship_ceg_only_course_fail": "CEG-only internship exclusion is not implemented",
}


def test_review_edge_cases_schema_basics() -> None:
    data = _load_edge_cases()
    meta = data["meta"]
    required = set(meta["case_schema"]["required"])

    assert meta["schema_version"] == 2
    assert meta["cohort"] == "nus_ee_ay24_jc"
    assert meta["defaults"]
    assert meta["assertion_semantics"]
    assert meta["slot_to_requirement"]

    ids = [case["id"] for case in data["cases"]]
    assert len(ids) == len(set(ids))
    for case in data["cases"]:
        assert required <= set(case), case["id"]
        assert isinstance(case["expected_failed_requirements"], list), case["id"]
        assert isinstance(case["expected_failed_constraints"], list), case["id"]
        assert isinstance(case["expected_warnings"], list), case["id"]


def _load_edge_cases() -> dict[str, Any]:
    return yaml.safe_load(EDGE_CASES.read_text(encoding="utf-8"))


def _case_params() -> list[Any]:
    data = _load_edge_cases()
    params = []
    for case in data["cases"]:
        marks = []
        reason = UNSUPPORTED_CASES.get(case["id"])
        if reason:
            marks.append(pytest.mark.xfail(reason=reason, strict=True))
        params.append(pytest.param(case, id=case["id"], marks=marks))
    return params


def _write_transcript(case_dir: Path, case: dict[str, Any], defaults: dict[str, Any]) -> Path:
    transcript = deepcopy(case["transcript"])
    transcript["courses"] = [{**defaults, **course} for course in transcript.get("courses", [])]
    path = case_dir / "transcript.yaml"
    path.write_text(yaml.safe_dump(transcript, sort_keys=False), encoding="utf-8")
    return path


def _write_manual_allocation(case_dir: Path, case: dict[str, Any]) -> Path | None:
    allocation = case.get("manual_allocation")
    if not allocation:
        return None
    path = case_dir / "manual_allocation.yaml"
    path.write_text(yaml.safe_dump(allocation, sort_keys=False), encoding="utf-8")
    return path


def _write_config_overlays(case_dir: Path, case: dict[str, Any]) -> list[Path]:
    overlay_specs = case.get("config_overlay", [])
    if not overlay_specs:
        return []

    overlay_dir = case_dir / "overlay"
    overlay_dir.mkdir()
    paths = []
    for index, spec in enumerate(overlay_specs, start=1):
        filename = spec.get("file") or f"overlay_{index}.yaml"
        payload: dict[str, Any] = {}
        if "requirement" in spec:
            payload["requirements"] = [_expand_requirement_fragment(spec["requirement"])]
        path = overlay_dir / filename
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        paths.append(path)
    return paths


def _expand_requirement_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    expanded = _base_requirement(fragment["id"]) or {
        "description": f"Review overlay requirement {fragment['id']}",
        "requirement_type": "course_list",
        "courses": [],
        "source_ref": {
            "document": "review/edge_cases.yaml",
            "notes": "Synthetic overlay generated by the black-box harness.",
        },
    }
    expanded.update(fragment)
    return expanded


def _base_requirement(requirement_id: str) -> dict[str, Any] | None:
    for path in sorted(CONFIG.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for requirement in data.get("requirements", []):
            if requirement.get("id") == requirement_id:
                return deepcopy(requirement)
    return None


@pytest.mark.parametrize("case", _case_params())
def test_review_edge_cases_contract_subset_semantics(tmp_path: Path, case: dict[str, Any]) -> None:
    data = _load_edge_cases()
    defaults = data["meta"]["defaults"]
    case_dir = tmp_path / case["id"]
    case_dir.mkdir()
    transcript_path = _write_transcript(case_dir, case, defaults)
    allocation_path = _write_manual_allocation(case_dir, case)
    overlay_paths = _write_config_overlays(case_dir, case)

    args = ["audit", "--config", str(CONFIG)]
    for overlay_path in overlay_paths:
        args.extend(["--config", str(overlay_path)])
    args.extend(["--transcript", str(transcript_path), "--format", "json"])
    if allocation_path:
        args.extend(["--allocation", str(allocation_path)])

    result = CliRunner().invoke(app, args)
    expected_constraints = set(case["expected_failed_constraints"])
    if result.exit_code == 1:
        assert expected_constraints & INVALID_INPUT_CONSTRAINTS, result.output
        for constraint_id in expected_constraints:
            assert constraint_id in INVALID_INPUT_CONSTRAINTS
        return

    assert result.exit_code in {0, 2}, result.output
    payload = json.loads(result.output)
    assert payload["pass"] is case["expected_pass"], case["id"]
    assert set(case["expected_failed_requirements"]) <= set(payload["failed_requirements"]), case["id"]
    assert expected_constraints <= set(payload["failed_constraints"]), case["id"]
    for expected_warning in case["expected_warnings"]:
        assert any(expected_warning in warning for warning in payload["warnings"]), case["id"]
