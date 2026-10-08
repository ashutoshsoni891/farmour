import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import type { Lang } from "../i18n";
import { formatRupees } from "../lib/format";

type Plan = components["schemas"]["PlanOut"];

/** For a plan that grows medicinal herbs: what the library holds as a price, where to sell, and
 * the one rule that matters most: agree a buyer and a rate before sowing. */
export function MedicinalMarkets({ plan, lang }: { plan: Plan; lang: Lang }) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const api = apiClient(token);
  const grows =
    plan.plantings.some((p) => p.crop.medicinal) || plan.fields.some((f) => f.crop.medicinal);
  const markets = useQuery({
    queryKey: ["markets", plan.id, token],
    enabled: grows,
    queryFn: async () =>
      (
        await api.GET("/api/v1/farms/{farm_id}/plan/{plan_id}/markets", {
          params: { path: { farm_id: plan.farm_id, plan_id: plan.id } },
        })
      ).data,
  });
  const data = markets.data;
  if (!grows || !data || data.herbs.length === 0) return null;
  const pick = (en: string | null | undefined, hi: string | null | undefined) =>
    (lang === "hi" ? hi : en) ?? en ?? "";
  const priced = new Set(data.prices.map((p) => p.slug));
  const unpriced = data.herbs.filter((h) => !priced.has(h.slug));
  return (
    <section className="flex flex-col gap-3 rounded-xl border-2 border-lime-800 bg-lime-50 p-3">
      <div>
        <h2 className="text-xl font-bold text-lime-900">{t("herbs.title")}</h2>
        <p className="text-base text-neutral-800">{t("herbs.rule")}</p>
      </div>
      {data.prices.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-lg font-semibold">{t("herbs.prices")}</p>
          <ul className="flex flex-col gap-1">
            {data.prices.map((p) => (
              <li key={p.slug} className="rounded-lg bg-white px-3 py-2">
                <p className="text-lg">
                  <span className="font-semibold">{lang === "hi" ? p.name_hi : p.name_en}</span>
                  {": "}
                  {t("herbs.per_kg", { price: formatRupees(p.price_paise_per_kg, lang) })}
                </p>
                {p.note && <p className="text-sm text-neutral-700">{p.note}</p>}
                {p.source_url && (
                  <a
                    href={p.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-lime-900 underline"
                  >
                    {t("herbs.source")}
                  </a>
                )}
              </li>
            ))}
          </ul>
          <p className="text-sm text-neutral-700">{t("herbs.price_caveat")}</p>
        </div>
      )}
      {unpriced.length > 0 && (
        <p className="text-base">
          {t("herbs.no_price", {
            names: unpriced.map((h) => (lang === "hi" ? h.name_hi : h.name_en)).join(", "),
          })}
        </p>
      )}
      {data.centres.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-lg font-semibold">{t("herbs.where")}</p>
          <ul className="flex flex-col gap-2">
            {data.centres.map((c) => (
              <li key={c.code} className="rounded-lg bg-white px-3 py-2">
                <p className="text-lg font-semibold">
                  {pick(c.name_en, c.name_hi)}
                  {c.district && (
                    <span className="text-base font-normal text-neutral-700">
                      {" · "}
                      {c.district}
                    </span>
                  )}
                </p>
                <p className="text-base">{pick(c.note_en, c.note_hi)}</p>
                {c.url && (
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-base text-lime-900 underline"
                  >
                    {t("herbs.open")}
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
