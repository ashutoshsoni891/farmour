"""Curated lookup data for site intelligence (backend/seeds/site)."""

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site import repository as repo
from app.modules.site.models import CostNorm, DistrictRegion, Kvk, Scheme

SEED_DIR = Path(__file__).resolve().parents[3] / "seeds" / "site"


async def load(session: AsyncSession) -> dict[str, int]:
    data = json.loads((SEED_DIR / "district_regions.json").read_text(encoding="utf-8"))
    region = await repo.region_by_slug(session, data["region"])
    if region is None:
        return {"districts": 0}
    added = 0
    for district in data["districts"]:
        result = await session.execute(
            insert(DistrictRegion)
            .values(state=data["state"], district=district, region_id=region.id)
            .on_conflict_do_nothing(index_elements=["state", "district"])
        )
        added += int(getattr(result, "rowcount", 0) or 0)
    return {"districts": added}


def _checked(sources: dict[str, Any]) -> tuple[bool, date | None]:
    entries = [e for group in sources.values() for e in group]
    dates = [e.get("checked_on") for e in entries]
    ok = bool(entries) and all(e.get("quote") and e.get("checked_on") for e in entries)
    return ok, min(date.fromisoformat(d) for d in dates) if ok and dates else None


async def load_schemes(session: AsyncSession) -> dict[str, int]:
    """Schemes from seeds/site/schemes.json. A scheme whose every source was checked is
    `ai_verified`; entries an agronomist has taken into review or approved are left alone."""
    path = SEED_DIR / "schemes.json"
    if not path.exists():
        return {"schemes": 0}
    counts = {"schemes_ai_verified": 0, "schemes_draft": 0, "schemes_skipped": 0}
    fields = (
        "level", "state", "benefit_type", "name_en", "name_hi", "gives_en", "gives_hi",
        "eligibility_en", "eligibility_hi", "documents", "apply_en", "apply_hi", "apply_url",
        "rule", "sources",
    )  # fmt: skip
    for item in json.loads(path.read_text(encoding="utf-8"))["schemes"]:
        row = await session.scalar(select(Scheme).where(Scheme.code == item["code"]))
        if row is not None and row.status not in ("draft", "ai_verified"):
            counts["schemes_skipped"] += 1
            continue
        ok, checked_on = _checked(item.get("sources", {}))
        values = {f: item.get(f) for f in fields}
        values.update(status="ai_verified" if ok else "draft", checked_on=checked_on)
        if values["documents"] is None:
            values["documents"] = []
        if row is None:
            session.add(Scheme(code=item["code"], **values))
        else:
            for k, v in values.items():
                setattr(row, k, v)
        counts["schemes_ai_verified" if ok else "schemes_draft"] += 1
    await session.flush()
    return counts


async def load_cost_norms(session: AsyncSession) -> dict[str, int]:
    """Cost norms from seeds/site/cost_norms.json, loaded like the schemes: a norm whose every
    source was checked is `ai_verified`; entries in review, approved or retired are left alone."""
    path = SEED_DIR / "cost_norms.json"
    if not path.exists():
        return {"cost_norms": 0}
    counts = {"cost_norms_ai_verified": 0, "cost_norms_draft": 0, "cost_norms_skipped": 0}
    fields = (
        "group", "name_en", "name_hi", "unit", "tiers", "subsidy_pct", "subsidy_max_qty", "tags",
        "note_en", "note_hi", "sources",
    )  # fmt: skip
    for item in json.loads(path.read_text(encoding="utf-8"))["cost_norms"]:
        row = await session.scalar(select(CostNorm).where(CostNorm.code == item["code"]))
        if row is not None and row.status not in ("draft", "ai_verified"):
            counts["cost_norms_skipped"] += 1
            continue
        ok, checked_on = _checked(item.get("sources", {}))
        values = {f: item.get(f) for f in fields}
        values.update(status="ai_verified" if ok else "draft", checked_on=checked_on)
        values["tags"] = values["tags"] or []
        if row is None:
            session.add(CostNorm(code=item["code"], **values))
        else:
            for k, v in values.items():
                setattr(row, k, v)
        counts["cost_norms_ai_verified" if ok else "cost_norms_draft"] += 1
    await session.flush()
    return counts


async def load_kvks(session: AsyncSession) -> dict[str, int]:
    """KVK directory from seeds/site/kvks.json, loaded like the cost norms."""
    path = SEED_DIR / "kvks.json"
    if not path.exists():
        return {"kvks": 0}
    counts = {"kvks_ai_verified": 0, "kvks_draft": 0, "kvks_skipped": 0}
    fields = ("district", "state", "address_en", "phones", "email", "sources")
    for item in json.loads(path.read_text(encoding="utf-8"))["kvks"]:
        row = await session.scalar(select(Kvk).where(Kvk.code == item["code"]))
        if row is not None and row.status not in ("draft", "ai_verified"):
            counts["kvks_skipped"] += 1
            continue
        ok, checked_on = _checked(item.get("sources", {}))
        values = {f: item.get(f) for f in fields}
        values.update(status="ai_verified" if ok else "draft", checked_on=checked_on)
        values["phones"] = values["phones"] or []
        if row is None:
            session.add(Kvk(code=item["code"], **values))
        else:
            for k, v in values.items():
                setattr(row, k, v)
        counts["kvks_ai_verified" if ok else "kvks_draft"] += 1
    await session.flush()
    return counts
