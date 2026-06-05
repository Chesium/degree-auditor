from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from degree_auditor.merge import merge_config_fragments
from degree_auditor.models import Allocation, CourseAttempt, DegreeAuditConfig


class ConfigLoadError(ValueError):
    """Raised when config or fixture YAML cannot be loaded."""


def load_config(paths: Iterable[str | Path]) -> DegreeAuditConfig:
    fragments = [_read_yaml_file(path) for path in _expand_paths(paths)]
    merged = merge_config_fragments(fragments)
    return DegreeAuditConfig.model_validate(merged)


def load_transcript(path: str | Path) -> list[CourseAttempt]:
    data = _read_yaml_file(Path(path))
    courses = data.get("courses", data.get("course_attempts"))
    if courses is None:
        raise ConfigLoadError(f"Transcript {path} must contain courses or course_attempts")
    return [CourseAttempt.model_validate(item) for item in courses]


def load_allocations(path: str | Path) -> list[Allocation]:
    data = _read_yaml_file(Path(path))
    allocations = data.get("allocations")
    if allocations is None:
        raise ConfigLoadError(f"Allocation file {path} must contain allocations")
    return [Allocation.model_validate({**item, "manual": item.get("manual", True)}) for item in allocations]


def _expand_paths(paths: Iterable[str | Path]) -> list[Path]:
    expanded: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise ConfigLoadError(f"Config path does not exist: {path}")
        if path.is_dir():
            expanded.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in {".yaml", ".yml"}))
        elif path.suffix.lower() in {".yaml", ".yml"}:
            expanded.append(path)
        else:
            raise ConfigLoadError(f"Config path is not a YAML file or directory: {path}")
    return expanded


def _read_yaml_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"YAML file {path} must contain a mapping at the top level")
    return data

