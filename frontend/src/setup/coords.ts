/** Parse "22.8456, 75.8933" (also "22.8456 N 75.8933 E", or a pair pasted from Google Maps). */
export function parsePoint(text: string): [number, number] | null {
  const nums = text.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? [];
  if (nums.length < 2) return null;
  let [lat, lng] = [nums[0] ?? NaN, nums[1] ?? NaN];
  // In India latitude is 6-38 and longitude 68-98: swap if typed the other way round.
  if (lat > 60 && lng < 40) [lat, lng] = [lng, lat];
  if (!(lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180)) return null;
  return [lng, lat];
}

/** One "lat, long" per line, at least 3 corners -> a closed GeoJSON polygon ring. */
export function parseCorners(text: string): { type: "Polygon"; coordinates: number[][][] } | null {
  const pts = text
    .split(/\n|;/)
    .map((line) => parsePoint(line))
    .filter((p): p is [number, number] => p !== null);
  if (pts.length < 3) return null;
  const ring = pts.map(([lng, lat]) => [lng, lat]);
  const first = ring[0] ?? [0, 0];
  const last = ring[ring.length - 1] ?? [0, 0];
  if (first[0] !== last[0] || first[1] !== last[1]) ring.push([first[0] ?? 0, first[1] ?? 0]);
  return { type: "Polygon", coordinates: [ring] };
}
