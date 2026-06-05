from pathlib import Path

from typer.testing import CliRunner

from degree_auditor.allocation import (
    FIXED_MAJOR_CORE_REQUIREMENT_ID,
    UE_RESIDUAL_REQUIREMENT_ID,
    plan_allocations,
)
from degree_auditor.audit import audit
from degree_auditor.cli import app
from degree_auditor.config_loader import load_allocations, load_config, load_transcript
from degree_auditor.eligibility import MAJOR_CHOICE_REQUIREMENT_ID, TC_REQUIREMENT_ID, TE_REQUIREMENT_ID
from degree_auditor.models import CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"
ALLOCATIONS = ROOT / "examples" / "manual_allocations"


def test_major_core_pass_basic() -> None:
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)

    result = audit(config, courses)

    assert result.overall_status == "PASS"
    assert result.requirement_statuses["EE24JC_MAJOR"] == "PASS"
    assert result.requirement_statuses[FIXED_MAJOR_CORE_REQUIREMENT_ID] == "PASS"
    assert result.requirement_statuses[MAJOR_CHOICE_REQUIREMENT_ID] == "PASS"
    assert result.requirement_statuses[TE_REQUIREMENT_ID] == "PASS"


def test_greedy_allocation_output() -> None:
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    courses.append(CourseAttempt(course_code="GEA1000", units=4))

    allocations = plan_allocations(config, courses)

    assert _count(allocations, FIXED_MAJOR_CORE_REQUIREMENT_ID) == 7
    assert [a.course_code for a in allocations if a.requirement_id == MAJOR_CHOICE_REQUIREMENT_ID] == ["EE2028"]
    assert _count(allocations, TC_REQUIREMENT_ID) == 3
    assert _count(allocations, TE_REQUIREMENT_ID) == 2
    residual = [a for a in allocations if a.requirement_id == UE_RESIDUAL_REQUIREMENT_ID]
    assert [a.course_code for a in residual] == ["GEA1000"]
    assert residual[0].allocation_role == "residual_ue"
    assert all(not allocation.manual for allocation in allocations)


def test_manual_allocation_override() -> None:
    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    manual = load_allocations(ALLOCATIONS / "manual_override_major_choice.yaml")

    result = audit(config, courses, manual)

    major_choices = [a.course_code for a in result.allocations if a.requirement_id == MAJOR_CHOICE_REQUIREMENT_ID]
    assert result.overall_status == "PASS"
    assert major_choices == ["EE2026"]
    assert all(allocation.manual for allocation in result.allocations)


def test_plan_allocation_cli_writes_yaml(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "allocation.yaml"

    result = runner.invoke(
        app,
        [
            "plan-allocation",
            "--config",
            str(CONFIG),
            "--transcript",
            str(TRANSCRIPT),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert out.exists()
    allocations = load_allocations(out)
    assert any(allocation.requirement_id == FIXED_MAJOR_CORE_REQUIREMENT_ID for allocation in allocations)
    assert all(not allocation.manual for allocation in allocations)


def test_list_requirements_cli_smoke() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["list-requirements", "--config", str(CONFIG)])

    assert result.exit_code == 0
    assert "EE24JC_MAJOR_CORE" in result.output
    assert "EE24JC_TC" in result.output
    assert "EE24JC_TE" in result.output


def _count(allocations, requirement_id: str) -> int:
    return sum(1 for allocation in allocations if allocation.requirement_id == requirement_id)

