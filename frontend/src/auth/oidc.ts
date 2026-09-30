import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const authority = `${import.meta.env.VITE_KEYCLOAK_URL ?? `${location.origin}/auth`}/realms/${
  import.meta.env.VITE_KEYCLOAK_REALM ?? "farm"
}`;

export const userManager = new UserManager({
  authority,
  client_id: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "farm-web",
  redirect_uri: `${location.origin}/login/callback`, // outside /auth, which Caddy sends to Keycloak
  post_logout_redirect_uri: `${location.origin}/`,
  response_type: "code",
  scope: "openid email profile",
  automaticSilentRenew: true,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
});
