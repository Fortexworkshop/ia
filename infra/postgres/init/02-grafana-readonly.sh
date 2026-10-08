#!/bin/sh
# Compte PostgreSQL en LECTURE SEULE pour Grafana (moindre privilege).
# Execute automatiquement a la creation de la base ; sur une base existante :
#   docker compose exec -T postgres sh /docker-entrypoint-initdb.d/02-grafana-readonly.sh
set -eu
: "${GRAFANA_DB_PASSWORD:?GRAFANA_DB_PASSWORD manquant}"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v pw="$GRAFANA_DB_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE grafana_ro LOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro')
\gexec
ALTER ROLE grafana_ro WITH LOGIN PASSWORD :'pw';
GRANT CONNECT ON DATABASE fortex TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
SQL
echo "Compte grafana_ro (lecture seule) pret"
