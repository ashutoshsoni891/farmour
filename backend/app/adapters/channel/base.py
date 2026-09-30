from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Button:
    label: str
    payload: str


@dataclass(frozen=True)
class OutboundMessage:
    chat_id: str
    text: str
    buttons: list[Button] = field(default_factory=list)


class Channel(Protocol):
    name: str

    async def send(self, message: OutboundMessage) -> str:
        """Send a message; return the channel's message id."""
        ...
