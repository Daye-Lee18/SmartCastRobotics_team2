#!/usr/bin/env bash
# Next.js Web :3001 실행.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ui/web"

[ -d node_modules ] || { echo "✗ node_modules 없음. ./scripts/setup.sh 먼저 실행."; exit 1; }

PORT="${PORT:-3001}"
echo "→ Next.js dev on http://localhost:$PORT"
exec npm run dev -- --port "$PORT"
