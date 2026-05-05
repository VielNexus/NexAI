#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[AgentX CI check]"
echo "Root: $ROOT"
echo

echo "[1/4] Python compileall"
cd "$ROOT"
python3 -m compileall AgentX/agentx apps/api/agentx_api apps/api/tests >/dev/null
echo "OK"

echo "[2/4] Frontend install"
cd "$ROOT/AgentXWeb"
npm ci
echo "OK"

echo "[3/4] Frontend typecheck + tests"
npm run typecheck
npm test
echo "OK"

echo "[4/4] Frontend build"
npm run build
echo "OK"

echo
echo "AgentX CI check passed."
