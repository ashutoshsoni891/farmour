"""Dev helper: create a demo owner with two farms (plot, site data, layout plan) on the local stack.

    python -m scripts.seed_demo

Local use only (it logs in through the local Keycloak with the dev test password). Safe to re-run:
farms that already exist by name are left alone.
"""

import json
import math
import time
import urllib.error
import urllib.request
from typing import Any

from scripts.dev_login import PASSWORD, login

BASE = "http://localhost/api/v1"
EMAIL = "demo.owner@example.test"
M_PER_DEG_LAT = 110_540.0


def _ring(lat: float, lng: float, points_m: list[tuple[float, float]]) -> dict[str, Any]:
    """A GeoJSON polygon from (east, north) metre offsets around a point."""
    m_per_deg_lng = 111_320.0 * math.cos(math.radians(lat))
    ring = [[lng + e / m_per_deg_lng, lat + n / M_PER_DEG_LAT] for e, n in points_m]
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def _point(lat: float, lng: float, east: float, north: float) -> dict[str, Any]:
    m_per_deg_lng = 111_320.0 * math.cos(math.radians(lat))
    return {
        "type": "Point",
        "coordinates": [lng + east / m_per_deg_lng, lat + north / M_PER_DEG_LAT],
    }


def _call(token: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    req = urllib.request.Request(  # noqa: S310 (local http only)
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {path} failed: {exc.code} {exc.read().decode()[:300]}") from exc
    return json.loads(raw) if raw else None


FARMS: list[dict[str, Any]] = [
    {
        "farm": {
            "name": "Demo farm - 1 acre near Sanwer",
            "site_type": "ground",
            "district": "Indore",
            "village": "Sanwer",
            "lat": "22.970000",
            "lng": "75.830000",
            "goal": "both",
            "labour": "caretaker",
            "water_source": "bore",
            "electricity": True,
        },
        "parcel": {
            "boundary": _ring(22.97, 75.83, [(-35, -30), (38, -28), (34, 32), (-30, 36)]),
            "soil_type": "black",
            "drainage": "ok",
            "slope_dir": "SE",
            "north_bearing_deg": 0,
            "gate": _point(22.97, 75.83, 2, -29),
            "obstacles": [  # two existing trees
                {
                    "type": "Feature",
                    "properties": {"kind": "tree"},
                    "geometry": _point(22.97, 75.83, -10, 5),
                },
                {
                    "type": "Feature",
                    "properties": {"kind": "tree"},
                    "geometry": _point(22.97, 75.83, 18, -8),
                },
            ],
        },
    },
    {
        "farm": {
            "name": "Demo farm - half acre, waterlogging",
            "site_type": "ground",
            "district": "Indore",
            "village": "Bijalpur",
            "lat": "22.760000",
            "lng": "75.900000",
            "goal": "income",
            "labour": "self",
            "water_source": "well",
            "electricity": False,
        },
        "parcel": {
            "boundary": _ring(22.76, 75.90, [(-22, -25), (24, -22), (20, 26), (-24, 23)]),
            "soil_type": "clay",
            "drainage": "waterlogs",
            "slope_dir": "W",
            "north_bearing_deg": 12,
        },
    },
]


def main() -> None:
    token = login(EMAIL)
    existing = {f["name"] for f in _call(token, "GET", "/farms")}
    for spec in FARMS:
        name = spec["farm"]["name"]
        if name in existing:
            print("exists:", name)
            continue
        farm = _call(token, "POST", "/farms", spec["farm"])
        _call(token, "PUT", f"/farms/{farm['id']}/parcel", spec["parcel"])
        time.sleep(1)  # the parcel save is committed just after its response is sent
        plan = _call(token, "POST", f"/farms/{farm['id']}/plan")
        print(
            f"created: {name} ({farm['id']}): plan v{plan['version']}, "
            f"template {plan['template']}, {len(plan['beds'])} beds, "
            f"warnings {[w['code'] for w in plan['warnings']]}"
        )
    print(f"login: {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
