-- SPEC-RFID-001: RFID 스캔 이력 append-only 테이블
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_rfid_scan_log.sql
-- 2026-04-20, 멱등 실행 가능
--
-- 설계:
--   HW(ESP32 + RC522) → Jetson(Serial) → Mgmt(gRPC ReportRfidScan) → 본 테이블
--   payload 예: 'order_1_item_20260417_1'
--   - 파싱 성공 시: parse_status='ok' + (ord_id, item_key)
--   - 포맷 오류 : parse_status='bad_format', raw_payload 만 보존
--   - item lookup / unknown_item 판정: Wave 2 범위 외
--
-- TimescaleDB 확장 존재 시 hypertable 전환 (handoff_acks 패턴 준용).

BEGIN;

-- 1. public.rfid_scan_log 테이블 (멱등)
CREATE TABLE IF NOT EXISTS public.rfid_scan_log (
    id BIGSERIAL,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reader_id TEXT NOT NULL,
    zone TEXT,
    raw_payload TEXT NOT NULL,
    ord_id TEXT,
    item_key TEXT,                        -- 'YYYYMMDD_seq'
    item_id BIGINT,                       -- Wave 2 에서는 NULL 유지 (후속 item binding 용)
    parse_status TEXT NOT NULL,           -- 'ok' | 'bad_format'
    idempotency_key TEXT,
    metadata JSONB,
    PRIMARY KEY (id, scanned_at)          -- hypertable 호환 복합 PK
);

-- 2. 인덱스 (멱등)
CREATE INDEX IF NOT EXISTS idx_rfid_scan_reader_time
    ON public.rfid_scan_log (reader_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_rfid_scan_item_time
    ON public.rfid_scan_log (item_id, scanned_at DESC)
    WHERE item_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_scan_idempotency
    ON public.rfid_scan_log (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- 3. TimescaleDB hypertable (확장 설치된 경우만)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable(
            'public.rfid_scan_log',
            'scanned_at',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        RAISE NOTICE 'SPEC-RFID-001: TimescaleDB hypertable 활성화';
    ELSE
        RAISE NOTICE 'SPEC-RFID-001: TimescaleDB 미설치 — 일반 테이블로 운영';
    END IF;
END $$;

COMMIT;

-- 확인 쿼리 (수동):
--   SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='rfid_scan_log';
--   SELECT count(*) FROM public.rfid_scan_log;
--   SELECT parse_status, count(*) FROM public.rfid_scan_log GROUP BY parse_status;
