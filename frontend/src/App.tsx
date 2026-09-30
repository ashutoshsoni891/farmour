import { useTranslation } from "react-i18next";
import { Route, Routes } from "react-router";

import { useAuth } from "./auth/AuthProvider";
import { Screen } from "./components/Screen";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { HomePage } from "./pages/HomePage";
import { LinkLoginPage } from "./pages/LinkLoginPage";
import { LoginPage } from "./pages/LoginPage";

function Root() {
  const { ready, token } = useAuth();
  const { t } = useTranslation();
  if (!ready) {
    return (
      <Screen>
        <p role="status">{t("common.loading")}</p>
      </Screen>
    );
  }
  return token ? <HomePage /> : <LoginPage />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login/callback" element={<AuthCallbackPage />} />
      <Route path="/login/link" element={<LinkLoginPage />} />
      <Route path="*" element={<Root />} />
    </Routes>
  );
}
