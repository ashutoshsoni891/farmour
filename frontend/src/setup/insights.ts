import type { TFunction } from "i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatNumber } from "../lib/format";

type Fact = components["schemas"]["FactOut"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthName(i: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { month: "short" }).format(
    new Date(2000, i, 1),
  );
}

/** Plain-language takeaways from site facts. Only statements the data (or a spec rule)
 * supports; no agronomy advice is invented here. */
export function insights(facts: Fact[], t: TFunction, lang: Lang): string[] {
  const by = Object.fromEntries(facts.map((f) => [f.key, f.value as unknown]));
  const n = (v: number, d = 0) => formatNumber(v, lang, d);
  const out: string[] = [];

  const region = by["region"] as { name_en: string; name_hi: string } | undefined;
  if (region)
    out.push(t("insight.region", { region: lang === "hi" ? region.name_hi : region.name_en }));

  const soil = by["soil.type"];
  if (soil === "clay" || soil === "black") out.push(t("insight.soil_heavy")); // spec 7: raised beds
  if (soil === "sandy") out.push(t("insight.soil_sandy"));

  const rain = by["climate.rain_monthly_mm"] as number[] | undefined;
  const total = by["climate.annual_rain_mm"] as number | undefined;
  if (rain?.length === 12 && total) {
    const wet = rain.map((mm, i) => (mm >= 100 ? i : -1)).filter((i) => i >= 0);
    if (wet.length) {
      out.push(
        t("insight.rain", {
          mm: n(total),
          from: monthName(wet[0] ?? 0, lang),
          to: monthName(wet[wet.length - 1] ?? 0, lang),
        }),
      );
    }
  }
  const hot = by["climate.hottest_month"] as { month: string; tmax_c: number } | undefined;
  if (hot)
    out.push(
      t("insight.heat", { c: n(hot.tmax_c), month: monthName(MONTHS.indexOf(hot.month), lang) }),
    );

  const gw = by["water.groundwater_class"] as { category: string } | undefined;
  if (gw && (gw.category === "critical" || gw.category === "over_exploited")) {
    out.push(t("insight.groundwater_stress")); // spec 7: water penalty doubles
  }

  type Route = { name: string; distance_km: number; minutes: number; method: string };
  const mandi = (by["markets.nearest"] as Route[] | undefined)?.[0];
  if (mandi) out.push(t("insight.mandi", { name: mandi.name, km: n(mandi.distance_km) }));
  const city = (by["markets.reference"] as Route[] | undefined)?.[0];
  if (city) {
    out.push(
      city.method === "osrm"
        ? t("insight.city_road", { name: city.name, min: n(city.minutes) })
        : t("insight.city_line", { name: city.name, km: n(city.distance_km) }),
    );
  }
  return out;
}
