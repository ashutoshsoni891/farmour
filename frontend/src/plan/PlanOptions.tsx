import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatNumber } from "../lib/format";
import { ZONE_COLORS } from "../setup/PlotMap";

type Options = components["schemas"]["OptionsOut"];
type Option = components["schemas"]["OptionOut"];

const LEVEL_DOTS: Record<string, number> = { low: 1, medium: 2, high: 3 };
const BAR_ORDER = [
  "beds",
  "polyhouse",
  "orchard",
  "rotation",
  "water",
  "livestock",
  "nursery",
  "utility",
  "border",
];

function Meter({ label, level }: { label: string; level: string }) {
  const { t } = useTranslation();
  const n = LEVEL_DOTS[level] ?? 2;
  return (
    <span className="flex items-center gap-1 text-sm" title={t(`option.level.${level}`)}>
      <span className="text-neutral-700">{label}</span>
      <span aria-label={t(`option.level.${level}`)} className="flex gap-0.5">
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            className={`inline-block h-2.5 w-3.5 rounded-sm ${i <= n ? "bg-green-700" : "bg-neutral-200"}`}
          />
        ))}
      </span>
    </span>
  );
}

function LandBar({ option }: { option: Option }) {
  const { t } = useTranslation();
  const parts = BAR_ORDER.map((k) => [k, option.land_use[k] ?? 0] as const).filter(
    ([, v]) => v > 0,
  );
  return (
    <div className="flex flex-col gap-1">
      <div className="flex h-4 w-full overflow-hidden rounded" aria-hidden="true">
        {parts.map(([k, v]) => (
          <span key={k} style={{ width: `${v * 100}%`, background: ZONE_COLORS[k] ?? "#999" }} />
        ))}
      </div>
      <p className="text-sm text-neutral-700">
        {parts
          .filter(([k]) =>
            ["beds", "polyhouse", "orchard", "rotation", "water", "livestock"].includes(k),
          )
          .map(([k, v]) => `${t(`option.land.${k}`)} ${Math.round(v * 100)}%`)
          .join(" · ")}
      </p>
    </div>
  );
}

/** The plan options side by side: what each gives and costs, so the owner can pick one. */
export function PlanOptions({
  options,
  selected,
  onSelect,
  lang,
}: {
  options: Options;
  selected: string | null;
  onSelect: (planId: string) => void;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const cards = (
    <div className="flex flex-col gap-2">
      {options.options.map((o) => {
        const on = o.plan_id === selected;
        return (
          <button
            key={o.plan_id}
            type="button"
            aria-pressed={on}
            onClick={() => onSelect(o.plan_id)}
            className={`flex flex-col gap-1.5 rounded-xl border-2 p-3 text-left ${
              on ? "border-green-800 bg-green-50 shadow" : "border-neutral-300 bg-white"
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-lg font-bold">{t(`option.${o.option}.name`)}</span>
              {o.recommended && (
                <span className="rounded-full bg-green-800 px-2 text-sm font-semibold text-white">
                  {t("option.recommended")}
                </span>
              )}
              {o.status === "active" && (
                <span className="rounded-full bg-amber-500 px-2 text-sm font-semibold text-white">
                  {t("option.active")}
                </span>
              )}
              {o.custom && (
                <span className="rounded-full border border-neutral-500 px-2 text-sm">
                  {t("option.custom")}
                </span>
              )}
            </div>
            {on && <p className="text-base text-neutral-800">{t(`option.${o.option}.what`)}</p>}
            {o.suits.length > 0 && (
              <p className="text-sm text-green-900">
                {o.suits.map((s) => t(`option.suits.${s}`)).join(" · ")}
              </p>
            )}
            <LandBar option={o} />
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              <Meter label={t("option.harvest")} level={o.levels["harvest"] ?? "medium"} />
              <Meter label={t("option.water")} level={o.levels["water"] ?? "medium"} />
              <Meter label={t("option.work")} level={o.levels["work"] ?? "medium"} />
            </div>
            <p className="text-base">
              {t("option.numbers", {
                beds: o.metrics.beds,
                crops: o.metrics.crops_total,
                kg: formatNumber(o.metrics.harvest_kg, lang, 0),
              })}
            </p>
          </button>
        );
      })}
    </div>
  );
  if (options.active_plan_id) {
    return (
      <details className="rounded-xl border-2 border-neutral-300 p-2">
        <summary className="min-h-11 cursor-pointer text-lg font-bold text-green-900">
          {t("option.compare", { n: options.options.length })}
        </summary>
        <div className="mt-2">{cards}</div>
      </details>
    );
  }
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-xl font-bold text-green-900">{t("option.title")}</h2>
        <p className="text-base text-neutral-700">{t("option.hint")}</p>
      </div>
      {cards}
    </section>
  );
}
