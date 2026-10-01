"""Site data sources (spec section 17). Each source turns a location into facts."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol


@dataclass(frozen=True)
class SiteContext:
    lat: float
    lng: float
    area_sqm: float | None = None
    district: str | None = None
    state: str | None = None


@dataclass(frozen=True)
class Fact:
    key: str
    value: Any
    source: str
    method: str
    confidence: float
    unit: str | None = None
    ttl_days: int = 365
    attribution: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def expires_at(self) -> datetime:
        return self.fetched_at + timedelta(days=self.ttl_days)


class SiteSource(Protocol):
    name: str

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        """Return facts for the location. A source that cannot answer returns [] (it must
        never raise for ordinary failures and must never invent values)."""
        ...
