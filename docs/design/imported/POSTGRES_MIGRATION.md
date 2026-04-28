# PostgreSQL 마이그레이션 가이드

> **대상 환경**: PostgreSQL 16 + TimescaleDB 2.x
> **현재 DB**: SQLite (`backend/casting_factory.db`)
> **마이그레이션 시점**: Phase 1 (MQTT 파이프라인 도입과 함께)

## 배경

Casting Factory 시스템은 다음 이유로 SQLite → PostgreSQL 16 로 전환한다:

1. **다중 하드웨어 동시 쓰기**: ESP32 / Cobot 2대 / AMR 3대 / Vision 이 초당 30~40회 동시 쓰기 발생 → SQLite file lock 한계
2. **JSONB 네이티브 타입**: MQTT payload 저장/쿼리에 필수
3. **시계열 하이퍼테이블**: TimescaleDB 확장으로 센서 텔레메트리 압축/파티션/자동집계
4. **네트워크 접속**: Jetson Orin NX, AMR Controller 등 원격 클라이언트가 DB 접근해야 함
5. **알람 룰 엔진**: PL/pgSQL 트리거 기반
6. **HA / 복제**: streaming replication 으로 공장 가동 중단 방지

## 설치 단계 (RPi5 또는 전용 DB 서버)

### 1. PostgreSQL 16 설치

```bash
# Ubuntu 22.04 / 24.04 기준
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib-16

# 서비스 시작 및 자동 실행 설정
sudo systemctl enable --now postgresql

# 상태 확인
sudo systemctl status postgresql
```

### 2. TimescaleDB 확장 설치

```bash
# TimescaleDB 공식 APT 저장소 추가
sudo apt install -y gnupg postgresql-common apt-transport-https lsb-release wget
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/$(lsb_release -cs) main' \
    > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

sudo apt update
sudo apt install -y timescaledb-2-postgresql-16

# 튜닝 스크립트 실행
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

### 3. 데이터베이스 / 사용자 생성

```bash
sudo -u postgres psql << 'SQL'
CREATE USER casting_user WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE casting_factory OWNER casting_user;
GRANT ALL PRIVILEGES ON DATABASE casting_factory TO casting_user;
\c casting_factory
CREATE EXTENSION IF NOT EXISTS timescaledb;
SQL
```

### 4. 네트워크 접속 허용

`/etc/postgresql/16/main/postgresql.conf`:
```ini
listen_addresses = '*'
```

`/etc/postgresql/16/main/pg_hba.conf`:
```
host    casting_factory    casting_user    192.168.0.0/16    scram-sha-256
```

```bash
sudo systemctl restart postgresql
sudo ufw allow 5432/tcp
```

## Python 백엔드 설정

### 1. 의존성 설치

`backend/requirements.txt` 에 이미 추가되어 있음:

```bash
cd /Users/ibkim/Project/casting-factory/backend
source venv/bin/activate
pip install -r requirements.txt
```

설치되는 패키지:
- `psycopg[binary]==3.2.3` — 동기 드라이버 (SQLAlchemy 기본)
- `asyncpg==0.29.0` — 비동기 드라이버
- `alembic==1.13.3` — 스키마 마이그레이션 도구

### 2. 환경 변수 설정

`backend/.env` 파일 생성 (git ignore):

```bash
DATABASE_URL=postgresql+psycopg://casting_user:CHANGE_ME@192.168.0.100:5432/casting_factory
```

개발 환경 (로컬 SQLite 유지):
```bash
# 설정하지 않으면 자동으로 SQLite 폴백
unset DATABASE_URL
```

### 3. Alembic 초기화

```bash
cd backend
alembic init alembic
```

`alembic.ini` 수정:
```ini
sqlalchemy.url = postgresql+psycopg://casting_user:CHANGE_ME@192.168.0.100:5432/casting_factory
```

`alembic/env.py` 에 모델 import:
```python
from app.models.models import Base
target_metadata = Base.metadata
```

초기 마이그레이션 생성:
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## 시계열 하이퍼테이블 생성

`mqtt_events`, `telemetry`, `conveyor_status` 같은 고빈도 시계열 테이블은 TimescaleDB 하이퍼테이블로 변환:

```sql
-- MQTT 이벤트 원본 저장
CREATE TABLE mqtt_events (
  id BIGSERIAL,
  topic TEXT NOT NULL,
  payload JSONB NOT NULL,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('mqtt_events', 'created_at',
                         chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_mqtt_topic_time ON mqtt_events (topic, created_at DESC);
CREATE INDEX idx_mqtt_payload_gin ON mqtt_events USING gin(payload);

-- 장비 텔레메트리
CREATE TABLE telemetry (
  id BIGSERIAL,
  device TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('telemetry', 'created_at',
                         chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_telemetry_device_metric_time
  ON telemetry (device, metric, created_at DESC);

-- 압축 정책 (7일 이전 데이터 자동 압축)
ALTER TABLE mqtt_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'topic'
);
SELECT add_compression_policy('mqtt_events', INTERVAL '7 days');

-- 보존 정책 (90일 이후 자동 삭제)
SELECT add_retention_policy('mqtt_events', INTERVAL '90 days');
```

## Continuous Aggregate (자동 집계)

시간 단위 OEE/KPI 집계를 자동화:

```sql
CREATE MATERIALIZED VIEW hourly_throughput
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', created_at) AS bucket,
  topic,
  count(*) AS event_count,
  jsonb_agg(payload->>'count') FILTER (WHERE payload ? 'count') AS cycle_counts
FROM mqtt_events
WHERE topic LIKE 'conveyor/%/event'
GROUP BY bucket, topic;

SELECT add_continuous_aggregate_policy('hourly_throughput',
  start_offset => INTERVAL '3 hours',
  end_offset   => INTERVAL '10 minutes',
  schedule_interval => INTERVAL '10 minutes');
```

## 모델 변경 사항

`backend/app/models/models.py` 에서 JSON 타입을 `JSONB` 로 전환해야 함:

```python
# Before (SQLite)
from sqlalchemy import Column, JSON
payload = Column(JSON)

# After (PostgreSQL + TimescaleDB)
from sqlalchemy.dialects.postgresql import JSONB
payload = Column(JSONB)
```

## 테스트

```bash
# 1) DB 연결 확인
cd backend
source venv/bin/activate
python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT version();'))
    print(result.scalar())
"

# 2) FastAPI 서버 기동
DATABASE_URL=postgresql+psycopg://casting_user:CHANGE_ME@localhost/casting_factory \
uvicorn app.main:app --reload

# 3) 헬스체크
curl http://localhost:8000/api/dashboard/stats
```

## 백업 / 복구

```bash
# 전체 백업
pg_dump -U casting_user -d casting_factory -F c -f backup_$(date +%Y%m%d).dump

# 복구
pg_restore -U casting_user -d casting_factory -c backup_20260407.dump

# WAL 아카이빙 (실시간 백업) 은 postgresql.conf 에서
#   archive_mode = on
#   archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
```

## 모니터링

```bash
# 연결 상태
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname='casting_factory';"

# 하이퍼테이블 크기
sudo -u postgres psql -d casting_factory -c "
SELECT hypertable_name,
       pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables;"
```

## 롤백 계획

문제 발생 시 SQLite 로 즉시 롤백:

```bash
# 1) DATABASE_URL 환경변수 제거
unset DATABASE_URL

# 2) FastAPI 재시작
uvicorn app.main:app --reload

# → 자동으로 backend/casting_factory.db (SQLite) 사용
```

## 참고 자료

- PostgreSQL 16 공식: https://www.postgresql.org/docs/16/
- TimescaleDB: https://docs.timescale.com/
- SQLAlchemy PostgreSQL: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- Alembic 마이그레이션: https://alembic.sqlalchemy.org/
