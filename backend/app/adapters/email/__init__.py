"""Outbound email for app notices (Keycloak sends its own auth emails). Interface and fake only."""

from app.adapters.email.base import Email, Mailer
from app.adapters.email.fake import FakeMailer
from app.adapters.registry import Registry

registry: Registry[Mailer] = Registry("email")
registry.register("fake", FakeMailer)

__all__ = ["Email", "Mailer", "registry"]
