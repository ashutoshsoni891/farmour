"""Pydantic v2 contracts for the site module."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Group = Literal["region", "soil_land", "climate", "water", "markets", "nearby"]


class FactOut(BaseModel):
    key: str
    group: Group
    value: Any
    unit: str | None
    source: str
    method: str | None
    confidence: float
    status: Literal["derived", "confirmed", "edited", "rejected"]
    fetched_at: datetime
    attribution: str | None


class BuildOut(BaseModel):
    status: Literal["none", "running", "done", "failed"]
    finished_at: datetime | None = None
    sources: dict[str, Any] = {}


class ProfileOut(BaseModel):
    build: BuildOut
    facts: list[FactOut]
    questions: list[str]  # fact keys the owner should answer (low confidence or missing)
    attributions: list[str]


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    action: Literal["confirm", "edit", "reject"]
    value: Any = None


class AnswerBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Answer]


class SchemeSource(BaseModel):
    url: str | None
    title: str


class SchemeOut(BaseModel):
    """A scheme the farm may be eligible for. Never "you qualify": the department decides."""

    code: str
    level: str
    state: str | None
    benefit_type: str
    name_en: str
    name_hi: str
    gives_en: str
    gives_hi: str
    eligibility_en: str
    eligibility_hi: str
    documents: list[dict[str, Any]]
    apply_en: str | None
    apply_hi: str | None
    apply_url: str | None
    sources: list[SchemeSource]
    checked_on: date | None
    ai_checked: bool
    reasons: list[str]  # what in the plan made it show: "orchard", "pond", "goal:income", ...
    conditions: list[str]  # what the owner must still check, e.g. "check.land_in_name"
