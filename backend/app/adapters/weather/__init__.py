"""Weather and climate data (Open-Meteo implementation arrives in M2). Interface and fake only."""

from app.adapters.registry import Registry
from app.adapters.weather.base import DailyWeather, WeatherSource
from app.adapters.weather.fake import FakeWeather

registry: Registry[WeatherSource] = Registry("weather")
registry.register("fake", FakeWeather)

__all__ = ["DailyWeather", "WeatherSource", "registry"]
