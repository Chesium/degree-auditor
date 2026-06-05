from pathlib import Path

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_allocations, load_config, load_transcript


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"
ALLOCATIONS = ROOT / "examples" / "manual_allocations"


def _result_with_allocations(name: str):
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    allocations = load_allocations(ALLOCATIONS / name)
    return audit(config, courses, allocations)


def test_tc_te_mutual_exclusion_fail() -> None:
    result = _result_with_allocations("tc_te_conflict.yaml")

    failure = next(
        item for item in result.constraint_results if item.constraint_id == "EE24JC_TC_TE_MUTUAL_EXCLUSION"
    )
    assert result.overall_status == "FAIL"
    assert not failure.passed
    assert failure.affected_courses == ["EE3331C"]
    assert failure.source_ref is not None
    assert failure.source_ref.document == "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf"


def test_ee2026_ee2028_choice_tc_success() -> None:
    result = _result_with_allocations("ee2026_tc_success.yaml")

    assert result.overall_status == "PASS"
    assert all(item.passed for item in result.constraint_results)


def test_te_exclusions_fail() -> None:
    result = _result_with_allocations("te_exclusions.yaml")

    failure = next(item for item in result.constraint_results if item.constraint_id == "EE24JC_TE_ELIGIBILITY")
    assert result.overall_status == "FAIL"
    assert not failure.passed
    assert failure.affected_courses == ["EE3031", "EE3033"]
    assert failure.source_ref is not None
    assert failure.source_ref.document == "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf"

