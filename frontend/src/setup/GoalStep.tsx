import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";

import { apiClient, errorKey } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";

type Farm = components["schemas"]["FarmOut"];
type Goal = NonNullable<Farm["goal"]>;
type Method = Farm["methods"][number];
type Budget = NonNullable<Farm["budget_band"]>;
type Labour = NonNullable<Farm["labour"]>;

const GOALS: Goal[] = ["income", "low_work", "home_food", "both"];
const METHODS: Method[] = [
  "multilayer",
  "orchard",
  "flowers",
  "natural",
  "polyhouse",
  "integrated",
];
const BUDGETS: Budget[] = ["low", "medium", "high"];
const LABOUR: Labour[] = ["self", "family", "caretaker", "mixed"];
const ICON: Record<string, string> = {
  income: "💰", low_work: "🧘", home_food: "🍲", both: "⚖️",
  multilayer: "🪜", orchard: "🌳", flowers: "🌼", natural: "🐄", polyhouse: "🏠", integrated: "🔄",
}; // prettier-ignore

const card = "flex min-h-14 items-start gap-3 rounded-xl border-2 p-3 text-left";
const on = "border-green-800 bg-green-50";
const off = "border-neutral-300 bg-white";

/** Step 3 of setup: what the owner wants from the land. Drives the plan options. */
export function GoalStep() {
  const { t } = useTranslation();
  const { farmId = "" } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const api = apiClient(token);
  const farm = useQuery({
    queryKey: ["farm", farmId, token],
    queryFn: async () =>
      (await api.GET("/api/v1/farms/{farm_id}", { params: { path: { farm_id: farmId } } })).data,
  });
  const [goal, setGoal] = useState<Goal | null>(null);
  const [methods, setMethods] = useState<Method[] | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [labour, setLabour] = useState<Labour | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!farm.data) {
    return (
      <Screen>
        <p role="status">{t("common.loading")}</p>
      </Screen>
    );
  }
  const f = farm.data;
  const g = goal ?? f.goal ?? null;
  const m = methods ?? (f.methods.length ? f.methods : ["multilayer", "orchard", "natural"]);
  const b = budget ?? f.budget_band ?? null;
  const l = labour ?? f.labour ?? null;

  const save = async (skip: boolean) => {
    setBusy(true);
    setError(null);
    const body = skip
      ? { goal: f.goal ?? "both", methods: m, budget_band: f.budget_band ?? "medium" }
      : {
          goal: g ?? "both",
          methods: m,
          budget_band: b ?? "medium",
          ...(l ? { labour: l } : {}),
        };
    const patched = await api.PATCH("/api/v1/farms/{farm_id}", {
      params: { path: { farm_id: farmId } },
      body,
    });
    if (patched.error) {
      setBusy(false);
      return setError(t(errorKey(patched.error)));
    }
    // Build the plan options right away so the farm page opens with them.
    await api.POST("/api/v1/farms/{farm_id}/plan/options", {
      params: { path: { farm_id: farmId } },
    });
    await queryClient.invalidateQueries({ queryKey: ["farm", farmId] });
    await queryClient.invalidateQueries({ queryKey: ["plan-options", farmId] });
    await queryClient.invalidateQueries({ queryKey: ["plan", farmId] });
    setBusy(false);
    void navigate(`/farms/${farmId}`, { replace: true });
  };

  return (
    <Screen>
      <p className="text-base font-semibold text-neutral-700">
        {t("setup.step", { n: 3, total: 3 })}
      </p>
      <h1 className="text-2xl font-bold">{t("goal.title")}</h1>
      <p className="text-base text-neutral-700">{t("goal.hint")}</p>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-lg font-bold">{t("goal.q_goal")}</legend>
        {GOALS.map((x) => (
          <button
            key={x}
            type="button"
            aria-pressed={g === x}
            onClick={() => setGoal(x)}
            className={`${card} ${g === x ? on : off}`}
          >
            <span aria-hidden="true" className="text-2xl">
              {ICON[x]}
            </span>
            <span>
              <span className="block text-lg font-semibold">{t(`goal.goal.${x}`)}</span>
              <span className="block text-base text-neutral-700">{t(`goal.goal.${x}_what`)}</span>
            </span>
          </button>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-lg font-bold">{t("goal.q_methods")}</legend>
        <p className="text-base text-neutral-700">{t("goal.methods_hint")}</p>
        <div className="grid grid-cols-2 gap-2">
          {METHODS.map((x) => {
            const picked = m.includes(x);
            return (
              <button
                key={x}
                type="button"
                aria-pressed={picked}
                onClick={() => setMethods(picked ? m.filter((y) => y !== x) : [...m, x])}
                className={`${card} flex-col ${picked ? on : off}`}
              >
                <span aria-hidden="true" className="text-2xl">
                  {ICON[x]}
                </span>
                <span className="text-base font-semibold">{t(`goal.method.${x}`)}</span>
                <span className="text-sm text-neutral-700">{t(`goal.method.${x}_what`)}</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-lg font-bold">{t("goal.q_budget")}</legend>
        <div className="flex flex-wrap gap-2">
          {BUDGETS.map((x) => (
            <button
              key={x}
              type="button"
              aria-pressed={b === x}
              onClick={() => setBudget(x)}
              className={`min-h-12 rounded-xl border-2 px-4 text-lg font-semibold ${b === x ? "border-green-800 bg-green-800 text-white" : "border-neutral-400 bg-white"}`}
            >
              {t(`goal.budget.${x}`)}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-lg font-bold">{t("setup.about.labour")}</legend>
        <div className="flex flex-wrap gap-2">
          {LABOUR.map((x) => (
            <button
              key={x}
              type="button"
              aria-pressed={l === x}
              onClick={() => setLabour(x)}
              className={`min-h-12 rounded-xl border-2 px-4 text-lg font-semibold ${l === x ? "border-green-800 bg-green-800 text-white" : "border-neutral-400 bg-white"}`}
            >
              {t(`setup.labour.${x}`)}
            </button>
          ))}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={busy}
        onClick={() => void save(false)}
        className="min-h-14 rounded-xl bg-green-800 px-5 text-lg font-semibold text-white disabled:opacity-50"
      >
        {busy ? t("goal.building") : t("goal.done")}
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() => void save(true)}
        className="min-h-11 text-lg font-semibold text-green-800 underline"
      >
        {t("goal.later")}
      </button>
    </Screen>
  );
}
