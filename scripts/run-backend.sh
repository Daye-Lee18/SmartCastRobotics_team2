#!/usr/bin/env bash
# Backend FastAPI :8000 실행.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/server/main_service"

[ -d .venv ] || { echo "✗ .venv 없음. ./scripts/setup.sh 먼저 실행."; exit 1; }
[ -f .env.local ] || { echo "✗ .env.local 없음. setup.sh 먼저 실행 후 비밀번호 입력."; exit 1; }

source .venv/bin/activate
export PYTHONPATH=src

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
echo "→ FastAPI on http://$HOST:$PORT (Ctrl+C 종료)"
exec uvicorn main_service.app.main:app --host "$HOST" --port "$PORT" --env-file .env.local --reload
