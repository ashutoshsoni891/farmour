import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { apiClient, errorKey } from "../api/client";
import type { components } from "../api/schema";
import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";
import { EntryActions } from "../library/EntryActions";
import { Group, LinesField, NumberField, Row, TextField, useEntryForm } from "../library/form";
import type { SourceDict } from "../library/form";

type Recipe = components["schemas"]["RecipeOut"];
type Ingredient = components["schemas"]["Ingredient"];
const cell = "rounded-lg border-2 border-neutral-400 px-3 text-base";

function RecipeForm({
  recipe,
  onChanged,
  onSaved,
}: {
  recipe: Recipe;
  onChanged: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const form = useEntryForm(
    recipe as unknown as Record<string, unknown>,
    recipe.sources as SourceDict,
  );
  const [ingredients, setIngredients] = useState<Ingredient[]>(recipe.ingredients);
  const [error, setError] = useState<string | null>(null);

  const field = (key: string) => ({
    name: key,
    label: t(`library.field.${key}`),
    value: form.values[key],
    onChange: (v: unknown) => form.set(key, v),
    source: { value: form.sources[key] ?? "", onChange: (s: string) => form.setSource(key, s), field: key },
  }); // prettier-ignore

  const setIngredient = (i: number, patch: Partial<Ingredient>) => {
    const next = ingredients.map((x, j) => (j === i ? { ...x, ...patch } : x));
    setIngredients(next);
    form.set("ingredients", next);
  };

  const save = async (): Promise<boolean> => {
    setError(null);
    const { error: err, response } = await apiClient(token).PATCH("/api/v1/library/recipes/{recipe_id}", {
      params: { path: { recipe_id: recipe.id } },
      body: form.patch as never,
    }); // prettier-ignore
    if (!response.ok) {
      setError(t(errorKey(err)));
      return false;
    }
    onSaved();
    onChanged();
    return true;
  };

  return (
    <>
      <Group title={t("library.group.ingredients")}>
        <Row
          label={t("library.group.ingredients")}
          htmlFor="ingredients"
          source={{
            value: form.sources["ingredients"] ?? "",
            field: "ingredients",
            onChange: (s) => form.setSource("ingredients", s),
          }}
        >
          <div id="ingredients" className="flex flex-col gap-3">
            {ingredients.map((ing, i) => (
              <div key={i} className="flex flex-wrap items-end gap-2">
                <input
                  aria-label={t("library.ingredient.name_en")}
                  placeholder={t("library.ingredient.name_en")}
                  value={ing.name_en}
                  onChange={(e) => setIngredient(i, { name_en: e.target.value })}
                  className={cell}
                />
                <input
                  aria-label={t("library.ingredient.name_hi")}
                  placeholder={t("library.ingredient.name_hi")}
                  value={ing.name_hi ?? ""}
                  onChange={(e) => setIngredient(i, { name_hi: e.target.value })}
                  className={cell}
                />
                <input
                  aria-label={t("library.ingredient.qty")}
                  placeholder={t("library.ingredient.qty")}
                  inputMode="decimal"
                  value={ing.qty ?? ""}
                  onChange={(e) =>
                    setIngredient(i, { qty: e.target.value === "" ? null : Number(e.target.value) })
                  }
                  className={`${cell} w-24`}
                />
                <input
                  aria-label={t("library.ingredient.unit")}
                  placeholder={t("library.ingredient.unit")}
                  value={ing.unit ?? ""}
                  onChange={(e) => setIngredient(i, { unit: e.target.value })}
                  className={`${cell} w-24`}
                />
                <button
                  type="button"
                  onClick={() => {
                    const next = ingredients.filter((_, j) => j !== i);
                    setIngredients(next);
                    form.set("ingredients", next);
                  }}
                  className={cell}
                >
                  {t("library.remove")}
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => {
                const next = [...ingredients, { name_en: "" }];
                setIngredients(next);
                form.set("ingredients", next);
              }}
              className="self-start rounded-lg border-2 border-green-800 px-4 text-base font-semibold text-green-900"
            >
              {t("library.add_ingredient")}
            </button>
          </div>
        </Row>
      </Group>

      <Group title={t("library.group.recipe")}>
        <NumberField {...field("per_area_sqm")} />
        <NumberField {...field("ferment_days")} />
        <NumberField {...field("shelf_life_days")} />
        <NumberField {...field("apply_every_days")} />
        <TextField {...field("apply_method")} />
        <LinesField {...field("steps_en")} />
        <LinesField {...field("steps_hi")} />
        <TextField {...field("safety_notes_en")} />
        <TextField {...field("safety_notes_hi")} />
      </Group>

      {error && (
        <p role="alert" className="font-semibold text-red-800">
          {error}
        </p>
      )}
      <EntryActions
        entity="recipes"
        id={recipe.id}
        status={recipe.status}
        dirty={form.isDirty}
        missing={recipe.missing_for_review ?? []}
        onSave={save}
        onChanged={onChanged}
      />
    </>
  );
}

export function RecipeEditPage() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState(false);
  const recipes = useQuery({
    queryKey: ["recipes", token],
    queryFn: async () => {
      const { data, error } = await apiClient(token).GET("/api/v1/library/recipes");
      if (error) throw error;
      return data;
    },
  });
  const recipe = recipes.data?.find((r) => r.id === id);

  return (
    <Screen>
      <Link to="/library?tab=recipes" className="text-lg font-semibold text-green-800 underline">
        {t("library.back")}
      </Link>
      {recipes.isError && <p role="alert">{t(errorKey(recipes.error))}</p>}
      {recipe && (
        <>
          <header>
            <h1 className="text-3xl font-bold">
              {i18n.language === "hi" ? recipe.name_hi : recipe.name_en}
            </h1>
            <p className="text-base text-neutral-700">
              {t(`library.status.${recipe.status}`)} ·{" "}
              {t("library.revision", { n: recipe.revision })}
            </p>
          </header>
          {notice && (
            <p role="status" className="font-semibold text-green-900">
              {t("library.saved")}
            </p>
          )}
          <RecipeForm
            key={`${recipe.id}-${recipe.updated_at}-${recipe.status}`}
            recipe={recipe}
            onChanged={() => void queryClient.invalidateQueries({ queryKey: ["recipes"] })}
            onSaved={() => setNotice(true)}
          />
        </>
      )}
    </Screen>
  );
}
