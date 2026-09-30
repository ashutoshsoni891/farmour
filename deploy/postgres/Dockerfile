# PostgreSQL 16 + PostGIS 3.5 + pgvector (built from a pinned tag).
FROM postgis/postgis:16-3.5
ARG PGVECTOR_VERSION=v0.8.6
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends build-essential git ca-certificates postgresql-server-dev-16; \
    git clone --depth 1 --branch "$PGVECTOR_VERSION" https://github.com/pgvector/pgvector.git /tmp/pgvector; \
    make -C /tmp/pgvector OPTFLAGS=""; \
    make -C /tmp/pgvector install; \
    rm -rf /tmp/pgvector; \
    apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16; \
    rm -rf /var/lib/apt/lists/*
