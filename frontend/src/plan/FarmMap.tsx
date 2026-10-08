import {
  FullscreenControl,
  GeolocateControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  ScaleControl,
} from "maplibre-gl";
import type { GeoJSONSource, MapMouseEvent } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { ZONE_COLORS } from "../setup/PlotMap";
import { satelliteAvailable } from "../setup/imagery";
import { STREETS } from "../setup/mapSetup";
import { SatelliteCredit, useSatellite } from "../setup/useSatellite";
import { bedColours, cropStyle, plantingsOf } from "./cropStyle";
import { bounds, labelPoint } from "./mapGeometry";
import type { PolygonGeometry } from "./mapGeometry";

type Plan = components["schemas"]["PlanOut"];

/** What the owner tapped on the map. */
export type MapSelection =
  | { kind: "bed"; code: string }
  | { kind: "zone"; id: string }
  | { kind: "plot"; code: string }
  | { kind: "plant"; group: number };

export function selectionKey(s: MapSelection | null): string {
  if (!s) return "";
  if (s.kind === "bed") return `bed:${s.code}`;
  if (s.kind === "zone") return `zone:${s.id}`;
  if (s.kind === "plot") return `plot:${s.code}`;
  return `plant:${s.group}`;
}

function fromKey(key: string): MapSelection | null {
  const [kind, value = ""] = [key.slice(0, key.indexOf(":")), key.slice(key.indexOf(":") + 1)];
  if (kind === "bed") return { kind, code: value };
  if (kind === "zone") return { kind, id: value };
  if (kind === "plot") return { kind, code: value };
  if (kind === "plant") return { kind, group: Number(value) };
  return null;
}

export const ZONE_ICON: Record<string, string> = {
  beds: "🥬",
  orchard: "🌳",
  rotation: "🌾",
  border: "🌿",
  water: "💧",
  utility: "♻️",
  nursery: "🌱",
  polyhouse: "🏠",
  livestock: "🐄",
  path: "🚪",
};
const NO_LABEL = new Set(["beds", "path", "border"]);
const EMPTY_BED = "#a8a29e";
// Clickable layers, most specific first: a tree on a bed wins over the bed, a bed over its zone.
const PICK_ORDER = ["p-plant", "f-bed", "f-plot", "f-zone"];

type Feature = {
  type: "Feature";
  id?: number;
  properties: Record<string, string | number>;
  geometry: PolygonGeometry | { type: "Point"; coordinates: number[] };
};
/** HTML labels on the map (they can show emoji and Hindi, which map fonts cannot); they let
 * taps through to the shapes underneath. */
function placeLabels(
  map: MapLibreMap,
  specs: readonly { at: readonly [number, number]; cls: string; text: string }[],
): Marker[] {
  return specs.map((l) => {
    const el = document.createElement("div");
    el.className = `map-label ${l.cls}`;
    el.textContent = l.text;
    el.style.pointerEvents = "none";
    return new Marker({ element: el, anchor: "center" }).setLngLat([l.at[0], l.at[1]]).addTo(map);
  });
}

const collection = (features: Feature[]) => ({ type: "FeatureCollection" as const, features });

interface Props {
  plan: Plan | null;
  boundary: PolygonGeometry;
  center: [number, number];
  seasonLabel: string | undefined;
  highlight: string | null;
  selection: MapSelection | null;
  onSelect: (s: MapSelection | null) => void;
  lang: Lang;
  /** Drawn over the top of the map (season tabs). */
  top?: ReactNode;
  /** Bottom-left legend; hidden while the inspector is open. */
  legend?: ReactNode;
  /** Details of the selection: a side panel on wide screens, a bottom sheet on phones. */
  inspector?: ReactNode;
  className?: string;
}

/** The farm plan on an interactive map: zones, beds, field plots, trees and hedge. Everything can
 * be tapped (details open in the inspector), hovered (name in a tooltip) and found in the legend. */
export function FarmMap(props: Props) {
  const { plan, boundary, center, seasonLabel, highlight, selection, lang } = props;
  const { t } = useTranslation();
  const wrap = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const onSelect = useRef(props.onSelect);
  const names = useRef<Map<string, string>>(new Map());
  const [ready, setReady] = useState(false);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  useEffect(() => {
    onSelect.current = props.onSelect;
  });
  // Esc closes the details.
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSelect.current(null);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  const nameOf = (c: { name_en: string; name_hi: string }) =>
    lang === "hi" ? c.name_hi : c.name_en;

  // Everything to draw, as GeoJSON, plus a readable name per feature for tooltips.
  const drawing = useMemo(() => {
    const shapes: Feature[] = [];
    const plants: Feature[] = [];
    const labels = new Map<string, string>();
    shapes.push({ type: "Feature", properties: { type: "boundary", key: "" }, geometry: boundary });
    if (!plan) return { shapes, plants, labels };

    for (const z of plan.zones) {
      const key = `zone:${z.id}`;
      labels.set(key, `${ZONE_ICON[z.kind] ?? ""} ${t(`map.zone.${z.kind}`)}`);
      shapes.push({
        type: "Feature",
        properties: { type: "zone", key, kind: z.kind, color: ZONE_COLORS[z.kind] ?? "#16a34a" },
        geometry: z.geometry as unknown as PolygonGeometry,
      });
    }

    const plots = new Map<string, (typeof plan.fields)[number]>();
    for (const f of plan.fields) if (!plots.has(f.plot_code)) plots.set(f.plot_code, f);
    for (const [code, f] of plots) {
      const now = plan.fields.find((x) => x.plot_code === code && x.season_label === seasonLabel);
      const key = `plot:${code}`;
      labels.set(
        key,
        now
          ? `${t("map.plot", { code })} · ${cropStyle(now.crop.slug).emoji} ${nameOf(now.crop)}`
          : `${t("map.plot", { code })} · ${t("map.fallow")}`,
      );
      shapes.push({
        type: "Feature",
        properties: {
          type: "plot",
          key,
          color: now ? cropStyle(now.crop.slug).color : (ZONE_COLORS.rotation ?? "#ca8a04"),
          op: highlight && now?.crop.slug !== highlight ? 0.2 : now ? 0.7 : 0.35,
        },
        geometry: f.geometry as unknown as PolygonGeometry,
      });
    }

    const colours = bedColours(plan, seasonLabel);
    const rows = plantingsOf(plan, seasonLabel);
    for (const b of plan.beds) {
      const key = `bed:${b.code}`;
      const here = rows.filter((r) => r.bed_code === b.code);
      const lit = !highlight || here.some((r) => r.crop.slug === highlight);
      labels.set(
        key,
        `${t("farm.bed_title", { code: b.code })} · ${
          here.length
            ? here.map((r) => `${cropStyle(r.crop.slug).emoji} ${nameOf(r.crop)}`).join(", ")
            : t("map.bed_free")
        }`,
      );
      shapes.push({
        type: "Feature",
        properties: {
          type: "bed",
          key,
          color: colours[b.code] ?? EMPTY_BED,
          op: !lit ? 0.18 : colours[b.code] ? 0.92 : 0.5,
        },
        geometry: b.geometry as unknown as PolygonGeometry,
      });
    }

    plan.perennials.forEach((g, i) => {
      const key = `plant:${i}`;
      labels.set(
        key,
        `${cropStyle(g.crop.slug).emoji} ${nameOf(g.crop)} · ${t(
          g.kind === "tree" ? "perennial.trees" : "perennial.plants",
          { n: g.count },
        )}`,
      );
      for (const c of g.points["coordinates"] as number[][]) {
        plants.push({
          type: "Feature",
          properties: {
            key,
            color: cropStyle(g.crop.slug).color,
            r: g.kind === "tree" ? g.spacing_m * 0.4 : g.spacing_m * 0.35,
            op: highlight && g.crop.slug !== highlight ? 0.3 : 0.95,
          },
          geometry: { type: "Point", coordinates: c },
        });
      }
    });
    return { shapes, plants, labels };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, boundary, seasonLabel, highlight, lang, t]);
  useEffect(() => {
    names.current = drawing.labels;
  }, [drawing]);

  // Create the map once.
  useEffect(() => {
    if (!box.current || !wrap.current) return;
    const map = new MapLibreMap({
      container: box.current,
      style: STREETS,
      center,
      zoom: 18,
      maxZoom: 21,
      attributionControl: { compact: true },
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new FullscreenControl({ container: wrap.current }), "top-right");
    map.addControl(
      new GeolocateControl({ positionOptions: { enableHighAccuracy: true } }),
      "top-right",
    );
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-right");
    const zoomBand = () => {
      const z = map.getZoom();
      if (wrap.current) wrap.current.dataset["z"] = z >= 19.8 ? "near" : z >= 18.6 ? "mid" : "far";
    };
    map.on("zoom", zoomBand);
    map.on("load", () => {
      const lat = center[1];
      const k = (z: number) => 2 ** z / (156543.03 * Math.cos((lat * Math.PI) / 180));
      const radius = [
        "interpolate", ["exponential", 2], ["zoom"],
        14, ["max", 2, ["*", ["get", "r"], k(14)]],
        22, ["*", ["get", "r"], k(22)],
      ] as never; // prettier-ignore
      map.addSource("shapes", { type: "geojson", data: collection([]) });
      map.addSource("plants", { type: "geojson", data: collection([]) });
      const of = (type: string) => ["==", ["get", "type"], type] as never;
      map.addLayer({
        id: "f-zone",
        type: "fill",
        source: "shapes",
        filter: of("zone"),
        paint: { "fill-color": ["get", "color"] as never, "fill-opacity": 0.3 },
      });
      map.addLayer({
        id: "f-zone-line",
        type: "line",
        source: "shapes",
        filter: of("zone"),
        paint: { "line-color": ["get", "color"] as never, "line-width": 1.5, "line-opacity": 0.9 },
      });
      map.addLayer({
        id: "f-plot",
        type: "fill",
        source: "shapes",
        filter: of("plot"),
        paint: { "fill-color": ["get", "color"] as never, "fill-opacity": ["get", "op"] as never },
      });
      map.addLayer({
        id: "f-plot-line",
        type: "line",
        source: "shapes",
        filter: of("plot"),
        paint: { "line-color": "#ffffff", "line-width": 1.5, "line-dasharray": [3, 2] },
      });
      map.addLayer({
        id: "f-bed",
        type: "fill",
        source: "shapes",
        filter: of("bed"),
        paint: { "fill-color": ["get", "color"] as never, "fill-opacity": ["get", "op"] as never },
      });
      map.addLayer({
        id: "f-bed-line",
        type: "line",
        source: "shapes",
        filter: of("bed"),
        paint: {
          "line-color": "#ffffff",
          "line-opacity": 0.85,
          "line-width": ["interpolate", ["linear"], ["zoom"], 16, 0.3, 21, 1.6] as never,
        },
      });
      map.addLayer({
        id: "f-boundary-halo",
        type: "line",
        source: "shapes",
        filter: of("boundary"),
        paint: { "line-color": "#14532d", "line-width": 6, "line-opacity": 0.6 },
      });
      map.addLayer({
        id: "f-boundary",
        type: "line",
        source: "shapes",
        filter: of("boundary"),
        paint: { "line-color": "#fef9c3", "line-width": 2.5 },
      });
      map.addLayer({
        id: "p-plant",
        type: "circle",
        source: "plants",
        paint: {
          "circle-color": ["get", "color"] as never,
          "circle-opacity": ["get", "op"] as never,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2,
          "circle-radius": radius,
        },
      });
      // Hover and selection outlines, driven by a filter on the feature key.
      const none = ["==", ["get", "key"], "-"] as never;
      map.addLayer({
        id: "hover-line",
        type: "line",
        source: "shapes",
        filter: none,
        paint: { "line-color": "#ffffff", "line-width": 3 },
      });
      map.addLayer({
        id: "sel-fill",
        type: "fill",
        source: "shapes",
        filter: none,
        paint: { "fill-color": "#facc15", "fill-opacity": 0.25 },
      });
      map.addLayer({
        id: "sel-line",
        type: "line",
        source: "shapes",
        filter: none,
        paint: { "line-color": "#facc15", "line-width": 4 },
      });
      map.addLayer({
        id: "p-sel",
        type: "circle",
        source: "plants",
        filter: none,
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-color": "#facc15",
          "circle-stroke-width": 3,
          "circle-radius": radius,
        },
      });
      zoomBand();
      setReady(true);
    });

    // Tap: the most specific thing under the finger (a few pixels of slack for small trees).
    const pick = (e: MapMouseEvent) => {
      const { x, y } = e.point;
      const found = map.queryRenderedFeatures(
        [
          [x - 5, y - 5],
          [x + 5, y + 5],
        ],
        { layers: PICK_ORDER.filter((l) => map.getLayer(l)) },
      );
      for (const layer of PICK_ORDER) {
        const hit = found.find((f) => f.layer.id === layer);
        const key = hit?.properties["key"];
        if (typeof key === "string" && key) return key;
      }
      return "";
    };
    map.on("click", (e) => {
      setTip(null);
      const key = pick(e);
      onSelect.current(key ? fromKey(key) : null);
    });
    const touch = window.matchMedia?.("(pointer: coarse)").matches;
    map.on("mousemove", (e) => {
      if (touch) return; // no hover on phones: a tap opens the details instead
      const key = pick(e);
      map.getCanvas().style.cursor = key ? "pointer" : "";
      if (map.getLayer("hover-line"))
        map.setFilter("hover-line", ["==", ["get", "key"], key || "-"] as never);
      const text = key ? names.current.get(key) : undefined;
      setTip(text ? { x: e.point.x, y: e.point.y, text } : null);
    });
    map.on("mouseout", () => setTip(null));
    mapRef.current = map;
    return () => {
      for (const m of markers.current) m.remove();
      markers.current = [];
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { satellite, setSatellite, provider, credit } = useSatellite(mapRef, lang);

  const fit = (animate: boolean) => {
    const map = mapRef.current;
    if (!map) return;
    const [minx, miny, maxx, maxy] = bounds([boundary]);
    const wide = (wrap.current?.clientWidth ?? 0) >= 1024;
    map.fitBounds(
      [
        [minx, miny],
        [maxx, maxy],
      ],
      {
        padding: { top: 64, bottom: 40, left: wide ? 40 : 20, right: wide ? 60 : 50 },
        maxZoom: 20,
        duration: animate ? 500 : 0,
      },
    );
  };

  // Data, whenever the plan, the season or the highlighted crop changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource("shapes") as GeoJSONSource).setData(collection(drawing.shapes) as never);
    (map.getSource("plants") as GeoJSONSource).setData(collection(drawing.plants) as never);
  }, [ready, drawing]);

  // Fit the plot when it first shows or its shape changes.
  useEffect(() => {
    if (ready) fit(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, boundary]);

  // Selection outline.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const key = selectionKey(selection) || "-";
    const f = ["==", ["get", "key"], key] as never;
    for (const id of ["sel-fill", "sel-line", "p-sel"]) map.setFilter(id, f);
  }, [ready, selection]);

  // Labels: zone names, field plots with their crop, and each bed's crop (close up).
  const labelSpecs = useMemo(() => {
    const out: { at: [number, number]; cls: string; text: string }[] = [];
    if (!plan) return out;
    const nm = (c: { name_en: string; name_hi: string }) => (lang === "hi" ? c.name_hi : c.name_en);
    for (const z of plan.zones) {
      if (NO_LABEL.has(z.kind)) continue;
      if (z.kind === "rotation" && plan.fields.length) continue; // the plots carry their own labels
      out.push({
        at: labelPoint(z.geometry as unknown as PolygonGeometry),
        cls: "map-label-zone",
        text: `${ZONE_ICON[z.kind] ?? ""} ${t(`map.zone.${z.kind}`)}`,
      });
    }
    const seen = new Set<string>();
    for (const f of plan.fields) {
      if (seen.has(f.plot_code)) continue;
      seen.add(f.plot_code);
      const now = plan.fields.find(
        (x) => x.plot_code === f.plot_code && x.season_label === seasonLabel,
      );
      out.push({
        at: labelPoint(f.geometry as unknown as PolygonGeometry),
        cls: "map-label-zone",
        text: now
          ? `${f.plot_code} · ${cropStyle(now.crop.slug).emoji} ${nm(now.crop)}`
          : f.plot_code,
      });
    }
    const rows = plantingsOf(plan, seasonLabel);
    for (const b of plan.beds) {
      const here = rows.filter((r) => r.bed_code === b.code);
      const emoji = [...new Set(here.map((r) => cropStyle(r.crop.slug).emoji))]
        .slice(0, 2)
        .join("");
      out.push({
        at: labelPoint(b.geometry as unknown as PolygonGeometry),
        cls: "map-label-bed",
        text: `${emoji || "·"}\n${b.code}`,
      });
    }
    return out;
  }, [plan, seasonLabel, lang, t]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const made = placeLabels(map, labelSpecs);
    markers.current = made;
    return () => {
      for (const m of made) m.remove();
    };
  }, [ready, labelSpecs]);

  const sheet = Boolean(props.inspector);
  return (
    <div
      ref={wrap}
      data-z="mid"
      className={`farm-map relative overflow-hidden rounded-2xl border border-neutral-300 bg-neutral-200 shadow-sm ${props.className ?? ""}`}
    >
      <div ref={box} className="h-full w-full" />

      {props.top && (
        <div className="pointer-events-none absolute top-2 right-14 left-2 z-10">{props.top}</div>
      )}

      <div className="absolute right-2 bottom-9 z-10 flex flex-col gap-2">
        {satelliteAvailable && (
          <button
            type="button"
            onClick={() => setSatellite((s) => !s)}
            className="min-h-11 rounded-xl bg-white/95 px-3 text-base font-semibold shadow"
          >
            {satellite ? t("map.streets") : t("map.satellite")}
          </button>
        )}
        <button
          type="button"
          onClick={() => fit(true)}
          className="min-h-11 rounded-xl bg-white/95 px-3 text-base font-semibold shadow"
        >
          {t("map.fit")}
        </button>
      </div>

      {props.legend && !sheet && (
        <div className="absolute bottom-9 left-2 z-10 max-w-[calc(100%-7.5rem)] lg:max-w-sm">
          {props.legend}
        </div>
      )}

      {sheet && (
        <div className="absolute inset-x-0 bottom-0 z-20 max-h-[72%] overflow-y-auto rounded-t-2xl bg-white shadow-2xl lg:inset-x-auto lg:top-16 lg:bottom-3 lg:left-3 lg:max-h-none lg:w-[400px] lg:rounded-2xl">
          {props.inspector}
        </div>
      )}

      {tip && (
        <div
          className="pointer-events-none absolute z-30 max-w-xs rounded-lg bg-neutral-900/90 px-2 py-1 text-sm text-white shadow"
          style={{ left: tip.x + 14, top: tip.y + 14 }}
        >
          {tip.text}
        </div>
      )}

      {satellite && (
        <SatelliteCredit provider={provider} credit={credit} className="bottom-1 left-2 z-0" />
      )}
    </div>
  );
}
