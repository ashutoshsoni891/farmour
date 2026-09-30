import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { userManager } from "../auth/oidc";
import { Screen } from "../components/Screen";

export function AuthCallbackPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    userManager
      .signinRedirectCallback()
      .then(() => navigate("/", { replace: true }))
      .catch(() => setFailed(true));
  }, [navigate]);

  return (
    <Screen>
      <p className="text-lg" role="status">
        {failed ? t("err.unauthenticated") : t("common.loading")}
      </p>
    </Screen>
  );
}
