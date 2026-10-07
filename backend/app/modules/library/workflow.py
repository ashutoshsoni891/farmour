"""Review rules for library entries (spec section 6), as pure functions.

An entry can go to review only when the fields the engine and planner need are filled AND every
agronomy value has a source (a public document or an agronomist's recorded judgement).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Fields that describe the entry rather than agronomy; they need no source.
IDENTITY_FIELDS = {
    "slug", "name_en", "name_hi", "scientific_name", "family", "category", "layers",
    "source_notes", "todo", "sources", "regional", "unit_to_kg",
}  # fmt: skip

# Required before review = what the design engine actually uses (decision 2026-10-06). Sun, height
# and canopy are welcome but optional: trees go in the open north strip and spacing drives layout.
CROP_ALWAYS = ["family", "seasons", "water_need"]
CROP_BED = [
    "days_to_first_harvest", "harvest_span_days", "spacing_plant_cm",
    "expected_yield_kg_per_sqm", "waterlogging_tolerant",
]  # fmt: skip
CROP_TREE = ["tree_spacing_m", "years_to_bear"]
CROP_BORDER = ["spacing_plant_cm"]
CROP_FIELD = ["days_to_first_harvest", "spacing_row_cm", "expected_yield_kg_per_sqm"]
CROP_GREEN_MANURE = ["days_to_first_harvest", "spacing_row_cm"]  # days until it is dug in
TREE_CATEGORIES = {"fruit_tree", "fruit_short"}
BORDER_CATEGORIES = {"border"}
GREEN_MANURE_CATEGORIES = {"green_manure"}


def _empty(v: Any) -> bool:
    return v is None or v == [] or v == {} or v == ""


def _has_source(sources: dict[str, Any], field: str) -> bool:
    return bool(sources.get(field))


def crop_missing(data: dict[str, Any], regions: list[str]) -> list[str]:
    """Reasons the crop can't go to review, as keys like 'field:x' or 'source:x'.
    `regions` is the lookup order for sowing windows: the farm's region, then its fallbacks."""
    required = list(CROP_ALWAYS)
    if data.get("category") in TREE_CATEGORIES:
        required += CROP_TREE
    elif data.get("category") in BORDER_CATEGORIES:
        required += CROP_BORDER
    elif data.get("category") in GREEN_MANURE_CATEGORIES:
        required += CROP_GREEN_MANURE
    elif data.get("layers"):
        required += CROP_BED
    else:
        required += CROP_FIELD
    missing = [f"field:{f}" for f in dict.fromkeys(required) if _empty(data.get(f))]

    seasons = data.get("seasons") or []
    by_region = data.get("regional") or {}
    found = next(
        (r for r in regions if not _empty((by_region.get(r) or {}).get("sow_windows"))), None
    )
    if seasons and seasons != ["perennial"]:
        if found is None:
            missing.append(f"field:sow_windows.{regions[0]}")
        elif not _has_source((by_region[found].get("sources") or {}), "sow_windows"):
            missing.append(f"source:sow_windows.{found}")

    sources = data.get("sources") or {}
    for field, value in data.items():
        if field in IDENTITY_FIELDS or _empty(value):
            continue
        if not _has_source(sources, field):
            missing.append(f"source:{field}")
    return missing


def recipe_missing(data: dict[str, Any]) -> list[str]:
    required = ["ingredients", "per_area_sqm", "steps_en", "steps_hi", "apply_method"]
    if data.get("apply_method") == "seed_treatment":
        required.remove("per_area_sqm")  # a seed-treatment batch is sized by seed weight, not area
    missing = [f"field:{f}" for f in required if _empty(data.get(f))]
    if any(i.get("qty") is None for i in data.get("ingredients") or []):
        missing.append("field:ingredients.qty")
    sources = data.get("sources") or {}
    for field, value in data.items():
        if field in IDENTITY_FIELDS or field == "steps_hi" or _empty(value):
            continue  # steps_hi is the translation of the sourced steps_en
        if field == "safety_notes_hi":
            continue
        if not _has_source(sources, field):
            missing.append(f"source:{field}")
    return missing


def pest_missing(data: dict[str, Any]) -> list[str]:
    missing = [
        f"field:{f}" for f in ("crop_slugs", "symptoms_en", "symptoms_hi") if _empty(data.get(f))
    ]
    sources = data.get("sources") or {}
    for field in ("symptoms_en", "months", "recipe_slugs", "escalate_if", "management_en"):
        if not _empty(data.get(field)) and not _has_source(sources, field):
            missing.append(f"source:{field}")
    return missing


def rule_missing(data: dict[str, Any]) -> list[str]:
    return ["field:params"] if _empty(data.get("params")) else []


@dataclass(frozen=True)
class ApprovalCheck:
    allowed: bool
    reason: str | None = None


def can_approve(
    *,
    status: str,
    approver_id: object,
    submitted_by: object,
    submitted_at: datetime | None,
    now: datetime,
    self_approve_after: timedelta,
) -> ApprovalCheck:
    """A different agronomist approves, or the submitter after a waiting period (spec 6)."""
    if status != "in_review":
        return ApprovalCheck(False, "not_in_review")
    too_soon = submitted_at is None or now - submitted_at < self_approve_after
    if approver_id == submitted_by and too_soon:
        return ApprovalCheck(False, "self_approval_too_soon")
    return ApprovalCheck(True)


def _unchecked(sources: dict[str, Any], prefix: str = "") -> list[str]:
    return [
        f"unchecked:{prefix}{field}"
        for field, entries in sources.items()
        if not entries or any(not (e.get("quote") and e.get("checked_on")) for e in entries)
    ]


def unchecked_sources(data: dict[str, Any]) -> list[str]:
    """Fields whose sources were not confirmed by the AI check (quote + checked_on), including
    regional sources. Empty = every cited value was found in its source."""
    problems = _unchecked(data.get("sources") or {})
    for region, values in (data.get("regional") or {}).items():
        problems += _unchecked(values.get("sources") or {}, f"{region}.")
    return problems
