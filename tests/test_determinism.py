from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.audit import audit
from degree_auditor.cli import app
from degree_auditor.config_loader import load_allocations, load_config, load_transcript


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"


def test_repeated_audit_json_is_identical() -> None:
    first = _invoke_audit("--format", "json")
    second = _invoke_audit("--format", "json")

    assert first.exit_code == 0
    assert first.output == second.output


def test_repeated_audit_yaml_is_identical() -> None:
    first = _invoke_audit("--format", "yaml")
    second = _invoke_audit("--format", "yaml")

    assert first.exit_code == 0
    assert first.output == second.output


def test_reordered_transcript_json_contract_is_identical(tmp_path: Path) -> None:
    data = yaml.safe_load(TRANSCRIPT.read_text(encoding="utf-8"))
    reordered = tmp_path / "reordered.yaml"
    reordered.write_text(yaml.safe_dump({"courses": list(reversed(data["courses"]))}, sort_keys=False), encoding="utf-8")

    baseline = json.loads(_invoke_audit("--format", "json").output)
    changed = json.loads(_invoke_audit("--transcript", str(reordered), "--format", "json").output)

    assert baseline == changed


def test_reordered_manual_allocation_json_contract_is_identical(tmp_path: Path) -> None:
    allocation = {
        "allocations": [
            {"course_code": "EE2028", "requirement_id": "EE24JC_MAJOR_DIGITAL_CHOICE"},
            {"course_code": "EE2026", "requirement_id": "EE24JC_TC"},
            {"course_code": "EE3331C", "requirement_id": "EE24JC_TC"},
            {"course_code": "EE3408C", "requirement_id": "EE24JC_TC"},
            {"course_code": "EE4308", "requirement_id": "EE24JC_TE"},
            {"course_code": "EE4211", "requirement_id": "EE24JC_TE"},
        ]
    }
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text(yaml.safe_dump(allocation, sort_keys=False), encoding="utf-8")
    second_path.write_text(
        yaml.safe_dump({"allocations": list(reversed(allocation["allocations"]))}, sort_keys=False),
        encoding="utf-8",
    )

    first = json.loads(_invoke_audit("--allocation", str(first_path), "--format", "json").output)
    second = json.loads(_invoke_audit("--allocation", str(second_path), "--format", "json").output)

    assert first == second


def test_plan_allocation_round_trip_and_deterministic_file(tmp_path: Path) -> None:
    first_out = tmp_path / "first.yaml"
    second_out = tmp_path / "second.yaml"
    first = _invoke_plan(first_out)
    second = _invoke_plan(second_out)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first_out.read_text(encoding="utf-8") == second_out.read_text(encoding="utf-8")

    config = load_config([CONFIG])
    courses = load_transcript(TRANSCRIPT)
    planned = audit(config, courses)
    round_trip = audit(config, courses, load_allocations(first_out))

    assert planned.overall_status == round_trip.overall_status
    assert [(a.course_code, a.requirement_id) for a in planned.allocations] == [
        (a.course_code, a.requirement_id) for a in round_trip.allocations
    ]


def _invoke_audit(*extra_args: str):
    return CliRunner().invoke(
        app,
        [
            "audit",
            "--config",
            str(CONFIG),
            "--transcript",
            str(TRANSCRIPT),
            *extra_args,
        ],
    )


def _invoke_plan(out: Path):
    return CliRunner().invoke(
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
