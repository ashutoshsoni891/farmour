import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { apiClient, errorKey } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import { EntryActions } from "../library/EntryActions";
import {
  BoolField,
  Group,
  MultiField,
  NumberField,
  Row,
  SelectField,
  TextField,
  useEntryForm,
} from "../library/form";
import type { SourceDict, SourceEntry } from "../library/form";
import { parseSource, sourceText } from "../library/form";

type Crop = components["schemas"]["CropOut"];
const REGION = "malwa"; // the only region in the MVP (setting library.default_region)

const LAYERS = ["underground", "surface", "middle", "climber", "canopy"];
const SEASONS = ["kharif", "rabi", "zaid", "perennial"];
const CATEGORIES = [
  "vegetable", "leafy", "root", "spice", "fruit_tree", "fruit_short", "pulse", "cereal",
  "millet", "oilseed", "herb", "border", "green_manure", "flower",
]; // prettier-ignore

const NUMBERS = {
  spacing: ["spacing_row_cm", "spacing_plant_cm", "rows_per_1_2m_bed", "height_max_cm", "root_depth_cm", "nursery_days", "days_to_first_harvest", "harvest_span_days"],
  conditions: ["heat_tolerance_c", "cold_tolerance_c", "min_container_depth_cm"],
  yield: ["expected_yield_kg_per_sqm"],
  trees: ["years_to_bear", "lifespan_years", "tree_spacing_m", "canopy_diameter_m"],
}; // prettier-ignore

interface Window {
  from: string;
  to: string;
  method: "direct" | "transplant";
}

function CropForm({
  crop,
  onChanged,
  onSaved,
}: {
  crop: Crop;
  onChanged: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const regional = crop.regional[REGION];
  const form = useEntryForm(crop as unknown as Record<string, unknown>, crop.sources as SourceDict);
  const [windows, setWindows] = useState<Window[]>(
    (regional?.sow_windows ?? []) as unknown as Window[],
  );
  const [windowSource, setWindowSource] = useState(
    sourceText(regional?.sources?.["sow_windows"] as SourceEntry[] | undefined),
  );
  const [windowsDirty, setWindowsDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const field = (key: string) => ({
    name: key,
    label: t(`library.field.${key}`),
    value: form.values[key],
    onChange: (v: unknown) => form.set(key, v),
    source: { value: form.sources[key] ?? "", onChange: (s: string) => form.setSource(key, s), field: key },
  }); // prettier-ignore

  const save = async (): Promise<boolean> => {
    setError(null);
    const body: Record<string, unknown> = { ...form.patch };
    if (windowsDirty) {
      const others = Object.entries((regional?.sources ?? {}) as SourceDict).filter(
        ([k]) => k !== "sow_windows",
      );
      const parsed = parseSource(windowSource);
      const sources: SourceDict = Object.fromEntries(others);
      if (parsed.length) sources["sow_windows"] = parsed;
      body["regional"] = { [REGION]: { sow_windows: windows, sources } };
    }
    const { error: err, response } = await apiClient(token).PATCH("/api/v1/library/crops/{crop_id}", {
      params: { path: { crop_id: crop.id } },
      body: body as never,
    }); // prettier-ignore
    if (!response.ok) {
      setError(t(errorKey(err)));
      return false;
    }
    onSaved();
    onChanged();
    return true;
  };

  const setWindow = (i: number, patch: Partial<Window>) => {
    setWindows((w) => w.map((x, j) => (j === i ? { ...x, ...patch } : x)));
    setWindowsDirty(true);
  };

  return (
    <>
      <Group title={t("library.group.identity")}>
        <SelectField
          {...field("category")}
          options={CATEGORIES}
          optionLabel={(o) => t(`library.category.${o}`)}
        />
        <TextField {...field("family")} />
        <TextField {...field("scientific_name")} />
        <MultiField
          {...field("layers")}
          options={LAYERS}
          optionLabel={(o) => t(`library.layer.${o}`)}
        />
        <MultiField
          {...field("seasons")}
          options={SEASONS}
          optionLabel={(o) => t(`library.season.${o}`)}
        />
      </Group>

      <Group title={t("library.group.sowing")}>
        <Row
          label={t("library.sow_windows")}
          htmlFor="sow-windows"
          source={{
            value: windowSource,
            field: "sow_windows",
            onChange: (s) => {
              setWindowSource(s);
              setWindowsDirty(true);
            },
          }}
        >
          <div id="sow-windows" className="flex flex-col gap-2">
            {windows.map((w, i) => (
              <div key={i} className="flex flex-wrap items-end gap-2">
                <input
                  aria-label={t("library.sow_from")}
                  placeholder="MM-DD"
                  value={w.from}
                  onChange={(e) => setWindow(i, { from: e.target.value })}
                  className="w-24 rounded-lg border-2 border-neutral-400 px-3 text-base"
                />
                <input
                  aria-label={t("library.sow_to")}
                  placeholder="MM-DD"
                  value={w.to}
                  onChange={(e) => setWindow(i, { to: e.target.value })}
                  className="w-24 rounded-lg border-2 border-neutral-400 px-3 text-base"
                />
                <select
                  aria-label={t("library.sow_method")}
                  value={w.method}
                  onChange={(e) => setWindow(i, { method: e.target.value as Window["method"] })}
                  className="rounded-lg border-2 border-neutral-400 px-3 text-base"
                >
                  <option value="direct">{t("library.method.direct")}</option>
                  <option value="transplant">{t("library.method.transplant")}</option>
                </select>
                <button
                  type="button"
                  onClick={() => {
                    setWindows((x) => x.filter((_, j) => j !== i));
                    setWindowsDirty(true);
                  }}
                  className="rounded-lg border-2 border-neutral-400 px-3 text-base"
                >
                  {t("library.remove")}
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => {
                setWindows((x) => [...x, { from: "", to: "", method: "direct" }]);
                setWindowsDirty(true);
              }}
              className="self-start rounded-lg border-2 border-green-800 px-4 text-base font-semibold text-green-900"
            >
              {t("library.add_window")}
            </button>
          </div>
        </Row>
      </Group>

      <Group title={t("library.group.spacing")}>
        {NUMBERS.spacing.map((k) => (
          <NumberField key={k} {...field(k)} />
        ))}
      </Group>
      <Group title={t("library.group.conditions")}>
        <SelectField
          {...field("sun")}
          options={["full", "partial", "shade_tolerant"]}
          optionLabel={(o) => t(`library.sun.${o}`)}
        />
        <SelectField
          {...field("water_need")}
          options={["low", "medium", "high"]}
          optionLabel={(o) => t(`library.water.${o}`)}
        />
        {NUMBERS.conditions.map((k) => (
          <NumberField key={k} {...field(k)} />
        ))}
        <BoolField {...field("waterlogging_tolerant")} />
        <BoolField {...field("terrace_ok")} />
      </Group>
      <Group title={t("library.group.yield")}>
        {NUMBERS.yield.map((k) => (
          <NumberField key={k} {...field(k)} />
        ))}
        <BoolField {...field("low_care")} />
      </Group>
      <Group title={t("library.group.trees")}>
        {NUMBERS.trees.map((k) => (
          <NumberField key={k} {...field(k)} />
        ))}
      </Group>

      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <EntryActions
        entity="crops"
        id={crop.id}
        status={crop.status}
        dirty={form.isDirty || windowsDirty}
        missing={crop.missing_for_review ?? []}
        onSave={save}
        onChanged={onChanged}
      />
    </>
  );
}

export function CropEditPage() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState(false);
  const crop = useQuery({
    queryKey: ["crop", id, token],
    queryFn: async () => {
      const { data, error } = await apiClient(token).GET("/api/v1/library/crops/{crop_id}", {
        params: { path: { crop_id: id } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Screen>
      <Link to="/library" className="text-lg font-semibold text-green-800 underline">
        {t("library.back")}
      </Link>
      {crop.isError && <p role="alert">{t(errorKey(crop.error))}</p>}
      {crop.data && (
        <>
          <header>
            <h1 className="text-3xl font-bold">
              {i18n.language === "hi" ? crop.data.name_hi : crop.data.name_en}
            </h1>
            <p className="text-base text-neutral-700">
              {t(`library.status.${crop.data.status}`)} ·{" "}
              {t("library.revision", { n: crop.data.revision })}
            </p>
          </header>
          {notice && (
            <p role="status" className="font-semibold text-green-900">
              {t("library.saved")}
            </p>
          )}
          <CropForm
            key={`${crop.data.id}-${crop.data.updated_at}-${crop.data.status}`}
            crop={crop.data}
            onChanged={() => void queryClient.invalidateQueries({ queryKey: ["crop", id] })}
            onSaved={() => setNotice(true)}
          />
        </>
      )}
    </Screen>
  );
}
