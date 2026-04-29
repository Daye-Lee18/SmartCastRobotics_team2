-- AWS RDS Casting (public) 보강 마이그레이션 — B 옵션 (가상 시나리오 검증용)
-- 본 스크립트는 ERP 29 테이블에 추가로 SPEC-AMR-001 / SPEC-RFID-001 가상 검증에
-- 필요한 운영 테이블을 'public' 스키마에 생성한다. 기존 ERP 테이블은 건드리지 않는다.
--
-- 적용:
--   PGPASSWORD=team21234 psql "host=teamdb.ct4cesagstqf.ap-northeast-2.rds.amazonaws.com \
--     port=5432 dbname=Casting user=postgres sslmode=verify-full \
--     sslrootcert=/Users/ibkim/Downloads/dbeaver-drivers/global-bundle.pem" \
--     -f backend/scripts/migrate_aws_rds_casting_b.sql

BEGIN;

-- transport_tasks (smartcast.handoff/AMR 가상 테스트용 — 실제로 본 시나리오에선 trans_task_txn 만 사용)
CREATE TABLE IF NOT EXISTS public.transport_tasks (
    id                VARCHAR PRIMARY KEY,
    from_name         VARCHAR NOT NULL,
    from_coord        VARCHAR DEFAULT '',
    to_name           VARCHAR NOT NULL,
    to_coord          VARCHAR DEFAULT '',
    item_id           VARCHAR DEFAULT '',
    item_name         VARCHAR DEFAULT '',
    quantity          INT NOT NULL DEFAULT 1,
    priority          VARCHAR NOT NULL DEFAULT 'medium',
    status            VARCHAR NOT NULL DEFAULT 'unassigned',
    assigned_robot_id VARCHAR DEFAULT '',
    requested_at      VARCHAR NOT NULL,
    completed_at      VARCHAR
);

-- handoff_acks 감사 테이블
CREATE TABLE IF NOT EXISTS public.handoff_acks (
    id                BIGSERIAL PRIMARY KEY,
    ack_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    task_id           VARCHAR REFERENCES public.transport_tasks(id) ON DELETE SET NULL,
    zone              VARCHAR NOT NULL,
    amr_id            VARCHAR,
    ack_source        VARCHAR NOT NULL,
    operator_id       VARCHAR,
    button_device_id  VARCHAR,
    orphan_ack        BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key   VARCHAR,
    metadata          JSONB
);
CREATE INDEX IF NOT EXISTS idx_handoff_acks_ack_at  ON public.handoff_acks (ack_at);
CREATE INDEX IF NOT EXISTS idx_handoff_acks_zone    ON public.handoff_acks (zone);
CREATE INDEX IF NOT EXISTS idx_handoff_acks_task_id ON public.handoff_acks (task_id);

-- rfid_scan_log append-only
CREATE TABLE IF NOT EXISTS public.rfid_scan_log (
    id              BIGSERIAL,
    scanned_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    reader_id       VARCHAR NOT NULL,
    zone            VARCHAR,
    raw_payload     VARCHAR NOT NULL,
    ord_id          VARCHAR,
    item_key        VARCHAR,
    item_id         BIGINT,
    parse_status    VARCHAR NOT NULL,
    idempotency_key VARCHAR,
    metadata        JSONB,
    PRIMARY KEY (id, scanned_at)
);
CREATE INDEX IF NOT EXISTS idx_rfid_scan_reader_time
    ON public.rfid_scan_log (reader_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_rfid_scan_item_time
    ON public.rfid_scan_log (item_id, scanned_at DESC) WHERE item_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_scan_idempotency
    ON public.rfid_scan_log (idempotency_key) WHERE idempotency_key IS NOT NULL;

-- alerts (execution_monitor 호환 — 본 시나리오에는 미사용이지만 ORM import 호환)
CREATE TABLE IF NOT EXISTS public.alerts (
    id              VARCHAR PRIMARY KEY,
    equipment_id    VARCHAR DEFAULT '',
    type            VARCHAR NOT NULL,
    severity        VARCHAR NOT NULL DEFAULT 'info',
    error_code      VARCHAR DEFAULT '',
    message         VARCHAR NOT NULL,
    abnormal_value  VARCHAR DEFAULT '',
    zone            VARCHAR,
    timestamp       VARCHAR NOT NULL,
    resolved_at     VARCHAR,
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE
);

COMMIT;
