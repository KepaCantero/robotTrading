#!/usr/bin/env bash
# Fase 6 parte 2 — local ops watcher for the paper stack (loopback only).
#
# Polls /ops/status every N seconds and (a) logs every status CHANGE,
# (b) fires a macOS notification when the stack leaves "healthy", so a
# dead database, stuck orders or a stale corpus surface without anyone
# watching a dashboard. Runs on the HOST against 127.0.0.1.
#
#   OPS_API_KEY=... bash scripts/ops/paper_watch.sh        # foreground
#   OPS_API_KEY=... nohup bash scripts/ops/paper_watch.sh &  # background
set -u

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
INTERVAL="${INTERVAL:-60}"
LOG_DIR="${LOG_DIR:-logs}"
LOG="$LOG_DIR/ops_watch.log"
mkdir -p "$LOG_DIR"

if [ -z "${OPS_API_KEY:-}" ]; then
    echo "OPS_API_KEY not set (admin key for /ops/status) — export it first" >&2
    exit 1
fi

last="none"
echo "[$(date -u +%FT%TZ)] watcher start: $API_BASE/ops/status every ${INTERVAL}s" >> "$LOG"

while true; do
    body="$(curl -sf -H "Authorization: Bearer $OPS_API_KEY" "$API_BASE/ops/status" 2>/dev/null)" || body=""
    if [ -z "$body" ]; then
        status="unreachable"
    else
        status="$(printf '%s' "$body" | sed -n 's/.*"status":"\([a-z]*\)".*/\1/p' | head -1)"
        [ -n "$status" ] || status="unknown"
    fi

    if [ "$status" != "$last" ]; then
        echo "[$(date -u +%FT%TZ)] status: $last -> $status" >> "$LOG"
        if [ "$status" != "healthy" ] && command -v osascript > /dev/null 2>&1; then
            osascript -e "display notification \"paper stack: $status\" with title \"robotTrading ops\"" \
                > /dev/null 2>&1 || true
        fi
        last="$status"
    fi
    sleep "$INTERVAL"
done
