import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { cropStyle } from "./cropStyle";

type Planting = components["schemas"]["PlantingOut"];

const DAY = 86_400_000;

/** A year strip for one bed: each crop from sowing (light) to harvest (solid). */
export function BedTimeline({
  rows,
  start,
  days = 365,
  lang,
}: {
  rows: Planting[];
  start: string;
  days?: number;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const t0 = new Date(start).getTime();
  const pos = (d: string) =>
    Math.min(100, Math.max(0, ((new Date(d).getTime() - t0) / DAY / days) * 100));
  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(t0);
    d.setMonth(d.getMonth() + i, 1);
    return {
      left: pos(d.toISOString().slice(0, 10)),
      label: new Intl.DateTimeFormat(`${lang === "hi" ? "hi-IN" : "en-IN"}-u-nu-latn`, {
        month: lang === "hi" ? "short" : "narrow",
      }).format(d),
    };
  });
  const sorted = [...rows].sort((a, b) => a.planned_sow.localeCompare(b.planned_sow));
  return (
    <div className="flex flex-col gap-1" aria-label={t("picture.timeline")}>
      <p className="text-sm font-semibold text-neutral-700">{t("picture.timeline")}</p>
      <div className="relative h-5 border-b border-neutral-300">
        {months.map((m) => (
          <span
            key={m.label + m.left}
            className="absolute text-[11px] text-neutral-600"
            style={{ left: `${m.left}%` }}
          >
            {m.label}
          </span>
        ))}
      </div>
      {sorted.map((r) => {
        const s = cropStyle(r.crop.slug);
        const sow = pos(r.planned_sow);
        const hs = pos(r.harvest_start ?? r.planned_sow);
        const he = pos(r.harvest_end ?? r.harvest_start ?? r.planned_sow);
        return (
          <div
            key={r.layer + r.season_label + r.crop.slug}
            className="relative h-7 rounded bg-neutral-100"
          >
            <span
              className="absolute top-1 h-5 rounded-l opacity-35"
              style={{ left: `${sow}%`, width: `${Math.max(hs - sow, 0.5)}%`, background: s.color }}
            />
            <span
              className="absolute top-1 h-5 rounded-r"
              style={{ left: `${hs}%`, width: `${Math.max(he - hs, 1.5)}%`, background: s.color }}
            />
            <span className="absolute top-0.5 left-1 text-xs font-semibold text-neutral-900 drop-shadow-[0_0_2px_#fff]">
              {s.emoji} {lang === "hi" ? r.crop.name_hi : r.crop.name_en}
            </span>
          </div>
        );
      })}
      <p className="text-xs text-neutral-600">{t("picture.timeline_hint")}</p>
    </div>
  );
}
