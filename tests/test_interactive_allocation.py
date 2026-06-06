import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.allocation import UE_RESIDUAL_REQUIREMENT_ID
from degree_auditor.allocation_choices import allocation_choices_for_course
from degree_auditor.cli import app
from degree_auditor.config_loader import load_allocations, load_config
from degree_auditor.models import CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"


def test_allocation_choices_include_major_tc_te_specialisation_and_residual() -> None:
    config = load_config([CONFIG])

    choice_ids = {
        choice.requirement_id
        for choice in allocation_choices_for_course(config, CourseAttempt(course_code="EE4308"))
    }

    assert "EE24JC_TE" in choice_ids
    assert "RBT_ELECTIVES_20_UNITS" in choice_ids
    assert UE_RESIDUAL_REQUIREMENT_ID in choice_ids


def test_interactive_allocate_cli_writes_commented_yaml(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [{"course_code": "EE4308"}])
    out = tmp_path / "allocation.yaml"

    result = CliRunner().invoke(
        app,
        [
            "interactive-allocate",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--out",
            str(out),
        ],
        input="1\n",
    )

    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# EE4308 eligibility:" in text
    assert "EE24JC_TE" in text
    allocations = load_allocations(out)
    assert len(allocations) == 1
    assert allocations[0].course_code == "EE4308"
    assert allocations[0].requirement_id == "EE24JC_TE"
    assert allocations[0].manual


def test_interactive_allocate_blank_defaults_to_residual(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [{"course_code": "GEA1000"}])
    out = tmp_path / "allocation.yaml"

    result = CliRunner().invoke(
        app,
        [
            "interactive-allocate",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--out",
            str(out),
        ],
        input="\n",
    )

    assert result.exit_code == 0
    allocations = load_allocations(out)
    assert allocations[0].course_code == "GEA1000"
    assert allocations[0].requirement_id == UE_RESIDUAL_REQUIREMENT_ID
    assert allocations[0].allocation_role == "residual_ue"


def test_interactive_allocate_can_run_audit_text(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [{"course_code": "GEA1000"}])
    out = tmp_path / "allocation.yaml"

    result = CliRunner().invoke(
        app,
        [
            "interactive-allocate",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--out",
            str(out),
            "--audit",
        ],
        input="\n",
    )

    assert result.exit_code == 0
    assert "Wrote interactive allocation" in result.output
    assert "Overall status" in result.output


def test_interactive_allocate_can_run_audit_json(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [{"course_code": "GEA1000"}])
    out = tmp_path / "allocation.yaml"

    result = CliRunner().invoke(
        app,
        [
            "interactive-allocate",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--out",
            str(out),
            "--audit",
            "--audit-format",
            "json",
        ],
        input="\n",
    )

    assert result.exit_code == 0
    payload_start = result.output.index("{")
    payload = json.loads(result.output[payload_start:])
    assert {"overall_status", "constraint_results", "allocations"} <= set(payload)


def test_docs_include_interactive_allocation_feature() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    features = (ROOT / "additional_features.md").read_text(encoding="utf-8")

    for text in [readme, features]:
        assert "interactive-allocate" in text
        assert "comment" in text.lower()
        assert "eligibility" in text.lower()


def _write_transcript(tmp_path: Path, courses: list[dict]) -> Path:
    path = tmp_path / "transcript.yaml"
    path.write_text(yaml.safe_dump({"courses": courses}, sort_keys=False), encoding="utf-8")
    return path
