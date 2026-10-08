"""Public entry point of the site module: build, read and confirm a farm's site profile."""

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.geocode import get_geocoder
from app.adapters.mandi import get_mandi_source
from app.adapters.routing import RouteResult, get_router, haversine_km
from app.adapters.sitedata import Fact, SiteContext, active_sources
from app.core import audit, rate_limit
from app.core.errors import AppError
from app.core.queue import enqueue
from app.core.settings_store import get_setting
from app.modules.farms.service import Membership, farm_location
from app.modules.parcel.service import parcel_summary, set_site_options
from app.modules.site import repository as repo
from app.modules.site.models import SiteFact
from app.modules.site.schemas import (
    Answer,
    AnswerBatch,
    BuildOut,
    CostNormOut,
    FactOut,
    Group,
    KvkOut,
    MarketCentreOut,
    ProfileOut,
    SchemeOut,
    SchemeSource,
)

log = logging.getLogger(__name__)

GROUPS: dict[str, Group] = {
    "region": "region", "soil": "soil_land", "terrain": "soil_land", "climate": "climate",
    "water": "water", "markets": "markets", "nearby": "nearby",
}  # fmt: skip
# Facts a user answer is copied onto the parcel, which the design engine reads.
PARCEL_KEYS = {"soil.type": "soil_type", "soil.drainage": "drainage"}
TASK = "site.build_profile"


def group_of(key: str) -> Group:
    return GROUPS.get(key.split(".")[0], "soil_land")


def _fact_to_dict(f: Fact) -> dict[str, Any]:
    return {
        "key": f.key, "value": f.value, "unit": f.unit, "source": f.source, "method": f.method,
        "confidence": f.confidence, "attribution": f.attribution,
        "fetched_at": f.fetched_at.isoformat(), "expires_at": f.expires_at.isoformat(),
    }  # fmt: skip


def _row(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": f["key"], "value": f["value"], "unit": f["unit"], "source": f["source"],
        "method": f["method"], "confidence": round(float(f["confidence"]), 2),
        "attribution": f["attribution"],
        "fetched_at": datetime.fromisoformat(f["fetched_at"]),
        "expires_at": datetime.fromisoformat(f["expires_at"]),
    }  # fmt: skip


def _fresh(payload: Any) -> bool:
    now = datetime.now(UTC)
    return bool(payload) and all(datetime.fromisoformat(f["expires_at"]) > now for f in payload)


# ------------------------------------------------------------------ building


async def _local_facts(
    session: AsyncSession, ctx: SiteContext, state: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Facts from our own curated tables and ingested prices (no outside calls except routing)."""
    out: list[dict[str, Any]] = []
    report: dict[str, Any] = {}
    now = datetime.now(UTC)

    def add(key: str, value: Any, source: str, method: str, conf: float, **kw: Any) -> None:
        out.append({
            "key": key, "value": value, "unit": kw.get("unit"), "source": source,
            "method": method, "confidence": conf, "attribution": kw.get("attribution"),
            "fetched_at": now, "expires_at": None,
        })  # fmt: skip

    if ctx.district:
        region = await repo.region_for_district(session, state, ctx.district)
        if region:
            add("region", {"slug": region.slug, "name_en": region.name_en, "name_hi": region.name_hi},
                "district_table", "district_lookup", 0.9)  # fmt: skip
        water = await repo.groundwater_for_district(session, state, ctx.district)
        if water:
            add("water.groundwater_class", {"category": water.category, "year": water.assessed_year},
                "cgwb", "district_lookup", 0.6, attribution=water.source_url)  # fmt: skip
        report["lookups"] = {"region": bool(region), "groundwater": bool(water)}

    count = int(await get_setting(session, "site.nearest_mandis"))
    mandis = await repo.mandis_with_location(session, state)
    router = get_router()
    factor = float(await get_setting(session, "site.road_factor"))

    async def route(lat: float, lng: float) -> RouteResult:
        found = await router.route((ctx.lat, ctx.lng), (lat, lng))
        if found:
            return found
        km = round(haversine_km((ctx.lat, ctx.lng), (lat, lng)) * factor, 1)
        return RouteResult(km, round(km / 40 * 60), "straight_line")

    if mandis:
        near = sorted(mandis, key=lambda m: haversine_km((ctx.lat, ctx.lng), (float(m.lat or 0), float(m.lng or 0))))[:count]  # fmt: skip
        routes = await asyncio.gather(*[route(float(m.lat or 0), float(m.lng or 0)) for m in near])
        value = [
            {"name": m.name, "district": m.district, "distance_km": r.distance_km,
             "minutes": r.minutes, "method": r.method}
            for m, r in zip(near, routes, strict=True)
        ]  # fmt: skip
        road = all(r.method == "osrm" for r in routes)
        add("markets.nearest", value, "mandis", "osrm" if road else "straight_line", 0.7 if road else 0.3)  # fmt: skip
    refs: list[dict[str, Any]] = list(await get_setting(session, "site.reference_points"))
    if refs:
        routes = await asyncio.gather(*[route(float(r["lat"]), float(r["lng"])) for r in refs])
        value = [
            {"key": r["key"], "name": r["name"], "distance_km": x.distance_km, "minutes": x.minutes,
             "method": x.method}
            for r, x in zip(refs, routes, strict=True)
        ]  # fmt: skip
        road = all(x.method == "osrm" for x in routes)
        add("markets.reference", value, "routing", "osrm" if road else "straight_line", 0.7 if road else 0.3)  # fmt: skip
    return out, report


async def build_profile(session: AsyncSession, farm_id: uuid.UUID) -> dict[str, Any]:
    """Collect site facts for a farm. Partial results are fine; no source may block setup."""
    loc = await farm_location(session, farm_id)
    if loc is None:
        return {"status": "skipped", "reason": "no location"}
    parcel = await parcel_summary(session, farm_id)
    state = str(await get_setting(session, "site.default_state"))
    ctx = SiteContext(
        lat=parcel.lat if parcel else loc.lat, lng=parcel.lng if parcel else loc.lng,
        area_sqm=parcel.area_sqm if parcel else None, district=loc.district, state=state,
    )  # fmt: skip
    build = await repo.start_build(session, farm_id)
    await session.commit()  # make "running" visible while the sources are called

    budget = float(await get_setting(session, "site.build_budget_s"))
    cell = f"{ctx.lat:.2f}:{ctx.lng:.2f}"
    sources = active_sources()
    report: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []

    to_fetch = []
    for src in sources:
        cached = await repo.get_cache(session, cell, src.name)
        if cached and _fresh(cached.payload):
            rows += [_row(f) for f in cached.payload]
            report[src.name] = {"ok": True, "cached": True, "facts": len(cached.payload)}
        else:
            to_fetch.append(src)

    started = time.monotonic()
    tasks = {asyncio.ensure_future(s.fetch(ctx)): s for s in to_fetch}
    if tasks:
        # Keep 3 s of the budget for the local lookups and routing that follow.
        done, pending = await asyncio.wait(tasks, timeout=max(budget - 3, 1))
        for t in pending:
            t.cancel()
            report[tasks[t].name] = {"ok": False, "error": "timeout"}
        for t in done:
            src = tasks[t]
            try:
                facts = t.result()
            except Exception as exc:
                log.warning("site source %s failed: %s", src.name, type(exc).__name__)
                report[src.name] = {"ok": False, "error": type(exc).__name__}
                continue
            report[src.name] = {"ok": bool(facts), "facts": len(facts), "cached": False}
            if facts:
                payload = [_fact_to_dict(f) for f in facts]
                await repo.put_cache(session, cell, src.name, payload)
                rows += [_row(p) for p in payload]
    report["elapsed_s"] = round(time.monotonic() - started, 1)

    local, local_report = await _local_facts(session, ctx, state)
    rows += local
    report.update(local_report)

    written = 0
    for row in rows:
        if await repo.upsert_derived(session, farm_id, row):
            written += 1
    build = (await repo.get_build(session, farm_id)) or build
    build.status = "done" if written else "failed"
    build.finished_at = datetime.now(UTC)
    build.report = report
    await session.flush()
    return {"status": build.status, "facts": written, "report": report}


# ------------------------------------------------------------------ reading


def _winning(facts: list[SiteFact]) -> list[SiteFact]:
    """One value per key: the owner's answer, then a soil test, then the newest derived fact."""
    by_key: dict[str, list[SiteFact]] = {}
    for f in facts:
        by_key.setdefault(f.key, []).append(f)
    out = []
    for key_facts in by_key.values():
        user = [f for f in key_facts if f.source in repo.USER_SOURCES]
        pool = user or key_facts
        pool = sorted(pool, key=lambda f: (f.source == "soil_test", f.fetched_at), reverse=True)
        best = pool[0]
        if best.status != "rejected":
            out.append(best)
    return out


def _questions(winning: list[SiteFact], threshold: float, has_data: bool) -> list[str]:
    """Only ask what changes the plan and is not known well (spec 17)."""
    by_key = {f.key: f for f in winning}
    asks = []
    soil = by_key.get("soil.type")
    if soil is None or (float(soil.confidence) < threshold and soil.status == "derived"):
        asks.append("soil.type")
    soil_clay = soil is not None and soil.value in ("clay", "black")
    if "soil.drainage" not in by_key and (soil is None or soil_clay):
        asks.append("soil.drainage")
    del has_data
    return asks


async def get_profile(session: AsyncSession, m: Membership) -> ProfileOut:
    facts = _winning(await repo.facts_for_farm(session, m.farm_id))
    threshold = float(await get_setting(session, "site.low_confidence"))
    build = await repo.get_build(session, m.farm_id)
    out = [
        FactOut(
            key=f.key, group=group_of(f.key), value=f.value, unit=f.unit, source=f.source,
            method=f.method, confidence=float(f.confidence), status=f.status,
            fetched_at=f.fetched_at, attribution=f.attribution,
        )
        for f in sorted(facts, key=lambda f: f.key)
    ]  # fmt: skip
    return ProfileOut(
        build=BuildOut(
            status=build.status if build else "none",
            finished_at=build.finished_at if build else None,
            sources=build.report if build else {},
        ),
        facts=out,
        questions=_questions(facts, threshold, bool(out)),
        attributions=sorted(
            {f.attribution for f in out if f.attribution and f.source != "district_table"}
        ),
    )


# ------------------------------------------------------------------ answering


async def answer(session: AsyncSession, m: Membership, batch: AnswerBatch) -> ProfileOut:
    current = {f.key: f for f in _winning(await repo.facts_for_farm(session, m.farm_id))}
    soil_updates: dict[str, str] = {}
    for item in batch.items:
        await _apply(session, m, item, current)
        if item.key in PARCEL_KEYS and item.action in ("confirm", "edit"):
            value = item.value if item.action == "edit" else current[item.key].value
            if value is not None:
                soil_updates[PARCEL_KEYS[item.key]] = str(value)
    if soil_updates:
        await set_site_options(session, m.farm_id, **soil_updates)
    return await get_profile(session, m)


async def _apply(
    session: AsyncSession, m: Membership, item: Answer, current: dict[str, SiteFact]
) -> None:
    if item.action == "confirm":
        fact = current.get(item.key)
        if fact is None:
            raise AppError("UNKNOWN_FACT", 422, {"key": item.key})
        saved = await repo.save_user_fact(
            session, m.farm_id, key=item.key, value=fact.value, status="confirmed", unit=fact.unit
        )
    elif item.action == "edit":
        if item.value is None:
            raise AppError("VALUE_REQUIRED", 422, {"key": item.key})
        saved = await repo.save_user_fact(
            session, m.farm_id, key=item.key, value=item.value, status="edited"
        )
    else:
        saved = await repo.save_user_fact(
            session, m.farm_id, key=item.key, value=None, status="rejected"
        )
    await audit.record(
        session, actor_id=m.user_id, entity="site_fact", entity_id=saved.id, action=item.action,
        after={"key": item.key},
    )  # fmt: skip


async def request_refresh(session: AsyncSession, m: Membership) -> None:
    await rate_limit.enforce(f"site-refresh:{m.farm_id}", limit=3, window_seconds=600)
    enqueue(TASK, str(m.farm_id))


def queue_build(farm_id: uuid.UUID) -> None:
    enqueue(TASK, str(farm_id))


# ------------------------------------------------------------------ price ingest


async def ingest_mandi_prices(session: AsyncSession) -> dict[str, Any]:
    """Pull Agmarknet prices for the state into our tables and locate new mandis (spec 17)."""
    source = get_mandi_source()
    if source is None:
        log.info("mandi ingest skipped: no DATA_GOV_IN_API_KEY")
        return {"skipped": "no_api_key"}
    state = str(await get_setting(session, "site.default_state"))
    pages = int(await get_setting(session, "site.mandi_ingest_max_pages"))
    rows = await source.fetch(state, max_pages=pages)
    ids: dict[tuple[str, str], uuid.UUID] = {}
    values: list[dict[str, Any]] = []
    for r in rows:
        if not r.market or not r.commodity:
            continue
        key = (r.market, r.district)
        if key not in ids:
            ids[key] = await repo.upsert_mandi(session, r.market, r.district, state)

        def paise(rupees: float | None) -> int | None:
            return None if rupees is None else round(rupees * 100)

        values.append({
            "id": uuid.uuid4(), "mandi_id": ids[key], "commodity": r.commodity, "variety": r.variety,
            "price_date": r.price_date, "min_paise": paise(r.min_rupees_per_quintal),
            "max_paise": paise(r.max_rupees_per_quintal), "modal_paise": paise(r.modal_rupees_per_quintal),
            "unit": "quintal",
        })  # fmt: skip
    inserted = 0
    for i in range(0, len(values), 500):
        inserted += await repo.upsert_prices(session, values[i : i + 500])
    located = await locate_mandis(session, state, limit=15)
    return {"rows": len(rows), "new_prices": inserted, "mandis": len(ids), "located": located}


async def locate_mandis(session: AsyncSession, state: str, *, limit: int) -> int:
    """Find coordinates for newly seen mandis (Nominatim, politely, a few per run)."""
    geocoder = get_geocoder()
    found = 0
    for mandi in await repo.mandis_to_geocode(session, limit):
        mandi.geocode_tried = True
        try:
            places = await geocoder.search(
                f"{mandi.name} mandi, {mandi.district}, {state}", lang="en", limit=1
            )
        except Exception as exc:
            log.info("mandi geocode failed: %s", type(exc).__name__)
            continue
        if places and 21.0 <= places[0].lat <= 27.0 and 73.0 <= places[0].lng <= 83.5:
            mandi.lat, mandi.lng = Decimal(str(places[0].lat)), Decimal(str(places[0].lng))
            found += 1
    await session.flush()
    return found


async def load_seed(session: AsyncSession) -> dict[str, int]:
    """Load curated lookups (district -> region). Safe to re-run."""
    from app.modules.site import seed

    counts = await seed.load(session)
    counts.update(await seed.load_schemes(session))
    counts.update(await seed.load_cost_norms(session))
    counts.update(await seed.load_kvks(session))
    counts.update(await seed.load_market_centres(session))
    return counts


def scheme_matches(
    rule: dict[str, Any], tags: set[str], farm: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Does a scheme's structured rule match this plan and farm? Returns (match, conditions the
    owner must still check). Unknown farm facts do not exclude a scheme; they become conditions."""
    wanted = set(rule.get("tags_any", []))
    if wanted and not (wanted & tags or "all" in wanted):
        return False, []
    conditions: list[str] = []
    for group in ("farm", "farm_any"):
        for key, allowed in (rule.get(group) or {}).items():
            value = farm.get(key)
            if value is None:
                conditions.append(f"check.{key}")
            elif value not in allowed:
                return False, []
            else:
                conditions.append(f"farm:{key}")
    if rule.get("needs_land_in_name"):
        conditions.append("check.land_in_name")
    return True, conditions


async def schemes_for(
    session: AsyncSession, tags: set[str], farm: dict[str, Any]
) -> list[SchemeOut]:
    """Schemes the farm may be eligible for, given its plan (tags) and facts. Shown as "may be
    eligible": the department decides. AI-checked and approved entries only."""
    state = str(await get_setting(session, "site.default_state"))
    out = []
    for row in await repo.schemes(session, ["ai_verified", "approved"]):
        if row.state and row.state != state:
            continue
        ok, conditions = scheme_matches(row.rule, tags, farm)
        if not ok:
            continue
        farm_reasons = [c for c in conditions if c.startswith("farm:")]
        conditions = [c for c in conditions if not c.startswith("farm:")]
        reasons = sorted((set(row.rule.get("tags_any", [])) & tags) - {"all"}) + farm_reasons
        reasons = reasons or ["all"]
        out.append(
            SchemeOut(
                code=row.code, level=row.level, state=row.state, benefit_type=row.benefit_type,
                name_en=row.name_en, name_hi=row.name_hi, gives_en=row.gives_en,
                gives_hi=row.gives_hi, eligibility_en=row.eligibility_en,
                eligibility_hi=row.eligibility_hi, documents=row.documents,
                apply_en=row.apply_en, apply_hi=row.apply_hi, apply_url=row.apply_url,
                sources=[
                    SchemeSource(url=e.get("url"), title=e.get("title", ""))
                    for group in row.sources.values() for e in group
                ],
                checked_on=row.checked_on, ai_checked=row.status == "ai_verified",
                reasons=reasons, conditions=conditions,
            )
        )  # fmt: skip
    order = {"direct_benefit": 0, "subsidy": 1, "interest_rebate": 2, "insurance": 3,
             "loan": 4, "training": 5}  # fmt: skip
    return sorted(out, key=lambda x: (order.get(x.benefit_type, 9), x.code))


async def list_cost_norms(session: AsyncSession) -> list[CostNormOut]:
    """Setup costs and subsidy rates (government cost norms) that are cited and checked."""
    out = []
    for row in await repo.cost_norms(session, ["ai_verified", "approved"]):
        entries = [e for group in row.sources.values() for e in group]
        out.append(
            CostNormOut.model_validate(
                {
                    **{n: getattr(row, n) for n in CostNormOut.model_fields if hasattr(row, n)},
                    "sources": [SchemeSource.model_validate(e) for e in entries],
                    "ai_checked": row.status == "ai_verified",
                }
            )
        )
    return out


async def list_kvks(session: AsyncSession, district: str | None = None) -> list[KvkOut]:
    """Krishi Vigyan Kendras whose listing was checked against its source, optionally by district."""
    out = []
    for row in await repo.kvks(session, ["ai_verified", "approved"], district):
        entries = [e for group in row.sources.values() for e in group]
        out.append(
            KvkOut.model_validate(
                {
                    **{n: getattr(row, n) for n in KvkOut.model_fields if hasattr(row, n)},
                    "sources": [SchemeSource.model_validate(e) for e in entries],
                    "ai_checked": row.status == "ai_verified",
                }
            )
        )
    return out


async def list_market_centres(session: AsyncSession) -> list[MarketCentreOut]:
    """Herb mandis and portals whose listing was checked against its source."""
    out = []
    for row in await repo.market_centres(session, ["ai_verified", "approved"]):
        entries = [e for group in row.sources.values() for e in group]
        out.append(
            MarketCentreOut.model_validate(
                {
                    **{n: getattr(row, n) for n in MarketCentreOut.model_fields if hasattr(row, n)},
                    "sources": [SchemeSource.model_validate(e) for e in entries],
                    "ai_checked": row.status == "ai_verified",
                }
            )
        )
    return out
