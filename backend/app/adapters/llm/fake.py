from app.adapters.llm.base import ChatMessage


class FakeLLM:
    def __init__(self, reply: str = "fake reply") -> None:
        self.reply = reply
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, messages: list[ChatMessage], *, max_tokens: int) -> str:
        self.calls.append(messages)
        return self.reply
