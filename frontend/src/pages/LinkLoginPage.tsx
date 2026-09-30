import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { apiClient } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { saveCaretakerSession } from "../auth/session";
import { Screen } from "../components/Screen";

/** Caretaker opens the single-use link from Telegram: /login/link#token=... */
export function LinkLoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("token"));
  const [failed, setFailed] = useState(!token);
  const started = useRef(false);

  useEffect(() => {
    history.replaceState(null, "", location.pathname); // drop the token from the address bar
    if (!token || started.current) return;
    started.current = true;
    void apiClient(null)
      .POST("/api/v1/auth/otp/verify", { body: { token } })
      .then(({ data }) => {
        if (!data) return setFailed(true);
        saveCaretakerSession(data.access_token, data.expires_in);
        refresh();
        void navigate("/", { replace: true });
      })
      .catch(() => setFailed(true));
  }, [token, navigate, refresh]);

  return (
    <Screen>
      {failed ? (
        <>
          <p className="text-lg" role="alert">
            {t("login.link_failed")}
          </p>
          <Link to="/" className="text-lg font-semibold text-green-800 underline">
            {t("login.back")}
          </Link>
        </>
      ) : (
        <p className="text-lg" role="status">
          {t("login.link_checking")}
        </p>
      )}
    </Screen>
  );
}
