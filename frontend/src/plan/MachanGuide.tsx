import { useTranslation } from "react-i18next";

import type { Lang } from "../i18n";

export interface GuideStep {
  en: string;
  hi: string;
  source?: { url?: string; title?: string };
}

/** How to build the machan (trellis): a drawing, then the steps with where each comes from. */
export function MachanGuide({
  steps,
  heightM,
  bedM,
  lang,
}: {
  steps: GuideStep[];
  heightM: number | null;
  bedM: number | null;
  lang: Lang;
}) {
  const { t } = useTranslation();
  return (
    <details className="rounded-xl border-2 border-amber-700 bg-amber-50 p-3">
      <summary className="min-h-11 cursor-pointer text-lg font-bold text-amber-900">
        {t("machan.title")}
      </summary>
      <div className="mt-2 flex flex-col gap-3">
        <p className="text-base">{t("machan.what")}</p>
        <svg
          viewBox="0 0 320 210"
          role="img"
          aria-label={t("machan.alt")}
          className="w-full rounded-lg bg-sky-100"
        >
          <rect y="170" width="320" height="40" fill="#78350f" />
          <rect y="170" width="320" height="5" fill="#4d7c0f" />
          <rect x="40" y="30" width="7" height="142" fill="#92400e" />
          <rect x="273" y="30" width="7" height="142" fill="#92400e" />
          <rect x="36" y="30" width="248" height="8" rx="2" fill="#92400e" />
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <g key={i} stroke="#b45309" strokeWidth="1.3">
              <line x1={56 + i * 38} y1="38" x2={80 + i * 38} y2="168" />
              <line x1={80 + i * 38} y1="38" x2={56 + i * 38} y2="168" />
            </g>
          ))}
          <g fill="#0f172a" stroke="#0f172a" fontSize="12">
            <line x1="14" y1="30" x2="14" y2="170" strokeWidth="1.2" />
            <line x1="8" y1="30" x2="20" y2="30" strokeWidth="1.2" />
            <line x1="8" y1="170" x2="20" y2="170" strokeWidth="1.2" />
            {heightM !== null && (
              <text x="4" y="105" stroke="none" transform="rotate(-90 10 105)" textAnchor="middle">
                {heightM} m
              </text>
            )}
            {bedM !== null && (
              <text x="160" y="196" stroke="none" fill="#fde68a" textAnchor="middle">
                {t("machan.across", { w: bedM })}
              </text>
            )}
          </g>
          <text x="160" y="22" fontSize="12" textAnchor="middle" fill="#92400e">
            {t("machan.label_frame")}
          </text>
          <text x="160" y="125" fontSize="12" textAnchor="middle" fill="#7c2d12">
            {t("machan.label_rope")}
          </text>
          <text x="70" y="188" fontSize="11" fill="#fff" textAnchor="middle">
            {t("machan.label_post")}
          </text>
        </svg>
        <ol className="flex list-decimal flex-col gap-2 pl-6">
          {steps.map((s, i) => (
            <li key={i} className="text-base">
              {lang === "hi" ? s.hi : s.en}{" "}
              {s.source?.url && (
                <a
                  href={s.source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-green-800 underline"
                >
                  {t("machan.source")}
                </a>
              )}
            </li>
          ))}
        </ol>
        <p className="text-sm text-neutral-700">{t("machan.confirm")}</p>
      </div>
    </details>
  );
}
