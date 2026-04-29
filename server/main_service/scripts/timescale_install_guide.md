# TimescaleDB 설치 + hypertable 변환 가이드

> 본 작업은 **DB 서버 root 권한**(예진님 PC 또는 PostgreSQL 관리자)이 필요합니다.
> `team2` role 로는 OS 패키지 설치 / `CREATE EXTENSION` 모두 불가합니다.

## 1. OS 패키지 설치 (Ubuntu 24.04, PostgreSQL 16)

```bash
# Timescale 공식 APT 저장소 추가
sudo apt install -y curl gnupg lsb-release
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" \
  | sudo tee /etc/apt/sources.list.d/timescaledb.list
curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey \
  | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
sudo apt update

# PostgreSQL 16 용 TimescaleDB 패키지
sudo apt install -y timescaledb-2-postgresql-16

# postgresql.conf 자동 튜닝
sudo timescaledb-tune --quiet --yes

# PostgreSQL 재시작
sudo systemctl restart postgresql
```

## 2. Extension 활성화 (smartcast_robotics DB 에서)

```bash
sudo -u postgres psql smartcast_robotics -c "CREATE EXTENSION timescaledb;"
```

## 3. 권한 부여 (team2 role 이 hypertable 사용 가능하도록)

```sql
GRANT USAGE ON SCHEMA _timescaledb_catalog TO team2;
GRANT USAGE ON SCHEMA _timescaledb_internal TO team2;
GRANT SELECT ON ALL TABLES IN SCHEMA _timescaledb_information TO team2;
```

## 4. hypertable 변환 (smartcast schema)

다음 SQL 을 `team2` 로 실행해 시계열 집계가 무거운 테이블을 hypertable 로 전환합니다.

```sql
SET search_path TO smartcast, public;

-- equip_stat: 장비 상태 시계열 (RA cur_stat 변화)
SELECT create_hypertable('smartcast.equip_stat', 'updated_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_equip_stat_res_time
    ON smartcast.equip_stat (res_id, updated_at DESC);

-- trans_stat: AMR 상태 시계열 (배터리/위치 변화)
-- 주의: trans_stat 는 PRIMARY KEY (res_id) 1:1 stat 테이블. hypertable 변환 시
--       PK 변경 + 행 단위 timestamp 가 필요. 이력 보관이 필요하면 trans_stat_log 분리 권장.
-- 일단 변환 보류 — 로그 테이블 신설 후 hypertable 화 검토.

-- equip_err_log / trans_err_log: 에러 발생 시계열 (낮은 빈도, 저장 효율 우선)
SELECT create_hypertable('smartcast.equip_err_log', 'occured_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
SELECT create_hypertable('smartcast.trans_err_log', 'occured_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);

-- ord_log: 발주 상태 전이 로그 (낮은 빈도)
-- create_hypertable 의 chunk_time_interval 은 7 일이 적절.
SELECT create_hypertable('smartcast.ord_log', 'logged_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);

-- 압축 정책 (30일 이전 데이터 압축)
SELECT add_compression_policy('smartcast.equip_stat', INTERVAL '30 days');
SELECT add_compression_policy('smartcast.equip_err_log', INTERVAL '30 days');
SELECT add_compression_policy('smartcast.trans_err_log', INTERVAL '30 days');
SELECT add_compression_policy('smartcast.ord_log', INTERVAL '30 days');

-- 보존 정책 (180일 이전 데이터 자동 삭제)
SELECT add_retention_policy('smartcast.equip_stat', INTERVAL '180 days');
SELECT add_retention_policy('smartcast.equip_err_log', INTERVAL '365 days');
SELECT add_retention_policy('smartcast.trans_err_log', INTERVAL '365 days');
```

## 5. continuous aggregate (선택 — 시계열 차트 가속)

```sql
-- 시간대별 item 생산 카운트 (hourly chart 용)
CREATE MATERIALIZED VIEW smartcast.item_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 hour', updated_at) AS bucket,
       COUNT(*) FILTER (WHERE cur_stat IS NOT NULL) AS produced
FROM smartcast.item
GROUP BY bucket;

SELECT add_continuous_aggregate_policy('smartcast.item_hourly',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');
```

## 6. 검증

```sql
-- 설치 확인
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';

-- hypertable 목록
SELECT hypertable_name, num_chunks, compression_enabled
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;
```

## 7. 본 가이드 적용 후 백엔드 변경

DBA 작업 완료 후 `backend/app/routes/production.py` 의 시계열 stub 엔드포인트
(`/hourly`, `/weekly`, `/temperature`, `/parameter-history`) 를 실제 hypertable
조회 쿼리로 교체. SPEC-DB-V2-MIGRATION 의 Open Questions 항목 참조.

---

**참조**:
- TimescaleDB 공식 설치 가이드: https://docs.timescale.com/install/latest/self-hosted/installation-debian/
- PostgreSQL 16 패키지명: `timescaledb-2-postgresql-16`
- 본 프로젝트의 SPEC: `.moai/specs/SPEC-DB-V2-MIGRATION/spec.md` § Open Questions
