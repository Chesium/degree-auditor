from __future__ import annotations

from copy import deepcopy
from typing import Any


LIST_KEYS_BY_ID = {
    "requirements",
    "requirement_groups",
    "course_pools",
    "constraints",
    "specialisations",
    "course_aliases",
}


class ConfigMergeError(ValueError):
    """Raised when two config fragments define incompatible objects."""


def merge_config_fragments(fragments: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for fragment in fragments:
        merged = merge_config_dicts(merged, fragment)
    return merged


def merge_config_dicts(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in incoming.items():
        if key in LIST_KEYS_BY_ID:
            result[key] = _merge_lists_by_id(key, result.get(key, []), value or [])
        elif key not in result:
            result[key] = deepcopy(value)
        elif result[key] == value:
            continue
        else:
            raise ConfigMergeError(f"Conflicting scalar config value for {key!r}")
    return result


def _merge_lists_by_id(key: str, base_items: list[dict[str, Any]], incoming_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {item["id"]: deepcopy(item) for item in base_items}
    order = [item["id"] for item in base_items]

    for incoming in incoming_items:
        item_id = incoming["id"]
        if item_id not in by_id:
            by_id[item_id] = deepcopy(incoming)
            order.append(item_id)
            continue

        existing = by_id[item_id]
        if _without_override(existing) == _without_override(incoming):
            continue

        if incoming.get("override") is True:
            by_id[item_id] = deepcopy(incoming)
            continue

        if key == "course_pools":
            by_id[item_id] = _merge_course_pool(existing, incoming)
            continue

        raise ConfigMergeError(f"Conflicting {key} object with id {item_id!r}; set override: true to replace it")

    return [by_id[item_id] for item_id in order]


def _merge_course_pool(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    comparable_existing = _without_override(existing)
    comparable_incoming = _without_override(incoming)
    for list_key in ("includes", "excludes"):
        comparable_existing.pop(list_key, None)
        comparable_incoming.pop(list_key, None)
    if comparable_existing != comparable_incoming:
        raise ConfigMergeError(
            f"Conflicting course_pools object with id {incoming['id']!r}; set override: true to replace it"
        )

    merged = deepcopy(existing)
    for list_key in ("includes", "excludes"):
        seen = set(merged.get(list_key, []))
        for item in incoming.get(list_key, []):
            if item not in seen:
                merged.setdefault(list_key, []).append(item)
                seen.add(item)
    return merged


def _without_override(item: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(item)
    copied.pop("override", None)
    return copied

