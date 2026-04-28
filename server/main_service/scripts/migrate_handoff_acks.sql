-- SPEC-AMR-001: 후처리존 인수인계 확인 이벤트 테이블
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_handoff_acks.sql
-- 2026-04-17, 멱등 실행 가능
--
-- 정책 변경 (2026-04-17):
--   DB 서버에 TimescaleDB 확장이 설치되지 않음(plpgsql 만 활성).
--   handoff ACK 이벤트는 저볼륨(일 수십~수백 건)이므로 일반 테이블로 충분.
--   추후 TimescaleDB 도입 시 이 마이그레이션의 hypertable 블록 주석 해제.
--
-- transport_tasks.status 값 확장은 String 컬럼이므로 DDL 불필요
-- (애플리케이션 레이어에서 'waiting_handoff_ack', 'handoff_complete' 인정).

BEGIN;

-- 1. handoff_acks 테이블 (멱등)
CREATE TABLE IF NOT EXISTS handoff_acks (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR REFERENCES transport_tasks(id) ON DELETE SET NULL,
    zone TEXT NOT NULL,
    amr_id TEXT,
    ack_source TEXT NOT NULL,                -- 'esp32_button' | 'debug_endpoint' | 'gui_override'
    operator_id TEXT,
    button_device_id TEXT,
    orphan_ack BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key TEXT,
    metadata JSONB,
    ack_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. 인덱스 (멱등)
CREATE INDEX IF NOT EXISTS idx_handoff_acks_zone_ack_at ON handoff_acks (zone, ack_at DESC);
CREATE INDEX IF NOT EXISTS idx_handoff_acks_task_id ON handoff_acks (task_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_handoff_acks_idempotency
    ON handoff_acks (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- 3. TimescaleDB hypertable (확장 설치된 경우만, 현재는 NO-OP)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- SQLAlchemy create_all 이 기존에 단순 PK 로 만들었을 수 있음.
        -- hypertable 전환 전 PK 를 (id, ack_at) 로 바꿔야 하므로 조건부 처리.
        PERFORM create_hypertable('handoff_acks', 'ack_at', if_not_exists => TRUE, migrate_data => TRUE);
        RAISE NOTICE 'TimescaleDB hypertable 활성화됨';
    ELSE
        RAISE NOTICE 'TimescaleDB 확장 미설치 - 일반 테이블로 운영';
    END IF;
END $$;

COMMIT;

-- 확인 쿼리 (수동):
--   SELECT indexname FROM pg_indexes WHERE tablename = 'handoff_acks';
--   SELECT count(*) FROM handoff_acks;
