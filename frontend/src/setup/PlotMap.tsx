import area from "@turf/area";
import kinks from "@turf/kinks";
import {
  FullscreenControl,
  GeolocateControl,
  ScaleControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode } from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";

import { googleCredit, googleSatelliteEnabled, googleSession, googleTileUrl } from "./googleTiles";
import { ESRI_CREDIT, ESRI_TILES, satelliteAvailable } from "./imagery";

export type PlotGeometry = { type: "Polygon"; coordinates: number[][][] };
/** A planned layout to draw over the plot: zones filled by kind, beds outlined with their codes. */
export interface PlotLayout {
  zones: { kind: string; geometry: PlotGeometry }[];
  beds: { code: string; geometry: PlotGeometry }[];
}
export const ZONE_COLORS: Record<string, string> = {
  beds: "#16a34a",
  orchard: "#166534",
  rotation: "#ca8a04",
  border: "#78716c",
  water: "#0284c7",
  utility: "#7c3aed",
  nursery: "#db2777",
  path: "#e7e5e4",
};
export interface PlotShape {
  geometry: PlotGeometry;
  areaSqm: number;
  crossing: boolean;
}

// A bundled worker file: works under a strict Content-Security-Policy (no blob workers).
setWorkerUrl(workerUrl);

const STREETS = "https://tiles.openfreemap.org/styles/liberty";

interface Props {
  center: [number, number]; // lng, lat
  zoom?: number;
  /** "pin": a tap drops the pin. "draw": the user draws the plot (a tap does not move the pin). */
  mode: "pin" | "draw" | "view";
  pin: [number, number] | null;
  onPin?: (lng: number, lat: number) => void;
  onShape?: (shape: PlotShape | null) => void;
  /** In "view" mode: the saved plot to show. */
  boundary?: PlotGeometry | undefined;
  /** In "draw" mode: a shape to start from, which the user can adjust. */
  initial?: PlotGeometry | undefined;
  /** Taller map, for drawing. */
  tall?: boolean;
  /** Bumped by the parent to clear the drawing and start again. */
  resetKey?: number;
  /** In "view" mode: the planned zones and beds to show on the plot. */
  layout?: PlotLayout | undefined;
}

export function PlotMap({
  center,
  zoom = 14,
  mode,
  pin,
  boundary,
  onPin,
  onShape,
  resetKey = 0,
  tall = false,
  initial,
  layout,
}: Props) {
  const { t } = useTranslation();
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const drawRef = useRef<TerraDraw | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const onPinRef = useRef(onPin);
  const onShapeRef = useRef(onShape);
  const modeRef = useRef(mode);
  const initialRef = useRef(initial);
  const { i18n } = useTranslation();
  const lang = (i18n.language === "en" ? "en" : "hi") as "hi" | "en";
  const [satellite, setSatellite] = useState(satelliteAvailable);
  const [provider, setProvider] = useState<"google" | "esri" | null>(null);
  const [credit, setCredit] = useState("");
  useEffect(() => {
    onPinRef.current = onPin;
    onShapeRef.current = onShape;
    modeRef.current = mode;
    initialRef.current = initial;
  });

  // Create the map once.
  useEffect(() => {
    if (!box.current) return;
    const map = new MapLibreMap({
      container: box.current,
      style: STREETS,
      center,
      zoom,
      maxZoom: 21, // close enough to place corners of a very small plot
      attributionControl: { compact: true },
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new FullscreenControl(), "top-right");
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-right");
    map.addControl(
      new GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: false,
      }),
      "top-right",
    );
    map.on("click", (e: { lngLat: { lng: number; lat: number } }) => {
      if (modeRef.current === "pin") onPinRef.current?.(e.lngLat.lng, e.lngLat.lat);
    });
    mapRef.current = map;
    return () => {
      drawRef.current?.stop();
      drawRef.current = null;
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the pin marker in sync.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markerRef.current?.remove();
    markerRef.current = null;
    if (pin) {
      const marker = new Marker({ color: "#166534", draggable: modeRef.current === "pin" })
        .setLngLat(pin)
        .addTo(map);
      // Drag the pin to fine-tune the location.
      marker.on("dragend", () => {
        const p = marker.getLngLat();
        onPinRef.current?.(p.lng, p.lat);
      });
      markerRef.current = marker;
      map.easeTo({ center: pin, zoom: Math.max(map.getZoom(), 18), duration: 400 });
    }
  }, [pin]);

  // Drawing tools exist only in draw mode.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || mode !== "draw") return;
    let draw: TerraDraw | null = null;
    const start = () => {
      draw = new TerraDraw({
        adapter: new TerraDrawMapLibreGLAdapter({ map }),
        modes: [
          new TerraDrawPolygonMode(),
          new TerraDrawSelectMode({
            flags: {
              polygon: {
                feature: {
                  draggable: true, // move the whole plot
                  coordinates: { midpoints: true, draggable: true, deletable: true },
                },
              },
            },
          }),
        ],
      });
      draw.start();
      drawRef.current = draw;

      const report = () => {
        const polygon = draw?.getSnapshot().find((f) => f.geometry.type === "Polygon");
        if (!polygon) return onShapeRef.current?.(null);
        const geometry = polygon.geometry as PlotGeometry;
        onShapeRef.current?.({
          geometry,
          areaSqm: area({ type: "Feature", properties: {}, geometry }),
          crossing: kinks({ type: "Feature", properties: {}, geometry }).features.length > 0,
        });
      };
      draw.on("finish", (id, context) => {
        if (context.mode === "polygon") {
          draw?.setMode("select");
          draw?.selectFeature(id);
        }
        report();
      });
      draw.on("change", () => report());

      // Start from a known shape (the saved plot, or typed corner points) so it can be adjusted;
      // otherwise start drawing a new one.
      const initial = initialRef.current;
      if (initial) {
        const id = crypto.randomUUID();
        // Terra Draw accepts at most 9 decimals; ~1 mm precision is plenty.
        const geometry = {
          type: "Polygon" as const,
          coordinates: initial.coordinates.map((ring) =>
            ring.map((c) => c.map((v) => Math.round(v * 1e8) / 1e8)),
          ),
        };
        const result = draw.addFeatures([
          { id, type: "Feature", geometry, properties: { mode: "polygon" } },
        ]);
        if (!result[0]?.valid) console.warn("could not load plot shape:", result[0]?.reason);
        if (result[0]?.valid) {
          draw.setMode("select");
          draw.selectFeature(id);
          report();
          return;
        }
      }
      draw.setMode("polygon");
    };
    if (map.loaded()) start();
    else map.once("load", start);
    return () => {
      draw?.stop();
      drawRef.current = null;
    };
  }, [mode, resetKey]);

  // Show a saved plot (read-only view).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || mode !== "view" || !boundary) return;
    const show = () => {
      for (const id of ["plot-fill", "plot-line"]) if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource("plot")) map.removeSource("plot");
      map.addSource("plot", {
        type: "geojson",
        data: { type: "Feature", properties: {}, geometry: boundary },
      });
      map.addLayer({
        id: "plot-fill",
        type: "fill",
        source: "plot",
        paint: { "fill-color": "#166534", "fill-opacity": 0.3 },
      });
      map.addLayer({
        id: "plot-line",
        type: "line",
        source: "plot",
        paint: { "line-color": "#14532d", "line-width": 3 },
      });
      const ring = boundary.coordinates[0] ?? [];
      const lngs = ring.map((c) => c[0] ?? 0);
      const lats = ring.map((c) => c[1] ?? 0);
      map.fitBounds(
        [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ],
        { padding: 40, maxZoom: 19, duration: 0 },
      );
    };
    if (map.isStyleLoaded()) show();
    else map.once("load", show);
  }, [mode, boundary]);

  // The planned layout (zones and beds) over the plot.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || mode !== "view") return;
    const ids = ["layout-zones", "layout-beds", "layout-bed-codes"];
    const clear = () => {
      for (const id of ids) if (map.getLayer(id)) map.removeLayer(id);
      for (const id of ["layout-zones", "layout-beds", "layout-bed-points"])
        if (map.getSource(id)) map.removeSource(id);
    };
    const show = () => {
      clear();
      if (!layout) return;
      map.addSource("layout-zones", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: layout.zones.map((z) => ({
            type: "Feature",
            properties: { kind: z.kind },
            geometry: z.geometry,
          })),
        },
      });
      map.addLayer({
        id: "layout-zones",
        type: "fill",
        source: "layout-zones",
        paint: {
          "fill-color": [
            "match",
            ["get", "kind"],
            ...Object.entries(ZONE_COLORS).flat(),
            "#16a34a",
          ] as never,
          "fill-opacity": 0.45,
        },
      });
      map.addSource("layout-beds", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: layout.beds.map((b) => ({
            type: "Feature",
            properties: { code: b.code },
            geometry: b.geometry,
          })),
        },
      });
      map.addLayer({
        id: "layout-beds",
        type: "line",
        source: "layout-beds",
        paint: { "line-color": "#ffffff", "line-width": 1.2 },
      });
      map.addSource("layout-bed-points", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: layout.beds.map((b) => {
            const ring = b.geometry.coordinates[0] ?? [];
            const n = Math.max(ring.length - 1, 1);
            const lng = ring.slice(0, n).reduce((a, c) => a + (c[0] ?? 0), 0) / n;
            const lat = ring.slice(0, n).reduce((a, c) => a + (c[1] ?? 0), 0) / n;
            return {
              type: "Feature" as const,
              properties: { code: b.code },
              geometry: { type: "Point" as const, coordinates: [lng, lat] },
            };
          }),
        },
      });
      map.addLayer({
        id: "layout-bed-codes",
        type: "symbol",
        source: "layout-bed-points",
        minzoom: 19,
        layout: {
          "text-field": ["get", "code"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 12,
        },
        paint: { "text-color": "#ffffff", "text-halo-color": "#14532d", "text-halo-width": 1.5 },
      });
    };
    if (map.isStyleLoaded()) show();
    else map.once("load", show);
    return clear;
  }, [mode, layout]);

  // Satellite imagery: Google Map Tiles when a key is configured (default view), street map otherwise.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let cancelled = false;
    let onMove: (() => void) | null = null;
    const remove = () => {
      if (map.getLayer("satellite")) map.removeLayer("satellite");
      if (map.getSource("satellite")) map.removeSource("satellite");
    };
    const apply = async () => {
      remove();
      setCredit("");
      if (!satellite) return;
      const session = googleSatelliteEnabled ? await googleSession(lang) : null;
      if (cancelled) return;
      if (!session && !satelliteAvailable) return setSatellite(false);
      if (!session) {
        // Development imagery (Esri). Past zoom 19 it is stretched rather than blank.
        setProvider("esri");
        setCredit(ESRI_CREDIT);
        map.addSource("satellite", {
          type: "raster",
          tiles: [ESRI_TILES],
          tileSize: 256,
          maxzoom: 19,
        });
        const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
        map.addLayer({ id: "satellite", type: "raster", source: "satellite" }, firstLabel);
        return;
      }
      setProvider("google");
      map.addSource("satellite", {
        type: "raster",
        tiles: [googleTileUrl(session)],
        tileSize: 256,
        maxzoom: 22,
      });
      // Under the street labels and our drawing, over the street base.
      const firstSymbol = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
      map.addLayer({ id: "satellite", type: "raster", source: "satellite" }, firstSymbol);
      let timer: ReturnType<typeof setTimeout> | undefined;
      onMove = () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          const b = map.getBounds();
          void googleCredit(session, map.getZoom(), {
            north: b.getNorth(),
            south: b.getSouth(),
            east: b.getEast(),
            west: b.getWest(),
          }).then((c) => {
            if (!cancelled) setCredit(c);
          });
        }, 400);
      };
      map.on("moveend", onMove);
      onMove();
    };
    if (map.isStyleLoaded()) void apply();
    else map.once("load", () => void apply());
    return () => {
      cancelled = true;
      if (onMove) map.off("moveend", onMove);
    };
  }, [satellite, lang]);

  return (
    <div className="relative">
      <div
        ref={box}
        className={`${tall ? "h-[60vh]" : "h-80"} w-full overflow-hidden rounded-xl border-2 border-neutral-300`}
      />
      {satelliteAvailable && (
        <button
          type="button"
          onClick={() => setSatellite((s) => !s)}
          className="absolute top-2 left-2 rounded-lg bg-white px-3 text-base font-semibold shadow"
        >
          {satellite ? t("setup.plot.streets") : t("setup.plot.satellite")}
        </button>
      )}
      {satellite && (
        <div className="pointer-events-none absolute bottom-1 left-2 flex max-w-[70%] items-center gap-2">
          {provider === "google" && (
            <img
              src="https://maps.gstatic.com/mapfiles/api-3/images/google_white5.png"
              alt="Google"
              className="h-4"
            />
          )}
          {credit && <span className="truncate text-[11px] text-white drop-shadow">{credit}</span>}
        </div>
      )}
    </div>
  );
}
