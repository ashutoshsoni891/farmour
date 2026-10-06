import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
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
import type { PlotGeometry, PlotLayout } from "../setup/PlotMap";
import { Benefits } from "../plan/Benefits";
import { PlanEditor } from "../plan/PlanEditor";
import { PlanOptions } from "../plan/PlanOptions";
import { PlanView, SeasonTabs } from "../plan/PlanView";
import { bedColours, cropStyle, plantingsOf } from "../plan/cropStyle";

type Fact = components["schemas"]["FactOut"];
type FarmUpdate = components["schemas"]["FarmUpdate"];
const WATER = ["bore", "well", "canal", "municipal", "rain_only"] as const;
const GOALS = ["income", "low_work", "home_food", "both"] as const;
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
  const [planning, setPlanning] = useState(false);
  const [planId, setPlanId] = useState<string | null>(null);
  const [bed, setBed] = useState<string | null>(null);
  const [seasonIndex, setSeasonIndex] = useState(0);
  const [highlight, setHighlight] = useState<string | null>(null);

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
  const options = useQuery({
    queryKey: ["plan-options", id, token],
    queryFn: async () =>
      (
        await api.GET("/api/v1/farms/{farm_id}/plan/options", {
          params: { path: { farm_id: id } },
        })
      ).data ?? null,
  });
  // The plan on screen: the one the owner tapped, else the server's pick (active or recommended).
  const plan = useQuery({
    queryKey: ["plan", id, token, planId],
    queryFn: async () =>
      (
        await api.GET("/api/v1/farms/{farm_id}/plan", {
          params: { path: { farm_id: id }, query: planId ? { plan_id: planId } : {} },
        })
      ).data ?? null,
  });
  const planIdShown = plan.data?.id;
  const benefits = useQuery({
    queryKey: ["benefits", id, token, planIdShown],
    enabled: Boolean(planIdShown),
    queryFn: async () =>
      (
        await api.GET("/api/v1/farms/{farm_id}/plan/{plan_id}/benefits", {
          params: { path: { farm_id: id, plan_id: planIdShown ?? "" } },
        })
      ).data ?? [],
  });
  const mapLayout = useMemo(() => {
    const p = plan.data;
    if (!p) return undefined;
    const label = p.seasons[Math.min(seasonIndex, Math.max(p.seasons.length - 1, 0))]?.label;
    const colours = bedColours(p, label);
    const dim = new Set(
      highlight
        ? plantingsOf(p, label)
            .filter((x) => x.crop.slug !== highlight)
            .map((x) => x.bed_code)
        : [],
    );
    const hit = new Set(
      highlight
        ? plantingsOf(p, label)
            .filter((x) => x.crop.slug === highlight)
            .map((x) => x.bed_code)
        : [],
    );
    const plants = p.perennials.flatMap((g) =>
      (g.points["coordinates"] as number[][]).map((c) => ({
        color: cropStyle(g.crop.slug).color,
        radius_m: g.kind === "tree" ? g.spacing_m * 0.4 : g.spacing_m * 0.35,
        lng: c[0] ?? 0,
        lat: c[1] ?? 0,
      })),
    );
    return {
      zones: p.zones,
      plants,
      beds: p.beds.map((b) => ({
        code: b.code,
        geometry: b.geometry,
        color: colours[b.code],
        dim: highlight !== null && !hit.has(b.code) && dim.size >= 0,
      })),
    } as unknown as PlotLayout;
  }, [plan.data, seasonIndex, highlight]);
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
  const reload = async (nextPlanId: string | null) => {
    setBed(null);
    setPlanId(nextPlanId);
    await queryClient.invalidateQueries({ queryKey: ["plan-options", id] });
    await queryClient.invalidateQueries({ queryKey: ["plan", id] });
  };
  const buildPlan = async () => {
    setPlanning(true);
    setNotice(null);
    const { response, error } = await api.POST("/api/v1/farms/{farm_id}/plan/options", {
      params: { path: { farm_id: id } },
    });
    setPlanning(false);
    if (response.ok) await reload(null);
    else setNotice(t(errorKey(error)));
  };
  const redraw = async (
    delta: Partial<Record<"orchard" | "water" | "rotation" | "utility_nursery", number>>,
    bedSize: "narrow" | "standard" | "wide",
  ) => {
    if (!plan.data) return;
    setPlanning(true);
    setNotice(null);
    const { data, error } = await api.POST("/api/v1/farms/{farm_id}/plan/{plan_id}/adjust", {
      params: { path: { farm_id: id, plan_id: plan.data.id } },
      body: { share_delta: delta, bed_size: bedSize },
    });
    setPlanning(false);
    if (data) await reload(data.id);
    else setNotice(t(errorKey(error)));
  };
  const lock = async () => {
    if (!plan.data) return;
    setPlanning(true);
    const { data, error } = await api.POST("/api/v1/farms/{farm_id}/plan/{plan_id}/lock", {
      params: { path: { farm_id: id, plan_id: plan.data.id } },
    });
    setPlanning(false);
    if (data) {
      setNotice(t("editor.locked"));
      await reload(data.id);
    } else setNotice(t(errorKey(error)));
  };
  const loadAlternatives = async (code: string, season: string, layer: string) => {
    if (!plan.data) return [];
    const { data } = await api.GET(
      "/api/v1/farms/{farm_id}/plan/{plan_id}/beds/{code}/alternatives",
      {
        params: {
          path: { farm_id: id, plan_id: plan.data.id, code },
          query: { season_label: season, layer },
        },
      },
    );
    return data ?? [];
  };
  const swapCrop = async (code: string, season: string, layer: string, slug: string) => {
    if (!plan.data) return;
    const { response, error } = await api.PUT(
      "/api/v1/farms/{farm_id}/plan/{plan_id}/beds/{code}/layers",
      {
        params: { path: { farm_id: id, plan_id: plan.data.id, code } },
        body: {
          season_label: season,
          layer: layer as "underground" | "surface" | "middle" | "climber",
          crop_slug: slug,
        },
      },
    );
    if (response.ok) {
      await queryClient.invalidateQueries({ queryKey: ["plan", id] });
      await queryClient.invalidateQueries({ queryKey: ["plan-options", id] });
    } else setNotice(t(errorKey(error)));
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

      {options.data && options.data.options.length > 0 && (
        <PlanOptions
          options={options.data}
          selected={plan.data?.id ?? null}
          onSelect={(pid) => {
            setBed(null);
            setPlanId(pid);
          }}
          lang={lang}
        />
      )}
      {owner && plan.data && (
        <PlanEditor
          key={plan.data.id}
          plan={plan.data}
          busy={planning}
          onRedraw={(d, b) => void redraw(d, b)}
          onLock={() => void lock()}
        />
      )}
      {notice && (
        <p role="status" className="font-semibold text-green-900">
          {notice}
        </p>
      )}
      {plan.data && plan.data.seasons.length > 0 && (
        <SeasonTabs plan={plan.data} index={seasonIndex} onPick={setSeasonIndex} />
      )}
      {boundary ? (
        <PlotMap
          center={center}
          zoom={18}
          mode="view"
          pin={null}
          boundary={boundary}
          layout={mapLayout}
          selectedBed={bed}
          onBedClick={setBed}
        />
      ) : (
        <Link
          to={`/setup/${id}`}
          className="rounded-xl bg-green-800 px-5 py-3 text-center text-lg font-semibold text-white"
        >
          {t("farm.add_plot")}
        </Link>
      )}

      <PlanView
        plan={plan.data ?? null}
        seasonIndex={seasonIndex}
        selectedBed={bed}
        onCloseBed={() => setBed(null)}
        highlight={highlight}
        onHighlight={setHighlight}
        owner={owner}
        hasPlot={Boolean(boundary)}
        planning={planning}
        onBuild={() => void buildPlan()}
        unit={unit}
        lang={lang}
        bighaSqft={me.data?.bigha_sqft ? Number(me.data.bigha_sqft) : null}
        loadAlternatives={owner ? loadAlternatives : undefined}
        onSwap={owner ? swapCrop : undefined}
      />
      {benefits.data && <Benefits schemes={benefits.data} lang={lang} />}

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
            to={`/setup/${id}/goal`}
            className="min-h-11 text-lg font-semibold text-green-800 underline"
          >
            {t("farm.edit_goal")}
          </Link>
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
