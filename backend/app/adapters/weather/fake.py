from datetime import date, timedelta

from app.adapters.weather.base import DailyWeather


class FakeWeather:
    """Returns empty readings (no invented values) for each day in the range."""

    async def daily(self, lat: float, lng: float, start: date, end: date) -> list[DailyWeather]:
        days = (end - start).days + 1
        return [DailyWeather(start + timedelta(d), None, None, None) for d in range(days)]
