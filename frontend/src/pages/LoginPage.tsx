import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthProvider";
import { Screen } from "../components/Screen";

export function LoginPage() {
  const { t } = useTranslation();
  const { signIn } = useAuth();
  return (
    <Screen>
      <h1 className="text-3xl leading-tight font-bold">{t("login.title")}</h1>
      <p className="text-lg text-neutral-700">{t("login.subtitle")}</p>
      <button
        type="button"
        onClick={() => void signIn()}
        className="rounded-xl bg-green-800 px-6 py-3 text-lg font-semibold text-white"
      >
        {t("login.sign_in")}
      </button>
      <p className="rounded-lg bg-amber-50 p-4 text-base text-neutral-800">
        {t("login.caretaker_hint")}
      </p>
    </Screen>
  );
}
