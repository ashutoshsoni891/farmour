import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea, formatDayMonth, formatNumber } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { ZONE_COLORS } from "../setup/PlotMap";
import { BedPicture } from "./BedPicture";
import { BedTimeline } from "./BedTimeline";
import { MachanGuide } from "./MachanGuide";
import { SwapPicker } from "./SwapPicker";
import type { GuideStep } from "./MachanGuide";
import { cropStyle, plantingsOf } from "./cropStyle";

type Plan = components["schemas"]["PlanOut"];
type Planting = components["schemas"]["PlantingOut"];
type Alternative = components["schemas"]["AlternativeOut"];

/** "rabi 2026-27" -> "रबी 2026-27" */
export function seasonText(label: string, season: string, t: (k: string) => string): string {
  return label.replace(season, t(`plan.season.${season}`));
}

export function SeasonTabs({
  plan,
  index,
  onPick,
}: {
  plan: Plan;
  index: number;
  onPick: (i: number) => void;
}) {
  const { t } = useTranslation();
  if (plan.seasons.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label={t("farm.plan_what_grows")}>
      {plan.seasons.map((s, i) => (
        <button
          key={s.label}
          type="button"
          role="tab"
          aria-selected={i === index}
          onClick={() => onPick(i)}
          className={`min-h-11 rounded-full border-2 px-4 text-base font-semibold ${
            i === index ? "border-green-800 bg-green-800 text-white" : "border-neutral-400 bg-white"
          }`}
        >
          {seasonText(s.label, s.season, t)}
        </button>
      ))}
    </div>
  );
}

interface Props {
  plan: Plan | null;
  owner: boolean;
  hasPlot: boolean;
  planning: boolean;
  onBuild: () => void;
  unit: UnitPref;
  lang: Lang;
  bighaSqft: number | null;
  seasonIndex: number;
  selectedBed: string | null;
  onCloseBed: () => void;
  highlight: string | null;
  onHighlight: (slug: string | null) => void;
  /** Owner only: crops that may replace one bed layer, and the swap itself. */
  loadAlternatives?:
    ((code: string, season: string, layer: string) => Promise<Alternative[]>) | undefined;
  onSwap?:
    ((code: string, season: string, layer: string, slug: string) => Promise<void>) | undefined;
}

export function PlanView(props: Props) {
  const { plan, owner, hasPlot, planning, onBuild, unit, lang, bighaSqft } = props;
  const { loadAlternatives, onSwap } = props;
  const { t } = useTranslation();
  const [swapLayer, setSwapLayer] = useState<string | null>(null);

  if (!plan) {
    return (
      <section className="flex flex-col gap-2 rounded-lg bg-green-50 p-3">
        <p className="text-base">{t("farm.plan_none")}</p>
        {owner && hasPlot && (
          <button
            type="button"
            disabled={planning}
            onClick={onBuild}
            className="min-h-12 rounded-xl bg-green-800 px-5 text-lg font-semibold text-white disabled:opacity-50"
          >
            {planning ? t("farm.plan_building") : t("farm.plan_build")}
          </button>
        )}
      </section>
    );
  }

  const name = (p: Planting) => (lang === "hi" ? p.crop.name_hi : p.crop.name_en);
  const season = plan.seasons[Math.min(props.seasonIndex, Math.max(plan.seasons.length - 1, 0))];
  const inSeason = plantingsOf(plan, season?.label);

  // One chip per crop this season, with the number of beds it is in.
  const crops = new Map<string, { first: Planting; beds: Set<string>; kg: number }>();
  for (const p of inSeason) {
    const row = crops.get(p.crop.slug) ?? { first: p, beds: new Set<string>(), kg: 0 };
    row.beds.add(p.bed_code);
    row.kg += p.expected_yield_kg;
    if (p.planned_sow < row.first.planned_sow) row.first = p;
    crops.set(p.crop.slug, row);
  }
  const chips = [...crops.values()].sort((a, b) => b.beds.size - a.beds.size);
  const picked = props.highlight ? crops.get(props.highlight) : undefined;

  const byKind = new Map<string, number>();
  for (const z of plan.zones) byKind.set(z.kind, (byKind.get(z.kind) ?? 0) + z.area_sqm);
  const kinds = [...byKind.entries()].filter(([k]) => k !== "path").sort((a, b) => b[1] - a[1]);

  const bed = props.selectedBed ? plan.beds.find((b) => b.code === props.selectedBed) : undefined;
  const bedRows = bed ? inSeason.filter((p) => p.bed_code === bed.code) : [];
  const allBedRows = bed ? plan.plantings.filter((p) => p.bed_code === bed.code) : [];
  const hasClimbers = plan.plantings.some((p) => p.layer === "climber");

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-green-900">{t("farm.plan_title")}</h2>
      <p className="text-lg">{t("farm.plan_beds", { n: plan.beds.length })}</p>
      {plan.uses_ai_checked && (
        <p className="rounded-lg bg-sky-50 p-3 text-base">{t("farm.plan_ai_note")}</p>
      )}

      {season && (
        <div className="flex flex-col gap-2">
          <p className="text-base text-neutral-700">
            {t("farm.plan_season_dates", {
              from: formatDayMonth(new Date(season.begin), lang),
              to: formatDayMonth(new Date(season.end), lang),
            })}
            {" · "}
            {t("farm.plan_tap_bed")}
          </p>
          <div className="flex flex-wrap gap-2">
            {chips.map((r) => {
              const s = cropStyle(r.first.crop.slug);
              const on = props.highlight === r.first.crop.slug;
              return (
                <button
                  key={r.first.crop.slug}
                  type="button"
                  aria-pressed={on}
                  onClick={() => props.onHighlight(on ? null : r.first.crop.slug)}
                  className={`flex min-h-11 items-center gap-2 rounded-full border-2 px-3 text-base ${
                    on ? "bg-neutral-900 text-white" : "bg-white"
                  }`}
                  style={{ borderColor: s.color }}
                >
                  <span aria-hidden="true">{s.emoji}</span>
                  <span className="font-semibold">{name(r.first)}</span>
                  <span
                    className="rounded-full px-2 text-sm text-white"
                    style={{ background: s.color }}
                  >
                    {r.beds.size}
                  </span>
                </button>
              );
            })}
          </div>
          {picked && (
            <p className="rounded-lg bg-neutral-100 p-2 text-base">
              {t("farm.plan_crop_line", {
                beds: picked.beds.size,
                date: formatDayMonth(new Date(picked.first.planned_sow), lang),
                kg: formatNumber(picked.kg, lang, 0),
              })}
              <br />
              <span className="text-sm text-neutral-700">
                {t(String(picked.first.why["key"] ?? "plan.why.fits"))}
              </span>
            </p>
          )}
        </div>
      )}

      {bed && (
        <div className="flex flex-col gap-3 rounded-xl border-2 border-green-800 bg-white p-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xl font-bold">{t("farm.bed_title", { code: bed.code })}</p>
              <p className="text-base text-neutral-700">
                {t("farm.bed_size", {
                  length: formatNumber(bed.length_m, lang, 1),
                  width: formatNumber(bed.width_m, lang, 1),
                })}
                {bed.raised ? ` · ${t("farm.bed_raised")}` : ""}
                {bed.has_trellis ? ` · ${t("farm.bed_trellis")}` : ""}
              </p>
            </div>
            <button
              type="button"
              onClick={props.onCloseBed}
              aria-label={t("farm.bed_close")}
              className="min-h-11 min-w-11 rounded-lg border-2 border-neutral-400 text-lg"
            >
              ×
            </button>
          </div>
          <BedPicture
            onChange={props.loadAlternatives && season ? setSwapLayer : undefined}
            bed={bed}
            rows={bedRows}
            trellisM={plan.trellis_height_m ?? null}
            widthM={plan.bed_width_m ?? null}
            pathM={plan.path_width_m ?? null}
            lang={lang}
          />
          {swapLayer && season && loadAlternatives && onSwap && (
            <SwapPicker
              key={`${bed.code}-${season.label}-${swapLayer}`}
              load={() => loadAlternatives(bed.code, season.label, swapLayer)}
              onPick={async (slug) => {
                await onSwap(bed.code, season.label, swapLayer, slug);
                setSwapLayer(null);
              }}
              onClose={() => setSwapLayer(null)}
              lang={lang}
            />
          )}
          <BedTimeline rows={allBedRows} start={plan.start_date} lang={lang} />
        </div>
      )}

      {hasClimbers && plan.machan_guide.length > 0 && (
        <MachanGuide
          steps={plan.machan_guide as unknown as GuideStep[]}
          heightM={plan.trellis_height_m ?? null}
          bedM={plan.bed_width_m ?? null}
          lang={lang}
        />
      )}

      <details>
        <summary className="min-h-11 cursor-pointer text-base font-semibold text-green-800">
          {t("farm.plan_land_use")}
        </summary>
        <ul className="mt-2 flex flex-col gap-1">
          {kinds.map(([kind, sqm]) => {
            const a = formatArea(sqm, unit, lang, bighaSqft);
            return (
              <li key={kind} className="flex items-center gap-2 text-lg">
                <span
                  aria-hidden="true"
                  className="inline-block h-4 w-4 shrink-0 rounded"
                  style={{ background: ZONE_COLORS[kind] ?? "#16a34a" }}
                />
                <span className="font-semibold">{t(`plan.zone.${kind}`)}</span>
                <span className="text-neutral-700">{t(a.key, { n: a.n })}</span>
              </li>
            );
          })}
        </ul>
      </details>

      {plan.warnings.map((w) => (
        <p key={w.code + JSON.stringify(w.params)} className="rounded-lg bg-amber-50 p-3 text-base">
          {t(w.message_key, {
            ...w.params,
            season: w.params["season"]
              ? seasonText(
                  String(w.params["season"]),
                  String(w.params["season"]).split(" ")[0] ?? "",
                  t,
                )
              : undefined,
          })}
        </p>
      ))}
      <p className="text-sm text-neutral-600">{t("farm.plan_estimates")}</p>
      {owner && (
        <button
          type="button"
          disabled={planning}
          onClick={onBuild}
          className="min-h-11 self-start text-lg font-semibold text-green-800 underline disabled:opacity-50"
        >
          {planning ? t("farm.plan_building") : t("farm.plan_rebuild")}
        </button>
      )}
    </section>
  );
}
