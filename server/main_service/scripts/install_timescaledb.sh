#!/usr/bin/env bash
# =============================================================================
# TimescaleDB 자동 설치 + 활성화 스크립트
# =============================================================================
#
# 본 스크립트는 다음 4 단계를 한 번에 수행한다:
#   1. SSH + sudo 로 DB 서버에 OS 패키지 설치 (timescaledb-2-postgresql-16)
#   2. ssh + sudo -u postgres psql 로 CREATE EXTENSION + team2 권한 부여
#   3. team2 로 hypertable + continuous aggregate 변환
#   4. backend/scripts/timescale_verify.sql 실행으로 검증
#
# 실행 환경: 본인 Mac (이 저장소 root 에서 실행)
# 필요 권한: SSH 접속 + sudo 가능 (대화형 암호 입력)
# 멱등성: 재실행 안전 (CREATE EXTENSION IF NOT EXISTS, if_not_exists 등 사용)
#
# 사용법:
#   SSH_USER=ibkim ./backend/scripts/install_timescaledb.sh
#   (또는 ~/.ssh/config 에 yejin-laptop alias 가 있으면 SSH_HOST=yejin-laptop)
#
# 환경 변수 (override 가능):
#   SSH_HOST   (default: 100.107.120.14)
#   SSH_USER   (필수, default: $USER)
#   PG_HOST    (default: 100.107.120.14)
#   PG_USER    (default: team2)
#   PG_DB      (default: smartcast_robotics)
#   PG_PASSWORD (default: backend/.env.local 의 DATABASE_URL 에서 추출)
#
# 중간 실패 시 안전성:
#   - 단계 1 실패 → CREATE EXTENSION 시도 시 명시적 에러로 중단
#   - 단계 2 실패 → hypertable 단계 자동 중단
#   - 단계 3 실패 → 검증 단계 자동 중단
#   - 모든 단계는 set -e 로 즉시 정지
# =============================================================================

set -euo pipefail

# ----- 환경 변수 -----
SSH_HOST="${SSH_HOST:-100.107.120.14}"
SSH_USER="${SSH_USER:-$USER}"
PG_HOST="${PG_HOST:-100.107.120.14}"
PG_USER="${PG_USER:-team2}"
PG_DB="${PG_DB:-smartcast_robotics}"

# PG_PASSWORD 가 없으면 backend/.env.local 에서 추출
if [[ -z "${PG_PASSWORD:-}" ]]; then
    if [[ -f backend/.env.local ]]; then
        PG_PASSWORD=$(
            grep -E '^DATABASE_URL=' backend/.env.local \
            | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|' \
            | head -1
        )
    fi
fi
if [[ -z "${PG_PASSWORD:-}" ]]; then
    echo "❌ PG_PASSWORD 가 설정되지 않았고 backend/.env.local 에서도 추출 실패."
    echo "   PG_PASSWORD=... ./backend/scripts/install_timescaledb.sh 형태로 실행하세요."
    exit 1
fi

REPO_ROOT=$(pwd)

# ----- 색상 출력 -----
GRN='\033[0;32m'
YLW='\033[0;33m'
RED='\033[0;31m'
RST='\033[0m'

step() { echo -e "\n${GRN}===== $* =====${RST}"; }
warn() { echo -e "${YLW}⚠ $*${RST}"; }
fail() { echo -e "${RED}❌ $*${RST}"; exit 1; }

# ----- 사전 체크 -----
step "0. 사전 체크"
echo "  SSH:  ${SSH_USER}@${SSH_HOST}"
echo "  PG:   ${PG_USER}@${PG_HOST}/${PG_DB}"
command -v psql >/dev/null || fail "psql 명령이 없습니다. brew install postgresql 등으로 설치하세요."
command -v ssh  >/dev/null || fail "ssh 명령이 없습니다."

# SSH 연결 테스트 (10초 타임아웃)
ssh -o ConnectTimeout=10 -o BatchMode=no "${SSH_USER}@${SSH_HOST}" 'true' \
    || fail "SSH 접속 실패: ${SSH_USER}@${SSH_HOST}. ~/.ssh/config 또는 ssh-copy-id 확인."

# DB 연결 테스트
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -c '\q' \
    || fail "DB 연결 실패: ${PG_USER}@${PG_HOST}/${PG_DB}. PG_PASSWORD 확인."

# 이미 설치돼 있는지 사전 확인
ALREADY_AVAIL=$(
    PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -At -X -c \
    "SELECT 1 FROM pg_available_extensions WHERE name='timescaledb';" 2>/dev/null || true
)
if [[ "$ALREADY_AVAIL" == "1" ]]; then
    warn "TimescaleDB 패키지가 이미 사용 가능 — 단계 1 (OS 설치) 건너뜀"
    SKIP_OS_INSTALL=1
else
    SKIP_OS_INSTALL=0
fi

# ============================================================
# 단계 1 — OS 패키지 설치 (필요 시)
# ============================================================
if [[ "$SKIP_OS_INSTALL" == "0" ]]; then
    step "1. OS 패키지 설치 (sudo 암호 입력 요구됨)"
    ssh -t "${SSH_USER}@${SSH_HOST}" 'bash -s' <<'REMOTE_SH'
set -euo pipefail
echo "[remote] APT 저장소 추가"
sudo apt-get update -q
sudo apt-get install -y -q curl gnupg lsb-release

sudo install -d -m 0755 /etc/apt/keyrings 2>/dev/null || true

if [[ ! -f /etc/apt/sources.list.d/timescaledb.list ]]; then
    echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" \
      | sudo tee /etc/apt/sources.list.d/timescaledb.list >/dev/null
fi

if [[ ! -f /etc/apt/trusted.gpg.d/timescaledb.gpg ]]; then
    curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey \
      | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
fi

sudo apt-get update -q
echo "[remote] timescaledb-2-postgresql-16 설치"
sudo apt-get install -y timescaledb-2-postgresql-16

echo "[remote] timescaledb-tune (자동 튜닝)"
sudo timescaledb-tune --quiet --yes

echo "[remote] PostgreSQL 재시작"
sudo systemctl restart postgresql
sudo systemctl is-active --quiet postgresql && echo "[remote] PostgreSQL active" || \
    { echo "[remote] PostgreSQL not active"; exit 1; }

echo "[remote] OS install 완료"
REMOTE_SH
fi

# ============================================================
# 단계 2 — CREATE EXTENSION + team2 권한 (postgres role)
# ============================================================
step "2. Extension 활성화 + team2 권한 부여 (sudo -u postgres)"
ssh -t "${SSH_USER}@${SSH_HOST}" "sudo -u postgres psql ${PG_DB} <<'EOSQL'
CREATE EXTENSION IF NOT EXISTS timescaledb;
GRANT USAGE ON SCHEMA _timescaledb_catalog TO ${PG_USER};
GRANT USAGE ON SCHEMA _timescaledb_internal TO ${PG_USER};
GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_information TO ${PG_USER};
SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';
EOSQL"

# ============================================================
# 단계 3 — hypertable + continuous aggregate (team2 권한으로 충분)
# ============================================================
step "3. hypertable + continuous aggregate 변환"
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" <<'SQL'
SET search_path TO smartcast, public;

\echo '-- hypertable 4종 변환 --'
SELECT create_hypertable('smartcast.equip_stat', 'updated_at',
    chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('smartcast.equip_err_log', 'occured_at',
    chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('smartcast.trans_err_log', 'occured_at',
    chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('smartcast.ord_log', 'logged_at',
    chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_equip_stat_res_time
    ON smartcast.equip_stat (res_id, updated_at DESC);

\echo '-- 압축 정책 (30일 이상 데이터 압축) --'
DO $$ BEGIN
    PERFORM add_compression_policy('smartcast.equip_stat', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.equip_err_log', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.trans_err_log', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.ord_log', INTERVAL '30 days', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'compression policy: %', SQLERRM;
END $$;

\echo '-- 보존 정책 (180~365일 retention) --'
DO $$ BEGIN
    PERFORM add_retention_policy('smartcast.equip_stat', INTERVAL '180 days', if_not_exists => TRUE);
    PERFORM add_retention_policy('smartcast.equip_err_log', INTERVAL '365 days', if_not_exists => TRUE);
    PERFORM add_retention_policy('smartcast.trans_err_log', INTERVAL '365 days', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'retention policy: %', SQLERRM;
END $$;

\echo '-- continuous aggregate (item_hourly) --'
CREATE MATERIALIZED VIEW IF NOT EXISTS smartcast.item_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 hour', updated_at) AS bucket,
       COUNT(*) FILTER (WHERE cur_stat IS NOT NULL) AS produced
FROM smartcast.item
GROUP BY bucket;

DO $$ BEGIN
    PERFORM add_continuous_aggregate_policy('smartcast.item_hourly',
        start_offset => INTERVAL '7 days',
        end_offset   => INTERVAL '1 hour',
        schedule_interval => INTERVAL '30 minutes',
        if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'continuous aggregate policy: %', SQLERRM;
END $$;

CALL refresh_continuous_aggregate('smartcast.item_hourly', NULL, NULL);
SQL

# ============================================================
# 단계 4 — 검증
# ============================================================
step "4. 검증 (timescale_verify.sql)"
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
    -f "${REPO_ROOT}/backend/scripts/timescale_verify.sql"

# ============================================================
# 단계 5 — backend 재시작 안내
# ============================================================
step "5. Backend 재시작 안내"
echo ""
echo "  TimescaleDB 검출 캐시 갱신을 위해 backend 재시작 필요:"
echo ""
echo "    PIDS=\$(lsof -ti :8000); [ -n \"\$PIDS\" ] && kill \$PIDS && sleep 2"
echo "    FMS_AUTOPLAY=1 nohup backend/venv/bin/uvicorn app.main:app \\"
echo "        --app-dir backend --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &"
echo "    disown"
echo ""
echo "  검증:"
echo "    curl -s http://localhost:8000/api/dashboard/stats | jq .timescaledb_enabled"
echo "    # → true (이전엔 false)"
echo ""
echo -e "${GRN}✓ 모든 단계 완료${RST}"
