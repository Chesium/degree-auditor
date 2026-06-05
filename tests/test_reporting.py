import json
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from degree_auditor.audit import audit
from degree_auditor.cli import app
from degree_auditor.config_loader import load_config, load_transcript
from degree_auditor.models import Allocation, CourseAttempt
from degree_auditor.reporting import render_audit_report


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_report_text_includes_major_tc_te_and_source_refs() -> None:
    config = load_config([CONFIG])
    result = audit(config, load_transcript(TRANSCRIPT))

    text = _render_text(config, result)

    assert "NUS EE AY24 JC Degree Audit" in text
    assert "Major Programme" in text
    assert "Technical Courses" in text
    assert "Technical Electives" in text
    assert "EE24JC_TE_SEP_ONE_NUS" in text
    assert "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf" in text


def test_report_text_includes_specialisation_overlap_sep_and_capstone_lock() -> None:
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    courses.append(CourseAttempt(course_code="EE4002D", units=8, topic_tags=["robotics"]))
    result = audit(
        config,
        courses,
        [
            Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
            Allocation(course_code="EE2026", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3331C", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE3408C", requirement_id="EE24JC_TC"),
            Allocation(course_code="EE4308", requirement_id="EE24JC_TE"),
            Allocation(course_code="EE4211", requirement_id="EE24JC_TE"),
            Allocation(course_code="EE4002D", requirement_id="CDE_CAPSTONE", units=8),
            Allocation(course_code="EE4308", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4212", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4216", requirement_id="RBT_ELECTIVES_12_UNITS"),
            Allocation(course_code="EE4002D", requirement_id="RBT_CAPSTONE", units=8),
        ],
    )

    text = _render_text(config, result)

    assert "Selected Specialisations" in text
    assert "RBT" in text
    assert "RBT_WITH_CAPSTONE" in text
    assert "Overlap Budget" in text
    assert "8 / 8" in text
    assert "SEP Status" in text
    assert "Capstone lock active" in text
    assert "RBT_CAPSTONE_LOCK" in text


def test_audit_json_shape_contains_core_result_fields() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "audit",
            "--config",
            str(CONFIG),
            "--transcript",
            str(TRANSCRIPT),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert {
        "overall_status",
        "requirement_statuses",
        "satisfied_requirements",
        "failed_requirements",
        "allocations",
        "constraint_results",
        "specialisation_results",
        "warnings",
    } <= set(payload)
    assert {"constraint_id", "passed", "source_ref", "message"} <= set(payload["constraint_results"][0])
    assert isinstance(payload["specialisation_results"], list)


def _render_text(config, result) -> str:
    console = Console(record=True, width=220, color_system=None)
    render_audit_report(config, result, console=console)
    return console.export_text(styles=False)
