import pytest

from degree_auditor.merge import ConfigMergeError, merge_config_fragments


def test_merge_conflicting_duplicate_id_fails() -> None:
    source_ref = {
        "document": "L_AY24JC_Checklist_Revised_3TC_4June2025.pdf",
        "page": 1,
        "section": "Technical Courses",
    }
    first = {
        "requirements": [
            {
                "id": "EE24JC_TC",
                "description": "First description",
                "requirement_type": "pool_count",
                "pool_id": "EE24JC_TC_POOL",
                "min_count": 3,
                "source_ref": source_ref,
            }
        ]
    }
    second = {
        "requirements": [
            {
                "id": "EE24JC_TC",
                "description": "Conflicting description",
                "requirement_type": "pool_count",
                "pool_id": "EE24JC_TC_POOL",
                "min_count": 3,
                "source_ref": source_ref,
            }
        ]
    }

    with pytest.raises(ConfigMergeError, match="Conflicting requirements object"):
        merge_config_fragments([first, second])

