import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import hi from "./hi.json";

export const LANGS = ["hi", "en"] as const;
export type Lang = (typeof LANGS)[number];
const STORAGE_KEY = "farm.lang";

export function isLang(value: unknown): value is Lang {
  return typeof value === "string" && (LANGS as readonly string[]).includes(value);
}

/** The language explicitly chosen on this device, if any. */
export function savedLang(): Lang | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return isLang(saved) ? saved : null;
  } catch {
    return null; // storage unavailable (private mode)
  }
}

function initialLang(): Lang {
  return savedLang() ?? "hi"; // spec section 5: users.language defaults to 'hi'
}

export async function setLang(lang: Lang): Promise<void> {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // ignore
  }
  document.documentElement.lang = lang;
  await i18n.changeLanguage(lang);
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi } },
  lng: initialLang(),
  fallbackLng: "en",
  keySeparator: false,
  interpolation: { escapeValue: false },
});
document.documentElement.lang = i18n.language;

export default i18n;
