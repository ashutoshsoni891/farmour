import type { components } from "../api/schema";

type Planting = components["schemas"]["PlantingOut"];
type Plan = components["schemas"]["PlanOut"];

/** How a crop looks in drawings: a colour and an emoji. Presentation only (no agronomy). */
const STYLE: Record<string, { color: string; emoji: string }> = {
  tomato: { color: "#dc2626", emoji: "🍅" },
  brinjal: { color: "#7e22ce", emoji: "🍆" },
  chilli: { color: "#ea580c", emoji: "🌶️" },
  okra: { color: "#4d7c0f", emoji: "🥒" },
  "bottle-gourd": { color: "#65a30d", emoji: "🥒" },
  cucumber: { color: "#16a34a", emoji: "🥒" },
  methi: { color: "#0d9488", emoji: "🌿" },
  spinach: { color: "#15803d", emoji: "🥬" },
  coriander: { color: "#22c55e", emoji: "🌿" },
  radish: { color: "#db2777", emoji: "🥕" },
  onion: { color: "#a21caf", emoji: "🧅" },
  peas: { color: "#84cc16", emoji: "🫛" },
};
const FALLBACK = ["#0369a1", "#b45309", "#be123c", "#4338ca", "#0f766e"];

export function cropStyle(slug: string): { color: string; emoji: string } {
  const known = STYLE[slug];
  if (known) return known;
  let h = 0;
  for (const ch of slug) h = (h * 31 + ch.charCodeAt(0)) % FALLBACK.length;
  return { color: FALLBACK[h] ?? "#0369a1", emoji: "🌱" };
}

export const LAYERS_TOP_DOWN = ["climber", "middle", "surface", "underground"] as const;
export type Layer = (typeof LAYERS_TOP_DOWN)[number];

/** The crop that gives a bed its colour on the map: main crop first, then trellis, leafy, roots. */
const COLOUR_ORDER = ["middle", "climber", "surface", "underground"];

export function plantingsOf(plan: Plan, seasonLabel: string | undefined): Planting[] {
  return seasonLabel ? plan.plantings.filter((p) => p.season_label === seasonLabel) : [];
}

export function bedColours(plan: Plan, seasonLabel: string | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  const byBed = new Map<string, Planting[]>();
  for (const p of plantingsOf(plan, seasonLabel)) {
    byBed.set(p.bed_code, [...(byBed.get(p.bed_code) ?? []), p]);
  }
  for (const [code, rows] of byBed) {
    const main = [...rows].sort(
      (a, b) => COLOUR_ORDER.indexOf(a.layer) - COLOUR_ORDER.indexOf(b.layer),
    )[0];
    if (main) out[code] = cropStyle(main.crop.slug).color;
  }
  return out;
}
