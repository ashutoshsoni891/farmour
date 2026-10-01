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

CROP_ALWAYS = ["family", "seasons", "sun", "water_need"]
CROP_BED = [
    "days_to_first_harvest", "harvest_span_days", "spacing_plant_cm", "height_max_cm",
    "expected_yield_kg_per_sqm", "terrace_ok", "waterlogging_tolerant",
]  # fmt: skip
CROP_TREE = ["tree_spacing_m", "canopy_diameter_m", "years_to_bear", "height_max_cm"]
CROP_FIELD = ["days_to_first_harvest", "spacing_row_cm", "spacing_plant_cm",
              "expected_yield_kg_per_sqm"]  # fmt: skip
TREE_CATEGORIES = {"fruit_tree"}


def _empty(v: Any) -> bool:
    return v is None or v == [] or v == {} or v == ""


def _has_source(sources: dict[str, Any], field: str) -> bool:
    return bool(sources.get(field))


def crop_missing(data: dict[str, Any], region_slug: str) -> list[str]:
    """Reasons the crop can't go to review, as keys like 'field:x' or 'source:x'."""
    required = list(CROP_ALWAYS)
    if data.get("category") in TREE_CATEGORIES:
        required += CROP_TREE
    elif data.get("layers"):
        required += CROP_BED
    else:
        required += CROP_FIELD
    missing = [f"field:{f}" for f in dict.fromkeys(required) if _empty(data.get(f))]

    seasons = data.get("seasons") or []
    regional = (data.get("regional") or {}).get(region_slug) or {}
    if seasons and seasons != ["perennial"]:
        if _empty(regional.get("sow_windows")):
            missing.append(f"field:sow_windows.{region_slug}")
        elif not _has_source(regional.get("sources") or {}, "sow_windows"):
            missing.append(f"source:sow_windows.{region_slug}")

    sources = data.get("sources") or {}
    for field, value in data.items():
        if field in IDENTITY_FIELDS or _empty(value):
            continue
        if not _has_source(sources, field):
            missing.append(f"source:{field}")
    return missing


def recipe_missing(data: dict[str, Any]) -> list[str]:
    missing = [
        f"field:{f}"
        for f in ("ingredients", "per_area_sqm", "steps_en", "steps_hi", "apply_method")
        if _empty(data.get(f))
    ]
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
    for field in ("symptoms_en", "months", "recipe_slugs", "escalate_if"):
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
