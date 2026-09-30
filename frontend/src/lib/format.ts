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
