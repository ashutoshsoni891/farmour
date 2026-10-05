import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export interface SourceEntry {
  url?: string | null;
  title: string;
  note?: string | null;
  quote?: string | null;
  checked_on?: string | null;
}
export type SourceDict = Record<string, SourceEntry[]>;

/** "https://..." becomes a linked source, anything else is kept as a written note. */
export function parseSource(text: string): SourceEntry[] {
  const value = text.trim();
  if (!value) return [];
  if (/^https?:\/\//i.test(value)) {
    try {
      return [{ url: value, title: new URL(value).hostname }];
    } catch {
      /* fall through to a plain note */
    }
  }
  return [{ title: value }];
}

export function sourceText(entries: SourceEntry[] | undefined): string {
  const first = entries?.[0];
  return first ? (first.url ?? first.title) : "";
}

type Values = Record<string, unknown>;

/** Tracks edits to an entry and builds a PATCH containing only what changed. */
export function useEntryForm(initial: Values, initialSources: SourceDict) {
  const [values, setValues] = useState<Values>(initial);
  const [dirty, setDirty] = useState<Set<string>>(new Set());
  const [sources, setSources] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(initialSources).map(([k, v]) => [k, sourceText(v)])),
  );
  const [sourcesDirty, setSourcesDirty] = useState<Set<string>>(new Set());

  const set = useCallback((key: string, value: unknown) => {
    setValues((v) => ({ ...v, [key]: value }));
    setDirty((d) => new Set(d).add(key));
  }, []);
  const setSource = useCallback((key: string, text: string) => {
    setSources((s) => ({ ...s, [key]: text }));
    setSourcesDirty((d) => new Set(d).add(key));
  }, []);

  // What the AI check found in each cited source, shown to the reviewing agronomist.
  const quotes = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(initialSources).map(([k, v]) => [k, v[0]?.quote ?? undefined]),
      ) as Record<string, string | undefined>,
    [initialSources],
  );

  const isDirty = dirty.size > 0 || sourcesDirty.size > 0;
  const patch = useMemo(() => {
    const body: Values = {};
    for (const key of dirty) body[key] = values[key];
    if (sourcesDirty.size > 0) {
      const merged: SourceDict = {};
      for (const [key, entries] of Object.entries(initialSources)) {
        if (!sourcesDirty.has(key)) merged[key] = entries;
      }
      for (const key of sourcesDirty) {
        const parsed = parseSource(sources[key] ?? "");
        if (parsed.length) merged[key] = parsed;
      }
      body["sources"] = merged;
    }
    return body;
  }, [dirty, sourcesDirty, values, sources, initialSources]);

  return { values, sources, quotes, set, setSource, isDirty, patch };
}

interface RowProps {
  label: string;
  htmlFor: string;
  source?:
    | { value: string; onChange: (text: string) => void; field: string; quote?: string | undefined }
    | undefined;
  children: ReactNode;
}

export function Row({ label, htmlFor, source, children }: RowProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1 border-b border-neutral-200 pb-3">
      <label htmlFor={htmlFor} className="text-base font-semibold">
        {label}
      </label>
      {children}
      {source && (
        <input
          aria-label={`${t("library.source")}: ${label}`}
          placeholder={t("library.source_hint")}
          value={source.value}
          onChange={(e) => source.onChange(e.target.value)}
          className="rounded-lg border border-neutral-300 px-3 text-base text-neutral-700"
        />
      )}
      {source?.quote && (
        <p className="text-sm text-neutral-600 italic">
          {t("library.source_quote")}: “{source.quote}”
        </p>
      )}
    </div>
  );
}

const input = "rounded-lg border-2 border-neutral-400 px-3 text-base";

interface FieldProps {
  name: string;
  label: string;
  value: unknown;
  onChange: (v: unknown) => void;
  source?: RowProps["source"];
}

export function NumberField({ name, label, value, onChange, source }: FieldProps) {
  return (
    <Row label={label} htmlFor={name} source={source}>
      <input
        id={name}
        inputMode="decimal"
        value={value === null || value === undefined ? "" : String(value)}
        onChange={(e) => {
          const raw = e.target.value.trim();
          onChange(raw === "" || Number.isNaN(Number(raw)) ? null : Number(raw));
        }}
        className={input}
      />
    </Row>
  );
}

export function TextField({ name, label, value, onChange, source }: FieldProps) {
  return (
    <Row label={label} htmlFor={name} source={source}>
      <input
        id={name}
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value || null)}
        className={input}
      />
    </Row>
  );
}

export function LinesField({ name, label, value, onChange, source }: FieldProps) {
  const lines = Array.isArray(value) ? (value as string[]) : [];
  return (
    <Row label={label} htmlFor={name} source={source}>
      <textarea
        id={name}
        rows={5}
        value={lines.join("\n")}
        onChange={(e) => onChange(e.target.value.split("\n").filter((l) => l.trim() !== ""))}
        className={input + " py-2"}
      />
    </Row>
  );
}

interface SelectProps extends FieldProps {
  options: string[];
  optionLabel: (o: string) => string;
}

export function SelectField({
  name,
  label,
  value,
  onChange,
  source,
  options,
  optionLabel,
}: SelectProps) {
  const { t } = useTranslation();
  return (
    <Row label={label} htmlFor={name} source={source}>
      <select
        id={name}
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value || null)}
        className={input}
      >
        <option value="">{t("library.unknown")}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {optionLabel(o)}
          </option>
        ))}
      </select>
    </Row>
  );
}

export function BoolField({ name, label, value, onChange, source }: FieldProps) {
  const { t } = useTranslation();
  const current = value === true ? "yes" : value === false ? "no" : "";
  return (
    <Row label={label} htmlFor={name} source={source}>
      <select
        id={name}
        value={current}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value === "yes")}
        className={input}
      >
        <option value="">{t("library.unknown")}</option>
        <option value="yes">{t("library.yes")}</option>
        <option value="no">{t("library.no")}</option>
      </select>
    </Row>
  );
}

export function MultiField({
  name,
  label,
  value,
  onChange,
  source,
  options,
  optionLabel,
}: SelectProps) {
  const chosen = new Set(Array.isArray(value) ? (value as string[]) : []);
  return (
    <Row label={label} htmlFor={name} source={source}>
      <div id={name} className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = chosen.has(o);
          return (
            <button
              key={o}
              type="button"
              aria-pressed={on}
              onClick={() => {
                const next = new Set(chosen);
                if (on) next.delete(o);
                else next.add(o);
                onChange(options.filter((x) => next.has(x)));
              }}
              className={`rounded-lg border-2 px-3 text-base font-semibold ${
                on
                  ? "border-green-800 bg-green-800 text-white"
                  : "border-neutral-400 bg-white text-neutral-900"
              }`}
            >
              {optionLabel(o)}
            </button>
          );
        })}
      </div>
    </Row>
  );
}

export function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="mt-4 text-xl font-bold text-green-900">{title}</h2>
      {children}
    </section>
  );
}
