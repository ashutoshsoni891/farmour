import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";

type Plan = components["schemas"]["PlanOut"];

/** A small drawing of one bed's layers, from the trellis down to the roots. */
function LayersIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-12 w-12 shrink-0" aria-hidden="true">
      <rect x="4" y="4" width="40" height="3" fill="#92400e" />
      <rect x="6" y="4" width="2" height="30" fill="#92400e" />
      <rect x="40" y="4" width="2" height="30" fill="#92400e" />
      <ellipse cx="18" cy="12" rx="2.5" ry="5" fill="#16a34a" />
      <ellipse cx="30" cy="12" rx="2.5" ry="5" fill="#16a34a" />
      <circle cx="16" cy="22" r="6" fill="#15803d" />
      <circle cx="32" cy="22" r="6" fill="#15803d" />
      <circle cx="15" cy="21" r="1.6" fill="#dc2626" />
      <circle cx="33" cy="23" r="1.6" fill="#dc2626" />
      <path
        d="M8 34 l3 -5 l3 5 M20 34 l3 -5 l3 5 M32 34 l3 -5 l3 5"
        stroke="#22c55e"
        strokeWidth="2"
        fill="none"
      />
      <rect x="0" y="34" width="48" height="14" fill="#78350f" />
      <path d="M12 37 q3 0 3 4 q-1.5 5 -3 6 q-1.5 -1 -3 -6 q0 -4 3 -4z" fill="#db2777" />
      <path d="M30 37 q3 0 3 4 q-1.5 5 -3 6 q-1.5 -1 -3 -6 q0 -4 3 -4z" fill="#db2777" />
    </svg>
  );
}

/** "How this plan farms": the methods this plan uses, each in one line, with what it means. */
export function Methods({
  plan,
  methods,
  unit,
  lang,
  bighaSqft,
}: {
  plan: Plan;
  methods: string[];
  unit: UnitPref;
  lang: Lang;
  bighaSqft: number | null;
}) {
  const { t } = useTranslation();
  const area = (kind: string) =>
    plan.zones.filter((z) => z.kind === kind).reduce((a, z) => a + z.area_sqm, 0);
  const show = (sqm: number) => {
    const a = formatArea(sqm, unit, lang, bighaSqft);
    return t(a.key, { n: a.n });
  };
  // beds that hold 3 or more crops at once in some season
  const perBedSeason = new Map<string, number>();
  for (const p of plan.plantings) {
    const k = `${p.bed_code}|${p.season_label}`;
    perBedSeason.set(k, (perBedSeason.get(k) ?? 0) + 1);
  }
  const stacked = new Set(
    [...perBedSeason.entries()].filter(([, n]) => n >= 3).map(([k]) => k.split("|")[0]),
  );
  const trees = plan.perennials.filter((p) => p.kind === "tree");
  const hedge = plan.perennials.filter((p) => p.kind === "hedge");
  const covered = plan.beds.filter((b) => b.protected).length;
  const cards: { icon: React.ReactNode; title: string; text: string }[] = [];

  if (stacked.size > 0) {
    cards.push({
      icon: <LayersIcon />,
      title: t("method.multilayer"),
      text: t("method.multilayer_text", { n: stacked.size }),
    });
  }
  if (trees.length > 0) {
    cards.push({
      icon: <span className="text-4xl">🌳</span>,
      title: t("method.orchard"),
      text: t("method.orchard_text", {
        n: trees.reduce((a, p) => a + p.count, 0),
        kinds: trees.length,
      }),
    });
  }
  if (area("polyhouse") > 0) {
    cards.push({
      icon: <span className="text-4xl">🏠</span>,
      title: t("method.polyhouse"),
      text: t("method.polyhouse_text", { area: show(area("polyhouse")), n: covered }),
    });
  } else if (methods.includes("polyhouse")) {
    cards.push({
      icon: <span className="text-4xl">🏠</span>,
      title: t("method.polyhouse"),
      text: t("method.polyhouse_no_room"),
    });
  }
  if (area("livestock") > 0) {
    cards.push({
      icon: <span className="text-4xl">🐄</span>,
      title: t("method.integrated"),
      text: t("method.integrated_text", { area: show(area("livestock")) }),
    });
  } else if (methods.includes("integrated")) {
    cards.push({
      icon: <span className="text-4xl">🐄</span>,
      title: t("method.integrated"),
      text: t("method.integrated_no_room"),
    });
  }
  if (area("water") > 0 && area("utility") > 0) {
    cards.push({
      icon: <span className="text-4xl">🔄</span>,
      title: t("method.loop"),
      text: t("method.loop_text"),
    });
  }
  if (methods.includes("natural")) {
    cards.push({
      icon: <span className="text-4xl">🌱</span>,
      title: t("method.natural"),
      text: t("method.natural_text"),
    });
  }
  if (hedge.length > 0) {
    cards.push({
      icon: <span className="text-4xl">🌿</span>,
      title: t("method.hedge"),
      text: t("method.hedge_text"),
    });
  }
  cards.push({
    icon: <span className="text-4xl">♻️</span>,
    title: t("method.rotation"),
    text: t("method.rotation_text"),
  });

  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-xl font-bold text-green-900">{t("method.title")}</h2>
      <ul className="grid grid-cols-1 gap-2">
        {cards.map((c) => (
          <li
            key={c.title}
            className="flex items-start gap-3 rounded-xl border border-green-700 bg-white p-3"
          >
            <span
              aria-hidden="true"
              className="flex h-12 w-12 shrink-0 items-center justify-center"
            >
              {c.icon}
            </span>
            <span>
              <span className="block text-lg font-semibold">{c.title}</span>
              <span className="block text-base text-neutral-800">{c.text}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
