#!/usr/bin/env bash
# End-to-end smoke test: boot the monolith, curl /_stcore/health, kill.
# Green exit == the import graph + session_state init + CSS load all work.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT=${SMOKE_PORT:-8599}
LOG=${SMOKE_LOG:-/tmp/whisperforge_smoke.log}

export OPENAI_API_KEY=${OPENAI_API_KEY:-dummy}
export ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-dummy}
export NOTION_API_KEY=${NOTION_API_KEY:-dummy}
export NOTION_DATABASE_ID=${NOTION_DATABASE_ID:-dummy}
export SERVICE_TOKEN=${SERVICE_TOKEN:-dummy}

venv/bin/python -m streamlit run app.py \
    --server.headless true \
    --server.port "$PORT" \
    --server.runOnSave false > "$LOG" 2>&1 &
SPID=$!

cleanup() { kill "$SPID" 2>/dev/null || true; wait "$SPID" 2>/dev/null || true; }
trap cleanup EXIT

# Wait up to 15s for the health endpoint to come up.
for i in {1..15}; do
    sleep 1
    if curl -s -f "http://127.0.0.1:${PORT}/_stcore/health" > /dev/null; then
        echo "smoke: streamlit health OK on port ${PORT}"
        exit 0
    fi
done

echo "smoke: streamlit failed to come up. log tail:"
tail -50 "$LOG"
exit 1
