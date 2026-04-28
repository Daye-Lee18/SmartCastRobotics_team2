#!/usr/bin/env bash
# PyQt Monitoring 데스크톱 앱 실행.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ui/pyqt/factory_operator"

[ -d .venv ] || { echo "✗ .venv 없음. ./scripts/setup.sh 먼저 실행."; exit 1; }

source .venv/bin/activate
export PYTHONPATH=src

# .env.local 의 변수를 셸에 export (있을 때만)
if [ -f .env.local ]; then
  set -a; source .env.local; set +a
fi

echo "→ PyQt Monitoring 시작 (API_BASE_URL=${API_BASE_URL:-http://localhost:8000})"
exec python -m factory_operator.main
