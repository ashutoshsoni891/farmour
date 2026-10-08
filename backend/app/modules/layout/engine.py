"""Deterministic layout engine (spec section 7, steps 1-7 and 11): parcel -> zones and beds.

Pure functions: no database, no clock, no randomness. The same parcel and parameters always give
the same layout. Metric work happens in a local frame: UTM 43N (EPSG:32643), centred on the parcel
and rotated so true north is +y. Zone shares and widths come in through `EngineParams`
(built from the `rules` and `settings` tables); nothing agronomic is decided here.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from pyproj import Transformer
from shapely import affinity
from shapely.geometry import Point, Polygon, box, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

# 0.3: trees, hedge, flowers, polyhouse, livestock; 0.3.1: orchard mix; 0.3.2: medicinal herbs;
# 0.4: field crops on the rotation field
ENGINE_VERSION = "0.4.0"

_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

Template = Literal["S", "M", "L"]
ZoneKind = Literal[
    "beds", "orchard", "rotation", "border", "water", "utility", "nursery", "path", "polyhouse",
    "livestock",
]  # fmt: skip
COMPASS = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
EPS = 1e-6


class LayoutError(Exception):
    """A layout problem with a section-12 error code."""

    def __init__(self, code: str, details: dict[str, object] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class EngineParams:
    """Every number the engine uses. Built from `rules` and `settings`; never literals here."""

    bed_width_m: float
    path_width_m: float
    max_bed_length_m: float
    min_bed_area_sqm: float
    min_bed_width_m: float
    bed_axis_tolerance_deg: float
    min_area_sqm: float
    max_area_sqm: float
    obstacle_buffer_m: float
    border_m: dict[str, float]
    shares: dict[str, dict[str, float]]  # template -> zone -> percent of the parcel
    gate_opening_m: float
    nursery_share_of_utility: float
    zone_aspect: float
    area_tolerance_pct: float
    min_beds_share_pct: float
    min_beds_axis_extent_m: float
    # optional zones the owner asked for (goal step methods): kind -> percent of the plot
    extra_zones: dict[str, float] = field(default_factory=dict)
    small_below_sqm: float = 150.0  # spec 7 template table: S < 150
    medium_up_to_sqm: float = 2000.0  # M 150-2,000; L above


@dataclass(frozen=True)
class SiteInputs:
    boundary: dict[str, Any]  # GeoJSON polygon, WGS84
    north_bearing_deg: float = 0.0
    gate: dict[str, Any] | None = None  # GeoJSON point
    slope_dir: str | None = None
    drainage: str | None = None
    soil_type: str | None = None
    obstacles: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ZoneResult:
    kind: ZoneKind
    label: str
    geom: Polygon  # local metres
    area_sqm: float


@dataclass
class BedResult:
    code: str
    zone_index: int  # index into LayoutResult.zones
    geom: Polygon
    length_m: float
    width_m: float
    raised: bool
    orientation_deg: float
    has_trellis: bool
    protected: bool = False  # inside the polyhouse


@dataclass
class LayoutResult:
    template: Template
    area_sqm: float
    zones: list[ZoneResult]
    beds: list[BedResult]
    warnings: list[dict[str, Any]]
    frame: "Frame"
    hedge_line: BaseGeometry | None = None  # middle of the border band (local metres)
    gate: Point | None = None
    gate_gap_m: float = 0.0

    def geojson(self, geom: Polygon) -> dict[str, Any]:
        return self.frame.to_wgs84_geojson(geom)


# ------------------------------------------------------------------ frame


@dataclass(frozen=True)
class Frame:
    """Local metre frame: UTM, centred on the parcel, rotated so true north is +y."""

    cx: float
    cy: float
    bearing_deg: float

    def to_local(self, geom: BaseGeometry) -> BaseGeometry:
        utm = transform(_TO_UTM.transform, geom)
        moved = affinity.translate(utm, -self.cx, -self.cy)
        return affinity.rotate(moved, self.bearing_deg, origin=(0, 0))

    def to_wgs84(self, geom: BaseGeometry) -> BaseGeometry:
        back = affinity.rotate(geom, -self.bearing_deg, origin=(0, 0))
        utm = affinity.translate(back, self.cx, self.cy)
        return transform(_TO_WGS.transform, utm)

    def to_wgs84_geojson(self, geom: BaseGeometry) -> dict[str, Any]:
        from shapely.geometry import mapping

        return dict(mapping(self.to_wgs84(geom)))


def _polygon(data: dict[str, Any]) -> Polygon:
    try:
        geom = shape(data)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise LayoutError("PARCEL_INVALID_GEOMETRY") from exc
    if not isinstance(geom, Polygon) or geom.is_empty:
        raise LayoutError("PARCEL_INVALID_GEOMETRY")
    return geom


def _parts(geom: BaseGeometry) -> list[Polygon]:
    """Polygon parts of a geometry, largest first (stable order for ties: by position)."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        parts = [geom]
    elif hasattr(geom, "geoms"):
        parts = [p for g in geom.geoms for p in _parts(g)]
    else:
        parts = []
    return sorted(
        (p for p in parts if p.area > EPS),
        key=lambda p: (-round(p.area, 6), round(p.centroid.x, 6), round(p.centroid.y, 6)),
    )


# ------------------------------------------------------------------ carving helpers


def _search_area(
    make: Any, target: float, tolerance: float, lo: float, hi: float, iterations: int = 60
) -> float:
    """Find the parameter in [lo, hi] for which `make(param).area` is closest to `target`.

    `make` returns a geometry whose area grows with the parameter."""
    best, best_err = hi, float("inf")
    for _ in range(iterations):
        mid = (lo + hi) / 2
        err = make(mid).area - target
        if abs(err) < best_err:
            best, best_err = mid, abs(err)
        if abs(err) <= tolerance * target:
            return mid
        if err < 0:
            lo = mid
        else:
            hi = mid
    return best


def _north_piece(remaining: BaseGeometry, target: float, tol: float) -> BaseGeometry:
    """The part of `remaining` north of a horizontal line, sized to `target` (spec 7)."""
    minx, miny, maxx, maxy = remaining.bounds

    def piece(t: float) -> BaseGeometry:
        return remaining.intersection(box(minx - 1, t, maxx + 1, maxy + 1))

    t = _search_area(lambda p: piece(maxy - p), target, tol, 0.0, maxy - miny)
    return piece(maxy - t)


def _south_piece(remaining: BaseGeometry, target: float, tol: float) -> BaseGeometry:
    minx, miny, maxx, maxy = remaining.bounds

    def piece(t: float) -> BaseGeometry:
        return remaining.intersection(box(minx - 1, miny - 1, maxx + 1, miny + t))

    t = _search_area(piece, target, tol, 0.0, maxy - miny)
    return piece(t)


def _anchored_piece(
    remaining: BaseGeometry, anchor: Point, target: float, aspect: float, tol: float
) -> BaseGeometry:
    """A compact piece of `remaining` near `anchor`, sized to `target` (area within tolerance).

    A rectangle of the given aspect (long side east-west) is grown around the anchor, pulled toward
    the middle of the remaining land so it sits against the boundary rather than half outside."""
    centroid = remaining.centroid
    dx, dy = centroid.x - anchor.x, centroid.y - anchor.y
    dist = math.hypot(dx, dy)
    ux, uy = (dx / dist, dy / dist) if dist > EPS else (0.0, 0.0)

    def rect(scale: float) -> BaseGeometry:
        h = math.sqrt(scale / aspect)
        w = aspect * h
        shift = min(dist, 0.25 * math.hypot(w, h))
        cx, cy = anchor.x + ux * shift, anchor.y + uy * shift
        return remaining.intersection(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))

    scale = _search_area(rect, target, tol, 0.0, 4.0 * remaining.area)
    parts = _parts(rect(scale))
    if not parts:
        return Polygon()
    # keep the part nearest the anchor (the largest wins ties)
    return min(parts, key=lambda p: (round(p.distance(anchor), 6), -p.area))


def _nearest(geom: BaseGeometry, point: Point) -> Point:
    from shapely.ops import nearest_points

    return nearest_points(geom, point)[0]


def _farthest_vertex(geom: BaseGeometry, point: Point) -> Point:
    coords: list[tuple[float, float]] = []
    for part in _parts(geom):
        coords += list(part.exterior.coords)
    best = max(coords, key=lambda c: (round(math.dist(c, (point.x, point.y)), 6), c))
    return Point(best)


def _extreme_vertex(geom: BaseGeometry, bearing_deg: float) -> Point:
    """The vertex furthest in a compass direction (0 = north, clockwise)."""
    a = math.radians(bearing_deg)
    ux, uy = math.sin(a), math.cos(a)
    coords: list[tuple[float, float]] = []
    for part in _parts(geom):
        coords += list(part.exterior.coords)
    best = max(coords, key=lambda c: (round(c[0] * ux + c[1] * uy, 6), c))
    return Point(best)


def _default_gate(boundary: Polygon) -> Point:
    """The midpoint of the south-most edge (spec 7 default)."""
    pts = list(boundary.exterior.coords)
    edges = [((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2)
             for i in range(len(pts) - 1)]  # fmt: skip
    return Point(min(edges, key=lambda m: (round(m[1], 6), m[0])))


# ------------------------------------------------------------------ the pipeline


def _template(area: float, p: EngineParams) -> Template:
    if area < p.small_below_sqm:
        return "S"
    return "M" if area <= p.medium_up_to_sqm else "L"


def _carve(
    usable: Polygon,
    gate: Point,
    template: Template,
    site: SiteInputs,
    p: EngineParams,
    drop: set[str],
) -> tuple[list[ZoneResult], BaseGeometry]:
    """Carve border -> north strip -> water -> utility/nursery -> rotation. Returns the zones and
    what is left for beds."""
    tol = p.area_tolerance_pct / 100
    total = usable.area
    share = p.shares[template]
    zones: list[ZoneResult] = []

    def add(kind: ZoneKind, label: str, geom: BaseGeometry) -> None:
        for i, part in enumerate(_parts(geom)):
            name = label if i == 0 else f"{label} {i + 1}"
            zones.append(ZoneResult(kind, name, part, part.area))

    # border: an inward band, skipping the gate segment
    width = p.border_m[template]
    inner = usable.buffer(-width, join_style="mitre")
    if inner.is_empty:
        raise LayoutError("PLAN_NO_ROOM", {"reason": "border_fills_plot"})
    band = usable.difference(inner)
    opening = band.intersection(gate.buffer(p.gate_opening_m / 2))
    add("border", "border", band.difference(opening))
    add("path", "gate", opening)
    remaining: BaseGeometry = inner

    # north strip: tall crops and canopy (orchard share)
    if "orchard" not in drop and share["orchard"] > 0:
        piece = _north_piece(remaining, total * share["orchard"] / 100, tol)
        add("orchard", "orchard", piece)
        remaining = remaining.difference(piece)

    # water: lowest point if the slope is known, else the far side from the gate
    water_zone: BaseGeometry = Polygon()
    if "water" not in drop and share["water"] > 0 and not remaining.is_empty:
        if site.slope_dir in COMPASS:
            anchor = _extreme_vertex(remaining, COMPASS[site.slope_dir])
        else:
            anchor = _farthest_vertex(remaining, gate)
        water_zone = _anchored_piece(
            remaining, anchor, total * share["water"] / 100, p.zone_aspect, tol
        )
        add("water", "pond", water_zone)
        remaining = remaining.difference(water_zone)

    # nursery next to the gate; utility next to the water (or far from the gate)
    util_total = total * share["utility_nursery"] / 100
    if util_total > 0 and not remaining.is_empty:
        nursery = _anchored_piece(
            remaining,
            _nearest(remaining, gate),
            util_total * p.nursery_share_of_utility,
            p.zone_aspect,
            tol,
        )
        add("nursery", "nursery", nursery)
        remaining = remaining.difference(nursery)
        if not remaining.is_empty:
            near = water_zone.centroid if not water_zone.is_empty else None
            anchor = _nearest(remaining, near) if near else _farthest_vertex(remaining, gate)
            utility = _anchored_piece(
                remaining, anchor, util_total * (1 - p.nursery_share_of_utility), p.zone_aspect, tol
            )
            add("utility", "utility", utility)
            remaining = remaining.difference(utility)

    # polyhouse and livestock (only when asked for): next to the compost and tools area, so water,
    # inputs and manure are close by
    for kind, label in (("polyhouse", "polyhouse"), ("livestock", "livestock area")):
        pct = p.extra_zones.get(kind, 0)
        if pct <= 0 or kind in drop or remaining.is_empty:
            continue
        hub = next((z.geom for z in zones if z.kind == "utility"), None)
        anchor = _nearest(remaining, hub.centroid) if hub else _farthest_vertex(remaining, gate)
        piece = _anchored_piece(remaining, anchor, total * pct / 100, p.zone_aspect, tol)
        add(kind, label, piece)  # type: ignore[arg-type]
        remaining = remaining.difference(piece)

    # rotation field (large plots): the southern slab, away from the north strip
    if "rotation" not in drop and share["rotation"] > 0 and not remaining.is_empty:
        piece = _south_piece(remaining, total * share["rotation"] / 100, tol)
        add("rotation", "rotation field", piece)
        remaining = remaining.difference(piece)

    return zones, remaining


def _bed_frame_angle(piece: Polygon, p: EngineParams) -> tuple[float, bool]:
    """Angle (degrees, counter-clockwise) that turns a beds piece so beds run along +y.

    North-south (0) unless the piece is narrower than `min_beds_axis_extent_m` in that direction,
    in which case beds follow the piece's own main axis."""
    _, y0, _, y1 = piece.bounds
    if (y1 - y0) >= p.min_beds_axis_extent_m:
        return 0.0, False
    pts = list(piece.minimum_rotated_rectangle.exterior.coords)
    edges = [(math.dist(pts[i], pts[i + 1]), pts[i], pts[i + 1]) for i in range(2)]
    _, a, b = max(edges, key=lambda e: e[0])
    long_edge = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))  # from +x
    return 90.0 - long_edge, True


def _dimensions(poly: Polygon) -> tuple[float, float]:
    """(length, width) of a bed from its minimum rotated rectangle."""
    pts = list(poly.minimum_rotated_rectangle.exterior.coords)
    a, b = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    return (max(a, b), min(a, b))


def _tile_beds(zone: Polygon, p: EngineParams) -> tuple[list[tuple[Polygon, int, float]], bool]:
    """Tile one beds zone. Returns [(bed polygon, column index, orientation_deg)] and whether the
    zone's main axis was used instead of north-south."""
    angle, along_axis = _bed_frame_angle(zone, p)
    rotated = affinity.rotate(zone, angle, origin=(0, 0)) if angle else zone
    minx, miny, maxx, maxy = rotated.bounds
    pitch_x = p.bed_width_m + p.path_width_m
    pitch_y = p.max_bed_length_m + p.path_width_m  # a cross path every max length (spec 7)
    out: list[tuple[Polygon, int, float]] = []
    col, x = 0, minx
    while x < maxx - EPS:
        y = miny
        while y < maxy - EPS:
            cell = box(x, y, x + p.bed_width_m, y + p.max_bed_length_m)
            for piece in _parts(rotated.intersection(cell)):
                if (
                    piece.area >= p.min_bed_area_sqm
                    and _dimensions(piece)[1] >= p.min_bed_width_m - EPS
                ):
                    back = affinity.rotate(piece, -angle, origin=(0, 0)) if angle else piece
                    out.append((back, col, (-angle) % 180 if angle else 0.0))
            y += pitch_y
        x += pitch_x
        col += 1
    return out, along_axis


def _bed_order(poly: Polygon, gate: Point) -> tuple[float, float, float]:
    c = poly.centroid
    return (round(c.distance(gate), 3), round(c.x, 3), round(c.y, 3))


def _verify(parcel: Polygon, zones: list[ZoneResult], beds: list[BedResult]) -> None:
    """Spec 5 invariants: zones inside the parcel, no overlaps; beds inside their zone."""
    grown = parcel.buffer(0.01)
    for z in zones:
        if not z.geom.within(grown):
            raise LayoutError("PLAN_INVARIANT_FAILED", {"check": "zone_in_parcel", "zone": z.label})
    for i, a in enumerate(zones):
        for b in zones[i + 1 :]:
            if a.geom.intersection(b.geom).area > 0.01:
                raise LayoutError(
                    "PLAN_INVARIANT_FAILED", {"check": "zone_overlap", "zones": [a.label, b.label]}
                )
    for bed in beds:
        if not bed.geom.within(zones[bed.zone_index].geom.buffer(0.01)):
            raise LayoutError("PLAN_INVARIANT_FAILED", {"check": "bed_in_zone", "bed": bed.code})


def generate(site: SiteInputs, p: EngineParams) -> LayoutResult:
    """Run the pipeline. Raises LayoutError (a section-12 code) when the plot can't be planned."""
    # 1. validate
    boundary_wgs = _polygon(site.boundary)
    centre_x, centre_y = _TO_UTM.transform(boundary_wgs.centroid.x, boundary_wgs.centroid.y)
    frame = Frame(centre_x, centre_y, site.north_bearing_deg)
    # 2. project (UTM 43N, rotated so north is up)
    parcel = frame.to_local(boundary_wgs)
    if not isinstance(parcel, Polygon) or not parcel.is_valid:
        raise LayoutError("PARCEL_SELF_INTERSECTS")
    if parcel.area < p.min_area_sqm:
        raise LayoutError("PARCEL_TOO_SMALL", {"area_sqm": round(parcel.area, 2)})
    if parcel.area > p.max_area_sqm:
        raise LayoutError("PARCEL_TOO_LARGE", {"area_sqm": round(parcel.area, 2)})
    warnings: list[dict[str, Any]] = []

    # 3. subtract obstacles with a buffer
    usable: BaseGeometry = parcel
    for feature in site.obstacles:
        geometry = feature.get("geometry") if feature.get("type") == "Feature" else feature
        try:
            obstacle = frame.to_local(shape(geometry))
        except (ValueError, TypeError, AttributeError):
            continue
        usable = usable.difference(obstacle.buffer(p.obstacle_buffer_m))
    parts = _parts(usable)
    if not parts:
        raise LayoutError("PLAN_NO_ROOM", {"reason": "obstacles_fill_plot"})
    main = parts[0]  # the largest connected piece is planned; smaller leftovers are left alone
    if len(parts) > 1:
        warnings.append({"code": "PLOT_SPLIT_BY_OBSTACLES", "message_key": "warn.plot_split"})

    # 5. template
    template = _template(parcel.area, p)
    gate = (
        _nearest(parcel.exterior, frame.to_local(shape(site.gate)).centroid)
        if site.gate
        else _default_gate(parcel)
    )
    gate = _nearest(main.exterior, gate)

    # 6. zones; drop optional zones in the spec's order if the beds would get too little room
    drop_order = ["livestock", "polyhouse", "rotation", "water", "orchard"]
    drop: set[str] = set()
    # zones the owner asked for (polyhouse, livestock) come out of the beds target, not the reverse
    beds_target = max(p.shares[template]["beds"] - sum(p.extra_zones.values()), 0)
    min_beds = parcel.area * beds_target / 100 * p.min_beds_share_pct / 100
    zones, remaining = _carve(main, gate, template, site, p, drop)
    while remaining.area < min_beds and drop_order:
        step = drop_order.pop(0)
        if p.shares[template].get(step, 0) <= 0 and p.extra_zones.get(step, 0) <= 0:
            continue
        drop.add(step)
        warnings.append(
            {"code": f"ZONE_DROPPED_{step.upper()}", "message_key": f"warn.dropped_{step}"}
        )
        zones, remaining = _carve(main, gate, template, site, p, drop)
    if remaining.area < p.min_bed_area_sqm:
        raise LayoutError("PLAN_NO_ROOM", {"reason": "no_room_for_beds"})

    # 7. beds inside the beds zone
    raised = site.drainage == "waterlogs" or site.soil_type in ("black", "clay")
    candidates: list[tuple[Polygon, int, float, int]] = []
    for piece in _parts(remaining):
        tiles, along_axis = _tile_beds(piece, p)
        if not tiles:
            continue  # a leftover sliver with no room for a bed stays unassigned
        zones.append(ZoneResult("beds", "beds", piece, piece.area))
        zone_index = len(zones) - 1
        if along_axis and not any(w["code"] == "BEDS_ALONG_MAIN_AXIS" for w in warnings):
            warnings.append({"code": "BEDS_ALONG_MAIN_AXIS", "message_key": "warn.beds_axis"})
        candidates += [(poly, col, ori, zone_index) for poly, col, ori in tiles]
    # covered beds inside the polyhouse
    covered = set()
    for zi, z in enumerate(list(zones)):
        if z.kind != "polyhouse":
            continue
        tiles, _ = _tile_beds(z.geom, p)
        for poly, col, ori in tiles:
            covered.add(id(poly))
            candidates.append((poly, col, ori, zi))
    # B1, B2... from the gate side
    candidates.sort(key=lambda c: _bed_order(c[0], gate))
    beds = []
    for n, (poly, col, orientation, zone_index) in enumerate(candidates, start=1):
        length, width = _dimensions(poly)
        beds.append(
            BedResult(
                code=f"B{n}", zone_index=zone_index, geom=poly, length_m=length, width_m=width,
                raised=raised, orientation_deg=orientation, has_trellis=col % 2 == 0,
                protected=id(poly) in covered,
            )
        )  # fmt: skip
    # label beds zones
    beds_zones = [z for z in zones if z.kind == "beds"]
    for i, z in enumerate(beds_zones):
        z.label = "beds" if len(beds_zones) == 1 else f"beds {i + 1}"
    if not beds:
        raise LayoutError("PLAN_NO_ROOM", {"reason": "no_bed_fits"})

    # 11. invariants
    _verify(parcel, zones, beds)
    width = p.border_m[template]
    hedge = main.buffer(-width / 2, join_style="mitre")
    hedge_line = hedge.exterior if isinstance(hedge, Polygon) and not hedge.is_empty else None
    return LayoutResult(
        template, parcel.area, zones, beds, warnings, frame,
        hedge_line=hedge_line, gate=gate, gate_gap_m=p.gate_opening_m,
    )  # fmt: skip


__all__ = ["ENGINE_VERSION", "EngineParams", "LayoutError", "SiteInputs", "generate"]
