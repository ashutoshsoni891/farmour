import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea, formatDayMonth, formatNumber } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { cropStyle } from "./cropStyle";

type FieldCrop = components["schemas"]["FieldPlantingOut"];

/** Crops on the plots of the rotation field, plot by plot, in the order they are sown. */
export function FieldCrops({
  items,
  unit,
  lang,
  bighaSqft,
}: {
  items: FieldCrop[];
  unit: UnitPref;
  lang: Lang;
  bighaSqft: number | null;
}) {
  const { t } = useTranslation();
  if (items.length === 0) return null;
  const plots = new Map<string, FieldCrop[]>();
  for (const f of items) plots.set(f.plot_code, [...(plots.get(f.plot_code) ?? []), f]);
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl font-bold text-green-900">{t("fields.title")}</h2>
      <p className="text-base text-neutral-700">{t("fields.hint")}</p>
      {[...plots.entries()].map(([code, rows]) => {
        const area = formatArea(rows[0]?.area_sqm ?? 0, unit, lang, bighaSqft);
        return (
          <div key={code} className="flex flex-col gap-2">
            <p className="text-lg font-semibold">
              {t("fields.plot", { code })}
              <span className="text-base font-normal text-neutral-700">
                {" · "}
                {t(area.key, { n: area.n })}
              </span>
            </p>
            <ul className="flex flex-col gap-2">
              {rows.map((f) => {
                const s = cropStyle(f.crop.slug);
                const manure = f.why["key"] === "plan.why.green_manure";
                return (
                  <li
                    key={f.season_label + f.crop.slug}
                    className="rounded-lg border bg-white px-3 py-2"
                    style={{ borderLeft: `6px solid ${s.color}` }}
                  >
                    <p className="text-lg font-semibold">
                      <span aria-hidden="true">{s.emoji} </span>
                      {lang === "hi" ? f.crop.name_hi : f.crop.name_en}
                    </p>
                    <p className="text-base">
                      {t("fields.sow", { date: formatDayMonth(new Date(f.planned_sow), lang) })}
                      {f.harvest_end &&
                        ` · ${t(manure ? "fields.dig_in" : "fields.harvest", {
                          date: formatDayMonth(new Date(f.harvest_end), lang),
                        })}`}
                      {!manure &&
                        f.expected_yield_kg > 0 &&
                        ` · ${t("fields.kg", { kg: formatNumber(f.expected_yield_kg, lang, 0) })}`}
                    </p>
                    <p className="text-sm text-neutral-700">
                      {t(String(f.why["key"] ?? "plan.why.fits"))}
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
