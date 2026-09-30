"""Messaging channels (spec section 10). Telegram is added in M5; WhatsApp is post-MVP."""

from app.adapters.channel.base import Button, Channel, OutboundMessage
from app.adapters.channel.fake import FakeChannel
from app.adapters.registry import Registry
from app.config import get_config

registry: Registry[Channel] = Registry("channel")
registry.register("fake", FakeChannel)


def get_channel() -> Channel:
    return registry.get(get_config().channel_adapter)


__all__ = ["Button", "Channel", "OutboundMessage", "get_channel", "registry"]
