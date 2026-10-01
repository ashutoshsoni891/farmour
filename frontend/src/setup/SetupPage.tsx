import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import type { Lang } from "../i18n";
import { FEET_PER_METRE, formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { Choice } from "./Choice";
import { parseCorners, parsePoint } from "./coords";
import { PlotMap } from "./PlotMap";
import type { PlotGeometry, PlotShape } from "./PlotMap";

type Farm = components["schemas"]["FarmOut"];
type Parcel = components["schemas"]["ParcelOut"];
const INDORE: [number, number] = [75.8577, 22.7196];
const SQFT_PER_SQM = 10.7639104167;
const SQFT_PER_ACRE = 43560;

/** Text for an API error body, filling in numbers such as the minimum plot size. */
function errorText(t: TFunction, error: unknown): string {
  const e = (error as { error?: { message_key?: string; details?: Record<string, unknown> } })
    ?.error;
  const key = e?.message_key ?? "err.internal_error";
  return t(key, { min: e?.details?.["min"] ?? "", defaultValue: t("err.internal_error") });
}

const big = "min-h-14 rounded-xl border-2 px-4 text-lg font-semibold";
const off = "border-neutral-400 bg-white text-neutral-900";
const on = "border-green-800 bg-green-800 text-white";
const primary =
  "rounded-xl bg-green-800 px-6 py-3 text-lg font-semibold text-white disabled:opacity-40";
const linkBtn = "min-h-11 self-start text-lg font-semibold text-green-800 underline";

function useMe() {
  const { token } = useAuth();
  return useQuery({
    queryKey: ["me-basic", token],
    queryFn: async () => (await apiClient(token).GET("/api/v1/me")).data,
  });
}

/* ------------------------------------------------------------ screen 1: where */

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
  const [terrace, setTerrace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [locating, setLocating] = useState(false);
  const [coordText, setCoordText] = useState("");
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
    setPlace(known ?? {});
    setResolving(true);
    // The district is looked up in English whatever the display language: the region table
    // is keyed by the English district name ("Indore"), not "इन्दौर ज़िला".
    const { data } = await api.GET("/api/v1/geo/reverse", {
      params: { query: { lat, lng, lang: "en" } },
    });
    setResolving(false);
    if (data) {
      setPlace((p) => ({
        name: p.name ?? data.name,
        village: p.village || data.village || "",
        district: data.district ?? p.district ?? "",
      }));
    }
  };

  const locate = () => {
    if (!("geolocation" in navigator)) return setError(t("setup.where.gps_failed"));
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        void choose(pos.coords.longitude, pos.coords.latitude);
      },
      () => {
        setLocating(false);
        setError(t("setup.where.gps_failed"));
      },
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };

  const next = async () => {
    if (!pin) return;
    setBusy(true);
    setError(null);
    // Defaults instead of questions; the owner can change them on the farm page.
    const { data, error: err } = await api.POST("/api/v1/farms", {
      body: {
        name: t("setup.default_farm_name"),
        site_type: terrace ? "terrace" : "ground",
        lat: Number(pin[1].toFixed(6)),
        lng: Number(pin[0].toFixed(6)),
        goal: "both",
        labour: "self",
        ...(place.village ? { village: place.village } : {}),
        ...(place.district ? { district: place.district } : {}),
      },
    });
    setBusy(false);
    if (err || !data) return setError(errorText(t, err));
    void navigate(`/setup/${data.id}`, { replace: true });
  };

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.where.title")}</h1>
      <button type="button" onClick={locate} disabled={locating} className={primary}>
        {locating ? t("setup.where.locating") : t("setup.where.use_location")}
      </button>
      <p className="text-base text-neutral-700">{t("setup.where.or_search")}</p>
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
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const p = parsePoint(coordText);
          if (!p) return setError(t("setup.where.coords_invalid"));
          setError(null);
          void choose(p[0], p[1]);
        }}
      >
        <input
          aria-label={t("setup.where.coords")}
          placeholder={t("setup.where.coords_placeholder")}
          value={coordText}
          onChange={(e) => setCoordText(e.target.value)}
          inputMode="text"
          className="min-w-0 flex-1 rounded-lg border-2 border-neutral-400 px-3 text-lg"
        />
        <button type="submit" className={`${big} ${off}`}>
          {t("setup.where.coords_go")}
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
      <PlotMap
        center={center}
        zoom={pin ? 18 : 11}
        mode="pin"
        pin={pin}
        onPin={(lng, lat) => void choose(lng, lat)}
      />
      <p className="text-base text-neutral-700">{t("setup.where.hint")}</p>
      {pin && (
        <p role="status" className="text-base font-semibold text-green-900">
          {t("setup.where.picked", {
            place: place.village || place.name || `${pin[1].toFixed(4)}, ${pin[0].toFixed(4)}`,
          })}{" "}
          <span className="font-normal text-neutral-700">
            ({pin[1].toFixed(5)}, {pin[0].toFixed(5)})
          </span>
        </p>
      )}
      <label className="flex min-h-11 items-center gap-3 text-lg">
        <input
          type="checkbox"
          checked={terrace}
          onChange={(e) => setTerrace(e.target.checked)}
          className="h-6 w-6"
        />
        {t("setup.where.is_terrace")}
      </label>
      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={!pin || busy || resolving}
        onClick={() => void next()}
        className={primary}
      >
        {busy ? t("setup.saving") : t("setup.next")}
      </button>
    </>
  );
}

/* ------------------------------------------------------------ screen 2: how big */

type PlotMode = "area" | "draw" | "sides" | "corners";
type AreaUnit = "sqft" | "acre" | "bigha";

function PlotStep({ farm, parcel }: { farm: Farm; parcel: Parcel | null }) {
  const { t, i18n } = useTranslation();
  const { token } = useAuth();
  const navigate = useNavigate();
  const me = useMe();
  const lang = i18n.language as Lang;
  const unitPref = (me.data?.unit_pref ?? "sqft") as UnitPref;
  const bighaSqft = me.data?.bigha_sqft ? Number(me.data.bigha_sqft) : null;
  const queryClient = useQueryClient();
  const saved = parcel?.boundary as unknown as PlotGeometry | undefined;
  // A saved plot opens on the map, ready to adjust; a new farm starts with "how big".
  const [mode, setMode] = useState<PlotMode>(saved ? "draw" : "area");
  const [initial, setInitial] = useState<PlotGeometry | undefined>(saved);
  const [cornerText, setCornerText] = useState("");
  const [areaUnit, setAreaUnit] = useState<AreaUnit>("sqft");
  const [lenUnit, setLenUnit] = useState<"ft" | "m">("ft");
  const [v, setV] = useState<Record<string, string>>({});
  const [shape, setShape] = useState<PlotShape | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const api = apiClient(token);
  const center: [number, number] = [Number(farm.lng ?? INDORE[0]), Number(farm.lat ?? INDORE[1])];

  const num = (key: string): number => {
    const n = Number(v[key]);
    return Number.isFinite(n) && n > 0 ? n : 0;
  };
  const metres = (key: string) => (lenUnit === "ft" ? num(key) / FEET_PER_METRE : num(key));
  const areaSqm = (): number => {
    const n = num("area");
    if (areaUnit === "acre") return (n * SQFT_PER_ACRE) / SQFT_PER_SQM;
    if (areaUnit === "bigha") return bighaSqft ? (n * bighaSqft) / SQFT_PER_SQM : 0;
    return n / SQFT_PER_SQM;
  };
  const showArea = (sqm: number) => {
    const a = formatArea(sqm, unitPref, lang, bighaSqft);
    return t(a.key, { n: a.n });
  };

  const liveSqm =
    mode === "area" ? areaSqm()
    : mode === "draw" ? (shape?.areaSqm ?? 0)
    : 0; // prettier-ignore

  const save = async () => {
    setBusy(true);
    setError(null);
    const [lng, lat] = center;
    let result: { data?: Parcel | undefined; error?: unknown };
    if (mode === "draw") {
      if (!shape) return setBusy(false);
      result = await api.PUT("/api/v1/farms/{farm_id}/parcel", {
        params: { path: { farm_id: farm.id } },
        body: { boundary: shape.geometry },
      });
    } else {
      // "How big" only: a square of that area, centred on the pin. Drawing refines it later.
      const side = Math.sqrt(areaSqm());
      const shapeBody =
        mode === "area"
          ? { kind: "rectangle" as const, lat, lng, length_m: side, width_m: side, bearing_deg: 0 }
          : { kind: "rectangle" as const, lat, lng, length_m: metres("length"), width_m: metres("width"), bearing_deg: 0 }; // prettier-ignore
      result = await api.POST("/api/v1/farms/{farm_id}/parcel/from-measurements", {
        params: { path: { farm_id: farm.id } },
        body: { shape: shapeBody },
      });
    }
    setBusy(false);
    if (result.error || !result.data) return setError(errorText(t, result.error));
    // Refresh what the farm page shows (it may hold an older "no plot yet" answer).
    await queryClient.invalidateQueries({ queryKey: ["parcel", farm.id] });
    await queryClient.invalidateQueries({ queryKey: ["site-profile", farm.id] });
    void navigate(`/farms/${farm.id}`, { replace: true });
  };

  const canSave =
    mode === "area" ? areaSqm() > 0
    : mode === "sides" ? num("length") > 0 && num("width") > 0
    : mode === "corners" ? false
    : !!shape && !shape.crossing; // prettier-ignore

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
  const areaUnits: AreaUnit[] = bighaSqft ? ["sqft", "acre", "bigha"] : ["sqft", "acre"];

  return (
    <>
      <h1 className="text-3xl font-bold">{t("setup.plot.title")}</h1>
      {parcel && (
        <p role="status" className="font-semibold text-green-900">
          {t("setup.plot.current", { area: showArea(parcel.area_sqm) })}
        </p>
      )}

      {mode === "area" && (
        <>
          {numField("area", t("setup.plot.area_label"))}
          <div role="group" className="flex flex-wrap gap-2">
            {areaUnits.map((u) => (
              <button
                key={u}
                type="button"
                aria-pressed={areaUnit === u}
                onClick={() => setAreaUnit(u)}
                className={`${big} ${areaUnit === u ? on : off}`}
              >
                {t(`setup.plot.unit_${u}`)}
              </button>
            ))}
          </div>
        </>
      )}

      {mode === "sides" && (
        <>
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
          <div className="grid grid-cols-2 gap-3">
            {numField("length", t("setup.plot.length"))}
            {numField("width", t("setup.plot.width"))}
          </div>
        </>
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
            initial={initial}
            tall
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
              setInitial(undefined);
              setResetKey((k) => k + 1);
            }}
            className={`${big} ${off} self-start`}
          >
            {t("setup.plot.clear")}
          </button>
        </>
      )}

      {mode === "corners" && (
        <>
          <label className="flex flex-col gap-1 text-base font-semibold">
            {t("setup.plot.corners_label")}
            <textarea
              rows={5}
              value={cornerText}
              onChange={(e) => setCornerText(e.target.value)}
              placeholder={
                "22.84560, 75.89330\n22.84560, 75.89345\n22.84540, 75.89345\n22.84540, 75.89330"
              }
              className="rounded-lg border-2 border-neutral-400 px-3 py-2 font-mono text-base"
            />
          </label>
          <button
            type="button"
            onClick={() => {
              const poly = parseCorners(cornerText);
              if (!poly) return setError(t("setup.plot.corners_invalid"));
              setError(null);
              setInitial(poly);
              setShape(null);
              setResetKey((k) => k + 1);
              setMode("draw");
            }}
            className={`${big} ${off} self-start`}
          >
            {t("setup.plot.corners_show")}
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
        {busy ? t("setup.saving") : t("setup.plot.done")}
      </button>

      <div className="flex flex-col gap-1">
        {mode !== "area" && (
          <button type="button" onClick={() => setMode("area")} className={linkBtn}>
            {t("setup.plot.mode.area")}
          </button>
        )}
        {mode !== "draw" && (
          <button type="button" onClick={() => setMode("draw")} className={linkBtn}>
            {t("setup.plot.mode.draw")}
          </button>
        )}
        {mode !== "corners" && (
          <button type="button" onClick={() => setMode("corners")} className={linkBtn}>
            {t("setup.plot.mode.corners")}
          </button>
        )}
        {mode !== "sides" && (
          <button type="button" onClick={() => setMode("sides")} className={linkBtn}>
            {t("setup.plot.mode.sides")}
          </button>
        )}
      </div>
    </>
  );
}

/* ------------------------------------------------------------ page */

function Existing({ farmId }: { farmId: string }) {
  const { t } = useTranslation();
  const { token } = useAuth();
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
  return <PlotStep farm={farm.data} parcel={parcel.data ?? null} />;
}

export function SetupPage() {
  const { t } = useTranslation();
  const { farmId } = useParams();
  return (
    <Screen>
      <p className="text-base font-semibold text-neutral-700">
        {t("setup.step", { n: farmId ? 2 : 1, total: 2 })}
      </p>
      {farmId ? <Existing farmId={farmId} /> : <WhereStep />}
    </Screen>
  );
}

export { Choice };
