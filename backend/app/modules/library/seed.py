"""Load seed files (backend/seeds/library/*.json) into the library as drafts.

Safe to re-run: entries that are in review, approved or retired are never touched, and for
drafts only empty fields are filled, so an agronomist's edits survive.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library import repository as repo
from app.modules.library.models import Crop, Recipe, Rule

SEED_DIR = Path(__file__).resolve().parents[3] / "seeds" / "library"


def _empty(v: Any) -> bool:
    return v is None or v in ([], {}, "")


def _fill(entry: Any, values: dict[str, Any]) -> bool:
    """Set values on an existing draft only where it is still empty."""
    changed = False
    for key, value in values.items():
        if _empty(getattr(entry, key, None)) and not _empty(value):
            setattr(entry, key, value)
            changed = True
    return changed


def read_research(seed_dir: Path = SEED_DIR) -> dict[str, dict[str, Any]]:
    """AI research files, one per crop: {slug: values in the CropUpdate shape}."""
    folder = seed_dir / "research" / "crops"
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))
    }


async def load(session: AsyncSession, seed_dir: Path = SEED_DIR) -> dict[str, int]:
    counts = {"created": 0, "updated": 0, "skipped": 0}

    def read(name: str, key: str) -> list[dict[str, Any]]:
        path = seed_dir / name
        return list(json.loads(path.read_text(encoding="utf-8"))[key]) if path.exists() else []

    for values in read("crops.json", "crops"):
        existing = await repo.get_crop_by_slug(session, values["slug"])
        if existing is None:
            session.add(Crop(**values, todo=["TODO(agronomist): agronomy values"]))
            counts["created"] += 1
        elif existing.status == "draft":
            counts["updated" if _fill(existing, values) else "skipped"] += 1
        else:
            counts["skipped"] += 1

    for values in read("recipes.json", "recipes"):
        recipe = await repo.get_recipe_by_slug(session, values["slug"])
        if recipe is None:
            session.add(Recipe(**values, todo=["TODO(agronomist): ingredients, quantities, steps"]))
            counts["created"] += 1
        elif recipe.status == "draft":
            counts["updated" if _fill(recipe, values) else "skipped"] += 1
        else:
            counts["skipped"] += 1

    for values in read("rules.json", "rules"):
        rule = await repo.get_rule_by_code(session, values["code"])
        if rule is None:
            session.add(Rule(**values))
            counts["created"] += 1
        else:
            counts["skipped"] += 1

    await session.flush()
    return counts
