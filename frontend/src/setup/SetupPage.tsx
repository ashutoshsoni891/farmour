import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router";

import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import type { Lang } from "../i18n";
import { FEET_PER_METRE, formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { PlotMap } from "./PlotMap";
import type { PlotShape } from "./PlotMap";

type Farm = components["schemas"]["FarmOut"];
type Parcel = components["schemas"]["ParcelOut"];
type StepId = "where" | "plot" | "about";
const STEPS: StepId[] = ["where", "plot", "about"];
const INDORE: [number, number] = [75.8577, 22.7196];

/** Text for an API error body, filling in numbers such as the minimum plot size. */
function errorText(t: TFunction, error: unknown): string {
  const e = (error as { error?: { message_key?: string; details?: Record<string, unknown> } })
    ?.error;
  const key = e?.message_key ?? "err.internal_error";
  return t(key, { min: e?.details?.["min"] ?? "", defaultValue: t("err.internal_error") });
}

const big = "min-h-14 rounded-xl border-2 px-4 text-lg font-semibold";
const on = "border-green-800 bg-green-800 text-white";
const off = "border-neutral-400 bg-white text-neutral-900";
const primary =
  "rounded-xl bg-green-800 px-6 py-3 text-lg font-semibold text-white disabled:opacity-40";

function Choice<T extends string>(props: {
  label: string;
  value: T | null;
  options: T[];
  text: (o: T) => string;
  onPick: (o: T) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-lg font-bold">{props.label}</legend>
      <div className="flex flex-wrap gap-2">
        {props.options.map((o) => (
          <button
            key={o}
            type="button"
            aria-pressed={props.value === o}
            onClick={() => props.onPick(o)}
            className={`${big} ${props.value === o ? on : off}`}
          >
            {props.text(o)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function useMe() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["me-basic", token],
    queryFn: async () => (await apiClient(token).GET("/api/v1/me")).data,
  });
}

/* ------------------------------------------------------------ step 1: where */

function WhereStep() {
  const { t, i18n } = useTranslation();
  const { token } = useAuth();
  const navigate = useNavigate();
  const lang = i18n.language as Lang;
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<components["schemas"]["PlaceOut"][] | null>(null);
  const [pin, setPin] = useState<[number, number] | null>(null);
  const [place, setPlace] = useState<{ name?: string; village?: string; district?: string }>({});
  const [center, setCenter] = useState<[number, number]>(INDORE);
  const [siteType, setSiteType] = useState<"ground" | "terrace" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const api = apiClient(token);

  const search = async () => {
    if (query.trim().length < 2) return;
    setError(null);
    const { data, error: err } = await api.GET("/api/v1/geo/search", {
      params: { query: { q: query.trim(), lang } },
    });
    if (err) return setError(errorText(t, err));
    setResults(data);
  };

  const choose = async (lng: number, lat: number, known?: typeof place) => {
    setPin([lng, lat]);
    setCenter([lng, lat]);
    setResults(null);
    if (known) return setPlace(known);
    setPlace({});
    const { data } = await api.GET("/api/v1/geo/reverse", {
      params: { query: { lat, lng, lang } },
    });
    if (data)
      setPlace({ name: data.name, village: data.village ?? "", district: data.district ?? "" });
  };

  const next = async () => {
    if (!pin || !siteType) return;
    setBusy(true);
    setError(null);
    const { data, error: err } = await api.POST("/api/v1/farms", {
      body: {
        name: t("setup.default_farm_name"),
        site_type: siteType,
        lat: Number(pin[1].toFixed(6)),
        lng: Number(pin[0].toFixed(6)),
        ...(place.village ? { village: place.village } : {}),
        ...(place.district ? { district: place.district } : {}),
      },
    });
    setBusy(false);
    if (err || !data) return setError(errorText(t, err));
    void navigate(`/setup/${data.id}?step=plot`, { replace: true });
  };

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.where.title")}</h1>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
      >
        <input
          aria-label={t("setup.where.search")}
          placeholder={t("setup.where.search")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="min-w-0 flex-1 rounded-lg border-2 border-neutral-400 px-3 text-lg"
        />
        <button type="submit" className={`${big} ${off}`}>
          {t("setup.where.search_button")}
        </button>
      </form>
      {results && results.length === 0 && <p>{t("setup.where.no_results")}</p>}
      {results && results.length > 0 && (
        <ul className="flex flex-col gap-2">
          {results.map((r) => (
            <li key={`${r.lat},${r.lng}`}>
              <button
                type="button"
                onClick={() =>
                  void choose(r.lng, r.lat, {
                    name: r.name,
                    village: r.village ?? "",
                    district: r.district ?? "",
                  })
                }
                className="w-full rounded-xl border-2 border-neutral-300 px-4 py-2 text-left text-base"
              >
                {r.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-base text-neutral-700">{t("setup.where.hint")}</p>
      <PlotMap
        center={center}
        zoom={pin ? 16 : 11}
        mode="pin"
        pin={pin}
        onPin={(lng, lat) => void choose(lng, lat)}
      />
      {pin && (
        <p role="status" className="text-base font-semibold text-green-900">
          {t("setup.where.picked", {
            place: place.village || place.name || `${pin[1].toFixed(4)}, ${pin[0].toFixed(4)}`,
          })}
        </p>
      )}
      <Choice
        label={t("setup.where.site_type")}
        value={siteType}
        options={["ground", "terrace"] as const}
        text={(o) => t(`setup.site.${o}`)}
        onPick={setSiteType}
      />
      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={!pin || !siteType || busy}
        onClick={() => void next()}
        className={primary}
      >
        {busy ? t("setup.saving") : t("setup.next")}
      </button>
    </>
  );
}

/* ------------------------------------------------------------ step 2: plot */

type PlotMode = "size" | "draw" | "sides";

function PlotStep({
  farm,
  parcel,
  onSaved,
}: {
  farm: Farm;
  parcel: Parcel | null;
  onSaved: () => void;
}) {
  const { t, i18n } = useTranslation();
  const { token } = useAuth();
  const me = useMe();
  const lang = i18n.language as Lang;
  const unitPref = (me.data?.unit_pref ?? "sqft") as UnitPref;
  const bigha = me.data?.bigha_sqft ? Number(me.data.bigha_sqft) : null;
  const [mode, setMode] = useState<PlotMode>("size");
  const [lenChoice, setLenUnit] = useState<"ft" | "m" | null>(null);
  const lenUnit = lenChoice ?? (unitPref === "sqft" ? "ft" : "m");
  const [v, setV] = useState<Record<string, string>>({});
  const [shape, setShape] = useState<PlotShape | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const [saved, setSaved] = useState<Parcel | null>(parcel);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const api = apiClient(token);
  const center: [number, number] = [Number(farm.lng ?? INDORE[0]), Number(farm.lat ?? INDORE[1])];

  const metres = (key: string): number => {
    const n = Number(v[key]);
    return Number.isFinite(n) && n > 0 ? (lenUnit === "ft" ? n / FEET_PER_METRE : n) : 0;
  };
  const showArea = (sqm: number) => {
    const a = formatArea(sqm, unitPref, lang, bigha);
    return t(a.key, { n: a.n });
  };

  const liveSqm =
    mode === "size"
      ? metres("length") * metres("width")
      : mode === "draw"
        ? (shape?.areaSqm ?? 0)
        : 0;

  const fail = (err: unknown) => {
    setError(errorText(t, err));
    setBusy(false);
  };
  const done = (p: Parcel) => {
    setSaved(p);
    setBusy(false);
    onSaved();
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    const lat = center[1];
    const lng = center[0];
    if (mode === "draw") {
      if (!shape) return setBusy(false);
      const { data, error: err } = await api.PUT("/api/v1/farms/{farm_id}/parcel", {
        params: { path: { farm_id: farm.id } },
        body: { boundary: shape.geometry },
      });
      return err || !data ? fail(err) : done(data);
    }
    const body =
      mode === "size"
        ? { shape: { kind: "rectangle" as const, lat, lng, length_m: metres("length"), width_m: metres("width"), bearing_deg: 0 } }
        : {
            shape: {
              kind: "four_sides" as const, lat, lng,
              side_ab_m: metres("ab"), side_bc_m: metres("bc"), side_cd_m: metres("cd"),
              side_da_m: metres("da"), diagonal_ac_m: metres("diag"), bearing_deg: 0,
            },
          }; // prettier-ignore
    const { data, error: err } = await api.POST(
      "/api/v1/farms/{farm_id}/parcel/from-measurements",
      {
        params: { path: { farm_id: farm.id } },
        body,
      },
    );
    return err || !data ? fail(err) : done(data);
  };

  const canSave =
    mode === "size"
      ? metres("length") > 0 && metres("width") > 0
      : mode === "sides"
        ? ["ab", "bc", "cd", "da", "diag"].every((k) => metres(k) > 0)
        : !!shape && !shape.crossing;

  const numField = (key: string, label: string) => (
    <label key={key} className="flex flex-col gap-1 text-base font-semibold">
      {label}
      <input
        inputMode="decimal"
        value={v[key] ?? ""}
        onChange={(e) => setV((s) => ({ ...s, [key]: e.target.value }))}
        className="rounded-lg border-2 border-neutral-400 px-3 text-lg"
      />
    </label>
  );

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.plot.title")}</h1>
      <div role="tablist" className="flex flex-wrap gap-2">
        {(["size", "draw", "sides"] as const).map((m) => (
          <button
            key={m}
            role="tab"
            aria-selected={mode === m}
            onClick={() => {
              setMode(m);
              setError(null);
            }}
            className={`${big} ${mode === m ? on : off}`}
          >
            {t(`setup.plot.mode.${m}`)}
          </button>
        ))}
      </div>

      {mode !== "draw" && (
        <div role="group" className="flex gap-2">
          {(["ft", "m"] as const).map((u) => (
            <button
              key={u}
              type="button"
              aria-pressed={lenUnit === u}
              onClick={() => setLenUnit(u)}
              className={`${big} ${lenUnit === u ? on : off}`}
            >
              {t(`setup.plot.unit_${u}`)}
            </button>
          ))}
        </div>
      )}

      {mode === "size" && (
        <div className="grid grid-cols-2 gap-3">
          {numField("length", t("setup.plot.length"))}
          {numField("width", t("setup.plot.width"))}
        </div>
      )}
      {mode === "sides" && (
        <div className="grid grid-cols-2 gap-3">
          {numField("ab", t("setup.plot.side_ab"))}
          {numField("bc", t("setup.plot.side_bc"))}
          {numField("cd", t("setup.plot.side_cd"))}
          {numField("da", t("setup.plot.side_da"))}
          <div className="col-span-2">{numField("diag", t("setup.plot.diagonal"))}</div>
        </div>
      )}
      {mode === "draw" && (
        <>
          <p className="text-base text-neutral-700">{t("setup.plot.draw_hint")}</p>
          <PlotMap
            center={center}
            zoom={19}
            mode="draw"
            pin={center}
            onShape={setShape}
            resetKey={resetKey}
          />
          {shape?.crossing && (
            <p role="alert" className="font-semibold text-red-800">
              {t("setup.plot.crossing")}
            </p>
          )}
          <button
            type="button"
            onClick={() => {
              setShape(null);
              setResetKey((k) => k + 1);
            }}
            className={`${big} ${off} self-start`}
          >
            {t("setup.plot.clear")}
          </button>
        </>
      )}

      {liveSqm > 0 && (
        <p role="status" className="text-xl font-bold text-green-900">
          {t("setup.plot.area", { area: showArea(liveSqm) })}
        </p>
      )}
      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={!canSave || busy}
        onClick={() => void save()}
        className={primary}
      >
        {busy ? t("setup.saving") : t("setup.plot.use")}
      </button>
      {saved && (
        <p role="status" className="font-semibold text-green-900">
          {t("setup.plot.saved", { area: showArea(saved.area_sqm) })}
        </p>
      )}
    </>
  );
}

/* ------------------------------------------------------------ step 3: about */

function AboutStep({ farm }: { farm: Farm }) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [water, setWater] = useState<Farm["water_source"]>(farm.water_source);
  const [goal, setGoal] = useState<Farm["goal"]>(farm.goal);
  const [labour, setLabour] = useState<Farm["labour"]>(farm.labour);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const finish = async () => {
    setBusy(true);
    const { error: err } = await apiClient(token).PATCH("/api/v1/farms/{farm_id}", {
      params: { path: { farm_id: farm.id } },
      body: {
        ...(water ? { water_source: water } : {}),
        ...(goal ? { goal } : {}),
        ...(labour ? { labour } : {}),
      },
    });
    setBusy(false);
    if (err) return setError(errorText(t, err));
    void navigate("/");
  };

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.about.title")}</h1>
      <Choice
        label={t("setup.about.water")}
        value={water ?? null}
        options={["bore", "well", "canal", "municipal", "rain_only"] as const}
        text={(o) => t(`setup.water.${o}`)}
        onPick={setWater}
      />
      <Choice
        label={t("setup.about.goal")}
        value={goal ?? null}
        options={["home_food", "income", "both"] as const}
        text={(o) => t(`setup.goal.${o}`)}
        onPick={setGoal}
      />
      <Choice
        label={t("setup.about.labour")}
        value={labour ?? null}
        options={["self", "family", "caretaker", "mixed"] as const}
        text={(o) => t(`setup.labour.${o}`)}
        onPick={setLabour}
      />
      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <button type="button" disabled={busy} onClick={() => void finish()} className={primary}>
        {busy ? t("setup.saving") : t("setup.finish")}
      </button>
    </>
  );
}

/* ------------------------------------------------------------ page */

function Existing({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const farm = useQuery({
    queryKey: ["farm", farmId, token],
    queryFn: async () =>
      (
        await apiClient(token).GET("/api/v1/farms/{farm_id}", {
          params: { path: { farm_id: farmId } },
        })
      ).data,
  });
  const parcel = useQuery({
    queryKey: ["parcel", farmId, token],
    queryFn: async () =>
      (
        await apiClient(token).GET("/api/v1/farms/{farm_id}/parcel", {
          params: { path: { farm_id: farmId } },
        })
      ).data ?? null,
  });
  if (!farm.data || parcel.isPending) return <p role="status">{t("common.loading")}</p>;
  const step = (params.get("step") as StepId | null) ?? (parcel.data ? "about" : "plot");
  return (
    <>
      {step === "plot" && (
        <PlotStep
          farm={farm.data}
          parcel={parcel.data ?? null}
          onSaved={() => void parcel.refetch()}
        />
      )}
      {step === "plot" && parcel.data && (
        <button type="button" onClick={() => setParams({ step: "about" })} className={primary}>
          {t("setup.next")}
        </button>
      )}
      {step === "about" && <AboutStep farm={farm.data} />}
      {step === "about" && (
        <button
          type="button"
          onClick={() => setParams({ step: "plot" })}
          className="self-start text-lg font-semibold text-green-800 underline"
        >
          {t("setup.back")}
        </button>
      )}
    </>
  );
}

export function SetupPage() {
  const { t } = useTranslation();
  const { farmId } = useParams();
  const [params] = useSearchParams();
  const step: StepId = !farmId ? "where" : ((params.get("step") as StepId | null) ?? "plot");
  const n = STEPS.indexOf(step) + 1;
  return (
    <Screen>
      <p className="text-base font-semibold text-neutral-700">
        {t("setup.step", { n, total: STEPS.length })}
      </p>
      {farmId ? <Existing farmId={farmId} /> : <WhereStep />}
    </Screen>
  );
}
