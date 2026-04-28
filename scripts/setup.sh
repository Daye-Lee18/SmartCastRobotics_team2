#!/usr/bin/env bash
# 모든 모듈의 가상환경 생성 + 의존성 설치 + .env.local 템플릿 복사.
# Idempotent — 여러 번 실행해도 안전.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${YELLOW}[setup]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
fail() { echo -e "${RED}  ✗${NC} $*"; exit 1; }

# 1. 사전 도구 점검
log "사전 도구 점검"
command -v python3.11 >/dev/null || { python3 --version 2>&1 | grep -q "3.11" || fail "python3.11 필요 (brew install python@3.11)"; }
command -v python3.12 >/dev/null || { python3 --version 2>&1 | grep -q "3.12" || log "python3.12 권장 (PyQt). python3 으로 진행."; }
command -v node >/dev/null || fail "node 필요 (https://nodejs.org)"
command -v npm  >/dev/null || fail "npm 필요"
ok "python/node/npm 확인"

# 2. backend
log "[1/3] server/main_service venv + 의존성"
cd "$ROOT/server/main_service"
PY=$(command -v python3.11 || command -v python3)
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
deactivate
[ -f .env.local ] || { cp .env.example .env.local && log ".env.local 생성됨 — 비밀번호 채우기 필요"; }
ok "server/main_service 준비 완료"

# 3. PyQt
log "[2/3] ui/pyqt/factory_operator venv + 의존성"
cd "$ROOT/ui/pyqt/factory_operator"
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
deactivate
[ -f .env.local ] || cp .env.example .env.local
ok "ui/pyqt/factory_operator 준비 완료"

# 4. Web
log "[3/3] ui/web npm install"
cd "$ROOT/ui/web"
npm install --silent --no-audit --no-fund
[ -f .env.local ] || cp .env.example .env.local
ok "ui/web 준비 완료"

cd "$ROOT"
log "완료. 다음 단계:"
echo "  1) server/main_service/.env.local 의 DATABASE_URL 비밀번호/엔드포인트 입력"
echo "  2) ./scripts/run-all.sh  (또는 개별 ./scripts/run-{backend,pyqt,web}.sh)"
