import type { User } from "oidc-client-ts";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import i18n from "../i18n";
import { userManager } from "./oidc";
import { caretakerToken, clearCaretakerSession } from "./session";

interface AuthState {
  ready: boolean;
  token: string | null;
  kind: "owner" | "caretaker" | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [oidcUser, setOidcUser] = useState<User | null>(null);
  const [caretaker, setCaretaker] = useState<string | null>(() => caretakerToken());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    void userManager.getUser().then((u) => {
      if (alive) {
        setOidcUser(u && !u.expired ? u : null);
        setReady(true);
      }
    });
    const onLoaded = (u: User) => setOidcUser(u);
    const onUnloaded = () => setOidcUser(null);
    userManager.events.addUserLoaded(onLoaded);
    userManager.events.addUserUnloaded(onUnloaded);
    return () => {
      alive = false;
      userManager.events.removeUserLoaded(onLoaded);
      userManager.events.removeUserUnloaded(onUnloaded);
    };
  }, []);

  const signIn = useCallback(async () => {
    // Keycloak shows its pages in the language chosen here.
    await userManager.signinRedirect({ ui_locales: i18n.language });
  }, []);

  const signOut = useCallback(async () => {
    clearCaretakerSession();
    setCaretaker(null);
    if (oidcUser) await userManager.signoutRedirect();
  }, [oidcUser]);

  const refresh = useCallback(() => setCaretaker(caretakerToken()), []);

  const value = useMemo<AuthState>(() => {
    const token = oidcUser?.access_token ?? caretaker;
    const kind = oidcUser ? "owner" : caretaker ? "caretaker" : null;
    return { ready, token, kind, signIn, signOut, refresh };
  }, [oidcUser, caretaker, ready, signIn, signOut, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
