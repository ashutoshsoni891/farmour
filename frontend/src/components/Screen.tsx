import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitch } from "./LanguageSwitch";
import type { Lang } from "../i18n";

export function Screen({
  children,
  onLangChange,
}: {
  children: ReactNode;
  onLangChange?: (lang: Lang) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-4 py-4">
      <header className="mb-8 flex items-center justify-between gap-4">
        <span className="text-xl font-bold text-green-900">{t("app.name")}</span>
        <LanguageSwitch {...(onLangChange ? { onChange: onLangChange } : {})} />
      </header>
      <main className="flex flex-1 flex-col gap-6">{children}</main>
    </div>
  );
}
