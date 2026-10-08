import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { ZONE_COLORS } from "../setup/PlotMap";
import { ZONE_ICON } from "./FarmMap";
import type { MapSelection } from "./FarmMap";
import { cropStyle, plantingsOf } from "./cropStyle";

type Plan = components["schemas"]["PlanOut"];

const wideScreen = () =>
  typeof window !== "undefined" && window.matchMedia?.("(min-width: 1024px)").matches;

/** What the colours on the map mean. Crops of the season (tap to light up where they grow),
 * field plots, trees and hedge, and the land areas (tap to open). */
export function MapLegend({
  plan,
  seasonLabel,
  highlight,
  onHighlight,
  onSelect,
  lang,
}: {
  plan: Plan;
  seasonLabel: string | undefined;
  highlight: string | null;
  onHighlight: (slug: string | null) => void;
  onSelect: (s: MapSelection) => void;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(wideScreen);
  const name = (c: { name_en: string; name_hi: string }) => (lang === "hi" ? c.name_hi : c.name_en);

  const crops = new Map<string, { crop: (typeof plan.plantings)[number]["crop"]; n: number }>();
  for (const p of plantingsOf(plan, seasonLabel)) {
    const row = crops.get(p.crop.slug) ?? { crop: p.crop, n: 0 };
    row.n += 1;
    crops.set(p.crop.slug, row);
  }
  // count beds, not layers
  for (const [slug, row] of crops) {
    row.n = new Set(
      plantingsOf(plan, seasonLabel)
        .filter((p) => p.crop.slug === slug)
        .map((p) => p.bed_code),
    ).size;
  }
  const fieldNow = plan.fields.filter((f) => f.season_label === seasonLabel);
  const kinds = [...new Set(plan.zones.map((z) => z.kind))].filter((k) => k !== "path");

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="pointer-events-auto flex min-h-11 items-center gap-2 rounded-xl bg-white/95 px-3 text-base font-semibold shadow"
      >
        <span aria-hidden="true">🗺️</span>
        {t("map.legend")}
      </button>
    );
  }

  const chip = (
    key: string,
    color: string,
    label: string,
    on: boolean,
    onClick: () => void,
    count?: number,
  ) => (
    <button
      key={key}
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`flex min-h-9 items-center gap-1.5 rounded-full border px-2.5 text-sm ${
        on ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 bg-white"
      }`}
    >
      <span className="inline-block h-3 w-3 shrink-0 rounded-sm" style={{ background: color }} />
      <span className="font-medium">{label}</span>
      {count !== undefined && <span className="text-neutral-500">{count}</span>}
    </button>
  );

  return (
    <div className="pointer-events-auto flex max-h-[38vh] flex-col gap-2 overflow-y-auto rounded-2xl bg-white/95 p-3 shadow-lg backdrop-blur lg:max-h-[46vh]">
      <div className="flex items-center justify-between gap-2">
        <p className="text-base font-bold">{t("map.legend")}</p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label={t("map.legend_hide")}
          className="min-h-9 min-w-9 rounded-lg text-lg text-neutral-600"
        >
          ×
        </button>
      </div>
      <p className="text-sm text-neutral-600">{t("map.tap_hint")}</p>

      {crops.size > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-neutral-700">{t("map.beds_now")}</p>
          <div className="flex flex-wrap gap-1.5">
            {[...crops.values()]
              .sort((a, b) => b.n - a.n)
              .map(({ crop, n }) =>
                chip(
                  crop.slug,
                  cropStyle(crop.slug).color,
                  `${cropStyle(crop.slug).emoji} ${name(crop)}`,
                  highlight === crop.slug,
                  () => onHighlight(highlight === crop.slug ? null : crop.slug),
                  n,
                ),
              )}
          </div>
        </div>
      )}

      {fieldNow.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-neutral-700">{t("map.plots_now")}</p>
          <div className="flex flex-wrap gap-1.5">
            {fieldNow.map((f) =>
              chip(
                `plot-${f.plot_code}`,
                cropStyle(f.crop.slug).color,
                `${f.plot_code} · ${cropStyle(f.crop.slug).emoji} ${name(f.crop)}`,
                false,
                () => onSelect({ kind: "plot", code: f.plot_code }),
              ),
            )}
          </div>
        </div>
      )}

      {plan.perennials.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold text-neutral-700">{t("map.trees")}</p>
          <div className="flex flex-wrap gap-1.5">
            {plan.perennials.map((g, i) =>
              chip(
                `plant-${i}`,
                cropStyle(g.crop.slug).color,
                `${cropStyle(g.crop.slug).emoji} ${name(g.crop)}`,
                false,
                () => onSelect({ kind: "plant", group: i }),
                g.count,
              ),
            )}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-neutral-700">{t("map.areas")}</p>
        <div className="flex flex-wrap gap-1.5">
          {kinds.map((k) => {
            const zone = plan.zones.find((z) => z.kind === k);
            return chip(
              `zone-${k}`,
              ZONE_COLORS[k] ?? "#16a34a",
              `${ZONE_ICON[k] ?? ""} ${t(`map.zone.${k}`)}`,
              false,
              () => zone && onSelect({ kind: "zone", id: zone.id }),
            );
          })}
        </div>
      </div>
    </div>
  );
}
