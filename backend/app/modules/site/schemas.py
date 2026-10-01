"""Pydantic v2 contracts for the site module."""

from datetime import datetime
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
