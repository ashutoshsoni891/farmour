import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatNumber } from "../lib/format";
import { BedPicture } from "./BedPicture";
import { BedTimeline } from "./BedTimeline";
import { SwapPicker } from "./SwapPicker";

type Plan = components["schemas"]["PlanOut"];
type Alternative = components["schemas"]["AlternativeOut"];

/** Everything planned in one bed: size, a side view of this season's layers (tap a layer to
 * change its crop), and the bed's crops through the year. */
export function BedDetail({
  plan,
  code,
  seasonLabel,
  lang,
  loadAlternatives,
  onSwap,
}: {
  plan: Plan;
  code: string;
  seasonLabel: string | undefined;
  lang: Lang;
  loadAlternatives?:
    ((code: string, season: string, layer: string) => Promise<Alternative[]>) | undefined;
  onSwap?:
    ((code: string, season: string, layer: string, slug: string) => Promise<void>) | undefined;
}) {
  const { t } = useTranslation();
  const [swapLayer, setSwapLayer] = useState<string | null>(null);
  const bed = plan.beds.find((b) => b.code === code);
  if (!bed) return null;
  const rows = plan.plantings.filter((p) => p.bed_code === code && p.season_label === seasonLabel);
  const all = plan.plantings.filter((p) => p.bed_code === code);
  return (
    <div className="flex flex-col gap-3">
      <p className="text-base text-neutral-700">
        {t("farm.bed_size", {
          length: formatNumber(bed.length_m, lang, 1),
          width: formatNumber(bed.width_m, lang, 1),
        })}
        {bed.raised ? ` · ${t("farm.bed_raised")}` : ""}
        {bed.has_trellis ? ` · ${t("farm.bed_trellis")}` : ""}
        {bed.protected ? ` · ${t("farm.bed_covered")}` : ""}
      </p>
      {rows.length === 0 && <p className="text-base">{t("map.bed_free_season")}</p>}
      <BedPicture
        onChange={loadAlternatives && seasonLabel ? setSwapLayer : undefined}
        bed={bed}
        rows={rows}
        trellisM={plan.trellis_height_m ?? null}
        widthM={plan.bed_width_m ?? null}
        pathM={plan.path_width_m ?? null}
        lang={lang}
      />
      {swapLayer && seasonLabel && loadAlternatives && onSwap && (
        <SwapPicker
          key={`${code}-${seasonLabel}-${swapLayer}`}
          load={() => loadAlternatives(code, seasonLabel, swapLayer)}
          onPick={async (slug) => {
            await onSwap(code, seasonLabel, swapLayer, slug);
            setSwapLayer(null);
          }}
          onClose={() => setSwapLayer(null)}
          lang={lang}
        />
      )}
      <BedTimeline rows={all} start={plan.start_date} lang={lang} />
    </div>
  );
}
