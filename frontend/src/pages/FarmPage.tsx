import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { apiClient, errorKey } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import type { Lang } from "../i18n";
import { formatArea, formatDayMonth } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { Choice } from "../setup/Choice";
import { GROUPS, buildRows } from "../setup/FoundStep";
import { insights } from "../setup/insights";
import { PlotMap } from "../setup/PlotMap";
import type { PlotGeometry } from "../setup/PlotMap";

type Fact = components["schemas"]["FactOut"];
type FarmUpdate = components["schemas"]["FarmUpdate"];
const WATER = ["bore", "well", "canal", "municipal", "rain_only"] as const;
const GOALS = ["home_food", "income", "both"] as const;
const LABOUR = ["self", "family", "caretaker", "mixed"] as const;
const SOILS = ["black", "red", "sandy", "clay", "loam", "mixed"] as const;

export function FarmPage() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const lang = i18n.language as Lang;
  const api = apiClient(token);
  const [notice, setNotice] = useState<string | null>(null);

  const me = useQuery({
    queryKey: ["me-basic", token],
    queryFn: async () => (await api.GET("/api/v1/me")).data,
  });
  const farm = useQuery({
    queryKey: ["farm", id, token],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/farms/{farm_id}", {
        params: { path: { farm_id: id } },
      });
      if (error) throw error;
      return data;
    },
  });
  const parcel = useQuery({
    queryKey: ["parcel", id, token],
    queryFn: async () =>
      (await api.GET("/api/v1/farms/{farm_id}/parcel", { params: { path: { farm_id: id } } }))
        .data ?? null,
  });
  const profile = useQuery({
    queryKey: ["site-profile", id, token],
    queryFn: async () =>
      (await api.GET("/api/v1/farms/{farm_id}/site-profile", { params: { path: { farm_id: id } } }))
        .data,
    // Facts arrive in the background right after setup: keep checking until the build is done.
    refetchInterval: (q) =>
      ["done", "failed"].includes(q.state.data?.build.status ?? "") ? false : 3000,
  });

  if (farm.isError) {
    return (
      <Screen>
        <p role="alert" className="text-lg">
          {t(errorKey(farm.error))}
        </p>
        <Link to="/" className="text-lg font-semibold text-green-800 underline">
          {t("farm.back")}
        </Link>
      </Screen>
    );
  }
  if (!farm.data) {
    return (
      <Screen>
        <p role="status">{t("common.loading")}</p>
      </Screen>
    );
  }

  const f = farm.data;
  const owner = f.my_role === "owner";
  const unit = (me.data?.unit_pref ?? "sqft") as UnitPref;
  const area = parcel.data
    ? formatArea(
        parcel.data.area_sqm,
        unit,
        lang,
        me.data?.bigha_sqft ? Number(me.data.bigha_sqft) : null,
      )
    : null;
  const facts = (profile.data?.facts ?? []) as Fact[];
  const rows = buildRows(facts, t, lang);
  const takeaways = insights(facts, t, lang);
  const building = ["none", "running"].includes(profile.data?.build.status ?? "none");
  const boundary = parcel.data?.boundary as unknown as PlotGeometry | undefined;
  const center: [number, number] = [Number(f.lng ?? 75.8577), Number(f.lat ?? 22.7196)];
  const soil = facts.find((x) => x.key === "soil.type")?.value as string | undefined;

  const saved = async () => {
    setNotice(t("farm.saved"));
    await queryClient.invalidateQueries({ queryKey: ["farm", id] });
  };
  const patchFarm = async (body: FarmUpdate) => {
    const { response } = await api.PATCH("/api/v1/farms/{farm_id}", {
      params: { path: { farm_id: id } },
      body,
    });
    if (response.ok) await saved();
  };
  const setSoil = async (value: string) => {
    const { response } = await api.PATCH("/api/v1/farms/{farm_id}/site-profile", {
      params: { path: { farm_id: id } },
      body: { items: [{ key: "soil.type", action: "edit", value }] },
    });
    if (response.ok) {
      await queryClient.invalidateQueries({ queryKey: ["site-profile", id] });
      await saved();
    }
  };
  const refresh = async () => {
    const { response } = await api.POST("/api/v1/farms/{farm_id}/site-profile/refresh", {
      params: { path: { farm_id: id } },
    });
    setNotice(response.ok ? t("farm.refresh_started") : t("err.rate_limited"));
    await queryClient.invalidateQueries({ queryKey: ["site-profile", id] });
  };

  return (
    <Screen>
      <Link to="/" className="text-lg font-semibold text-green-800 underline">
        {t("farm.back")}
      </Link>
      <header>
        <h1 className="text-3xl font-bold">{f.name}</h1>
        <p className="text-lg text-neutral-700">
          {[f.village, f.district].filter(Boolean).join(", ")}
          {area ? ` · ${t(area.key, { n: area.n })}` : ""}
        </p>
      </header>

      {boundary ? (
        <PlotMap center={center} zoom={18} mode="view" pin={null} boundary={boundary} />
      ) : (
        <Link
          to={`/setup/${id}`}
          className="rounded-xl bg-green-800 px-5 py-3 text-center text-lg font-semibold text-white"
        >
          {t("farm.add_plot")}
        </Link>
      )}

      <p className="rounded-lg bg-green-50 p-3 text-base">{t("farm.plan_soon")}</p>

      <section className="flex flex-col gap-2">
        <h2 className="text-xl font-bold text-green-900">{t("farm.about_land")}</h2>
        {building && (
          <p role="status" className="text-lg">
            {t("setup.found.looking")}
          </p>
        )}
        {!building && takeaways.length === 0 && <p>{t("setup.found.none")}</p>}
        <ul className="flex flex-col gap-2">
          {takeaways.map((line) => (
            <li
              key={line}
              className="rounded-lg border-l-4 border-green-700 bg-white px-3 py-2 text-lg"
            >
              {line}
            </li>
          ))}
        </ul>
        {rows.length > 0 && (
          <details className="mt-1">
            <summary className="min-h-11 cursor-pointer text-base font-semibold text-green-800">
              {t("farm.see_details")}
            </summary>
            {GROUPS.map((g) => {
              const inGroup = rows.filter((r) => r.fact.group === g);
              if (!inGroup.length) return null;
              return (
                <div key={g} className="mt-2 flex flex-col gap-1">
                  <h3 className="text-lg font-bold">{t(`setup.found.group.${g}`)}</h3>
                  {inGroup.map((r) => (
                    <div key={`${r.key}-${r.label}`} className="border-b border-neutral-200 pb-1">
                      {g !== "region" && <p className="text-base font-semibold">{r.label}</p>}
                      {r.lines.map((line) => (
                        <p key={line} className="text-lg">
                          {line}
                        </p>
                      ))}
                      <p className="text-sm text-neutral-600">
                        {t("setup.found.source_line", {
                          source: t(`setup.found.src.${r.fact.source}`, {
                            defaultValue: r.fact.source,
                          }),
                          date: formatDayMonth(new Date(r.fact.fetched_at), lang),
                        })}
                      </p>
                    </div>
                  ))}
                </div>
              );
            })}
          </details>
        )}
      </section>

      {owner && (
        <section className="flex flex-col gap-4 rounded-xl border-2 border-green-800 p-4">
          <div>
            <h2 className="text-xl font-bold text-green-900">{t("farm.improve")}</h2>
            <p className="text-base text-neutral-700">{t("farm.improve_hint")}</p>
          </div>
          <Choice
            label={t("setup.about.water")}
            value={f.water_source ?? null}
            options={WATER}
            text={(o) => t(`setup.water.${o}`)}
            onPick={(o) => void patchFarm({ water_source: o })}
          />
          <Choice
            label={t("setup.about.labour")}
            value={f.labour ?? null}
            options={LABOUR}
            text={(o) => t(`setup.labour.${o}`)}
            onPick={(o) => void patchFarm({ labour: o })}
          />
          <Choice
            label={t("setup.about.goal")}
            value={f.goal ?? null}
            options={GOALS}
            text={(o) => t(`setup.goal.${o}`)}
            onPick={(o) => void patchFarm({ goal: o })}
          />
          <Choice
            label={t("farm.soil_right")}
            value={(soil as (typeof SOILS)[number] | undefined) ?? null}
            options={SOILS}
            text={(o) => t(`setup.found.soil.${o}`)}
            onPick={(o) => void setSoil(o)}
          />
          <Link
            to={`/setup/${id}`}
            className="min-h-11 text-lg font-semibold text-green-800 underline"
          >
            {t("farm.edit_plot")}
          </Link>
          <button
            type="button"
            onClick={() => void refresh()}
            className="min-h-11 self-start text-lg font-semibold text-green-800 underline"
          >
            {t("farm.refresh")}
          </button>
          {notice && (
            <p role="status" className="font-semibold text-green-900">
              {notice}
            </p>
          )}
        </section>
      )}
    </Screen>
  );
}
