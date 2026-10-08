import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";
import { ZONE_COLORS } from "../setup/PlotMap";
import { BedDetail } from "./BedDetail";
import { ZONE_ICON } from "./FarmMap";
import type { MapSelection } from "./FarmMap";
import { FieldRow } from "./FieldCrops";
import { PerennialCard } from "./Perennials";
import { cropStyle, plantingsOf } from "./cropStyle";

type Plan = components["schemas"]["PlanOut"];
type Alternative = components["schemas"]["AlternativeOut"];

/** Details of whatever was tapped on the map: a bed, a field plot, a kind of tree, or an area. */
export function MapInspector({
  plan,
  selection,
  seasonLabel,
  onSelect,
  onClose,
  unit,
  lang,
  bighaSqft,
  loadAlternatives,
  onSwap,
}: {
  plan: Plan;
  selection: MapSelection;
  seasonLabel: string | undefined;
  onSelect: (s: MapSelection) => void;
  onClose: () => void;
  unit: UnitPref;
  lang: Lang;
  bighaSqft: number | null;
  loadAlternatives?:
    ((code: string, season: string, layer: string) => Promise<Alternative[]>) | undefined;
  onSwap?:
    ((code: string, season: string, layer: string, slug: string) => Promise<void>) | undefined;
}) {
  const { t } = useTranslation();
  const name = (c: { name_en: string; name_hi: string }) => (lang === "hi" ? c.name_hi : c.name_en);
  const area = (sqm: number) => {
    const a = formatArea(sqm, unit, lang, bighaSqft);
    return t(a.key, { n: a.n });
  };

  let icon: string;
  let color: string;
  let title: string;
  let subtitle: string;
  let body: ReactNode;

  if (selection.kind === "bed") {
    const crops = plantingsOf(plan, seasonLabel).filter((p) => p.bed_code === selection.code);
    const main = crops[0];
    icon = main ? cropStyle(main.crop.slug).emoji : "🥬";
    color = main ? cropStyle(main.crop.slug).color : "#a8a29e";
    title = t("farm.bed_title", { code: selection.code });
    subtitle = crops.map((p) => name(p.crop)).join(" · ") || t("map.bed_free");
    body = (
      <BedDetail
        plan={plan}
        code={selection.code}
        seasonLabel={seasonLabel}
        lang={lang}
        loadAlternatives={loadAlternatives}
        onSwap={onSwap}
      />
    );
  } else if (selection.kind === "plot") {
    const rows = plan.fields.filter((f) => f.plot_code === selection.code);
    const now = rows.find((f) => f.season_label === seasonLabel);
    icon = now ? cropStyle(now.crop.slug).emoji : "🌾";
    color = now ? cropStyle(now.crop.slug).color : (ZONE_COLORS.rotation ?? "#ca8a04");
    title = t("map.plot", { code: selection.code });
    subtitle = `${area(rows[0]?.area_sqm ?? 0)} · ${now ? name(now.crop) : t("map.fallow")}`;
    body = (
      <div className="flex flex-col gap-2">
        <p className="text-base text-neutral-700">{t("fields.hint")}</p>
        <ul className="flex flex-col gap-2">
          {rows.map((f) => (
            <FieldRow
              key={f.season_label + f.crop.slug}
              f={f}
              lang={lang}
              now={f.season_label === seasonLabel}
            />
          ))}
        </ul>
      </div>
    );
  } else if (selection.kind === "plant") {
    const g = plan.perennials[selection.group];
    if (!g) return null;
    icon = cropStyle(g.crop.slug).emoji;
    color = cropStyle(g.crop.slug).color;
    title = name(g.crop);
    subtitle = t(g.kind === "tree" ? "perennial.trees" : "perennial.plants", { n: g.count });
    body = (
      <ul className="flex flex-col gap-2">
        <PerennialCard p={g} lang={lang} />
      </ul>
    );
  } else {
    const z = plan.zones.find((x) => x.id === selection.id);
    if (!z) return null;
    icon = ZONE_ICON[z.kind] ?? "";
    color = ZONE_COLORS[z.kind] ?? "#16a34a";
    title = t(`plan.zone.${z.kind}`);
    subtitle = area(z.area_sqm);
    const beds = plan.beds.filter((b) => b.zone_id === z.id);
    const kind = z.kind === "orchard" ? "tree" : z.kind === "border" ? "hedge" : null;
    const groups = kind
      ? plan.perennials.map((g, i) => ({ g, i })).filter(({ g }) => g.kind === kind)
      : [];
    const plots = [...new Set(plan.fields.map((f) => f.plot_code))];
    body = (
      <div className="flex flex-col gap-3">
        <p className="text-base">{t(`map.zone_what.${z.kind}`)}</p>
        {beds.length > 0 && (
          <p className="text-base font-semibold">{t("map.zone_beds", { n: beds.length })}</p>
        )}
        {groups.length > 0 && (
          <div className="flex flex-col gap-2">
            {groups.map(({ g, i }) => (
              <button
                key={i}
                type="button"
                onClick={() => onSelect({ kind: "plant", group: i })}
                className="flex min-h-11 items-center gap-2 rounded-lg border bg-white px-3 text-left text-base"
                style={{ borderLeft: `6px solid ${cropStyle(g.crop.slug).color}` }}
              >
                <span aria-hidden="true">{cropStyle(g.crop.slug).emoji}</span>
                <span className="font-semibold">{name(g.crop)}</span>
                <span className="text-neutral-600">
                  {t(g.kind === "tree" ? "perennial.trees" : "perennial.plants", { n: g.count })}
                </span>
              </button>
            ))}
          </div>
        )}
        {z.kind === "rotation" && plots.length > 0 && (
          <div className="flex flex-col gap-2">
            {plots.map((code) => {
              const now = plan.fields.find(
                (f) => f.plot_code === code && f.season_label === seasonLabel,
              );
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => onSelect({ kind: "plot", code })}
                  className="flex min-h-11 items-center gap-2 rounded-lg border bg-white px-3 text-left text-base"
                >
                  <span className="font-semibold">{t("map.plot", { code })}</span>
                  <span className="text-neutral-600">
                    {now ? `${cropStyle(now.crop.slug).emoji} ${name(now.crop)}` : t("map.fallow")}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div
        className="sticky top-0 z-10 flex items-start gap-3 border-b bg-white px-4 pt-3 pb-2"
        style={{ borderTop: `5px solid ${color}` }}
      >
        <span aria-hidden="true" className="text-3xl leading-none">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xl font-bold">{title}</p>
          <p className="truncate text-base text-neutral-700">{subtitle}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("farm.bed_close")}
          className="min-h-11 min-w-11 rounded-full bg-neutral-100 text-xl"
        >
          ×
        </button>
      </div>
      <div className="px-4 py-3">{body}</div>
    </div>
  );
}
