from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


FALLBACK_SLOT_TO_REQUIREMENT = {
    "EE24JC_TC": "TC_MIN_3",
    "EE24JC_TE": "TE_MIN_2",
    "EE24JC_UE": "UE_40",
    "EE24JC_MAJOR_DIGITAL": "MAJ_DIGITAL_CHOICE",
    "EE24JC_MAJOR_EE2027": "MAJ_EE2027",
    "MAJOR_INTERNSHIP": "MAJOR_INTERNSHIP_10",
    "AE_CORE": "AE_CORE",
    "AE_ELECTIVE": "AE_ELECTIVES_MIN_3",
    "IND4_CORE": "IND4_CORE",
    "IOT_CORE": "IOT_CORE",
    "IOT_ELECTIVE": "IOT_ELECTIVES_MIN_2_OR_8U",
    "MQM_CORE": "MQM_CORE",
    "MQM_ELECTIVE": "MQM_ELECTIVES_MIN_3_OR_12U",
    "RBT_BASKET": "RBT_PATH1_CAPSTONE",
    "RBT_CAPSTONE": "RBT_PATH1_CAPSTONE",
    "SET_ELECTIVE": "SET_ELECTIVES_MIN_2",
    "SPT_CORE": "SPT_CORE",
    "SPT_ELECTIVE": "SPT_ELECTIVES_MIN_2",
    "CC_CAPSTONE": "CC_CAPSTONE",
    "CC_GE_GESS": "CC_GE_GESS",
    "CC_ISK_ST": "CC_ISK_ST",
    "CC_ISK_CN": "CC_ISK_CN",
    "CC_ISK_SF": "CC_ISK_SF",
    "IDP_2ND_MAJOR": "IDP_2ND_MAJOR",
}

INTERNAL_SLOT_ALIASES = {
    "EE24JC_MAJOR_DIGITAL": "EE24JC_MAJOR_DIGITAL_CHOICE",
}

INTERNAL_TO_PUBLIC_REQUIREMENT = {
    "EE24JC_MAJOR_DIGITAL_CHOICE": "MAJ_DIGITAL_CHOICE",
    "EE24JC_MAJOR_CORE": "MAJOR_60",
    "EE24JC_MAJOR": "MAJOR_60",
    "CDE_COMMON_CURRICULUM": "CC_CDE_60",
    "UE_RESIDUAL": "UE_40",
    "CDE_CAPSTONE": "CC_CAPSTONE",
    "CC_ISK_CAPSTONE": "CC_CAPSTONE",
    "AE_ELECTIVES": "AE_ELECTIVES_MIN_3",
    "IND4_CORE_CONTROL": "IND4_CORE",
    "IND4_CORE_AUTOMATION": "IND4_CORE",
    "IND4_CORE_DATA": "IND4_CORE",
    "IND4_ELECTIVES": "IND4_ELECTIVES_MIN_3",
    "IND4_ELECTIVE": "IND4_ELECTIVES_MIN_3",
    "IOT_ELECTIVES": "IOT_ELECTIVES_MIN_2_OR_8U",
    "IOT_PROJECT": "IOT_ELECTIVES_MIN_2_OR_8U",
    "IOT_PROJECT_OPTIONS": "IOT_ELECTIVES_MIN_2_OR_8U",
    "MQM_ELECTIVES": "MQM_ELECTIVES_MIN_3_OR_12U",
    "MQM_PROJECT_OPTIONS": "MQM_ELECTIVES_MIN_3_OR_12U",
    "RBT_ELECTIVES_12_UNITS": "RBT_PATH1_CAPSTONE",
    "RBT_ELECTIVES_20_UNITS": "RBT_PATH2_COURSEWORK",
    "SET_CORE": "SET_CORE",
    "SET_ELECTIVES": "SET_ELECTIVES_MIN_2",
    "SPT_ELECTIVES": "SPT_ELECTIVES_MIN_2",
    "SPT_SATELLITE_CAPSTONE": "SPT_CORE",
    "SPT_IDP_REPLACEMENT_ELECTIVES": "SPT_IDP_PATH",
}


def _load_slot_to_requirement() -> dict[str, str]:
    review_path = Path(__file__).resolve().parents[1] / "review" / "edge_cases.yaml"
    if not review_path.exists():
        return dict(FALLBACK_SLOT_TO_REQUIREMENT)
    data = yaml.safe_load(review_path.read_text(encoding="utf-8")) or {}
    loaded = data.get("meta", {}).get("slot_to_requirement")
    if not isinstance(loaded, dict):
        return dict(FALLBACK_SLOT_TO_REQUIREMENT)
    return {str(key): str(value) for key, value in loaded.items()}


SLOT_TO_REQUIREMENT = _load_slot_to_requirement()
PUBLIC_SLOT_IDS = set(SLOT_TO_REQUIREMENT)
PUBLIC_REQUIREMENT_IDS = set(SLOT_TO_REQUIREMENT.values())


def normalize_slot_id(slot_id: str) -> str:
    return INTERNAL_SLOT_ALIASES.get(slot_id, slot_id)


def normalize_allocation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    requirement_id = payload.get("requirement_id")
    if isinstance(requirement_id, str):
        return {**payload, "requirement_id": normalize_slot_id(requirement_id)}
    return payload


def map_requirement_id(requirement_id: str) -> str:
    if requirement_id.startswith("SPECIALISATION_"):
        return requirement_id
    if requirement_id in SLOT_TO_REQUIREMENT:
        return SLOT_TO_REQUIREMENT[requirement_id]
    return INTERNAL_TO_PUBLIC_REQUIREMENT.get(requirement_id, requirement_id)
