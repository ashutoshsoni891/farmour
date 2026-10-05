import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../api/schema";

type Plan = components["schemas"]["PlanOut"];
type BedSize = "narrow" | "standard" | "wide";
const ZONES = ["orchard", "water", "rotation", "utility_nursery"] as const;
type Zone = (typeof ZONES)[number];

/** Change the chosen plan: land use (+/-10 points each, spec 7) and bed size, then redraw. */
export function PlanEditor({
  plan,
  busy,
  onRedraw,
  onLock,
}: {
  plan: Plan;
  busy: boolean;
  onRedraw: (delta: Partial<Record<Zone, number>>, bedSize: BedSize) => void;
  onLock: () => void;
}) {
  const { t } = useTranslation();
  const [delta, setDelta] = useState<Partial<Record<Zone, number>>>(plan.share_delta);
  const [size, setSize] = useState<BedSize>((plan.bed_size as BedSize) ?? "standard");
  return (
    <section className="flex flex-col gap-3 rounded-xl border-2 border-green-800 p-3">
      {plan.status === "active" ? (
        <p className="rounded-lg bg-amber-100 p-2 text-base font-semibold">
          {t("editor.is_active")}
        </p>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={onLock}
          className="min-h-12 rounded-xl bg-green-800 px-5 text-lg font-semibold text-white disabled:opacity-50"
        >
          {t("editor.lock")}
        </button>
      )}
      <details>
        <summary className="min-h-11 cursor-pointer text-lg font-bold text-green-900">
          {t("editor.title")}
        </summary>
        <div className="mt-2 flex flex-col gap-4">
          <p className="text-base text-neutral-700">{t("editor.hint")}</p>
          {ZONES.map((z) => {
            const v = delta[z] ?? 0;
            return (
              <label key={z} className="flex flex-col gap-1">
                <span className="flex justify-between text-base font-semibold">
                  <span>{t(`editor.zone.${z}`)}</span>
                  <span>
                    {v === 0
                      ? t("editor.as_option")
                      : t("editor.points", { n: v > 0 ? `+${v}` : v })}
                  </span>
                </span>
                <input
                  type="range"
                  min={-10}
                  max={10}
                  step={5}
                  value={v}
                  onChange={(e) => setDelta({ ...delta, [z]: Number(e.target.value) })}
                  className="h-11 accent-green-800"
                />
              </label>
            );
          })}
          <fieldset className="flex flex-col gap-2">
            <legend className="text-base font-semibold">{t("editor.bed_size")}</legend>
            <div className="flex flex-wrap gap-2">
              {(["narrow", "standard", "wide"] as const).map((b) => (
                <button
                  key={b}
                  type="button"
                  aria-pressed={size === b}
                  onClick={() => setSize(b)}
                  className={`min-h-11 rounded-full border-2 px-4 text-base ${
                    size === b ? "border-green-800 bg-green-800 text-white" : "border-neutral-400"
                  }`}
                >
                  {t(`editor.size.${b}`)}
                </button>
              ))}
            </div>
          </fieldset>
          <button
            type="button"
            disabled={busy}
            onClick={() => onRedraw(delta, size)}
            className="min-h-12 rounded-xl border-2 border-green-800 px-5 text-lg font-semibold text-green-900 disabled:opacity-50"
          >
            {busy ? t("farm.plan_building") : t("editor.redraw")}
          </button>
        </div>
      </details>
    </section>
  );
}
