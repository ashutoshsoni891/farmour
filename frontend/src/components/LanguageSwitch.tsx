import { useTranslation } from "react-i18next";

import { LANGS, setLang } from "../i18n";
import type { Lang } from "../i18n";

interface Props {
  onChange?: (lang: Lang) => void;
}

/** Always visible, including before login (spec section 13). */
export function LanguageSwitch({ onChange }: Props) {
  const { t, i18n } = useTranslation();
  return (
    <div role="group" aria-label={t("lang.switch_label")} className="flex gap-2">
      {LANGS.map((lang) => {
        const active = i18n.language === lang;
        return (
          <button
            key={lang}
            type="button"
            lang={lang}
            aria-pressed={active}
            onClick={() => {
              void setLang(lang);
              onChange?.(lang);
            }}
            className={`min-w-11 rounded-lg border-2 px-4 text-base font-semibold ${
              active
                ? "border-green-800 bg-green-800 text-white"
                : "border-neutral-400 bg-white text-neutral-900"
            }`}
          >
            {t(`lang.${lang}`)}
          </button>
        );
      })}
    </div>
  );
}
