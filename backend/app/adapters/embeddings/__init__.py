"""Text embeddings (BGE-M3 implementation arrives in M7). Interface and fake only."""

from app.adapters.embeddings.base import Embedder
from app.adapters.embeddings.fake import FakeEmbedder
from app.adapters.registry import Registry

registry: Registry[Embedder] = Registry("embeddings")
registry.register("fake", FakeEmbedder)

__all__ = ["Embedder", "registry"]
