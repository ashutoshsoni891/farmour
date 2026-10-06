import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatDayMonth } from "../lib/format";
import { LAYERS_TOP_DOWN, cropStyle } from "./cropStyle";

type Planting = components["schemas"]["PlantingOut"];
type Bed = components["schemas"]["BedOut"];

const GROUND = 200;
const TOP = 28; // the top of the machan in the drawing (not to scale)

/** Side view of one bed for one season: the machan, then each layer from the sky down to the roots. */
export function BedPicture({
  bed,
  rows,
  trellisM,
  widthM,
  pathM,
  lang,
  onChange,
}: {
  onChange?: ((layer: string) => void) | undefined;
  bed: Bed;
  rows: Planting[];
  trellisM: number | null;
  widthM: number | null;
  pathM: number | null;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const by = (layer: string) => rows.find((r) => r.layer === layer);
  const climber = by("climber");
  const middle = by("middle");
  const surface = by("surface");
  const roots = by("underground");
  const name = (p: Planting) => (lang === "hi" ? p.crop.name_hi : p.crop.name_en);

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox="0 0 360 290"
        role="img"
        aria-label={t("picture.alt", { code: bed.code })}
        className="w-full rounded-xl border border-neutral-300"
      >
        <rect width="360" height={GROUND} fill="#e0f2fe" />
        <rect y={GROUND} width="360" height="90" fill="#78350f" />
        <rect y={GROUND} width="360" height="6" fill="#4d7c0f" />

        {/* the bed itself, raised when the plan says so */}
        <rect
          x="60"
          y={bed.raised ? GROUND - 14 : GROUND - 4}
          width="240"
          height={bed.raised ? 18 : 8}
          rx="4"
          fill="#a16207"
        />

        {/* a covered bed inside the polyhouse: the plastic roof */}
        {bed.protected && (
          <path
            d={`M8 ${GROUND} L8 70 Q180 -10 352 70 L352 ${GROUND}`}
            fill="#e0f2fe"
            fillOpacity="0.35"
            stroke="#0369a1"
            strokeWidth="3"
          />
        )}

        {/* machan: posts, top frame, crisscross rope */}
        {bed.has_trellis && (
          <g>
            <rect x="52" y={TOP} width="6" height={GROUND - TOP} fill="#92400e" />
            <rect x="302" y={TOP} width="6" height={GROUND - TOP} fill="#92400e" />
            <rect x="48" y={TOP} width="264" height="7" rx="2" fill="#92400e" />
            {[0, 1, 2, 3, 4, 5, 6].map((i) => (
              <g key={i} stroke="#d6a56a" strokeWidth="1.2">
                <line x1={70 + i * 36} y1={TOP + 7} x2={88 + i * 36} y2={GROUND - 6} />
                <line x1={88 + i * 36} y1={TOP + 7} x2={70 + i * 36} y2={GROUND - 6} />
              </g>
            ))}
          </g>
        )}

        {/* climber: vines up the rope with fruit hanging from the frame */}
        {bed.has_trellis && climber && (
          <g>
            {[0, 1, 2, 3, 4].map((i) => {
              const x = 82 + i * 50;
              return (
                <g key={i}>
                  <path
                    d={`M${x} ${GROUND - 6} C ${x - 14} 150, ${x + 14} 100, ${x} ${TOP + 10}`}
                    stroke="#166534"
                    strokeWidth="3"
                    fill="none"
                  />
                  <ellipse cx={x + 10} cy="78" rx="6" ry="9" fill="#22c55e" />
                  <ellipse cx={x - 9} cy="118" rx="6" ry="9" fill="#22c55e" />
                  <ellipse
                    cx={x + 4}
                    cy="62"
                    rx="7"
                    ry="16"
                    fill={cropStyle(climber.crop.slug).color}
                  />
                  <ellipse
                    cx={x - 6}
                    cy="100"
                    rx="6"
                    ry="14"
                    fill={cropStyle(climber.crop.slug).color}
                  />
                </g>
              );
            })}
          </g>
        )}

        {/* main crop: bushes at mid height */}
        {middle && (
          <g>
            {[0, 1, 2, 3].map((i) => {
              const x = 100 + i * 52;
              const c = cropStyle(middle.crop.slug).color;
              return (
                <g key={i}>
                  <rect x={x - 2} y="132" width="4" height={GROUND - 136} fill="#166534" />
                  <circle cx={x} cy="140" r="26" fill="#16a34a" opacity="0.85" />
                  <circle cx={x - 12} cy="130" r="6" fill={c} />
                  <circle cx={x + 10} cy="146" r="6" fill={c} />
                  <circle cx={x + 2} cy="122" r="5" fill={c} />
                </g>
              );
            })}
          </g>
        )}

        {/* leafy crop at the foot */}
        {surface && (
          <g fill={cropStyle(surface.crop.slug).color} stroke="#14532d" strokeWidth="0.6">
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
              <path key={i} d={`M${72 + i * 24} ${GROUND - 4} q6 -26 12 0 z`} />
            ))}
          </g>
        )}

        {/* roots under the soil */}
        {roots && (
          <g fill={cropStyle(roots.crop.slug).color}>
            {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <path
                key={i}
                d={`M${76 + i * 26} ${GROUND + 8} q10 0 10 14 q-5 22 -10 26 q-5 -4 -10 -26 q0 -14 10 -14 z`}
              />
            ))}
          </g>
        )}

        {/* dimensions */}
        {bed.has_trellis && trellisM !== null && (
          <g stroke="#0f172a" strokeWidth="1.2" fill="#0f172a" fontSize="13">
            <line x1="26" y1={TOP} x2="26" y2={GROUND} />
            <line x1="20" y1={TOP} x2="32" y2={TOP} />
            <line x1="20" y1={GROUND} x2="32" y2={GROUND} />
            <text
              x="4"
              y={(TOP + GROUND) / 2}
              stroke="none"
              transform={`rotate(-90 12 ${(TOP + GROUND) / 2})`}
              textAnchor="middle"
            >
              {trellisM} m
            </text>
          </g>
        )}
        {widthM !== null && (
          <g stroke="#fde68a" strokeWidth="1.2" fill="#fde68a" fontSize="13">
            <line x1="60" y1="278" x2="300" y2="278" />
            <line x1="60" y1="272" x2="60" y2="284" />
            <line x1="300" y1="272" x2="300" y2="284" />
            <text x="180" y="270" stroke="none" textAnchor="middle">
              {t("picture.bed_width", { w: widthM })}
              {pathM !== null ? ` · ${t("picture.path", { p: pathM })}` : ""}
            </text>
          </g>
        )}
      </svg>

      {/* the same layers in words, top to bottom, matching the drawing */}
      <ol className="flex flex-col gap-1">
        {LAYERS_TOP_DOWN.map((layer) => {
          const r = by(layer);
          if (layer === "climber" && !bed.has_trellis) return null;
          const style = r ? cropStyle(r.crop.slug) : null;
          return (
            <li
              key={layer}
              className="flex items-center gap-2 rounded-lg border border-neutral-200 px-2 py-1"
              style={style ? { borderLeft: `6px solid ${style.color}` } : undefined}
            >
              <span className="w-28 shrink-0 text-sm text-neutral-600">
                {t(`plan.layer.${layer}`)}
              </span>
              {r && style ? (
                <span className="text-base">
                  <span aria-hidden="true">{style.emoji} </span>
                  <span className="font-semibold">{name(r)}</span>{" "}
                  <span className="text-sm text-neutral-700">
                    ·{" "}
                    {t("farm.bed_sow", {
                      date: formatDayMonth(new Date(r.planned_sow), lang),
                      n: r.plant_count,
                    })}
                  </span>
                </span>
              ) : (
                <span className="text-base text-neutral-500">{t("picture.empty")}</span>
              )}
              {onChange && (
                <button
                  type="button"
                  onClick={() => onChange(layer)}
                  className="ml-auto min-h-11 shrink-0 rounded-lg border-2 border-sky-700 px-2 text-sm font-semibold text-sky-900"
                >
                  {r ? t("swap.change") : t("swap.add")}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
