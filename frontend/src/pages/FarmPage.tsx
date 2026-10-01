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
import { GROUPS, buildRows } from "../setup/FoundStep";
import { PlotMap } from "../setup/PlotMap";
import type { PlotGeometry } from "../setup/PlotMap";

type Fact = components["schemas"]["FactOut"];
const link =
  "rounded-xl border-2 border-green-800 px-5 py-2 text-center text-lg font-semibold text-green-900";

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
  const rows = buildRows((profile.data?.facts ?? []) as Fact[], t, lang);
  const boundary = parcel.data?.boundary as unknown as PlotGeometry | undefined;
  const center: [number, number] = [Number(f.lng ?? 75.8577), Number(f.lat ?? 22.7196)];

  const refresh = async () => {
    setNotice(null);
    const { response } = await api.POST("/api/v1/farms/{farm_id}/site-profile/refresh", {
      params: { path: { farm_id: id } },
    });
    setNotice(response.ok ? t("farm.refresh_started") : t("err.rate_limited"));
    await queryClient.invalidateQueries({ queryKey: ["site-profile", id] });
  };

  const answers: [string, string | null | undefined][] = [
    [t("setup.where.site_type"), f.site_type ? t(`setup.site.${f.site_type}`) : null],
    [t("setup.about.water"), f.water_source ? t(`setup.water.${f.water_source}`) : null],
    [t("setup.about.goal"), f.goal ? t(`setup.goal.${f.goal}`) : null],
    [t("setup.about.labour"), f.labour ? t(`setup.labour.${f.labour}`) : null],
  ];

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
        <p className="rounded-lg bg-amber-50 p-3 text-base">{t("farm.no_plot")}</p>
      )}

      <section className="flex flex-col gap-1">
        <h2 className="text-xl font-bold text-green-900">{t("farm.setup_summary")}</h2>
        {answers.map(([label, value]) => (
          <p key={label} className="text-lg">
            <span className="font-semibold">{label}</span> {value ?? t("library.unknown")}
          </p>
        ))}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-bold text-green-900">{t("setup.found.title")}</h2>
        {profile.data?.build.status === "running" && (
          <p role="status">{t("setup.found.looking")}</p>
        )}
        {rows.length === 0 && profile.data?.build.status !== "running" && (
          <p>{t("setup.found.none")}</p>
        )}
        {GROUPS.map((g) => {
          const inGroup = rows.filter((r) => r.fact.group === g);
          if (!inGroup.length) return null;
          return (
            <div key={g} className="flex flex-col gap-1">
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
      </section>

      {owner && (
        <section className="flex flex-col gap-2">
          <Link to={`/setup/${id}?step=plot`} className={link}>
            {t("farm.edit_plot")}
          </Link>
          <Link to={`/setup/${id}?step=found`} className={link}>
            {t("farm.edit_found")}
          </Link>
          <Link to={`/setup/${id}?step=about`} className={link}>
            {t("farm.edit_about")}
          </Link>
          <button type="button" onClick={() => void refresh()} className={link}>
            {t("farm.refresh")}
          </button>
          {notice && (
            <p role="status" className="font-semibold text-green-900">
              {notice}
            </p>
          )}
        </section>
      )}

      <p className="rounded-lg bg-green-50 p-3 text-base">{t("farm.plan_soon")}</p>
    </Screen>
  );
}
