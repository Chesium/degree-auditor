from pathlib import Path

from degree_auditor.config_loader import load_config
from degree_auditor.eligibility import course_in_pool, expand_eligibility, is_te_eligible
from degree_auditor.models import CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"


def test_course_matching_exact_wildcard_alias_and_sep_mapped_to() -> None:
    config = load_config([CONFIG])
    tc_pool = config.pool_by_id("EE24JC_TC_POOL")
    assert tc_pool is not None

    assert course_in_pool("EE3331C", tc_pool)
    assert is_te_eligible(config, "EE4308")
    assert is_te_eligible(config, "EE3331C")
    assert is_te_eligible(config, "IE4213")

    expanded = expand_eligibility(
        config,
        [
            CourseAttempt(course_code="SEP-ROB-401", source="SEP", mapped_to="EE4308"),
            CourseAttempt(course_code="IE4213"),
        ],
    )
    assert expanded["SEP-ROB-401"] == ["EE24JC_TE"]
    assert expanded["IE4213"] == ["EE24JC_TE"]


def test_expand_eligibility_still_reports_tc_te_after_matcher_refactor() -> None:
    config = load_config([CONFIG])

    expanded = expand_eligibility(
        config,
        [
            CourseAttempt(course_code="EE2026"),
            CourseAttempt(course_code="EE3331C"),
            CourseAttempt(course_code="EE4308"),
        ],
    )

    assert expanded["EE2026"] == ["EE24JC_MAJOR_DIGITAL_CHOICE", "EE24JC_TC"]
    assert expanded["EE3331C"] == ["EE24JC_TC", "EE24JC_TE"]
    assert expanded["EE4308"] == ["EE24JC_TE"]

