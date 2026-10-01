import type { Lang } from "../i18n";

const LOCALE: Record<Lang, string> = { en: "en-IN", hi: "hi-IN" };

/** Indian digit grouping: 100000 -> "1,00,000" (Latin digits in both languages). */
export function formatNumber(value: number, lang: Lang, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat(`${LOCALE[lang]}-u-nu-latn`, { maximumFractionDigits }).format(
    value,
  );
}

/** Money is stored in integer paise; display rounds to rupees. */
export function formatRupees(paise: number, lang: Lang): string {
  return "₹" + formatNumber(Math.round(paise / 100), lang);
}

/** "28 Sep" / "28 सितंबर". Dates are shown in Asia/Kolkata. */
export function formatDayMonth(date: Date, lang: Lang): string {
  return new Intl.DateTimeFormat(`${LOCALE[lang]}-u-nu-latn`, {
    day: "numeric",
    month: lang === "hi" ? "long" : "short",
    timeZone: "Asia/Kolkata",
  }).format(date);
}

const SQFT_PER_SQM = 10.7639104167;
export type UnitPref = "sqft" | "acre" | "bigha" | "sqm";

/** Area in the user's preferred unit (bigha only when the user has set its size). */
export function formatArea(
  sqm: number,
  unit: UnitPref,
  lang: Lang,
  bighaSqft?: number | null,
): { key: string; n: string } {
  const sqft = sqm * SQFT_PER_SQM;
  if (unit === "bigha" && bighaSqft && bighaSqft > 0) {
    return { key: "area.bigha", n: formatNumber(sqft / bighaSqft, lang, 2) };
  }
  if (unit === "acre") return { key: "area.acre", n: formatNumber(sqft / 43560, lang, 3) };
  if (unit === "sqm") return { key: "area.sqm", n: formatNumber(sqm, lang, 1) };
  return { key: "area.sqft", n: formatNumber(sqft, lang, 0) };
}

export const FEET_PER_METRE = 3.28083989501;
