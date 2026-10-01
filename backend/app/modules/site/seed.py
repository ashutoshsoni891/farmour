"""Curated lookup data for site intelligence (backend/seeds/site)."""

import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site import repository as repo
from app.modules.site.models import DistrictRegion

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
