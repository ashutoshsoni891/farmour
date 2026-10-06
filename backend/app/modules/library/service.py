"""Public entry point of the library module: crops, recipes, pests, rules and the review flow."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit, events
from app.core.errors import AppError, not_found
from app.core.settings_store import get_int, get_setting
from app.modules.identity.schemas import Principal
from app.modules.library import repository as repo
from app.modules.library import workflow
from app.modules.library.models import Companion, Crop, Pest, Recipe, Rule
from app.modules.library.schemas import (
    CompanionIn,
    CompanionOut,
    CropCreate,
    CropName,
    CropOut,
    CropSummary,
    CropUpdate,
    EngineCompanion,
    EngineCrop,
    Page,
    PestCreate,
    PestFields,
    PestOut,
    RecipeCreate,
    RecipeFields,
    RecipeOut,
    ReviewItem,
    RuleOut,
    RuleUpdate,
)

CROP_EDITABLE = [f for f in CropUpdate.model_fields if f != "regional"]
RECIPE_EDITABLE = list(RecipeFields.model_fields)
APPROVED = ["approved"]
ALL_STATUSES = ["draft", "ai_verified", "in_review", "approved", "retired"]
OPEN = ("draft", "ai_verified", "in_review")  # statuses that show what is still missing


def _statuses(principal: Principal) -> list[str]:
    return ALL_STATUSES if principal.is_agronomist else APPROVED


def _need_agronomist(principal: Principal) -> None:
    if not principal.is_agronomist:
        raise AppError("FORBIDDEN_ROLE", 403)


def _dump(model: Any) -> dict[str, Any]:
    """Pydantic model -> JSON-safe dict with only the fields the caller set."""
    return dict(model.model_dump(mode="json", exclude_unset=True, by_alias=True))


async def _default_region(session: AsyncSession) -> str:
    return str(await get_setting(session, "library.default_region"))


# ---------------------------------------------------------------- crops


async def _crop_data(session: AsyncSession, crop: Crop) -> dict[str, Any]:
    slugs = await repo.region_slugs(session)
    regional = {}
    for row in (await repo.regional_for(session, [crop.id])).get(crop.id, []):
        regional[slugs[row.region_id]] = {
            "sow_windows": row.sow_windows,
            "agmarknet_commodity": row.agmarknet_commodity,
            "price_mandi_paise_per_kg": row.price_mandi_paise_per_kg,
            "price_direct_paise_per_kg": row.price_direct_paise_per_kg,
            "price_updated_on": row.price_updated_on,
            "sources": row.sources,
        }
    data = {name: getattr(crop, name) for name in CROP_EDITABLE}
    data["regional"] = regional
    return data


async def _crop_out(session: AsyncSession, crop: Crop, *, with_missing: bool) -> CropOut:
    missing: list[str] = []
    if with_missing and crop.status in OPEN:
        missing = workflow.crop_missing(
            await _crop_data(session, crop), await _default_region(session)
        )
    data = {name: getattr(crop, name) for name in CropOut.model_fields if hasattr(crop, name)}
    data["regional"] = (await _crop_data(session, crop))["regional"]
    data["missing_for_review"] = missing
    return CropOut.model_validate(data)


async def list_crops(
    session: AsyncSession,
    principal: Principal,
    *,
    status: str | None,
    q: str | None,
    category: str | None,
    cursor: str | None,
    limit: int,
) -> Page[CropSummary]:
    statuses = _statuses(principal)
    if status:
        statuses = [s for s in statuses if s == status]
    crops = await repo.list_crops(
        session, statuses=statuses, q=q, category=category, after=cursor, limit=limit + 1
    )
    page = crops[:limit]
    items = [
        CropSummary(
            id=c.id, slug=c.slug, name_en=c.name_en, name_hi=c.name_hi,
            category=c.category, layers=c.layers, status=c.status,
            revision=c.revision, todo_count=len(c.todo), updated_at=c.updated_at,
        )
        for c in page
    ]  # fmt: skip
    return Page[CropSummary](items=items, next_cursor=page[-1].slug if len(crops) > limit else None)


async def get_crop(session: AsyncSession, principal: Principal, crop_id: uuid.UUID) -> CropOut:
    crop = await repo.get_crop(session, crop_id)
    if crop is None or crop.status not in _statuses(principal):
        raise not_found("crop")
    return await _crop_out(session, crop, with_missing=principal.is_agronomist)


async def _apply_crop_fields(
    session: AsyncSession, crop: Crop, changes: dict[str, Any], actor: uuid.UUID | None
) -> None:
    regional = changes.pop("regional", None)
    for field, value in changes.items():
        setattr(crop, field, value)
    await session.flush()
    for slug, values in (regional or {}).items():
        region = await repo.region_by_slug(session, slug)
        if region is None:
            raise AppError("UNKNOWN_REGION", 422, {"region": slug})
        await repo.upsert_regional(session, crop.id, region.id, values)


async def create_crop(session: AsyncSession, principal: Principal, data: CropCreate) -> CropOut:
    _need_agronomist(principal)
    if await repo.get_crop_by_slug(session, data.slug) is not None:
        raise AppError("SLUG_IN_USE", 409)
    changes = _dump(data)
    regional = changes.pop("regional", None)
    crop = Crop(id=uuid.uuid4(), created_by=principal.user_id, **changes)
    await repo.add_all(session, crop)
    if regional:
        await _apply_crop_fields(session, crop, {"regional": regional}, principal.user_id)
    await audit.record(
        session, actor_id=principal.user_id, entity="crop", entity_id=crop.id, action="create"
    )
    return await _crop_out(session, crop, with_missing=True)


async def update_crop(
    session: AsyncSession, principal: Principal, crop_id: uuid.UUID, data: CropUpdate
) -> CropOut:
    _need_agronomist(principal)
    crop = await repo.get_crop(session, crop_id)
    if crop is None:
        raise not_found("crop")
    if crop.status == "retired":
        raise AppError("ENTRY_RETIRED", 409)
    before = await _crop_data(session, crop)
    await _apply_crop_fields(session, crop, _dump(data), principal.user_id)
    _back_to_draft(crop)
    await audit.record(
        session, actor_id=principal.user_id, entity="crop", entity_id=crop.id, action="update",
        before={k: str(v) for k, v in before.items() if v not in (None, [], {})}, reason=None,
    )  # fmt: skip
    await session.flush()
    await session.refresh(crop)
    return await _crop_out(session, crop, with_missing=True)


def _back_to_draft(entry: Crop | Recipe | Pest | Rule) -> None:
    """Editing an approved, AI-checked or in-review entry reopens it; plans keep their pinned
    revision."""
    if entry.status in ("approved", "ai_verified", "in_review"):
        entry.status = "draft"
        entry.submitted_by = entry.submitted_at = None


# ---------------------------------------------------------------- recipes


def _recipe_out(recipe: Recipe, *, with_missing: bool) -> RecipeOut:
    missing = []
    if with_missing and recipe.status in OPEN:
        missing = workflow.recipe_missing({n: getattr(recipe, n) for n in RECIPE_EDITABLE})
    data = {n: getattr(recipe, n) for n in RecipeOut.model_fields if hasattr(recipe, n)}
    data["missing_for_review"] = missing
    return RecipeOut.model_validate(data)


async def list_recipes(session: AsyncSession, principal: Principal) -> list[RecipeOut]:
    rows = await repo.list_recipes(session, _statuses(principal))
    return [_recipe_out(r, with_missing=principal.is_agronomist) for r in rows]


async def get_recipe(
    session: AsyncSession, principal: Principal, recipe_id: uuid.UUID
) -> RecipeOut:
    recipe = await repo.get_entity(session, "recipe", recipe_id)
    if not isinstance(recipe, Recipe) or recipe.status not in _statuses(principal):
        raise not_found("recipe")
    return _recipe_out(recipe, with_missing=principal.is_agronomist)


async def create_recipe(
    session: AsyncSession, principal: Principal, data: RecipeCreate
) -> RecipeOut:
    _need_agronomist(principal)
    if await repo.get_recipe_by_slug(session, data.slug) is not None:
        raise AppError("SLUG_IN_USE", 409)
    recipe = Recipe(id=uuid.uuid4(), created_by=principal.user_id, **_dump(data))
    await repo.add_all(session, recipe)
    await audit.record(
        session, actor_id=principal.user_id, entity="recipe", entity_id=recipe.id, action="create"
    )
    await session.refresh(recipe)
    return _recipe_out(recipe, with_missing=True)


async def update_recipe(
    session: AsyncSession, principal: Principal, recipe_id: uuid.UUID, data: RecipeFields
) -> RecipeOut:
    _need_agronomist(principal)
    recipe = await repo.get_entity(session, "recipe", recipe_id)
    if not isinstance(recipe, Recipe):
        raise not_found("recipe")
    if recipe.status == "retired":
        raise AppError("ENTRY_RETIRED", 409)
    for field, value in _dump(data).items():
        setattr(recipe, field, value)
    _back_to_draft(recipe)
    await audit.record(
        session, actor_id=principal.user_id, entity="recipe", entity_id=recipe.id, action="update"
    )
    await session.flush()
    await session.refresh(recipe)
    return _recipe_out(recipe, with_missing=True)


# ---------------------------------------------------------------- pests


async def _pest_out(session: AsyncSession, pest: Pest, *, with_missing: bool) -> PestOut:
    crops = {v: k for k, v in (await repo.crop_slug_map(session)).items()}
    recipes = {v: k for k, v in (await repo.recipe_slug_map(session)).items()}
    data = {n: getattr(pest, n) for n in PestOut.model_fields if hasattr(pest, n)}
    data["crop_slugs"] = [crops[c] for c in pest.crop_ids if c in crops]
    data["recipe_slugs"] = [recipes[r] for r in pest.recipe_ids if r in recipes]
    data["missing_for_review"] = (
        workflow.pest_missing(data) if with_missing and pest.status in OPEN else []
    )
    return PestOut.model_validate(data)


async def list_pests(session: AsyncSession, principal: Principal) -> list[PestOut]:
    rows = await repo.list_pests(session, _statuses(principal))
    return [await _pest_out(session, p, with_missing=principal.is_agronomist) for p in rows]


async def _pest_values(session: AsyncSession, changes: dict[str, Any]) -> dict[str, Any]:
    crops = await repo.crop_slug_map(session)
    recipes = await repo.recipe_slug_map(session)
    if "crop_slugs" in changes:
        unknown = [s for s in changes["crop_slugs"] if s not in crops]
        if unknown:
            raise AppError("UNKNOWN_CROP", 422, {"slugs": unknown})
        changes["crop_ids"] = [crops[s] for s in changes.pop("crop_slugs")]
    if "recipe_slugs" in changes:
        unknown = [s for s in changes["recipe_slugs"] if s not in recipes]
        if unknown:
            raise AppError("UNKNOWN_RECIPE", 422, {"slugs": unknown})
        changes["recipe_ids"] = [recipes[s] for s in changes.pop("recipe_slugs")]
    return changes


async def create_pest(session: AsyncSession, principal: Principal, data: PestCreate) -> PestOut:
    _need_agronomist(principal)
    if await repo.get_pest_by_slug(session, data.slug) is not None:
        raise AppError("SLUG_IN_USE", 409)
    pest = Pest(
        id=uuid.uuid4(), created_by=principal.user_id, **await _pest_values(session, _dump(data))
    )
    await repo.add_all(session, pest)
    await audit.record(
        session, actor_id=principal.user_id, entity="pest", entity_id=pest.id, action="create"
    )
    await session.refresh(pest)
    return await _pest_out(session, pest, with_missing=True)


async def update_pest(
    session: AsyncSession, principal: Principal, pest_id: uuid.UUID, data: PestFields
) -> PestOut:
    _need_agronomist(principal)
    pest = await repo.get_entity(session, "pest", pest_id)
    if not isinstance(pest, Pest):
        raise not_found("pest")
    if pest.status == "retired":
        raise AppError("ENTRY_RETIRED", 409)
    for field, value in (await _pest_values(session, _dump(data))).items():
        setattr(pest, field, value)
    _back_to_draft(pest)
    await audit.record(
        session, actor_id=principal.user_id, entity="pest", entity_id=pest.id, action="update"
    )
    await session.flush()
    await session.refresh(pest)
    return await _pest_out(session, pest, with_missing=True)


# ---------------------------------------------------------------- rules


def _rule_out(rule: Rule) -> RuleOut:
    data = {n: getattr(rule, n) for n in RuleOut.model_fields if hasattr(rule, n)}
    data["missing_for_review"] = workflow.rule_missing(data) if rule.status == "draft" else []
    return RuleOut.model_validate(data)


async def list_rules(session: AsyncSession, principal: Principal) -> list[RuleOut]:
    return [_rule_out(r) for r in await repo.list_rules(session, _statuses(principal))]


async def update_rule(
    session: AsyncSession, principal: Principal, rule_id: uuid.UUID, data: RuleUpdate
) -> RuleOut:
    _need_agronomist(principal)
    rule = await repo.get_entity(session, "rule", rule_id)
    if not isinstance(rule, Rule):
        raise not_found("rule")
    for field, value in _dump(data).items():
        setattr(rule, field, value)
    _back_to_draft(rule)
    await audit.record(
        session, actor_id=principal.user_id, entity="rule", entity_id=rule.id, action="update"
    )
    await session.flush()
    await session.refresh(rule)
    return _rule_out(rule)


# ---------------------------------------------------------------- companions


async def list_companions(session: AsyncSession, principal: Principal) -> list[CompanionOut]:
    slugs = {v: k for k, v in (await repo.crop_slug_map(session)).items()}
    return [
        CompanionOut(
            id=c.id, crop_a=slugs[c.crop_a], crop_b=slugs[c.crop_b], relation=c.relation,
            reason_en=c.reason_en, reason_hi=c.reason_hi, status=c.status,
            sources=c.sources,
        )
        for c in await repo.list_companions(session, _statuses(principal))
    ]  # fmt: skip


async def save_companion(
    session: AsyncSession, principal: Principal, data: CompanionIn
) -> CompanionOut:
    _need_agronomist(principal)
    crops = await repo.crop_slug_map(session)
    if data.crop_a not in crops or data.crop_b not in crops or data.crop_a == data.crop_b:
        raise AppError("UNKNOWN_CROP", 422)
    a, b = sorted((crops[data.crop_a], crops[data.crop_b]))
    row = await repo.get_companion_pair(session, a, b)
    values = {
        "relation": data.relation, "reason_en": data.reason_en, "reason_hi": data.reason_hi,
        "sources": data.model_dump(mode="json")["sources"], "status": "draft",
    }  # fmt: skip
    if row is None:
        row = Companion(crop_a=a, crop_b=b, created_by=principal.user_id, **values)
        await repo.add_all(session, row)
    else:
        for k, v in values.items():
            setattr(row, k, v)
    return next(c for c in await list_companions(session, principal) if c.id == row.id)


# ---------------------------------------------------------------- review workflow


async def _entry(session: AsyncSession, entity: str, entity_id: uuid.UUID) -> Any:
    entry = await repo.get_entity(session, entity, entity_id)
    if entry is None:
        raise not_found(entity)
    return entry


async def _missing(session: AsyncSession, entity: str, entry: Any) -> list[str]:
    if entity == "crop":
        return workflow.crop_missing(
            await _crop_data(session, entry), await _default_region(session)
        )
    if entity == "recipe":
        return _recipe_out(entry, with_missing=True).missing_for_review
    if entity == "pest":
        return (await _pest_out(session, entry, with_missing=True)).missing_for_review
    return workflow.rule_missing({"params": entry.params})


async def submit(
    session: AsyncSession, principal: Principal, entity: str, entity_id: uuid.UUID
) -> None:
    _need_agronomist(principal)
    entry = await _entry(session, entity, entity_id)
    if entry.status not in ("draft", "ai_verified"):
        raise AppError("NOT_A_DRAFT", 409)
    missing = await _missing(session, entity, entry)
    if missing:
        raise AppError("INCOMPLETE_ENTRY", 422, {"missing": missing})
    entry.status = "in_review"
    entry.submitted_by = principal.user_id
    entry.submitted_at = datetime.now(UTC)
    await audit.record(
        session, actor_id=principal.user_id, entity=entity, entity_id=entity_id, action="submit"
    )


async def _can_approve(
    session: AsyncSession, principal: Principal, entry: Any
) -> workflow.ApprovalCheck:
    hours = await get_int(session, "library.self_approve_after_hours")
    return workflow.can_approve(
        status=entry.status, approver_id=principal.user_id, submitted_by=entry.submitted_by,
        submitted_at=entry.submitted_at, now=datetime.now(UTC),
        self_approve_after=timedelta(hours=hours),
    )  # fmt: skip


async def _snapshot(session: AsyncSession, entity: str, entry: Any) -> dict[str, Any]:
    if entity == "crop":
        data = await _crop_data(session, entry) | {"slug": entry.slug, "id": entry.id}
    else:
        data = {c.name: getattr(entry, c.name) for c in entry.__table__.columns}
    return dict(_json_safe(data))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, uuid.UUID)) or type(value).__name__ in ("Decimal", "date"):
        return str(value)
    return value


async def approve(
    session: AsyncSession, principal: Principal, entity: str, entity_id: uuid.UUID
) -> None:
    _need_agronomist(principal)
    entry = await _entry(session, entity, entity_id)
    check = await _can_approve(session, principal, entry)
    if not check.allowed:
        raise AppError("APPROVAL_BLOCKED", 409, {"reason": check.reason})
    missing = await _missing(session, entity, entry)
    if missing:
        raise AppError("INCOMPLETE_ENTRY", 422, {"missing": missing})
    entry.status = "approved"
    entry.revision += 1
    entry.approved_by = principal.user_id
    entry.approved_at = datetime.now(UTC)
    await session.flush()
    await repo.add_revision(
        session, entity, entity_id, entry.revision, await _snapshot(session, entity, entry),
        principal.user_id,
    )  # fmt: skip
    await events.publish(
        session, "library.approved",
        {"entity": entity, "id": str(entity_id), "revision": entry.revision},
    )  # fmt: skip
    await audit.record(
        session, actor_id=principal.user_id, entity=entity, entity_id=entity_id, action="approve",
        after={"revision": entry.revision},
    )  # fmt: skip


async def retire(
    session: AsyncSession, principal: Principal, entity: str, entity_id: uuid.UUID
) -> None:
    _need_agronomist(principal)
    entry = await _entry(session, entity, entity_id)
    if entry.status == "retired":
        return
    entry.status = "retired"
    await audit.record(
        session, actor_id=principal.user_id, entity=entity, entity_id=entity_id, action="retire"
    )


async def review_queue(session: AsyncSession, principal: Principal) -> list[ReviewItem]:
    _need_agronomist(principal)
    items = []
    for entity, entry in await repo.list_in_review(session):
        check = await _can_approve(session, principal, entry)
        key = getattr(entry, "slug", None) or getattr(entry, "code", "")
        items.append(
            ReviewItem(
                entity=entity,
                id=entry.id, key=key,
                name_en=getattr(entry, "name_en", key), name_hi=getattr(entry, "name_hi", key),
                submitted_by=entry.submitted_by, submitted_at=entry.submitted_at,
                can_approve=check.allowed, blocked_reason=check.reason,
            )
        )  # fmt: skip
    return items


async def progress(session: AsyncSession) -> dict[str, int]:
    """Approved counts, for the M1 goal (>= 40 crops and >= 6 recipes)."""
    return await repo.count_approved(session)


async def engine_rules(session: AsyncSession) -> dict[str, dict[str, Any]]:
    """Engine parameters by rule code (e.g. `engine.bed`). Rules still in draft are used: they hold
    the spec defaults until an agronomist adjusts them; retired rules are ignored."""
    rows = await repo.list_rules(session, ["draft", "ai_verified", "in_review", "approved"])
    return {r.code: dict(r.params) for r in rows}


async def engine_crops(session: AsyncSession, region_slug: str | None = None) -> list[EngineCrop]:
    """Crops the engine may plan with (approved, plus AI-checked while the beta flag is on), with
    the sow windows and prices of one region (default: `library.default_region`)."""
    region = region_slug or await _default_region(session)
    slugs = await repo.region_slugs(session)
    crops = await repo.crops_with_status(session, await engine_statuses(session))
    regional = await repo.regional_for(session, [c.id for c in crops])
    out = []
    for c in crops:
        local = next((r for r in regional.get(c.id, []) if slugs.get(r.region_id) == region), None)
        out.append(
            EngineCrop(
                id=c.id, slug=c.slug, name_en=c.name_en, name_hi=c.name_hi, status=c.status,
                family=c.family, category=c.category, layers=list(c.layers),
                seasons=list(c.seasons), sow_windows=list(local.sow_windows) if local else [],
                nursery_days=c.nursery_days, days_to_first_harvest=c.days_to_first_harvest,
                harvest_span_days=c.harvest_span_days, spacing_row_cm=c.spacing_row_cm,
                spacing_plant_cm=c.spacing_plant_cm, height_max_cm=c.height_max_cm,
                water_need=c.water_need, waterlogging_tolerant=c.waterlogging_tolerant,
                expected_yield_kg_per_sqm=(
                    float(c.expected_yield_kg_per_sqm)
                    if c.expected_yield_kg_per_sqm is not None else None
                ),
                low_care=c.low_care,
                tree_spacing_m=float(c.tree_spacing_m) if c.tree_spacing_m is not None else None,
                years_to_bear=float(c.years_to_bear) if c.years_to_bear is not None else None,
                price_direct_paise_per_kg=local.price_direct_paise_per_kg if local else None,
                price_mandi_paise_per_kg=local.price_mandi_paise_per_kg if local else None,
            )
        )  # fmt: skip
    return out


async def engine_companions(session: AsyncSession) -> list[EngineCompanion]:
    """Crop pairs the engine may use (same status rule as crops)."""
    ids = {v: k for k, v in (await repo.crop_slug_map(session)).items()}
    rows = await repo.list_companions(session, await engine_statuses(session))
    return [
        EngineCompanion(
            crop_a=ids[r.crop_a], crop_b=ids[r.crop_b], relation=r.relation,
            reason_en=r.reason_en, reason_hi=r.reason_hi, status=r.status,
        )
        for r in rows
        if r.crop_a in ids and r.crop_b in ids
    ]  # fmt: skip


async def crop_names(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, CropName]:
    rows = await repo.crops_by_ids(session, ids)
    return {
        c.id: CropName(id=c.id, slug=c.slug, name_en=c.name_en, name_hi=c.name_hi, status=c.status)
        for c in rows
    }


async def engine_statuses(session: AsyncSession) -> list[str]:
    """Statuses the design engine may use: approved, plus AI-checked entries while the beta flag
    `library.allow_ai_verified` is on (plans then say "not yet reviewed by an expert")."""
    allow = bool(await get_setting(session, "library.allow_ai_verified"))
    return ["approved", "ai_verified"] if allow else ["approved"]


async def load_seed(session: AsyncSession) -> dict[str, int]:
    """Load the bundled seed files as drafts, then the AI research files
    (CLI: python -m app.cli load-library)."""
    from app.modules.library import seed

    counts = await seed.load(session)
    counts.update(await load_research(session, seed.read_research()))
    counts.update(await load_companion_research(session, seed.read_companions()))
    return counts


def _checked(sources: dict[str, Any]) -> bool:
    entries = [e for group in sources.values() for e in group]
    return bool(entries) and all(e.get("quote") and e.get("checked_on") for e in entries)


async def load_companion_research(
    session: AsyncSession, pairs: list[dict[str, Any]]
) -> dict[str, int]:
    """Crop pairs from AI research. A pair whose every source was checked is `ai_verified`;
    pairs an agronomist has taken into review or approved are left alone."""
    counts = {"companions_ai_verified": 0, "companions_draft": 0, "companions_skipped": 0}
    crops = await repo.crop_slug_map(session)
    for pair in pairs:
        if pair["crop_a"] not in crops or pair["crop_b"] not in crops:
            counts["companions_skipped"] += 1
            continue
        a, b = sorted((crops[pair["crop_a"]], crops[pair["crop_b"]]))
        row = await repo.get_companion_pair(session, a, b)
        if row is not None and row.status not in ("draft", "ai_verified"):
            counts["companions_skipped"] += 1
            continue
        status = "ai_verified" if _checked(pair["sources"]) else "draft"
        values = {
            "relation": pair["relation"], "reason_en": pair.get("reason_en"),
            "reason_hi": pair.get("reason_hi"), "sources": pair["sources"], "status": status,
        }  # fmt: skip
        if row is None:
            await repo.add_all(session, Companion(crop_a=a, crop_b=b, **values))
        else:
            for k, v in values.items():
                setattr(row, k, v)
        counts[f"companions_{'ai_verified' if status == 'ai_verified' else 'draft'}"] += 1
    await session.flush()
    return counts


async def load_research(session: AsyncSession, files: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Fill draft crops from AI research files (seeds/library/research/crops/<slug>.json).

    For drafts only empty fields and fields without a source are filled, so an agronomist's edits
    survive; entries still `ai_verified` (untouched since the check) take the file's values.
    A crop becomes `ai_verified` when nothing is missing for review and every source was
    confirmed by the check pass (quote + checked_on); otherwise it stays a draft whose todo list
    says what is missing. Entries in review, approved or retired are never touched.
    """
    counts = {"ai_verified": 0, "research_draft": 0, "research_skipped": 0}
    region = await _default_region(session)
    for slug, raw in files.items():
        crop = await repo.get_crop_by_slug(session, slug)
        if crop is None or crop.status not in ("draft", "ai_verified"):
            counts["research_skipped"] += 1
            continue
        found = _dump(CropUpdate.model_validate(raw))
        current = await _crop_data(session, crop)
        if crop.status == "ai_verified":
            # Untouched since the AI check (any human edit reopens it as a draft): the research
            # file is still the source of truth, so corrections in it are applied.
            changes = {k: v for k, v in found.items() if k not in ("regional", "sources")}
            changes["sources"] = found.get("sources") or {}
            regional = dict(found.get("regional") or {})
        else:
            changes = {
                k: v for k, v in found.items()
                if k not in ("regional", "sources") and current.get(k) in (None, [], {}, "")
            }  # fmt: skip
            changes["sources"] = {**(found.get("sources") or {}), **(crop.sources or {})}
            regional = {
                r: v for r, v in (found.get("regional") or {}).items()
                if not (current["regional"].get(r) or {}).get("sow_windows")
            }  # fmt: skip
        await _apply_crop_fields(session, crop, {**changes, "regional": regional}, crop.created_by)
        data = await _crop_data(session, crop)
        problems = workflow.crop_missing(data, region) + workflow.unchecked_sources(data)
        if problems:
            crop.status = "draft"
            crop.todo = [f"TODO(agronomist): {p}" for p in problems]
            counts["research_draft"] += 1
        else:
            crop.status = "ai_verified"
            crop.todo = ["TODO(agronomist): review AI-checked values"]
            counts["ai_verified"] += 1
    await session.flush()
    return counts
