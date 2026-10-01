from app.adapters.sitedata.base import Fact, SiteContext


class FakeSource:
    """Returns the facts it was given (tests), or nothing."""

    name = "fake"

    def __init__(self, facts: list[Fact] | None = None) -> None:
        self.facts = facts or []

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        return list(self.facts)
