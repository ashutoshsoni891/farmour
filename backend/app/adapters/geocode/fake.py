from app.adapters.geocode.base import Place


class FakeGeocoder:
    def __init__(self, places: list[Place] | None = None) -> None:
        self.places = places or []

    async def search(self, query: str, *, lang: str, limit: int) -> list[Place]:
        q = query.lower()
        return [p for p in self.places if q in p.name.lower()][:limit]

    async def reverse(self, lat: float, lng: float, *, lang: str) -> Place | None:
        return self.places[0] if self.places else None
