"""Daily mandi prices from Agmarknet via the data.gov.in open data API (free API key)."""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

import httpx

from app.adapters.registry import Registry
from app.config import get_config

log = logging.getLogger(__name__)
RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"  # Current daily price of commodities (mandi)
URL = f"https://api.data.gov.in/resource/{RESOURCE}"
PAGE = 1000


@dataclass(frozen=True)
class PriceRow:
    state: str
    district: str
    market: str
    commodity: str
    variety: str
    price_date: date
    min_rupees_per_quintal: float | None
    max_rupees_per_quintal: float | None
    modal_rupees_per_quintal: float | None


class MandiPriceSource(Protocol):
    async def fetch(self, state: str, *, max_pages: int) -> list[PriceRow]: ...


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class DataGovInSource:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._key = api_key
        self._transport = transport

    async def fetch(self, state: str, *, max_pages: int) -> list[PriceRow]:
        rows: list[PriceRow] = []
        async with httpx.AsyncClient(timeout=30, transport=self._transport) as client:
            for page in range(max_pages):
                params: dict[str, str | int] = {
                    "api-key": self._key, "format": "json", "limit": PAGE,
                    "offset": page * PAGE, "filters[state.keyword]": state,
                }  # fmt: skip
                try:
                    resp = await client.get(URL, params=params)
                    resp.raise_for_status()
                    records: list[dict[str, Any]] = resp.json().get("records", [])
                except (httpx.HTTPError, ValueError) as exc:
                    log.warning("data.gov.in unavailable: %s", type(exc).__name__)
                    break
                for r in records:
                    try:
                        day = datetime.strptime(str(r["arrival_date"]), "%d/%m/%Y").date()
                    except (KeyError, ValueError):
                        continue
                    rows.append(
                        PriceRow(
                            state=str(r.get("state", state)), district=str(r.get("district", "")),
                            market=str(r.get("market", "")), commodity=str(r.get("commodity", "")),
                            variety=str(r.get("variety", "") or ""), price_date=day,
                            min_rupees_per_quintal=_num(r.get("min_price")),
                            max_rupees_per_quintal=_num(r.get("max_price")),
                            modal_rupees_per_quintal=_num(r.get("modal_price")),
                        )
                    )  # fmt: skip
                if len(records) < PAGE:
                    break
        return rows


class FakeMandiSource:
    def __init__(self, rows: list[PriceRow] | None = None) -> None:
        self.rows = rows or []

    async def fetch(self, state: str, *, max_pages: int) -> list[PriceRow]:
        return list(self.rows)


registry: Registry[MandiPriceSource] = Registry("mandi")
registry.register("fake", FakeMandiSource)


def _real() -> MandiPriceSource:
    return DataGovInSource(get_config().data_gov_in_api_key.get_secret_value())


registry.register("data_gov_in", _real)


def get_mandi_source() -> MandiPriceSource | None:
    """None when no API key is configured (ingest is then skipped, never faked)."""
    cfg = get_config()
    if cfg.mandi_adapter == "data_gov_in" and not cfg.data_gov_in_api_key.get_secret_value():
        return None
    return registry.get(cfg.mandi_adapter)
