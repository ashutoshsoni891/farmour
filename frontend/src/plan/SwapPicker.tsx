import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";
import type { Lang } from "../i18n";
import { formatDayMonth, formatNumber } from "../lib/format";
import { cropStyle } from "./cropStyle";

type Alternative = components["schemas"]["AlternativeOut"];

/** Crops that can go in one bed layer instead (the engine checked every rule); tap one to swap. */
export function SwapPicker({
  load,
  onPick,
  onClose,
  lang,
}: {
  load: () => Promise<Alternative[]>;
  onPick: (slug: string) => Promise<void>;
  onClose: () => void;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const [items, setItems] = useState<Alternative[] | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    void load().then((x) => {
      if (live) setItems(x);
    });
    return () => {
      live = false;
    };
    // Load once per picker (the parent remounts it for another bed or layer).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="flex flex-col gap-2 rounded-lg border-2 border-sky-700 bg-sky-50 p-2">
      <div className="flex items-center justify-between">
        <p className="text-base font-semibold">{t("swap.title")}</p>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("farm.bed_close")}
          className="min-h-11 min-w-11 rounded-lg border border-neutral-400"
        >
          ×
        </button>
      </div>
      {items === null && <p role="status">{t("common.loading")}</p>}
      {items !== null && items.length <= 1 && <p className="text-base">{t("swap.none")}</p>}
      {items?.map((a) => {
        const s = cropStyle(a.crop.slug);
        return (
          <button
            key={a.crop.slug}
            type="button"
            disabled={busy || a.current}
            onClick={() => {
              setBusy(true);
              void onPick(a.crop.slug).finally(() => setBusy(false));
            }}
            className="flex min-h-11 flex-col items-start rounded-lg border bg-white px-3 py-2 text-left disabled:opacity-60"
            style={{ borderLeft: `6px solid ${s.color}` }}
          >
            <span className="text-base font-semibold">
              <span aria-hidden="true">{s.emoji} </span>
              {lang === "hi" ? a.crop.name_hi : a.crop.name_en}
              {a.current ? ` · ${t("swap.current")}` : ""}
            </span>
            <span className="text-sm text-neutral-700">
              {t("swap.line", {
                sow: formatDayMonth(new Date(a.planned_sow), lang),
                harvest: formatDayMonth(new Date(a.harvest_start), lang),
                kg: formatNumber(a.expected_yield_kg, lang, 0),
              })}
            </span>
          </button>
        );
      })}
    </div>
  );
}
