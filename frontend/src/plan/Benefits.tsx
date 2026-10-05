import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatDayMonth } from "../lib/format";

type Scheme = components["schemas"]["SchemeOut"];

const TYPE_COLOUR: Record<string, string> = {
  direct_benefit: "bg-emerald-700",
  subsidy: "bg-green-800",
  interest_rebate: "bg-sky-800",
  loan: "bg-sky-800",
  insurance: "bg-indigo-700",
  training: "bg-amber-700",
};

/** Government schemes this plan may be eligible for: what it gives, why it is shown, where to
 * apply and where the facts come from. Always "may be eligible": the department decides. */
export function Benefits({ schemes, lang }: { schemes: Scheme[]; lang: Lang }) {
  const { t } = useTranslation();
  if (schemes.length === 0) return null;
  const pick = (en: string | null | undefined, hi: string | null | undefined) =>
    (lang === "hi" ? hi : en) ?? en ?? "";
  return (
    <section className="flex flex-col gap-3 rounded-xl border-2 border-emerald-800 bg-emerald-50 p-3">
      <div>
        <h2 className="text-xl font-bold text-emerald-900">{t("benefit.title")}</h2>
        <p className="text-base text-neutral-800">{t("benefit.hint", { n: schemes.length })}</p>
      </div>
      <ul className="flex flex-col gap-2">
        {schemes.map((s) => (
          <li key={s.code}>
            <details className="rounded-lg border border-emerald-700 bg-white p-2">
              <summary className="flex min-h-11 cursor-pointer flex-col gap-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-lg font-semibold">{pick(s.name_en, s.name_hi)}</span>
                  <span
                    className={`rounded-full px-2 text-sm text-white ${TYPE_COLOUR[s.benefit_type] ?? "bg-neutral-700"}`}
                  >
                    {t(`benefit.type.${s.benefit_type}`)}
                  </span>
                  {s.level === "state" && (
                    <span className="rounded-full border border-neutral-500 px-2 text-sm">
                      {t("benefit.state_scheme")}
                    </span>
                  )}
                </span>
                <span className="text-base">{pick(s.gives_en, s.gives_hi)}</span>
                <span className="text-sm text-emerald-900">
                  {t("benefit.why")}:{" "}
                  {s.reasons.map((r) => t(`benefit.reason.${r.replace(":", "_")}`)).join(" · ")}
                </span>
              </summary>
              <div className="mt-2 flex flex-col gap-2 text-base">
                <p>
                  <span className="font-semibold">{t("benefit.who")}: </span>
                  {pick(s.eligibility_en, s.eligibility_hi)}
                </p>
                {s.conditions.length > 0 && (
                  <p className="rounded bg-amber-50 p-2">
                    <span className="font-semibold">{t("benefit.check")}: </span>
                    {s.conditions.map((c) => t(`benefit.${c}`)).join(" · ")}
                  </p>
                )}
                <p>
                  <span className="font-semibold">{t("benefit.documents")}: </span>
                  {s.documents.length > 0
                    ? s.documents
                        .map((d) => pick(String(d["en"] ?? ""), String(d["hi"] ?? "")))
                        .join(", ")
                    : t("benefit.documents_ask")}
                </p>
                <p>
                  <span className="font-semibold">{t("benefit.apply")}: </span>
                  {pick(s.apply_en, s.apply_hi)}
                  {s.apply_url && (
                    <>
                      {" "}
                      <a
                        href={s.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-800 underline"
                      >
                        {t("benefit.open_portal")}
                      </a>
                    </>
                  )}
                </p>
                <p className="text-sm text-neutral-700">
                  {t("benefit.sources")}:{" "}
                  {s.sources
                    .filter((src, i, all) => all.findIndex((x) => x.url === src.url) === i)
                    .map((src, i) => (
                      <span key={`${src.url ?? ""}-${i}`}>
                        {i > 0 ? " · " : ""}
                        {src.url ? (
                          <a href={src.url} target="_blank" rel="noreferrer" className="underline">
                            {src.title}
                          </a>
                        ) : (
                          src.title
                        )}
                      </span>
                    ))}
                  {s.checked_on &&
                    ` · ${t("benefit.checked", { date: formatDayMonth(new Date(s.checked_on), lang) })}`}
                  {s.ai_checked ? ` · ${t("benefit.ai_checked")}` : ""}
                </p>
              </div>
            </details>
          </li>
        ))}
      </ul>
      <p className="text-sm text-neutral-800">{t("benefit.disclaimer")}</p>
    </section>
  );
}
