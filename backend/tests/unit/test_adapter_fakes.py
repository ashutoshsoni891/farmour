"""Contract checks: every adapter kind has a fake registered, and the fakes behave."""

from datetime import date

from app.adapters import cache, channel, email, embeddings, geocode, identity, llm, storage, weather
from app.adapters.cache.memory import MemoryCache
from app.adapters.channel import OutboundMessage
from app.adapters.embeddings.fake import FakeEmbedder
from app.adapters.weather.fake import FakeWeather


def test_every_adapter_kind_has_a_fake() -> None:
    for reg in (
        channel.registry,
        embeddings.registry,
        email.registry,
        geocode.registry,
        identity.registry,
        llm.registry,
        storage.registry,
        weather.registry,
    ):
        assert "fake" in reg.names(), reg.kind
    assert "memory" in cache.registry.names()


async def test_memory_cache_window_counts() -> None:
    c = MemoryCache()
    assert [await c.incr_window("k", 60) for _ in range(3)] == [1, 2, 3]


async def test_fake_channel_records() -> None:
    ch = channel.registry.get("fake")
    await ch.send(OutboundMessage(chat_id="1", text="hi"))
    assert ch.sent[-1].text == "hi"  # type: ignore[attr-defined]


async def test_fake_embedder_is_deterministic_and_sized() -> None:
    e = FakeEmbedder()
    a, b = await e.embed(["लौकी", "लौकी"])
    assert a == b
    assert len(a) == 1024


async def test_fake_weather_invents_nothing() -> None:
    days = await FakeWeather().daily(22.7, 75.8, date(2026, 6, 1), date(2026, 6, 3))
    assert len(days) == 3
    assert all(d.temp_max_c is None and d.rain_mm is None for d in days)
