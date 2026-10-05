import { googleSatelliteEnabled } from "./googleTiles";

/** Satellite imagery sources, best first.
 *
 * Google Map Tiles (licensed, needs VITE_GOOGLE_MAPS_KEY) is the production source.
 * Esri World Imagery is free but its terms do not allow our commercial use, so it is only
 * switched on for local development/review builds (VITE_DEV_IMAGERY=esri) and never in
 * staging or production.
 */
export const esriDevImagery = import.meta.env.VITE_DEV_IMAGERY === "esri";
export const satelliteAvailable = googleSatelliteEnabled || esriDevImagery;

export const ESRI_TILES =
  "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
export const ESRI_CREDIT = "Esri, Maxar, Earthstar Geographics, and the GIS User Community";
