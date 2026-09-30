from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLM(Protocol):
    async def complete(self, messages: list[ChatMessage], *, max_tokens: int) -> str: ...
