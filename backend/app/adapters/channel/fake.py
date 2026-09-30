from app.adapters.channel.base import OutboundMessage


class FakeChannel:
    """Records messages instead of sending them."""

    name = "fake"

    def __init__(self) -> None:
        self.sent: list[OutboundMessage] = []

    async def send(self, message: OutboundMessage) -> str:
        self.sent.append(message)
        return f"fake-{len(self.sent)}"
