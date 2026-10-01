import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import type { Lang } from "../i18n";
import { formatDayMonth, formatNumber } from "../lib/format";

type Fact = components["schemas"]["FactOut"];
type Profile = components["schemas"]["ProfileOut"];
type Group = Fact["group"];

const GROUPS: Group[] = ["region", "soil_land", "climate", "water", "markets", "nearby"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const SOILS = ["black", "red", "sandy", "clay", "loam", "mixed"];
const DRAINAGE = ["good", "ok", "waterlogs"];
const POLL_MS = 3000;
const GIVE_UP_MS = 60_000;

const btn = "min-h-14 rounded-xl border-2 px-4 text-lg font-semibold";
const on = "border-green-800 bg-green-800 text-white";
const off = "border-neutral-400 bg-white text-neutral-900";

interface Row {
  key: string;
  label: string;
  lines: string[];
  fact: Fact;
}

function monthName(code: string, lang: Lang): string {
  const i = MONTHS.indexOf(code);
  if (i < 0) return code;
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { month: "long" }).format(
    new Date(2000, i, 1),
  );
}

function buildRows(facts: Fact[], t: TFunction, lang: Lang): Row[] {
  const by = Object.fromEntries(facts.map((f) => [f.key, f]));
  const rows: Row[] = [];
  const add = (key: string, label: string, lines: string[]) => {
    const fact = by[key];
    if (fact && lines.length) rows.push({ key, label, lines, fact });
  };
  const n = (v: number, d = 0) => formatNumber(v, lang, d);

  const region = by["region"]?.value as { name_en: string; name_hi: string } | undefined;
  if (region)
    add("region", t("setup.found.row.region"), [lang === "hi" ? region.name_hi : region.name_en]);

  const soil = by["soil.type"]?.value;
  if (typeof soil === "string")
    add("soil.type", t("setup.found.row.soil_type"), [
      t(`setup.found.soil.${soil}`, { defaultValue: soil }),
    ]);
  const ph = by["soil.ph"]?.value;
  if (typeof ph === "number") add("soil.ph", t("setup.found.row.soil_ph"), [n(ph, 1)]);
  const elev = by["terrain.elevation_m"]?.value;
  if (typeof elev === "number")
    add("terrain.elevation_m", t("setup.found.row.elevation"), [
      t("setup.found.value.meters", { n: n(elev) }),
    ]);
  const slope = by["terrain.slope"]?.value as
    { gradient_pct: number; lower_side: string | null } | undefined;
  if (slope) {
    add("terrain.slope", t("setup.found.row.slope"), [
      slope.gradient_pct < 1 || !slope.lower_side
        ? t("setup.found.value.slope_flat")
        : t("setup.found.value.slope_dir", {
            pct: n(slope.gradient_pct, 1),
            dir: t(`setup.found.dir.${slope.lower_side}`),
          }),
    ]);
  }

  const rain = by["climate.annual_rain_mm"]?.value;
  if (typeof rain === "number")
    add("climate.annual_rain_mm", t("setup.found.row.rain"), [
      t("setup.found.value.mm", { n: n(rain) }),
    ]);
  const hot = by["climate.hottest_month"]?.value as { month: string; tmax_c: number } | undefined;
  if (hot)
    add("climate.hottest_month", t("setup.found.row.hottest"), [
      t("setup.found.value.month_hot", { month: monthName(hot.month, lang), c: n(hot.tmax_c) }),
    ]);
  const cold = by["climate.coldest_month"]?.value as { month: string; tmin_c: number } | undefined;
  if (cold)
    add("climate.coldest_month", t("setup.found.row.coldest"), [
      t("setup.found.value.month_cold", { month: monthName(cold.month, lang), c: n(cold.tmin_c) }),
    ]);
  const onset = by["climate.monsoon_onset"]?.value;
  if (typeof onset === "string")
    add("climate.monsoon_onset", t("setup.found.row.monsoon"), [monthName(onset, lang)]);

  const gw = by["water.groundwater_class"]?.value as { category: string } | undefined;
  if (gw)
    add("water.groundwater_class", t("setup.found.row.groundwater"), [
      t(`setup.found.gw.${gw.category}`, { defaultValue: gw.category }),
    ]);

  type Route = { name: string; distance_km: number; minutes: number; method: string };
  const route = (r: Route) =>
    r.method === "straight_line"
      ? t("setup.found.value.distance_line", { name: r.name, km: n(r.distance_km) })
      : t("setup.found.value.distance_road", {
          name: r.name,
          km: n(r.distance_km),
          min: n(r.minutes),
        });
  const mandis = by["markets.nearest"]?.value as Route[] | undefined;
  if (mandis) add("markets.nearest", t("setup.found.row.mandis"), mandis.map(route));
  const refs = by["markets.reference"]?.value as Route[] | undefined;
  if (refs) add("markets.reference", t("setup.found.row.reference"), refs.map(route));

  const places = by["nearby.places"]?.value as
    Record<string, { name: string; distance_km: number }[]> | undefined;
  for (const [kind, list] of Object.entries(places ?? {})) {
    add(
      "nearby.places",
      t(`setup.found.place.${kind}`, { defaultValue: kind }),
      list.map((p) => t("setup.found.value.place", { name: p.name, km: n(p.distance_km, 1) })),
    );
  }
  return rows;
}

function Pick({
  label,
  options,
  prefix,
  value,
  onPick,
}: {
  label: string;
  options: string[];
  prefix: string;
  value: string | null;
  onPick: (v: string | null) => void;
}) {
  const { t } = useTranslation();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-lg font-bold">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            aria-pressed={value === o}
            onClick={() => onPick(o)}
            className={`${btn} ${value === o ? on : off}`}
          >
            {t(`${prefix}.${o}`)}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={value === "unsure"}
          onClick={() => onPick(null)}
          className={`${btn} ${value === null ? on : off}`}
        >
          {t("setup.found.not_sure")}
        </button>
      </div>
    </fieldset>
  );
}

export function FoundStep({ farmId, onDone }: { farmId: string; onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const lang = i18n.language as Lang;
  const [startedAt] = useState(() => Date.now());
  const [waited, setWaited] = useState(false);
  const [soil, setSoil] = useState<string | null | undefined>(undefined); // undefined = not answered
  const [drainage, setDrainage] = useState<string | null | undefined>(undefined);
  const [changing, setChanging] = useState(false);
  const [busy, setBusy] = useState(false);

  const profile = useQuery<Profile>({
    queryKey: ["site-profile", farmId, token],
    queryFn: async () => {
      const { data, error } = await apiClient(token).GET("/api/v1/farms/{farm_id}/site-profile", {
        params: { path: { farm_id: farmId } },
      });
      if (error) throw error;
      return data;
    },
    refetchInterval: (q) => {
      const status = q.state.data?.build.status;
      const settled = status === "done" || status === "failed";
      return settled || Date.now() - startedAt > GIVE_UP_MS ? false : POLL_MS;
    },
  });

  const status = profile.data?.build.status ?? "none";
  const building = (status === "none" || status === "running") && !waited;
  useEffect(() => {
    const id = setTimeout(() => setWaited(true), GIVE_UP_MS);
    return () => clearTimeout(id);
  }, []);

  const facts = profile.data?.facts ?? [];
  const rows = buildRows(facts, t, lang);
  const asks = new Set(profile.data?.questions ?? []);
  const askSoil = asks.has("soil.type") || changing;
  const askDrainage = asks.has("soil.drainage");
  const pending = (askSoil && soil === undefined) || (askDrainage && drainage === undefined);

  const submit = async () => {
    setBusy(true);
    const items: components["schemas"]["Answer"][] = [];
    for (const f of facts) {
      if (f.status === "derived" && f.key !== "soil.type")
        items.push({ key: f.key, action: "confirm" });
    }
    const soilFact = facts.find((f) => f.key === "soil.type");
    if (soil !== undefined) {
      items.push(
        soil
          ? { key: "soil.type", action: "edit", value: soil }
          : { key: "soil.type", action: "reject" },
      );
    } else if (soilFact?.status === "derived") {
      items.push({ key: "soil.type", action: "confirm" });
    }
    if (drainage !== undefined) {
      items.push(
        drainage
          ? { key: "soil.drainage", action: "edit", value: drainage }
          : { key: "soil.drainage", action: "reject" },
      );
    }
    await apiClient(token).PATCH("/api/v1/farms/{farm_id}/site-profile", {
      params: { path: { farm_id: farmId } },
      body: { items },
    });
    await queryClient.invalidateQueries({ queryKey: ["site-profile", farmId] });
    setBusy(false);
    onDone();
  };

  const attributions = profile.data?.attributions ?? [];
  const sourceText = (f: Fact) =>
    t("setup.found.source_line", {
      source: t(`setup.found.src.${f.source}`, { defaultValue: f.source }),
      date: formatDayMonth(new Date(f.fetched_at), lang),
    });

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.found.title")}</h1>
      {building && (
        <p role="status" className="rounded-lg bg-green-50 p-4 text-lg">
          {t("setup.found.looking")}
        </p>
      )}
      {!building && rows.length === 0 && (
        <p role="status" className="text-lg">
          {t("setup.found.none")}
        </p>
      )}

      {GROUPS.map((g) => {
        const inGroup = rows.filter((r) => r.fact.group === g);
        if (!inGroup.length) return null;
        return (
          <section key={g} className="flex flex-col gap-2">
            <h2 className="mt-2 text-xl font-bold text-green-900">{t(`setup.found.group.${g}`)}</h2>
            {inGroup.map((r) => (
              <div key={`${r.key}-${r.label}`} className="border-b border-neutral-200 pb-2">
                <p className="text-base font-semibold">{r.label}</p>
                {r.lines.map((line) => (
                  <p key={line} className="text-lg">
                    {line}
                  </p>
                ))}
                <p className="text-sm text-neutral-600">{sourceText(r.fact)}</p>
                {r.key === "soil.type" && (
                  <>
                    <p className="text-sm text-neutral-700">{t("setup.found.estimate")}</p>
                    {!changing && (
                      <button
                        type="button"
                        onClick={() => setChanging(true)}
                        className="min-h-11 text-base font-semibold text-green-800 underline"
                      >
                        {t("setup.found.change")}
                      </button>
                    )}
                  </>
                )}
              </div>
            ))}
          </section>
        );
      })}

      {!building && (askSoil || askDrainage) && (
        <section className="flex flex-col gap-4 rounded-xl border-2 border-green-800 p-4">
          {askSoil && (
            <Pick
              label={t("setup.found.question_soil")}
              options={SOILS}
              prefix="setup.found.soil"
              value={soil === undefined ? "" : soil}
              onPick={setSoil}
            />
          )}
          {askDrainage && (
            <Pick
              label={t("setup.found.question_drainage")}
              options={DRAINAGE}
              prefix="setup.found.drainage"
              value={drainage === undefined ? "" : drainage}
              onPick={setDrainage}
            />
          )}
        </section>
      )}

      {attributions.length > 0 && (
        <details className="text-sm text-neutral-700">
          <summary className="min-h-11 cursor-pointer font-semibold">
            {t("setup.found.sources")}
          </summary>
          <ul className="list-disc pl-5">
            {attributions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </details>
      )}

      <button
        type="button"
        disabled={building || busy || pending}
        onClick={() => void submit()}
        className="rounded-xl bg-green-800 px-6 py-3 text-lg font-semibold text-white disabled:opacity-40"
      >
        {rows.length > 0 && !askSoil && !askDrainage
          ? t("setup.found.looks_right")
          : t("setup.next")}
      </button>
    </>
  );
}
