# PostgreSQL 16 + PostGIS 3 + pgvector, from the official image and the PGDG apt repository
# it already trusts. Package versions are pinned; Dependabot bumps the base image.
FROM postgres:18.4-bookworm
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        postgresql-16-postgis-3=3.6.4+dfsg-2.pgdg12+1 \
        postgresql-16-pgvector=0.8.6-1.pgdg12+2; \
    rm -rf /var/lib/apt/lists/*
