import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";

import { apiClient, errorKey } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";

type Tab = "crops" | "recipes" | "review";
const STATUSES = ["draft", "in_review", "approved", "retired"];
const chip = "rounded-full bg-neutral-200 px-3 py-0.5 text-sm font-semibold";

function useApi() {
  const { token } = useAuth();
  return { api: apiClient(token), token };
}

function Progress() {
  const { t } = useTranslation();
  const { api, token } = useApi();
  const progress = useQuery({
    queryKey: ["library-progress", token],
    queryFn: async () => (await api.GET("/api/v1/library/progress")).data,
  });
  if (!progress.data) return null;
  return (
    <p className="rounded-lg bg-green-50 p-3 text-base">
      {t("library.progress", {
        crops: progress.data["crops"] ?? 0,
        recipes: progress.data["recipes"] ?? 0,
      })}
    </p>
  );
}

function Crops() {
  const { t, i18n } = useTranslation();
  const { api, token } = useApi();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const crops = useQuery({
    queryKey: ["crops", token, q, status],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/library/crops", {
        params: { query: { limit: 100, ...(q ? { q } : {}), ...(status ? { status } : {}) } },
      });
      if (error) throw error;
      return data;
    },
  });
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <input
          aria-label={t("library.search")}
          placeholder={t("library.search")}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="min-w-0 flex-1 rounded-lg border-2 border-neutral-400 px-3 text-base"
        />
        <select
          aria-label={t("library.all_statuses")}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border-2 border-neutral-400 px-3 text-base"
        >
          <option value="">{t("library.all_statuses")}</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`library.status.${s}`)}
            </option>
          ))}
        </select>
      </div>
      {crops.isError && <p role="alert">{t(errorKey(crops.error))}</p>}
      {crops.data?.items.length === 0 && <p>{t("library.no_items")}</p>}
      <ul className="flex flex-col gap-2">
        {crops.data?.items.map((c) => (
          <li key={c.id}>
            <Link
              to={`/library/crops/${c.id}`}
              className="flex min-h-11 items-center justify-between gap-2 rounded-xl border-2 border-neutral-300 px-4 py-2"
            >
              <span className="text-lg font-semibold">
                {i18n.language === "hi" ? c.name_hi : c.name_en}
              </span>
              <span className="flex items-center gap-2">
                {c.todo_count > 0 && c.status === "draft" && (
                  <span className="text-sm text-amber-800">
                    {t("library.todo_count", { count: c.todo_count })}
                  </span>
                )}
                <span className={chip}>{t(`library.status.${c.status}`)}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function Recipes() {
  const { t, i18n } = useTranslation();
  const { api, token } = useApi();
  const recipes = useQuery({
    queryKey: ["recipes", token],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/library/recipes");
      if (error) throw error;
      return data;
    },
  });
  return (
    <ul className="flex flex-col gap-2">
      {recipes.data?.map((r) => (
        <li key={r.id}>
          <Link
            to={`/library/recipes/${r.id}`}
            className="flex min-h-11 items-center justify-between gap-2 rounded-xl border-2 border-neutral-300 px-4 py-2"
          >
            <span className="text-lg font-semibold">
              {i18n.language === "hi" ? r.name_hi : r.name_en}
            </span>
            <span className={chip}>{t(`library.status.${r.status}`)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Review() {
  const { t, i18n } = useTranslation();
  const { api, token } = useApi();
  const queryClient = useQueryClient();
  const queue = useQuery({
    queryKey: ["review", token],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/library/review");
      if (error) throw error;
      return data;
    },
  });
  const [message, setMessage] = useState<string | null>(null);
  const approve = async (entity: string, id: string) => {
    setMessage(null);
    const kind =
      entity === "crop"
        ? "crops"
        : entity === "recipe"
          ? "recipes"
          : entity === "pest"
            ? "pests"
            : "rules";
    const { error, response } = await api.POST("/api/v1/library/{entity}/{entry_id}/approve", {
      params: { path: { entity: kind, entry_id: id } },
    });
    if (!response.ok) return setMessage(t(errorKey(error)));
    await queryClient.invalidateQueries();
  };
  if (queue.data?.length === 0) return <p>{t("library.review_empty")}</p>;
  return (
    <>
      {message && (
        <p role="alert" className="font-semibold text-red-800">
          {message}
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {queue.data?.map((item) => (
          <li
            key={item.id}
            className="flex flex-col gap-2 rounded-xl border-2 border-neutral-300 p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <Link
                to={
                  item.entity === "crop"
                    ? `/library/crops/${item.id}`
                    : `/library/recipes/${item.id}`
                }
                className="text-lg font-semibold underline"
              >
                {i18n.language === "hi" ? item.name_hi : item.name_en}
              </Link>
              <span className={chip}>{t(`library.entity.${item.entity}`)}</span>
            </div>
            {item.blocked_reason && (
              <p className="text-base text-neutral-700">
                {t(`library.blocked.${item.blocked_reason}`)}
              </p>
            )}
            <button
              type="button"
              disabled={!item.can_approve}
              onClick={() => void approve(item.entity, item.id)}
              className="self-start rounded-xl bg-green-800 px-5 text-lg font-semibold text-white disabled:opacity-40"
            >
              {t("library.approve")}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

export function LibraryPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab | null) ?? "crops";
  const tabs: Tab[] = ["crops", "recipes", "review"];
  return (
    <Screen>
      <h1 className="text-3xl font-bold">{t("library.title")}</h1>
      <Progress />
      <div role="tablist" className="flex gap-2">
        {tabs.map((x) => (
          <button
            key={x}
            role="tab"
            aria-selected={tab === x}
            onClick={() => setParams({ tab: x })}
            className={`rounded-lg border-2 px-4 text-base font-semibold ${tab === x ? "border-green-800 bg-green-800 text-white" : "border-neutral-400"}`}
          >
            {t(`library.tab.${x}`)}
          </button>
        ))}
      </div>
      {tab === "crops" && <Crops />}
      {tab === "recipes" && <Recipes />}
      {tab === "review" && <Review />}
    </Screen>
  );
}
