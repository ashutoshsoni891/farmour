import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { ZONE_COLORS } from "../setup/PlotMap";
import { FieldCrops } from "./FieldCrops";
import { MachanGuide } from "./MachanGuide";
import { MedicinalMarkets } from "./MedicinalMarkets";
import { Methods } from "./Methods";
import { Perennials } from "./Perennials";
import type { GuideStep } from "./MachanGuide";

type Plan = components["schemas"]["PlanOut"];

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
    <div
      className="pointer-events-auto flex gap-2 overflow-x-auto pb-1"
      role="tablist"
      aria-label={t("farm.plan_what_grows")}
    >
      {plan.seasons.map((s, i) => (
        <button
          key={s.label}
          type="button"
          role="tab"
          aria-selected={i === index}
          onClick={() => onPick(i)}
          className={`min-h-11 shrink-0 rounded-full border-2 px-4 text-base font-semibold shadow ${
            i === index
              ? "border-green-800 bg-green-800 text-white"
              : "border-white bg-white/95 text-neutral-900"
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
  methods?: string[] | undefined;
}

export function PlanView(props: Props) {
  const { plan, owner, hasPlot, planning, onBuild, unit, lang, bighaSqft } = props;
  const { t } = useTranslation();

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

  const byKind = new Map<string, number>();
  for (const z of plan.zones) byKind.set(z.kind, (byKind.get(z.kind) ?? 0) + z.area_sqm);
  const kinds = [...byKind.entries()].filter(([k]) => k !== "path").sort((a, b) => b[1] - a[1]);
  const hasClimbers = plan.plantings.some((p) => p.layer === "climber");

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-green-900">{t("farm.plan_title")}</h2>
      <p className="text-lg">{t("farm.plan_beds", { n: plan.beds.length })}</p>
      {plan.uses_ai_checked && (
        <p className="rounded-lg bg-sky-50 p-3 text-base">{t("farm.plan_ai_note")}</p>
      )}
      <Methods
        plan={plan}
        methods={props.methods ?? []}
        unit={unit}
        lang={lang}
        bighaSqft={bighaSqft}
      />
      <MedicinalMarkets plan={plan} lang={lang} />
      <Perennials items={plan.perennials} lang={lang} />
      <FieldCrops items={plan.fields} unit={unit} lang={lang} bighaSqft={bighaSqft} />

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
