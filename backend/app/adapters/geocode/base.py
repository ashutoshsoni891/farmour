from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lng: float
    village: str | None = None
    district: str | None = None
    state: str | None = None


class Geocoder(Protocol):
    async def search(self, query: str, *, lang: str, limit: int) -> list[Place]: ...

    async def reverse(self, lat: float, lng: float, *, lang: str) -> Place | None: ...
