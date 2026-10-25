#!/usr/bin/env sh
# Fase 6 parte 2 — restore a paper backup into the running postgres.
#
# A code rollback must NOT erase orders placed after the backup (plan §6):
# restores go into the EXISTING database with --clean --if-exists (drops
# the restored tables, keeps everything else), then reconciliation with
# IBKR is the operator's next step — never a bare --create over the volume.
#
#   sh scripts/db/restore_paper.sh /backups/postgres-20261025-120000.dump
set -eu

DUMP="${1:?usage: restore_paper.sh <dump-file> [--yes]}"
CONFIRMED="${2:-}"
[ "$CONFIRMED" = "--yes" ] || {
    echo "This DROPs the live-trading tables and restores '$DUMP'."
    echo "Re-run with --yes to proceed:"
    echo "  sh scripts/db/restore_paper.sh $DUMP --yes"
    exit 1
}

PGUSER="${PGUSER:-algotrading}"
PGDATABASE="${PGDATABASE:-algo_trading}"
PGPASSWORD="${PGPASSWORD:-paper-local-only}"  # pragma: allowlist secret  (loopback-only local password)

[ -f "$DUMP" ] || { echo "dump not found: $DUMP" >&2; exit 1; }
pg_restore --list "$DUMP" > /dev/null   # refuse corrupt archives up front

pg_restore -U "$PGUSER" -d "$PGDATABASE" --clean --if-exists --no-owner "$DUMP"
echo "restored $DUMP into $PGDATABASE (tables replaced in place; reconcile with the broker next)"
