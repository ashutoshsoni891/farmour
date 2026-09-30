"""Place search (Nominatim or Photon implementation arrives in M2). Interface and fake only."""

from app.adapters.geocode.base import Geocoder, Place
from app.adapters.geocode.fake import FakeGeocoder
from app.adapters.registry import Registry

registry: Registry[Geocoder] = Registry("geocode")
registry.register("fake", FakeGeocoder)

__all__ = ["Geocoder", "Place", "registry"]
