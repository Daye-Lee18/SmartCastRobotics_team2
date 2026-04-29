#!/usr/bin/env bash
# =============================================================================
# TimescaleDB 자동 설치 (LOCAL 실행 — yejin-laptop 에서 직접)
# =============================================================================
#
# 본 스크립트는 DB 서버 (yejin-laptop) 에서 직접 실행한다.
# 원격 SSH 가 필요 없고, sudo 비밀번호만 알면 끝.
#
# 사용법:
#   1. yejin-laptop 의 터미널 열기
#   2. 본 파일 다운로드 (또는 USB / git clone):
#        curl -fsSL https://raw.githubusercontent.com/kiminbean/casting-factory/feat/db-schema-v2-charts-ros2/backend/scripts/install_timescaledb_local.sh -o /tmp/ts.sh
#        chmod +x /tmp/ts.sh
#   3. 실행:
#        /tmp/ts.sh
#   4. sudo 비밀번호 입력 (보통 1번)
#
# 약 5~10분 소요 (인터넷 속도에 따라).
# 멱등 — 이미 설치돼 있으면 자동으로 단계 스킵.
#
# 끝나면 김기수 카톡으로 "완료" 알려주세요. 김기수가 자기 Mac 에서 hypertable
# 변환 + 검증 마무리합니다.
# =============================================================================

set -euo pipefail

GRN='\033[0;32m'
YLW='\033[0;33m'
RED='\033[0;31m'
RST='\033[0m'

step() { echo -e "\n${GRN}===== $* =====${RST}"; }
warn() { echo -e "${YLW}⚠ $*${RST}"; }
fail() { echo -e "${RED}❌ $*${RST}"; exit 1; }

# ----- 사전 체크 -----
step "0. 사전 체크"
[[ "$(id -u)" != "0" ]] || warn "root 로 실행 중 — 보통은 일반 사용자 + sudo 권장"
command -v psql >/dev/null || warn "psql 명령이 없습니다. CREATE EXTENSION 단계 별도 필요."
command -v lsb_release >/dev/null || fail "lsb_release 없음. apt install lsb-release 후 재시도."

UBUNTU_CODENAME=$(lsb_release -c -s)
PG_VERSION=$(pg_config --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "16")
echo "  Ubuntu: $UBUNTU_CODENAME"
echo "  PostgreSQL: ${PG_VERSION}"

# 이미 활성화돼 있는지 확인
ALREADY_ACTIVE=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_extension WHERE extname='timescaledb';" smartcast_robotics 2>/dev/null || echo "")
if [[ "$ALREADY_ACTIVE" == "1" ]]; then
    warn "TimescaleDB extension 이 이미 활성화되어 있습니다. 단계 1~3 자동 스킵 — 4 (검증) 만 진행"
    SKIP_INSTALL=1
else
    SKIP_INSTALL=0
fi

# ============================================================
# 단계 1 — APT 저장소 추가 + OS 패키지 설치
# ============================================================
if [[ "$SKIP_INSTALL" == "0" ]]; then
    step "1. OS 패키지 설치 (sudo 비밀번호 입력 요구)"
    sudo apt-get update -q
    sudo apt-get install -y -q curl gnupg lsb-release

    if [[ ! -f /etc/apt/sources.list.d/timescaledb.list ]]; then
        echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ ${UBUNTU_CODENAME} main" \
            | sudo tee /etc/apt/sources.list.d/timescaledb.list >/dev/null
    fi
    if [[ ! -f /etc/apt/trusted.gpg.d/timescaledb.gpg ]]; then
        curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey \
            | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
    fi

    sudo apt-get update -q
    sudo apt-get install -y "timescaledb-2-postgresql-${PG_VERSION%%.*}"

    step "1b. timescaledb-tune 자동 튜닝"
    sudo timescaledb-tune --quiet --yes

    step "1c. PostgreSQL 재시작 (10초 다운타임)"
    sudo systemctl restart postgresql
    sleep 3
    sudo systemctl is-active --quiet postgresql || fail "PostgreSQL 재시작 실패"
    echo "  ✓ PostgreSQL active"

    # ============================================================
    # 단계 2 — Extension + team2 권한
    # ============================================================
    step "2. Extension 활성화 + team2 권한 부여"
    sudo -u postgres psql smartcast_robotics <<'SQL'
CREATE EXTENSION IF NOT EXISTS timescaledb;
GRANT USAGE ON SCHEMA _timescaledb_catalog TO team2;
GRANT USAGE ON SCHEMA _timescaledb_internal TO team2;
GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_information TO team2;
SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';
SQL

    # ============================================================
    # 단계 3 — hypertable + continuous aggregate
    # ============================================================
    step "3. hypertable + continuous aggregate (smartcast schema)"
    sudo -u postgres psql smartcast_robotics <<'SQL'
SET search_path TO smartcast, public;

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

DO $$ BEGIN
    PERFORM add_compression_policy('smartcast.equip_stat', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.equip_err_log', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.trans_err_log', INTERVAL '30 days', if_not_exists => TRUE);
    PERFORM add_compression_policy('smartcast.ord_log', INTERVAL '30 days', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'compression: %', SQLERRM;
END $$;

DO $$ BEGIN
    PERFORM add_retention_policy('smartcast.equip_stat', INTERVAL '180 days', if_not_exists => TRUE);
    PERFORM add_retention_policy('smartcast.equip_err_log', INTERVAL '365 days', if_not_exists => TRUE);
    PERFORM add_retention_policy('smartcast.trans_err_log', INTERVAL '365 days', if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'retention: %', SQLERRM;
END $$;

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
EXCEPTION WHEN OTHERS THEN RAISE NOTICE 'continuous policy: %', SQLERRM;
END $$;

CALL refresh_continuous_aggregate('smartcast.item_hourly', NULL, NULL);
SQL
fi  # SKIP_INSTALL

# ============================================================
# 단계 4 — 검증 (postgres 또는 team2)
# ============================================================
step "4. 검증"
sudo -u postgres psql smartcast_robotics <<'SQL'
\echo '-- 1. extension --'
SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';

\echo '-- 2. hypertable 목록 (4건 예상) --'
SELECT hypertable_name, num_chunks, compression_enabled
FROM timescaledb_information.hypertables
WHERE hypertable_schema='smartcast'
ORDER BY hypertable_name;

\echo '-- 3. continuous aggregate 목록 (1건 예상: item_hourly) --'
SELECT view_name FROM timescaledb_information.continuous_aggregates
WHERE view_schema='smartcast';
SQL

step "✓ 모든 단계 완료"
echo ""
echo "  김기수에게 '완료' 카톡 부탁드립니다."
echo "  김기수가 자기 Mac 에서 backend 재시작 + dashboard 검증 진행합니다."
