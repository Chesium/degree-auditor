from pathlib import Path

from typer.testing import CliRunner

from degree_auditor.cli import app
from degree_auditor.config_loader import load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nus_ee_ay24_jc"


def test_config_loads_full_shape_with_specialisation_source_refs() -> None:
    config = load_config([CONFIG])

    assert {specialisation.id for specialisation in config.specialisations} == {
        "AE",
        "IND4",
        "IOT",
        "RBT",
        "SPT",
        "SET",
        "MQM",
    }
    for alias in config.course_aliases:
        assert alias.source_ref is not None
        assert alias.source_ref.document
    for requirement in config.requirements:
        assert requirement.source_ref.document
    for pool in config.course_pools:
        assert pool.source_ref.document
    for specialisation in config.specialisations:
        assert specialisation.source_ref.document
        assert specialisation.requirement_ids or specialisation.paths
        assert specialisation.total_units == 20
        assert specialisation.max_overlap_units == 8
        assert specialisation.min_distinct_units == 12
        for path in specialisation.paths:
            assert path.source_ref.document


def test_loading_base_folder_plus_identical_specialisation_file_merges() -> None:
    config = load_config([CONFIG, CONFIG / "specialisations" / "robotics.yaml"])

    assert [specialisation.id for specialisation in config.specialisations].count("RBT") == 1
    assert config.pool_by_id("RBT_ELECTIVE_POOL") is not None


def test_specialisation_references_exist() -> None:
    config = load_config([CONFIG])
    requirement_ids = {requirement.id for requirement in config.requirements}
    pool_ids = {pool.id for pool in config.course_pools}

    for specialisation in config.specialisations:
        assert set(specialisation.requirement_ids) <= requirement_ids
        assert set(specialisation.course_pool_ids) <= pool_ids
        for path in specialisation.paths:
            assert set(path.requirement_ids) <= requirement_ids


def test_list_specialisations_cli_smoke() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["list-specialisations", "--config", str(CONFIG)])

    assert result.exit_code == 0
    assert "AE" in result.output
    assert "RBT" in result.output
    assert "SPT" in result.output
    assert "MQM" in result.output

