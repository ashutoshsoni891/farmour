import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { apiClient, errorKey } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import { isLang, savedLang, setLang } from "../i18n";
import type { Lang } from "../i18n";

export function HomePage() {
  const { t } = useTranslation();
  const { token, signOut } = useAuth();
  const api = apiClient(token);
  const queryClient = useQueryClient();

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me");
      if (error) throw error;
      // The last explicit choice wins: a choice made on this device updates the profile,
      // otherwise the profile's language is applied.
      const chosen = savedLang();
      if (chosen && chosen !== data.language) {
        const updated = await api.PATCH("/api/v1/me", { body: { language: chosen } });
        return updated.data ?? data;
      }
      if (isLang(data.language)) await setLang(data.language);
      return data;
    },
  });
  const farms = useQuery({
    queryKey: ["farms", token],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/farms");
      if (error) throw error;
      return data;
    },
  });

  const saveLang = async (lang: Lang) => {
    await api.PATCH("/api/v1/me", { body: { language: lang } });
    await queryClient.invalidateQueries({ queryKey: ["me"] });
  };

  if (me.isError) {
    return (
      <Screen>
        <p role="alert" className="text-lg">
          {t(errorKey(me.error))}
        </p>
        <button
          type="button"
          onClick={() => void signOut()}
          className="rounded-xl border-2 border-neutral-400 px-6 text-lg"
        >
          {t("home.sign_out")}
        </button>
      </Screen>
    );
  }

  return (
    <Screen onLangChange={(lang) => void saveLang(lang)}>
      {me.isPending ? (
        <p role="status">{t("common.loading")}</p>
      ) : (
        <h1 className="text-3xl font-bold">
          {me.data.name ? t("home.greeting", { name: me.data.name }) : t("home.greeting_no_name")}
        </h1>
      )}
      {farms.data && (
        <p className="text-lg">
          {farms.data.length === 0
            ? t("home.no_farms")
            : t("home.farms_count", { count: farms.data.length })}
        </p>
      )}
      {me.data?.is_agronomist && (
        <Link
          to="/library"
          className="rounded-xl bg-green-800 px-6 py-3 text-center text-lg font-semibold text-white"
        >
          {t("home.open_library")}
        </Link>
      )}
      <button
        type="button"
        onClick={() => void signOut()}
        className="mt-auto rounded-xl border-2 border-neutral-400 px-6 text-lg font-semibold"
      >
        {t("home.sign_out")}
      </button>
    </Screen>
  );
}
