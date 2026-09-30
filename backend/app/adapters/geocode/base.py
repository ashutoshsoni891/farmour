from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lng: float


class Geocoder(Protocol):
    async def search(self, query: str, *, lang: str, limit: int) -> list[Place]: ...
