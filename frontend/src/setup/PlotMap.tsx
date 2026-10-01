import area from "@turf/area";
import kinks from "@turf/kinks";
import { Map as MapLibreMap, Marker, NavigationControl, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode } from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";

export type PlotGeometry = { type: "Polygon"; coordinates: number[][][] };
export interface PlotShape {
  geometry: PlotGeometry;
  areaSqm: number;
  crossing: boolean;
}

// A bundled worker file: works under a strict Content-Security-Policy (no blob workers).
setWorkerUrl(workerUrl);

const STREETS = "https://tiles.openfreemap.org/styles/liberty";
const SATELLITE_URL = import.meta.env.VITE_SATELLITE_TILES_URL; // off unless a licensed provider is set
const SATELLITE_ATTRIBUTION = import.meta.env.VITE_SATELLITE_ATTRIBUTION ?? "";

interface Props {
  center: [number, number]; // lng, lat
  zoom?: number;
  /** "pin": a tap drops the pin. "draw": the user draws the plot (a tap does not move the pin). */
  mode: "pin" | "draw";
  pin: [number, number] | null;
  onPin?: (lng: number, lat: number) => void;
  onShape?: (shape: PlotShape | null) => void;
  /** Bumped by the parent to clear the drawing and start again. */
  resetKey?: number;
}

export function PlotMap({ center, zoom = 14, mode, pin, onPin, onShape, resetKey = 0 }: Props) {
  const { t } = useTranslation();
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const drawRef = useRef<TerraDraw | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const onPinRef = useRef(onPin);
  const onShapeRef = useRef(onShape);
  const modeRef = useRef(mode);
  const [satellite, setSatellite] = useState(false);
  useEffect(() => {
    onPinRef.current = onPin;
    onShapeRef.current = onShape;
    modeRef.current = mode;
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
      markerRef.current = new Marker({ color: "#166534" }).setLngLat(pin).addTo(map);
      map.easeTo({ center: pin, zoom: Math.max(map.getZoom(), 16), duration: 400 });
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
                  draggable: false,
                  coordinates: { midpoints: true, draggable: true, deletable: true },
                },
              },
            },
          }),
        ],
      });
      draw.start();
      draw.setMode("polygon");
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
    };
    if (map.loaded()) start();
    else map.once("load", start);
    return () => {
      draw?.stop();
      drawRef.current = null;
    };
  }, [mode, resetKey]);

  // Optional satellite layer (only when a provider URL is configured).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !SATELLITE_URL) return;
    const apply = () => {
      if (map.getLayer("satellite")) map.removeLayer("satellite");
      if (map.getSource("satellite")) map.removeSource("satellite");
      if (!satellite) return;
      map.addSource("satellite", {
        type: "raster",
        tiles: [SATELLITE_URL],
        tileSize: 256,
        maxzoom: 20,
        attribution: SATELLITE_ATTRIBUTION,
      });
      const first = map.getStyle().layers[0]?.id;
      map.addLayer({ id: "satellite", type: "raster", source: "satellite" }, first);
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [satellite]);

  return (
    <div className="relative">
      <div
        ref={box}
        className="h-80 w-full overflow-hidden rounded-xl border-2 border-neutral-300"
      />
      {SATELLITE_URL && (
        <button
          type="button"
          onClick={() => setSatellite((s) => !s)}
          className="absolute top-2 left-2 rounded-lg bg-white px-3 text-base font-semibold shadow"
        >
          {satellite ? t("setup.plot.streets") : t("setup.plot.satellite")}
        </button>
      )}
    </div>
  );
}
