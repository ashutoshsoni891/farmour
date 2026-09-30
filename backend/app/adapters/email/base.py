from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class Mailer(Protocol):
    async def send(self, email: Email) -> None: ...
