#!/usr/bin/env bash
# Fase 6 parte 2 — E2E proof that backups actually RESTORE.
#
# A backup that was never restored is a hope, not a backup. This throws
# away postgres entirely, recreates it from a dump taken by
# backup_paper.sh, and asserts the data survived (row counts match).
# Runs on scratch containers/ports — never touches the paper stack.
#
#   bash scripts/db/test_backup_restore.sh
set -eu

export PATH="$HOME/.docker/bin:$PATH"
command -v docker > /dev/null || { echo "docker CLI not found" >&2; exit 1; }

NET="rt-backup-test"
PG="rt-backup-pg"
PORT="${TEST_PG_PORT:-55433}"
WORK="$(mktemp -d)/backups"

cleanup() {
    docker rm -f "$PG" > /dev/null 2>&1 || true
    docker network rm "$NET" > /dev/null 2>&1 || true
    rm -rf "$(dirname "$WORK")"
}
trap cleanup EXIT

docker network create "$NET" > /dev/null
docker run -d --rm --name "$PG" --network "$NET" \
    -e POSTGRES_USER=algotrading \
    -e POSTGRES_PASSWORD=paper-local-only \
    -e POSTGRES_DB=algo_trading \
    -p "127.0.0.1:$PORT:5432" \
    postgres:15-alpine > /dev/null

echo "waiting for postgres..."
for _ in $(seq 1 40); do
    docker exec "$PG" pg_isready -U algotrading -d algo_trading > /dev/null 2>&1 && break
    sleep 1
done

# 1. seed real tables + rows (the live-trading shape from migration 0004)
docker exec -i "$PG" psql -U algotrading -d algo_trading -q << 'SQL'
CREATE TABLE order_records (
    order_id VARCHAR(36) PRIMARY KEY, symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL, quantity NUMERIC(18,8) NOT NULL,
    status VARCHAR(20) NOT NULL, broker_name VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL);
INSERT INTO order_records VALUES
    ('ord-1', 'SCHD', 'BUY', 10, 'FILLED', 'paper', NOW() - INTERVAL '2 days'),
    ('ord-2', 'VYM',  'BUY',  5, 'FILLED', 'paper', NOW() - INTERVAL '1 day'),
    ('ord-3', 'BND',  'SELL', 5, 'PENDING', 'paper', NOW());
SQL

# 2. BACKUP with the real script (pg_dump ships in the postgres image)
docker cp scripts/db/backup_paper.sh "$PG":/backup_paper.sh
docker exec "$PG" sh /backup_paper.sh

# 3. copy the dump out, then DESTROY the database volume content
docker cp "$PG":/backups/. "$WORK"
echo "--- dumps taken: $(ls "$WORK" | tr '\n' ' ')"
docker exec "$PG" psql -U algotrading -d algo_trading -q -c 'DROP TABLE order_records;'
before_rows=$(docker exec "$PG" psql -U algotrading -d algo_trading -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_name='order_records'")
[ "$before_rows" = "0" ] || { echo "FAIL: table not actually dropped" >&2; exit 1; }

# 4. RESTORE with the real script (confirmation flag included)
dump_file="/backups/$(ls "$WORK" | head -1)"
docker cp "$WORK/$(ls "$WORK" | head -1)" "$PG":"$dump_file"
docker cp scripts/db/restore_paper.sh "$PG":/restore_paper.sh
docker exec "$PG" sh /restore_paper.sh "$dump_file" --yes

# 5. verify the data survived
rows=$(docker exec "$PG" psql -U algotrading -d algo_trading -tAc \
    'SELECT count(*) FROM order_records')
pending=$(docker exec "$PG" psql -U algotrading -d algo_trading -tAc \
    "SELECT count(*) FROM order_records WHERE status='PENDING'")

[ "$rows" = "3" ] || { echo "FAIL: expected 3 rows after restore, got $rows" >&2; exit 1; }
[ "$pending" = "1" ] || { echo "FAIL: PENDING order lost in restore" >&2; exit 1; }

echo "PASS: backup → drop → restore preserved all 3 rows (incl. PENDING order)"
