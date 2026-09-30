import hashlib


class FakeEmbedder:
    """Deterministic vectors derived from a hash of the text."""

    dimensions = 1024

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            out.append([digest[i % len(digest)] / 255 for i in range(self.dimensions)])
        return out
