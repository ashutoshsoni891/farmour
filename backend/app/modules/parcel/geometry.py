"""Pure geometry helpers for parcels (no database, no framework).

Storage is WGS84 (EPSG:4326); all metric work is done in UTM zone 43N (EPSG:32643), which is
the project's working projection for Indore (spec section 4 and 7).
"""

import math
from dataclasses import dataclass

from pyproj import Transformer
from shapely.geometry import Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


class GeometryError(Exception):
    """A parcel problem with an API error code (see spec section 12)."""

    def __init__(self, code: str, details: dict[str, object] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class ParcelShape:
    polygon_wgs84: Polygon
    area_sqm: float
    perimeter_m: float
    shortest_side_m: float


def to_utm(geom: BaseGeometry) -> BaseGeometry:
    from shapely.ops import transform

    return transform(_TO_UTM.transform, geom)


def to_wgs84(geom: BaseGeometry) -> BaseGeometry:
    from shapely.ops import transform

    return transform(_TO_WGS.transform, geom)


def polygon_from_geojson(data: dict[str, object]) -> Polygon:
    try:
        geom = shape(data)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise GeometryError("PARCEL_INVALID_GEOMETRY") from exc
    if not isinstance(geom, Polygon) or geom.is_empty:
        raise GeometryError("PARCEL_INVALID_GEOMETRY")
    if geom.interiors:
        raise GeometryError("PARCEL_INVALID_GEOMETRY", {"reason": "holes_not_supported"})
    minx, miny, maxx, maxy = geom.bounds
    if not (-180 <= minx <= maxx <= 180 and -90 <= miny <= maxy <= 90):
        raise GeometryError("PARCEL_INVALID_GEOMETRY", {"reason": "coordinates_out_of_range"})
    return geom


def _edge_lengths(utm: Polygon) -> list[float]:
    pts = list(utm.exterior.coords)
    return [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def measure(
    polygon_wgs84: Polygon, *, min_area_sqm: float, max_area_sqm: float, min_side_m: float
) -> ParcelShape:
    """Validate a parcel and measure it. Raises GeometryError with a section-12 error code."""
    utm = to_utm(polygon_wgs84)
    if not isinstance(utm, Polygon) or not utm.is_valid:
        raise GeometryError(
            "PARCEL_SELF_INTERSECTS", {"reason": explain_validity(polygon_wgs84)[:120]}
        )
    area = float(utm.area)
    if area < min_area_sqm:
        raise GeometryError("PARCEL_TOO_SMALL", {"area_sqm": round(area, 2), "min": min_area_sqm})
    if area > max_area_sqm:
        raise GeometryError("PARCEL_TOO_LARGE", {"area_sqm": round(area, 2), "max": max_area_sqm})
    edges = _edge_lengths(utm)
    shortest = min(edges)
    if shortest < min_side_m:
        raise GeometryError(
            "PARCEL_SIDE_TOO_SHORT", {"side_m": round(shortest, 2), "min": min_side_m}
        )
    return ParcelShape(polygon_wgs84, area, float(utm.length), shortest)


def to_geojson(geom: BaseGeometry) -> dict[str, object]:
    return dict(mapping(geom))


def _rotate(points: list[tuple[float, float]], bearing_deg: float) -> list[tuple[float, float]]:
    """Rotate points about the origin so the local +y axis points along `bearing_deg`
    (clockwise from north)."""
    a = math.radians(bearing_deg)
    c, s = math.cos(a), math.sin(a)
    return [(x * c + y * s, -x * s + y * c) for x, y in points]


def _at(points: list[tuple[float, float]], lng: float, lat: float, bearing_deg: float) -> Polygon:
    """Place local metre coordinates (centred on 0,0) at a WGS84 point, as a WGS84 polygon."""
    cx, cy = _TO_UTM.transform(lng, lat)
    ring = [(cx + x, cy + y) for x, y in _rotate(points, bearing_deg)]
    return Polygon([_TO_WGS.transform(x, y) for x, y in ring])


def rectangle(
    lng: float, lat: float, length_m: float, width_m: float, bearing_deg: float = 0.0
) -> Polygon:
    """A rectangle centred on a point; `length_m` runs along `bearing_deg` (default north-south)."""
    hl, hw = length_m / 2, width_m / 2
    return _at([(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)], lng, lat, bearing_deg)


def quadrilateral(
    lng: float,
    lat: float,
    a: float,
    b: float,
    c: float,
    d: float,
    diagonal: float,
    bearing_deg: float = 0.0,
) -> Polygon:
    """A four-sided plot from its sides AB=a, BC=b, CD=c, DA=d and the diagonal AC.

    Built from two triangles sharing the diagonal. Raises PARCEL_MEASUREMENTS_INVALID when the
    sides cannot form a plot.
    """

    def apex(p: float, q: float, base: float) -> float | None:
        # Height of the point at distance p from one base end and q from the other.
        x = (p * p - q * q + base * base) / (2 * base)
        h2 = p * p - x * x
        return None if h2 <= 0 else math.sqrt(h2)

    # Put A at (0,0) and C at (diagonal,0); B above the diagonal, D below it.
    xb = (a * a - b * b + diagonal * diagonal) / (2 * diagonal)
    hb = apex(a, b, diagonal)
    xd = (d * d - c * c + diagonal * diagonal) / (2 * diagonal)
    hd = apex(d, c, diagonal)
    if hb is None or hd is None:
        raise GeometryError("PARCEL_MEASUREMENTS_INVALID")
    pts = [(0.0, 0.0), (xb, hb), (diagonal, 0.0), (xd, -hd)]
    cx = sum(p[0] for p in pts) / 4
    cy = sum(p[1] for p in pts) / 4
    return _at([(x - cx, y - cy) for x, y in pts], lng, lat, bearing_deg)
