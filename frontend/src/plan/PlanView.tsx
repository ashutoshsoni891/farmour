import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea, formatDayMonth, formatNumber } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { ZONE_COLORS } from "../setup/PlotMap";

type Plan = components["schemas"]["PlanOut"];
type Planting = components["schemas"]["PlantingOut"];

const LAYER_ORDER = ["climber", "middle", "surface", "underground"];

/** "rabi 2026-27" -> "रबी 2026-27" */
function seasonText(label: string, season: string, t: (k: string) => string): string {
  return label.replace(season, t(`plan.season.${season}`));
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
  selectedBed: string | null;
  onCloseBed: () => void;
}

export function PlanView(props: Props) {
  const { plan, owner, hasPlot, planning, onBuild, unit, lang, bighaSqft } = props;
  const { t } = useTranslation();
  const [seasonIdx, setSeasonIdx] = useState(0);

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
  const season = plan.seasons[Math.min(seasonIdx, Math.max(plan.seasons.length - 1, 0))];
  const inSeason = season ? plan.plantings.filter((p) => p.season_label === season.label) : [];

  // One line per crop this season: beds, first sowing, total expected harvest, the usual reason.
  const crops = new Map<string, { first: Planting; beds: Set<string>; kg: number; why: string }>();
  for (const p of inSeason) {
    const row = crops.get(p.crop.slug) ?? {
      first: p,
      beds: new Set<string>(),
      kg: 0,
      why: String(p.why["key"] ?? "plan.why.fits"),
    };
    row.beds.add(p.bed_code);
    row.kg += p.expected_yield_kg;
    if (p.planned_sow < row.first.planned_sow) row.first = p;
    if (p.why["key"] === "plan.why.companion") row.why = "plan.why.companion";
    crops.set(p.crop.slug, row);
  }
  const cropRows = [...crops.values()].sort(
    (a, b) =>
      LAYER_ORDER.indexOf(a.first.layer) - LAYER_ORDER.indexOf(b.first.layer) ||
      b.beds.size - a.beds.size,
  );

  const byKind = new Map<string, number>();
  for (const z of plan.zones) byKind.set(z.kind, (byKind.get(z.kind) ?? 0) + z.area_sqm);
  const kinds = [...byKind.entries()].filter(([k]) => k !== "path").sort((a, b) => b[1] - a[1]);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-green-900">{t("farm.plan_title")}</h2>
      <p className="text-lg">{t("farm.plan_beds", { n: plan.beds.length })}</p>

      {plan.uses_ai_checked && (
        <p className="rounded-lg bg-sky-50 p-3 text-base">{t("farm.plan_ai_note")}</p>
      )}

      {props.selectedBed && (
        <BedDetails plan={plan} code={props.selectedBed} lang={lang} onClose={props.onCloseBed} />
      )}

      {plan.seasons.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-lg font-bold">{t("farm.plan_what_grows")}</h3>
          <div className="flex flex-wrap gap-2" role="tablist">
            {plan.seasons.map((s, i) => (
              <button
                key={s.label}
                type="button"
                role="tab"
                aria-selected={s.label === season?.label}
                onClick={() => setSeasonIdx(i)}
                className={`min-h-11 rounded-full border-2 px-4 text-base font-semibold ${
                  s.label === season?.label
                    ? "border-green-800 bg-green-800 text-white"
                    : "border-neutral-400 bg-white"
                }`}
              >
                {seasonText(s.label, s.season, t)}
              </button>
            ))}
          </div>
          {season && (
            <p className="text-base text-neutral-700">
              {t("farm.plan_season_dates", {
                from: formatDayMonth(new Date(season.begin), lang),
                to: formatDayMonth(new Date(season.end), lang),
              })}
            </p>
          )}
          <ul className="flex flex-col gap-2">
            {cropRows.map((r) => (
              <li
                key={r.first.crop.slug}
                className="rounded-lg border-l-4 border-green-700 bg-white px-3 py-2"
              >
                <p className="text-lg font-semibold">
                  {name(r.first)}{" "}
                  <span className="text-base font-normal text-neutral-700">
                    · {t(`plan.layer.${r.first.layer}`)}
                  </span>
                </p>
                <p className="text-base">
                  {t("farm.plan_crop_line", {
                    beds: r.beds.size,
                    date: formatDayMonth(new Date(r.first.planned_sow), lang),
                    kg: formatNumber(r.kg, lang, 0),
                  })}
                </p>
                <p className="text-sm text-neutral-700">{t(r.why)}</p>
              </li>
            ))}
          </ul>
          <p className="text-sm text-neutral-600">{t("farm.plan_tap_bed")}</p>
        </div>
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

function BedDetails({
  plan,
  code,
  lang,
  onClose,
}: {
  plan: Plan;
  code: string;
  lang: Lang;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const bed = plan.beds.find((b) => b.code === code);
  if (!bed) return null;
  const rows = plan.plantings.filter((p) => p.bed_code === code);
  return (
    <div className="flex flex-col gap-2 rounded-xl border-2 border-green-800 bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xl font-bold">{t("farm.bed_title", { code })}</p>
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
          onClick={onClose}
          aria-label={t("farm.bed_close")}
          className="min-h-11 min-w-11 rounded-lg border-2 border-neutral-400 text-lg"
        >
          ×
        </button>
      </div>
      {plan.seasons.map((s) => {
        const inSeason = rows.filter((r) => r.season_label === s.label);
        if (!inSeason.length) return null;
        return (
          <div key={s.label}>
            <p className="font-semibold">{seasonText(s.label, s.season, t)}</p>
            <ul className="flex flex-col">
              {inSeason.map((r) => (
                <li key={r.layer + r.crop.slug} className="text-base">
                  {lang === "hi" ? r.crop.name_hi : r.crop.name_en} · {t(`plan.layer.${r.layer}`)} ·{" "}
                  {t("farm.bed_sow", {
                    date: formatDayMonth(new Date(r.planned_sow), lang),
                    n: formatNumber(r.plant_count, lang, 0),
                  })}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
