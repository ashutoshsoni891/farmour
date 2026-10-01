"""Registry of site data sources, chosen by the SITE_SOURCES setting (comma list; "none" = off)."""

from app.adapters.registry import Registry
from app.adapters.sitedata.base import Fact, SiteContext, SiteSource
from app.adapters.sitedata.climate import OpenMeteoClimateSource, OpenMeteoTerrainSource
from app.adapters.sitedata.fake import FakeSource
from app.adapters.sitedata.places import OverpassPlacesSource
from app.adapters.sitedata.soil import SoilGridsSource
from app.config import get_config

registry: Registry[SiteSource] = Registry("site_source")
registry.register("fake", FakeSource)
registry.register("open_meteo", OpenMeteoClimateSource)
registry.register("open_meteo_dem", OpenMeteoTerrainSource)
registry.register("soilgrids", SoilGridsSource)
registry.register("osm_places", OverpassPlacesSource)


def active_sources() -> list[SiteSource]:
    names = [n.strip() for n in get_config().site_sources.split(",") if n.strip()]
    return [] if names == ["none"] else [registry.get(n) for n in names]


__all__ = ["Fact", "SiteContext", "SiteSource", "active_sources", "registry"]
