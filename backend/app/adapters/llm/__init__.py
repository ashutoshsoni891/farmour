"""LLM access (LiteLLM implementation arrives in M7). Interface and fake only."""

from app.adapters.llm.base import LLM, ChatMessage
from app.adapters.llm.fake import FakeLLM
from app.adapters.registry import Registry

registry: Registry[LLM] = Registry("llm")
registry.register("fake", FakeLLM)

__all__ = ["LLM", "ChatMessage", "registry"]
