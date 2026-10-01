"""Routes: /library. Approved entries are readable by any signed-in user; agronomists see all
statuses and can create, edit and review."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from app.modules.identity.deps import CurrentUser, SessionDep
from app.modules.library import service
from app.modules.library.schemas import (
    CompanionIn,
    CompanionOut,
    CropCreate,
    CropOut,
    CropSummary,
    CropUpdate,
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

router = APIRouter(prefix="/library", tags=["library"])
Entity = Literal["crops", "recipes", "pests", "rules"]
_ENTITY = {"crops": "crop", "recipes": "recipe", "pests": "pest", "rules": "rule"}


@router.get("/crops")
async def list_crops(
    principal: CurrentUser,
    session: SessionDep,
    status: str | None = None,
    q: str | None = None,
    category: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[CropSummary]:
    return await service.list_crops(
        session, principal, status=status, q=q, category=category, cursor=cursor, limit=limit
    )


@router.post("/crops", status_code=status.HTTP_201_CREATED)
async def create_crop(body: CropCreate, principal: CurrentUser, session: SessionDep) -> CropOut:
    return await service.create_crop(session, principal, body)


@router.get("/crops/{crop_id}")
async def get_crop(crop_id: uuid.UUID, principal: CurrentUser, session: SessionDep) -> CropOut:
    return await service.get_crop(session, principal, crop_id)


@router.patch("/crops/{crop_id}")
async def update_crop(
    crop_id: uuid.UUID, body: CropUpdate, principal: CurrentUser, session: SessionDep
) -> CropOut:
    return await service.update_crop(session, principal, crop_id, body)


@router.get("/recipes")
async def list_recipes(principal: CurrentUser, session: SessionDep) -> list[RecipeOut]:
    return await service.list_recipes(session, principal)


@router.post("/recipes", status_code=status.HTTP_201_CREATED)
async def create_recipe(
    body: RecipeCreate, principal: CurrentUser, session: SessionDep
) -> RecipeOut:
    return await service.create_recipe(session, principal, body)


@router.patch("/recipes/{recipe_id}")
async def update_recipe(
    recipe_id: uuid.UUID, body: RecipeFields, principal: CurrentUser, session: SessionDep
) -> RecipeOut:
    return await service.update_recipe(session, principal, recipe_id, body)


@router.get("/pests")
async def list_pests(principal: CurrentUser, session: SessionDep) -> list[PestOut]:
    return await service.list_pests(session, principal)


@router.post("/pests", status_code=status.HTTP_201_CREATED)
async def create_pest(body: PestCreate, principal: CurrentUser, session: SessionDep) -> PestOut:
    return await service.create_pest(session, principal, body)


@router.patch("/pests/{pest_id}")
async def update_pest(
    pest_id: uuid.UUID, body: PestFields, principal: CurrentUser, session: SessionDep
) -> PestOut:
    return await service.update_pest(session, principal, pest_id, body)


@router.get("/rules")
async def list_rules(principal: CurrentUser, session: SessionDep) -> list[RuleOut]:
    return await service.list_rules(session, principal)


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID, body: RuleUpdate, principal: CurrentUser, session: SessionDep
) -> RuleOut:
    return await service.update_rule(session, principal, rule_id, body)


@router.get("/companions")
async def list_companions(principal: CurrentUser, session: SessionDep) -> list[CompanionOut]:
    return await service.list_companions(session, principal)


@router.put("/companions")
async def save_companion(
    body: CompanionIn, principal: CurrentUser, session: SessionDep
) -> CompanionOut:
    return await service.save_companion(session, principal, body)


@router.get("/review")
async def review_queue(principal: CurrentUser, session: SessionDep) -> list[ReviewItem]:
    return await service.review_queue(session, principal)


@router.get("/progress")
async def progress(principal: CurrentUser, session: SessionDep) -> dict[str, int]:
    """Approved entries per kind, for the M1 goal (40 crops, 6 recipes)."""
    return await service.progress(session)


@router.post("/{entity}/{entry_id}/submit", status_code=status.HTTP_204_NO_CONTENT)
async def submit(
    entity: Entity, entry_id: uuid.UUID, principal: CurrentUser, session: SessionDep
) -> None:
    await service.submit(session, principal, _ENTITY[entity], entry_id)


@router.post("/{entity}/{entry_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve(
    entity: Entity, entry_id: uuid.UUID, principal: CurrentUser, session: SessionDep
) -> None:
    await service.approve(session, principal, _ENTITY[entity], entry_id)


@router.post("/{entity}/{entry_id}/retire", status_code=status.HTTP_204_NO_CONTENT)
async def retire(
    entity: Entity, entry_id: uuid.UUID, principal: CurrentUser, session: SessionDep
) -> None:
    await service.retire(session, principal, _ENTITY[entity], entry_id)
