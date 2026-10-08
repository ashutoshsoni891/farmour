import type { Map as MapLibreMap } from "maplibre-gl";
import { useEffect, useState } from "react";
import type { RefObject } from "react";

import { googleCredit, googleSatelliteEnabled, googleSession, googleTileUrl } from "./googleTiles";
import { ESRI_CREDIT, ESRI_TILES, satelliteAvailable } from "./imagery";

/** Satellite imagery under a MapLibre map: Google Map Tiles when a key is configured, the Esri
 * development imagery otherwise (local builds only), street map when neither is available.
 * Call it after the effect that creates the map. */
export function useSatellite(mapRef: RefObject<MapLibreMap | null>, lang: "hi" | "en") {
  const [satellite, setSatellite] = useState(satelliteAvailable);
  const [provider, setProvider] = useState<"google" | "esri" | null>(null);
  const [credit, setCredit] = useState("");

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let cancelled = false;
    let onMove: (() => void) | null = null;
    const remove = () => {
      if (map.getLayer("satellite")) map.removeLayer("satellite");
      if (map.getSource("satellite")) map.removeSource("satellite");
    };
    // Under the street labels and our drawing, over the street base.
    const below = () => map.getStyle().layers.find((l) => l.type === "symbol")?.id;
    const apply = async () => {
      remove();
      setCredit("");
      if (!satellite) return;
      const session = googleSatelliteEnabled ? await googleSession(lang) : null;
      if (cancelled) return;
      if (!session && !satelliteAvailable) return setSatellite(false);
      if (!session) {
        // Development imagery (Esri). Rural India is sharp only to zoom 18; past that the tiles are
        // grey placeholders, so zoom-18 tiles are stretched instead.
        setProvider("esri");
        setCredit(ESRI_CREDIT);
        map.addSource("satellite", {
          type: "raster",
          tiles: [ESRI_TILES],
          tileSize: 256,
          maxzoom: 18,
        });
        map.addLayer({ id: "satellite", type: "raster", source: "satellite" }, below());
        return;
      }
      setProvider("google");
      map.addSource("satellite", {
        type: "raster",
        tiles: [googleTileUrl(session)],
        tileSize: 256,
        maxzoom: 22,
      });
      map.addLayer({ id: "satellite", type: "raster", source: "satellite" }, below());
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
  }, [mapRef, satellite, lang]);

  return { satellite, setSatellite, provider, credit };
}

/** The imagery credit (and the Google logo) that must stay visible on the map. */
export function SatelliteCredit({
  provider,
  credit,
  className = "bottom-1 left-2",
}: {
  provider: "google" | "esri" | null;
  credit: string;
  className?: string;
}) {
  return (
    <div
      className={`pointer-events-none absolute flex max-w-[70%] items-center gap-2 ${className}`}
    >
      {provider === "google" && (
        <img
          src="https://maps.gstatic.com/mapfiles/api-3/images/google_white5.png"
          alt="Google"
          className="h-4"
        />
      )}
      {credit && <span className="truncate text-[11px] text-white drop-shadow">{credit}</span>}
    </div>
  );
}
