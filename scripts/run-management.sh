#!/usr/bin/env bash
# Management gRPC service :50051 실행.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/server/main_service"

[ -d .venv ] || { echo "✗ .venv 없음. ./scripts/setup.sh 먼저 실행."; exit 1; }
[ -f .env.local ] || { echo "✗ .env.local 없음. setup.sh 먼저 실행 후 비밀번호 입력."; exit 1; }

PY=".venv/bin/python"
[ -x "$PY" ] || { echo "✗ $PY 없음. ./scripts/setup.sh 다시 실행."; exit 1; }

"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else "backend .venv 가 Python 3.11 미만입니다. Python 3.11 설치 후 ./scripts/setup.sh 를 다시 실행하세요.")'
export PYTHONPATH=src/interface_service:src/main_service:src

HOST="${MANAGEMENT_GRPC_HOST:-0.0.0.0}"
PORT="${MANAGEMENT_GRPC_PORT:-50051}"
echo "→ Management gRPC on $HOST:$PORT (Ctrl+C 종료)"
exec "$PY" src/main_service/management/server.py
