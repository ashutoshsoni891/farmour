import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { apiClient } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import type { Lang } from "../i18n";
import { formatArea } from "../lib/format";
import type { UnitPref } from "../lib/format";

type Farm = components["schemas"]["FarmOut"];

export function FarmCard({
  farm,
  unit,
  bighaSqft,
}: {
  farm: Farm;
  unit: UnitPref;
  bighaSqft: number | null;
}) {
  const { t, i18n } = useTranslation();
  const { token } = useAuth();
  const parcel = useQuery({
    queryKey: ["parcel", farm.id, token],
    queryFn: async () =>
      (
        await apiClient(token).GET("/api/v1/farms/{farm_id}/parcel", {
          params: { path: { farm_id: farm.id } },
        })
      ).data ?? null,
  });
  if (parcel.isPending) return null;
  const area = parcel.data
    ? formatArea(parcel.data.area_sqm, unit, i18n.language as Lang, bighaSqft)
    : null;
  const unfinished = !parcel.data || !farm.water_source || !farm.goal || !farm.labour;
  return (
    <li className="flex flex-col gap-2 rounded-xl border-2 border-neutral-300 p-4">
      <Link to={`/farms/${farm.id}`} className="flex min-h-11 items-center justify-between gap-2">
        <span className="text-xl font-bold">
          {area
            ? t("home.farm_area", { name: farm.name, area: t(area.key, { n: area.n }) })
            : farm.name}
        </span>
        <span className="text-base font-semibold text-green-800 underline">
          {t("home.open_farm")}
        </span>
      </Link>
      {farm.village && <p className="text-base text-neutral-700">{farm.village}</p>}
      {unfinished && farm.my_role === "owner" && (
        <Link
          to={`/setup/${farm.id}${parcel.data ? "?step=about" : "?step=plot"}`}
          className="rounded-xl bg-green-800 px-5 py-2 text-center text-lg font-semibold text-white"
        >
          {t("home.continue_setup", { name: farm.name })}
        </Link>
      )}
    </li>
  );
}
