#!/usr/bin/env sh
# Fase 6 parte 2 — daily paper PostgreSQL backup with 14-day retention.
#
# Runs INSIDE a container (or the host) with pg_dump against the paper
# postgres. Custom format (-Fc) so pg_restore can do selective/parallel
# restores. Every dump is integrity-checked (pg_restore --list) before
# the old ones are pruned: a corrupt "newest" backup never deletes the
# good ones below it.
#
#   sh scripts/db/backup_paper.sh           # defaults: postgres:5432
#   PGHOST=127.0.0.1 PGPORT=5433 sh scripts/db/backup_paper.sh
set -eu

PGUSER="${PGUSER:-algotrading}"
PGDATABASE="${PGDATABASE:-algo_trading}"
PGPASSWORD="${PGPASSWORD:-paper-local-only}"  # pragma: allowlist secret  (loopback-only local password)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%d-%H%M%S)"
target="$BACKUP_DIR/postgres-$stamp.dump"

pg_dump -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$target"

# integrity gate: the archive must list its tables before anything is pruned
pg_restore --list "$target" > /dev/null

# prune ONLY on success and ONLY dumps older than the retention window
find "$BACKUP_DIR" -name 'postgres-*.dump' -mtime "+$RETENTION_DAYS" -delete

echo "backup ok: $target ($(du -h "$target" | cut -f1)), retention ${RETENTION_DAYS}d"
