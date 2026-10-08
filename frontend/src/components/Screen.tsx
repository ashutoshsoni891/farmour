import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitch } from "./LanguageSwitch";
import type { Lang } from "../i18n";

/** Page shell: a top bar with the app name and language, and the page content below. Forms use
 * a readable column; `wide` pages (the farm and its map) use the whole screen. */
export function Screen({
  children,
  onLangChange,
  wide = false,
}: {
  children: ReactNode;
  onLangChange?: (lang: Lang) => void;
  wide?: boolean;
}) {
  const { t } = useTranslation();
  const width = wide ? "max-w-[1680px]" : "max-w-2xl";
  return (
    <div className="min-h-dvh bg-neutral-50">
      <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white/90 backdrop-blur">
        <div className={`mx-auto flex items-center justify-between gap-4 px-4 py-2 ${width}`}>
          <span className="flex items-center gap-2 text-xl font-bold text-green-900">
            <span aria-hidden="true">🌱</span>
            {t("app.name")}
          </span>
          <LanguageSwitch {...(onLangChange ? { onChange: onLangChange } : {})} />
        </div>
      </header>
      <main className={`mx-auto flex w-full flex-col gap-6 px-4 py-4 lg:py-6 ${width}`}>
        {children}
      </main>
    </div>
  );
}
