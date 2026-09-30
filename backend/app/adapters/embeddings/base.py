from typing import Protocol


class Embedder(Protocol):
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
