from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class DailyWeather:
    day: date
    temp_max_c: float | None
    temp_min_c: float | None
    rain_mm: float | None


class WeatherSource(Protocol):
    async def daily(self, lat: float, lng: float, start: date, end: date) -> list[DailyWeather]: ...
