import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { apiClient, errorKey } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

export type Entity = "crops" | "recipes";

const btn = "rounded-xl px-5 text-lg font-semibold";

export function missingText(t: TFunction, code: string) {
  const [kind, name = ""] = code.split(":");
  const base = name.split(".")[0] ?? "";
  const label = base === "sow_windows" ? t("library.sow_windows") : t(`library.field.${base}`);
  return kind === "source"
    ? t("library.missing_source", { field: label })
    : t("library.missing_field", { field: label });
}

interface Props {
  entity: Entity;
  id: string;
  status: string;
  dirty: boolean;
  missing: string[];
  onSave: () => Promise<boolean>;
  onChanged: () => void;
}

export function EntryActions({ entity, id, status, dirty, missing, onSave, onChanged }: Props) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [message, setMessage] = useState<string | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const act = async (action: "submit" | "approve" | "retire") => {
    setBusy(true);
    setMessage(null);
    setProblems([]);
    try {
      if (dirty && action !== "retire" && !(await onSave())) return;
      const { error, response } = await apiClient(token).POST(
        `/api/v1/library/{entity}/{entry_id}/${action}`,
        { params: { path: { entity, entry_id: id } } },
      );
      if (!response.ok) {
        const body = error as { error?: { details?: { missing?: string[]; reason?: string } } };
        setMessage(t(errorKey(error)));
        setProblems(body.error?.details?.missing ?? []);
        const reason = body.error?.details?.reason;
        if (reason) setMessage(t(`library.blocked.${reason}`));
        return;
      }
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const shown = problems.length ? problems : status === "draft" ? missing : [];
  return (
    <div className="sticky bottom-0 -mx-4 flex flex-col gap-3 border-t-2 border-neutral-300 bg-white px-4 py-3">
      {shown.length > 0 && (
        <details className="rounded-lg bg-amber-50 p-3 text-base">
          <summary className="min-h-11 cursor-pointer font-semibold">
            {t("library.missing_title")} ({shown.length})
          </summary>
          <ul className="list-disc pl-6">
            {shown.slice(0, 12).map((m) => (
              <li key={m}>{missingText(t, m)}</li>
            ))}
            {shown.length > 12 && <li>… +{shown.length - 12}</li>}
          </ul>
        </details>
      )}
      {message && (
        <p role="alert" className="text-base font-semibold text-red-800">
          {message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !dirty}
          onClick={() => void onSave()}
          className={`${btn} border-2 border-green-800 text-green-900 disabled:opacity-40`}
        >
          {t("library.save")}
        </button>
        {status === "draft" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void act("submit")}
            className={`${btn} bg-green-800 text-white disabled:opacity-40`}
          >
            {t("library.submit")}
          </button>
        )}
        {status === "in_review" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void act("approve")}
            className={`${btn} bg-green-800 text-white disabled:opacity-40`}
          >
            {t("library.approve")}
          </button>
        )}
        {status !== "retired" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              if (window.confirm(t("library.confirm_retire"))) void act("retire");
            }}
            className={`${btn} border-2 border-neutral-400`}
          >
            {t("library.retire")}
          </button>
        )}
      </div>
    </div>
  );
}
