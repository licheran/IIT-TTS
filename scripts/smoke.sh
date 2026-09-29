#!/usr/bin/env bash
# Smoke test of a running stack (`docker compose up`): import L6, solve it, read a grid and export
# the HTML. Usage: scripts/smoke.sh [API_URL] [WORKBOOK]
set -euo pipefail

API="${1:-http://localhost:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKBOOK="${2:-$ROOT/backend/tests/fixtures/l6/l6.xlsx}"
GROUP="L6 SE / G1"
OUT="${SMOKE_OUT:-$(mktemp -d)}"

json() { python -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

echo "1. health"
curl -sf "$API/health" | json "d['status']" | grep -qx ok

echo "2. create a dataset"
DATASET=$(curl -sf -X POST "$API/datasets" -H 'content-type: application/json' \
  -d '{"name":"L6 smoke","preset":"academic_weekly"}' | json "d['id']")

echo "3. import $WORKBOOK"
curl -sf -X POST "$API/datasets/$DATASET/import" -F "file=@$WORKBOOK" | json "d['ok'] or sys.exit('import failed: %s' % d['errors'])"

echo "4. pre-flight"
curl -sf -X POST "$API/datasets/$DATASET/preflight" | json "d['has_errors'] and sys.exit('pre-flight errors: %s' % d['issues'])"

echo "5. start a run"
RUN=$(curl -sf -X POST "$API/datasets/$DATASET/runs" -H 'content-type: application/json' \
  -d '{"time_limit_s":60}' | json "d['run_id']")

echo "6. wait for it to finish"
for _ in $(seq 1 120); do
  STATUS=$(curl -sf "$API/runs/$RUN" | json "d['status']")
  case "$STATUS" in
    succeeded) break ;;
    queued | running) sleep 1 ;;
    *) echo "run ended with status $STATUS"; curl -s "$API/runs/$RUN"; exit 1 ;;
  esac
done
[ "$STATUS" = succeeded ] || { echo "timed out (status $STATUS)"; exit 1; }

echo "7. grid for $GROUP"
CELLS=$(curl -sfG "$API/runs/$RUN/grid" --data-urlencode "type=StudentGroup" \
  --data-urlencode "code=$GROUP" | json "len(d['cells'])")
[ "$CELLS" -gt 0 ] || { echo "the grid is empty"; exit 1; }
echo "   $CELLS events"

echo "8. export the HTML"
curl -sfG "$API/runs/$RUN/export" --data-urlencode "format=html" --data-urlencode "type=StudentGroup" \
  --data-urlencode "code=$GROUP" -o "$OUT/grid.html"
grep -q "$GROUP" "$OUT/grid.html"
echo "   wrote $OUT/grid.html"

echo "smoke test passed"
