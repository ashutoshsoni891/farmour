# Builds the PWA and serves it with Caddy (the only public service).
FROM node:26.10.0-alpine AS web
WORKDIR /web
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM=farm
ARG VITE_KEYCLOAK_CLIENT_ID=farm-web
# Google Map Tiles key (public in the browser; restrict it to your domains in Google Cloud).
ARG VITE_GOOGLE_MAPS_KEY=
# Local review builds only: free Esri imagery (its terms forbid commercial use).
ARG VITE_DEV_IMAGERY=
RUN pnpm build

FROM caddy:2.11.4-alpine
COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=web /web/dist /srv
