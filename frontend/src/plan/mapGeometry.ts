/** Small geometry helpers for drawing the plan on the map (display only). */

export type Ring = number[][];
export type PolygonGeometry = { type: "Polygon"; coordinates: Ring[] };

function inRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi = 0, yi = 0] = ring[i] ?? [];
    const [xj = 0, yj = 0] = ring[j] ?? [];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi || 1e-12) + xi) inside = !inside;
  }
  return inside;
}

export function inPolygon(x: number, y: number, poly: PolygonGeometry): boolean {
  const [outer, ...holes] = poly.coordinates;
  return Boolean(outer && inRing(x, y, outer) && !holes.some((h) => inRing(x, y, h)));
}

/** A point inside the polygon to put its label on: the vertex average when that falls inside,
 * else the best of a few points scanned across the shape (border rings, L-shapes). */
export function labelPoint(poly: PolygonGeometry): [number, number] {
  const ring = poly.coordinates[0] ?? [];
  const pts = ring.slice(0, Math.max(ring.length - 1, 1));
  const cx = pts.reduce((a, c) => a + (c[0] ?? 0), 0) / (pts.length || 1);
  const cy = pts.reduce((a, c) => a + (c[1] ?? 0), 0) / (pts.length || 1);
  if (inPolygon(cx, cy, poly)) return [cx, cy];
  const [minx, miny, maxx, maxy] = bounds([poly]);
  for (let k = 1; k < 12; k++) {
    for (const f of [0.5, 0.25, 0.75, 0.1, 0.9]) {
      const x = minx + ((maxx - minx) * k) / 12;
      const y = miny + (maxy - miny) * f;
      if (inPolygon(x, y, poly)) return [x, y];
    }
  }
  return [cx, cy];
}

export function bounds(polys: PolygonGeometry[]): [number, number, number, number] {
  let minx = Infinity;
  let miny = Infinity;
  let maxx = -Infinity;
  let maxy = -Infinity;
  for (const p of polys) {
    for (const c of p.coordinates[0] ?? []) {
      const [x = 0, y = 0] = c;
      minx = Math.min(minx, x);
      miny = Math.min(miny, y);
      maxx = Math.max(maxx, x);
      maxy = Math.max(maxy, y);
    }
  }
  return [minx, miny, maxx, maxy];
}
