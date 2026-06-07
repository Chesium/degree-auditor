from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"


def test_manual_alloc_unknown_course_error(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE4302"}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {"allocations": [{"course_code": "EE9999", "requirement_id": "EE24JC_TE"}]},
    )

    result = _invoke(transcript, allocation)

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INVALID" in result.stderr
    assert "Manual allocation references EE9999 which is not in the transcript" in result.stderr


def test_manual_alloc_units_exceed_attempt_error(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE4302", "units": 4}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {"allocations": [{"course_code": "EE4302", "requirement_id": "EE24JC_TE", "units": 8}]},
    )

    result = _invoke(transcript, allocation)

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INVALID" in result.stderr
    assert "Allocation of 8 units exceeds EE4302's 4 available units" in result.stderr


def test_manual_alloc_unknown_requirement_error(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE4302"}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {"allocations": [{"course_code": "EE4302", "requirement_id": "NO_SUCH_REQUIREMENT"}]},
    )

    result = _invoke(transcript, allocation)

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INVALID" in result.stderr
    assert "unknown requirement NO_SUCH_REQUIREMENT" in result.stderr


def test_manual_alloc_duplicate_single_instance_error(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE4302"}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {
            "allocations": [
                {"course_code": "EE4302", "requirement_id": "EE24JC_TE"},
                {"course_code": "EE4302", "requirement_id": "EE24JC_TE"},
            ]
        },
    )

    result = _invoke(transcript, allocation)

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INVALID" in result.stderr
    assert "repeats EE4302 for EE24JC_TE" in result.stderr


def test_manual_alloc_ineligible_requirement_error(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE2012"}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {"allocations": [{"course_code": "EE2012", "requirement_id": "EE24JC_TE"}]},
    )

    result = _invoke(transcript, allocation)

    assert result.exit_code == 1
    assert "MANUAL_ALLOC_INELIGIBLE" in result.stderr
    assert "EE2012 is not eligible for the TE requirement" in result.stderr


def test_tc_te_mutual_exclusion_remains_audit_failure(tmp_path: Path) -> None:
    transcript = _write_yaml(tmp_path / "transcript.yaml", {"courses": [{"course_code": "EE3331C"}]})
    allocation = _write_yaml(
        tmp_path / "allocation.yaml",
        {
            "allocations": [
                {"course_code": "EE3331C", "requirement_id": "EE24JC_TC"},
                {"course_code": "EE3331C", "requirement_id": "EE24JC_TE", "allocation_role": "double_count"},
            ]
        },
    )

    result = _invoke(transcript, allocation)
    payload = json.loads(result.output)

    assert result.exit_code == 2
    assert "TC_NOT_TE" in payload["failed_constraints"]


def _invoke(transcript: Path, allocation: Path):
    return CliRunner().invoke(
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


def _write_yaml(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path
