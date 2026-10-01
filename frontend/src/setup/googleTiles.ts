/** Google Map Tiles API (2D satellite) for our MapLibre map.
 *
 * Rules we follow (Google Map Tiles policies): a session token per client, the Google logo on the
 * map, and the imagery credit returned by the viewport API for what is on screen.
 * The key is public by nature; restrict it in Google Cloud to our domains and the Map Tiles API.
 */

const KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;
const STORE = "farm.gtiles.session";
const BASE = "https://tile.googleapis.com";

export const googleSatelliteEnabled = Boolean(KEY);

interface Stored {
  session: string;
  expiry: number; // unix seconds
  lang: string;
}

export async function googleSession(lang: "hi" | "en"): Promise<string | null> {
  if (!KEY) return null;
  try {
    const cached = JSON.parse(localStorage.getItem(STORE) ?? "null") as Stored | null;
    if (cached && cached.lang === lang && cached.expiry * 1000 > Date.now() + 60_000) {
      return cached.session;
    }
  } catch {
    // storage unavailable or corrupt: fetch a new session
  }
  const resp = await fetch(`${BASE}/v1/createSession?key=${encodeURIComponent(KEY)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mapType: "satellite",
      language: lang === "hi" ? "hi-IN" : "en-IN",
      region: "IN",
    }),
  });
  if (!resp.ok) return null;
  const data = (await resp.json()) as { session: string; expiry: string };
  try {
    localStorage.setItem(
      STORE,
      JSON.stringify({ session: data.session, expiry: Number(data.expiry), lang }),
    );
  } catch {
    // fine without caching
  }
  return data.session;
}

export function googleTileUrl(session: string): string {
  return `${BASE}/v1/2dtiles/{z}/{x}/{y}?session=${encodeURIComponent(session)}&key=${encodeURIComponent(KEY ?? "")}`;
}

/** Imagery credit for the visible area (must be shown on the map). */
export async function googleCredit(
  session: string,
  zoom: number,
  bounds: { north: number; south: number; east: number; west: number },
): Promise<string> {
  const q = new URLSearchParams({
    session,
    key: KEY ?? "",
    zoom: String(Math.max(0, Math.min(22, Math.round(zoom)))),
    north: bounds.north.toFixed(6),
    south: bounds.south.toFixed(6),
    east: bounds.east.toFixed(6),
    west: bounds.west.toFixed(6),
  });
  const resp = await fetch(`${BASE}/tile/v1/viewport?${q.toString()}`);
  if (!resp.ok) return "";
  const data = (await resp.json()) as { copyright?: string };
  return data.copyright ?? "";
}
