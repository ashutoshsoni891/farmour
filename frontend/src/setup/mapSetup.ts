import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

// A bundled worker file: works under a strict Content-Security-Policy (no blob workers).
setWorkerUrl(workerUrl);

/** Base street style (OpenFreeMap); satellite imagery goes on top of it when available. */
export const STREETS = "https://tiles.openfreemap.org/styles/liberty";
