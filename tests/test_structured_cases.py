from pathlib import Path
from typing import Any

import yaml

from degree_auditor.audit import audit
from degree_auditor.config_loader import load_config
from degree_auditor.models import Allocation, CourseAttempt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"
TEST_CASES = ROOT / "examples" / "test_cases"


def test_structured_fixture_runner_all_cases() -> None:
    config = load_config([CONFIG])
    cases = list(_load_cases())
    assert cases

    for case in cases:
        courses = [CourseAttempt.model_validate(item) for item in case["transcript"]["courses"]]
        allocation_data = case.get("manual_allocation")
        allocations = None
        if allocation_data is not None:
            allocations = [
                Allocation.model_validate({**item, "manual": item.get("manual", True)})
                for item in allocation_data["allocations"]
            ]
        result = audit(config, courses, allocations)
        expected = case["expected"]

        assert (result.overall_status == "PASS") is expected["pass"], case["id"]
        for requirement_id in expected.get("satisfied_requirements", []):
            assert requirement_id in result.satisfied_requirements, case["id"]
        for requirement_id in expected.get("failed_requirements", []):
            assert requirement_id in result.failed_requirements, case["id"]
        failed_constraints = {item.constraint_id for item in result.constraint_results if not item.passed}
        for constraint_id in expected.get("failed_constraints", []):
            assert constraint_id in failed_constraints, case["id"]
        assert result.warnings == expected.get("warnings", []), case["id"]


def _load_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(TEST_CASES.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cases" in data:
            cases.extend(data["cases"])
        elif isinstance(data, dict):
            cases.append(data)
        elif isinstance(data, list):
            cases.extend(data)
        else:
            raise AssertionError(f"Unsupported structured case file shape: {path}")
    return cases
