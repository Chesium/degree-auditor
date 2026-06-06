from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from degree_auditor.cli import app
from degree_auditor.config_loader import load_config
from degree_auditor.contract import to_contract_result
from degree_auditor.id_registry import PUBLIC_REQUIREMENT_IDS, PUBLIC_SLOT_IDS, SLOT_TO_REQUIREMENT, map_requirement_id
from degree_auditor.manual_validation import validate_manual_allocations
from degree_auditor.models import Allocation, AuditResult, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
EDGE_CASES = ROOT / "review" / "edge_cases.yaml"


def test_registry_matches_review_edge_case_slots() -> None:
    edge = yaml.safe_load(EDGE_CASES.read_text(encoding="utf-8"))

    assert SLOT_TO_REQUIREMENT == edge["meta"]["slot_to_requirement"]
    assert PUBLIC_SLOT_IDS == set(edge["meta"]["slot_to_requirement"])
    assert PUBLIC_REQUIREMENT_IDS == set(edge["meta"]["slot_to_requirement"].values())


def test_manual_allocation_accepts_all_review_slot_ids() -> None:
    config = load_config([CONFIG])
    courses = [CourseAttempt(course_code="EE4302")]
    allocations = [
        Allocation(course_code="EE4302", requirement_id=slot_id, manual=True)
        for slot_id in sorted(PUBLIC_SLOT_IDS)
    ]

    validate_manual_allocations(config, courses, allocations)


def test_contract_requirement_ids_match_edge_case_registry() -> None:
    for slot_id, requirement_id in SLOT_TO_REQUIREMENT.items():
        assert map_requirement_id(slot_id) == requirement_id


def test_public_contract_does_not_emit_mapped_internal_ids() -> None:
    config = load_config([CONFIG])
    result = AuditResult(
        overall_status="PASS",
        requirement_statuses={
            "EE24JC_MAJOR_DIGITAL_CHOICE": "PASS",
            "AE_ELECTIVES": "PASS",
            "RBT_CAPSTONE": "PASS",
            "SPT_ELECTIVES": "PASS",
        },
        allocations=[
            Allocation(course_code="EE2028", requirement_id="EE24JC_MAJOR_DIGITAL_CHOICE"),
            Allocation(course_code="EE4407", requirement_id="AE_ELECTIVES"),
            Allocation(course_code="EE4002D", requirement_id="RBT_CAPSTONE", units=8),
            Allocation(course_code="EE4101", requirement_id="SPT_ELECTIVES"),
        ],
    )

    payload = to_contract_result(config, result)
    emitted = {row["id"] for row in payload["requirements"]}
    allocation_ids = {row["requirement_id"] for row in payload["allocations"]}

    assert "EE24JC_MAJOR_DIGITAL_CHOICE" not in emitted
    assert "AE_ELECTIVES" not in emitted
    assert "SPT_ELECTIVES" not in emitted
    assert {"MAJ_DIGITAL_CHOICE", "AE_ELECTIVES_MIN_3", "SPT_ELECTIVES_MIN_2"} <= emitted
    assert {"MAJ_DIGITAL_CHOICE", "AE_ELECTIVES_MIN_3", "RBT_PATH1_CAPSTONE"} <= allocation_ids


def test_major_digital_public_slot_alias_is_accepted(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.yaml"
    transcript.write_text(
        yaml.safe_dump(
            {
                "courses": [
                    {"course_code": "EE2028"},
                    {"course_code": "EE2026"},
                    {"course_code": "EE3408C"},
                    {"course_code": "EE3331C"},
                    {"course_code": "EE4308"},
                    {"course_code": "EE4211"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    allocations = tmp_path / "allocations.yaml"
    allocations.write_text(
        yaml.safe_dump(
            {
                "allocations": [
                    {"course_code": "EE2028", "requirement_id": "EE24JC_MAJOR_DIGITAL"},
                    {"course_code": "EE2026", "requirement_id": "EE24JC_TC"},
                    {"course_code": "EE3408C", "requirement_id": "EE24JC_TC"},
                    {"course_code": "EE3331C", "requirement_id": "EE24JC_TC"},
                    {"course_code": "EE4308", "requirement_id": "EE24JC_TE"},
                    {"course_code": "EE4211", "requirement_id": "EE24JC_TE"},
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "audit",
            "--config",
            str(CONFIG),
            "--transcript",
            str(transcript),
            "--allocation",
            str(allocations),
            "--format",
            "json",
        ],
    )

    assert result.exit_code in {0, 2}
    payload = json.loads(result.output)
    assert any(row["requirement_id"] == "MAJ_DIGITAL_CHOICE" for row in payload["allocations"])
    assert "EE24JC_MAJOR_DIGITAL" not in result.output


def test_list_requirements_or_contract_contains_review_requirement_vocabulary() -> None:
    result = CliRunner().invoke(app, ["audit", "--config", str(CONFIG), "--transcript", str(ROOT / "examples/transcripts/simple_completed.yaml"), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    ids = {row["id"] for row in payload["requirements"]} | {row["requirement_id"] for row in payload["allocations"]}
    assert {"TC_MIN_3", "TE_MIN_2", "UE_40", "MAJ_DIGITAL_CHOICE"} <= ids
