import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TRANSCRIPT = ROOT / "examples" / "transcripts" / "simple_completed.yaml"
ALLOCATIONS = ROOT / "examples" / "manual_allocations"
CONTRACT_KEYS = {
    "pass",
    "cohort",
    "total_units",
    "requirements",
    "failed_requirements",
    "constraints",
    "failed_constraints",
    "warnings",
    "specialisations",
    "allocations",
}


def test_audit_contract_json_schema_trivial_pass() -> None:
    result = _invoke_audit("--format", "json")

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert CONTRACT_KEYS <= set(payload)
    assert payload["pass"] is True
    assert payload["cohort"] == "nus_ee_ay24_jc"
    assert payload["total_units"] == 160
    assert payload["requirements"]
    assert payload["constraints"]


def test_audit_contract_yaml_schema_trivial_pass() -> None:
    result = _invoke_audit("--format", "yaml")

    assert result.exit_code == 0
    payload = yaml.safe_load(result.output)
    assert CONTRACT_KEYS <= set(payload)
    assert payload["pass"] is True
    assert payload["cohort"] == "nus_ee_ay24_jc"
    assert payload["total_units"] == 160


def test_audit_failed_returns_exit_2(tmp_path: Path) -> None:
    transcript = tmp_path / "empty.yaml"
    transcript.write_text("courses: []\n", encoding="utf-8")

    result = _invoke_audit("--transcript", str(transcript), "--format", "json")

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["pass"] is False
    assert payload["failed_requirements"]


def test_audit_invalid_input_returns_exit_1(tmp_path: Path) -> None:
    transcript = tmp_path / "bad.yaml"
    transcript.write_text("courses:\n  - course_code: [bad]\n", encoding="utf-8")

    result = _invoke_audit("--transcript", str(transcript), "--format", "json")

    assert result.exit_code == 1
    assert "Invalid input:" in result.output


def test_audit_contract_known_id_vocabulary(tmp_path: Path) -> None:
    tc_te = _invoke_audit(
        "--allocation",
        str(ALLOCATIONS / "tc_te_conflict.yaml"),
        "--format",
        "json",
    )
    te_transcript = tmp_path / "te_exclusions_transcript.yaml"
    te_transcript.write_text(
        yaml.safe_dump(
            {
                "courses": [
                    {"course_code": "EE1111A"},
                    {"course_code": "EE2111A"},
                    {"course_code": "EE2012"},
                    {"course_code": "EE2022"},
                    {"course_code": "EE2023"},
                    {"course_code": "EE2027"},
                    {"course_code": "PC2020"},
                    {"course_code": "EE2028"},
                    {"course_code": "EE2026"},
                    {"course_code": "EE3331C"},
                    {"course_code": "EE3408C"},
                    {"course_code": "EE3031"},
                    {"course_code": "EE3033"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    te_exclusions = _invoke_audit(
        "--transcript",
        str(te_transcript),
        "--allocation",
        str(ALLOCATIONS / "te_exclusions.yaml"),
        "--format",
        "json",
    )
    sep_transcript = tmp_path / "sep.yaml"
    sep_transcript.write_text(
        yaml.safe_dump(
            {
                "courses": [
                    {"course_code": "SEP4308", "source": "SEP", "mapped_to": "EE4308"},
                    {"course_code": "SEP4211", "source": "SEP", "mapped_to": "EE4211"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    sep_allocations = tmp_path / "sep_allocations.yaml"
    sep_allocations.write_text(
        yaml.safe_dump(
            {
                "allocations": [
                    {"course_code": "SEP4308", "requirement_id": "EE24JC_TE"},
                    {"course_code": "SEP4211", "requirement_id": "EE24JC_TE"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    sep = _invoke_audit(
        "--transcript",
        str(sep_transcript),
        "--allocation",
        str(sep_allocations),
        "--format",
        "json",
    )

    assert tc_te.exit_code == 2
    assert "TC_NOT_TE" in json.loads(tc_te.output)["failed_constraints"]

    assert te_exclusions.exit_code == 2
    te_failed = set(json.loads(te_exclusions.output)["failed_constraints"])
    assert {"TE_EXCLUDE_EE3031", "TE_EXCLUDE_EE3033"} <= te_failed

    assert sep.exit_code == 2
    sep_failed = set(json.loads(sep.output)["failed_constraints"])
    assert {"SEP_TE_ONE_NUS", "SEP_TE_MAX_ONE_MAPPED"} <= sep_failed


def _invoke_audit(*extra_args: str):
    args = [
        "audit",
        "--config",
        str(CONFIG),
        "--transcript",
        str(TRANSCRIPT),
        *extra_args,
    ]
    return CliRunner().invoke(app, args)
