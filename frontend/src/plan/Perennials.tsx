import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatDayMonth, formatNumber } from "../lib/format";
import { cropStyle } from "./cropStyle";

type Perennial = components["schemas"]["PerennialOut"];

function monthYear(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(`${lang === "hi" ? "hi-IN" : "en-IN"}-u-nu-latn`, {
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}

/** Trees in the orchard strip and the hedge on the border: how many, when to plant, when they bear. */
export function Perennials({ items, lang }: { items: Perennial[]; lang: Lang }) {
  const { t } = useTranslation();
  if (items.length === 0) return null;
  const trees = items.filter((p) => p.kind === "tree");
  const hedge = items.filter((p) => p.kind === "hedge");
  const card = (p: Perennial) => {
    const s = cropStyle(p.crop.slug);
    return (
      <li
        key={p.kind + p.crop.slug}
        className="rounded-lg border bg-white px-3 py-2"
        style={{ borderLeft: `6px solid ${s.color}` }}
      >
        <p className="text-lg font-semibold">
          <span aria-hidden="true">{s.emoji} </span>
          {lang === "hi" ? p.crop.name_hi : p.crop.name_en}{" "}
          <span className="text-base font-normal text-neutral-700">
            · {t(p.kind === "tree" ? "perennial.trees" : "perennial.plants", { n: p.count })}
          </span>
        </p>
        <p className="text-base">
          {t("perennial.plant_on", { date: formatDayMonth(new Date(p.plant_on), lang) })}
          {" · "}
          {t("perennial.spacing", { m: formatNumber(p.spacing_m, lang, 1) })}
        </p>
        {p.first_harvest && (
          <p className="text-base">
            {t(p.kind === "tree" ? "perennial.first_fruit" : "perennial.first_harvest", {
              when: monthYear(p.first_harvest, lang),
            })}
            {p.yearly_kg_when_bearing
              ? ` · ${t("perennial.kg_year", { kg: formatNumber(p.yearly_kg_when_bearing, lang, 0) })}`
              : ""}
          </p>
        )}
      </li>
    );
  };
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl font-bold text-green-900">{t("perennial.title")}</h2>
      {trees.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-base text-neutral-800">{t("perennial.trees_hint")}</p>
          <ul className="flex flex-col gap-2">{trees.map(card)}</ul>
          <p className="rounded-lg bg-green-50 p-2 text-base">{t("perennial.intercrop")}</p>
        </div>
      )}
      {hedge.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-base text-neutral-800">{t("perennial.hedge_hint")}</p>
          <ul className="flex flex-col gap-2">{hedge.map(card)}</ul>
        </div>
      )}
    </section>
  );
}
