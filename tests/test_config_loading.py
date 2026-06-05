from pathlib import Path

from degree_auditor.config_loader import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_config_loads_seed_programme() -> None:
    config = load_config([ROOT / "configs" / "nus_ee_ay24_jc"])

    assert config.programme_id == "nus_ee_ay24_jc"
    assert config.requirement_by_id("EE24JC_TC") is not None
    assert config.requirement_by_id("EE24JC_TE") is not None
    assert config.pool_by_id("EE24JC_TC_POOL") is not None
    assert config.pool_by_id("EE24JC_TE_POOL") is not None

    for requirement in config.requirements:
        assert requirement.source_ref.document
    for pool in config.course_pools:
        assert pool.source_ref.document
    for constraint in config.constraints:
        assert constraint.source_ref.document

