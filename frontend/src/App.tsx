import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Route, Routes } from "react-router";

import { useAuth } from "./auth/AuthProvider";
import { Screen } from "./components/Screen";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { HomePage } from "./pages/HomePage";
import { LinkLoginPage } from "./pages/LinkLoginPage";
import { CropEditPage } from "./pages/CropEditPage";
import { LibraryPage } from "./pages/LibraryPage";
import { LoginPage } from "./pages/LoginPage";
import { RecipeEditPage } from "./pages/RecipeEditPage";
import { SetupPage } from "./setup/SetupPage";

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

/** Signed-in users only; the API itself rejects non-agronomists. */
function Guarded({ children }: { children: ReactNode }) {
  const { ready, token } = useAuth();
  if (!ready) return null;
  return token ? children : <LoginPage />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login/callback" element={<AuthCallbackPage />} />
      <Route path="/login/link" element={<LinkLoginPage />} />
      <Route
        path="/library"
        element={
          <Guarded>
            <LibraryPage />
          </Guarded>
        }
      />
      <Route
        path="/library/crops/:id"
        element={
          <Guarded>
            <CropEditPage />
          </Guarded>
        }
      />
      <Route
        path="/library/recipes/:id"
        element={
          <Guarded>
            <RecipeEditPage />
          </Guarded>
        }
      />
      <Route
        path="/setup"
        element={
          <Guarded>
            <SetupPage />
          </Guarded>
        }
      />
      <Route
        path="/setup/:farmId"
        element={
          <Guarded>
            <SetupPage />
          </Guarded>
        }
      />
      <Route path="*" element={<Root />} />
    </Routes>
  );
}
