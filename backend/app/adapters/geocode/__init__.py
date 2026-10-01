"""Place search and reverse lookup (Nominatim for the MVP; self-host or swap by config)."""

from app.adapters.geocode.base import Geocoder, Place
from app.adapters.geocode.fake import FakeGeocoder
from app.adapters.registry import Registry
from app.config import get_config

registry: Registry[Geocoder] = Registry("geocode")
registry.register("fake", FakeGeocoder)


def _nominatim() -> Geocoder:
    from app.adapters.geocode.nominatim import NominatimGeocoder

    cfg = get_config()
    return NominatimGeocoder(cfg.nominatim_url, cfg.geocoder_user_agent)


registry.register("nominatim", _nominatim)


def get_geocoder() -> Geocoder:
    return registry.get(get_config().geocode_adapter)


__all__ = ["Geocoder", "Place", "get_geocoder", "registry"]
