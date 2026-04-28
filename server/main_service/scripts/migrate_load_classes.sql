-- EN 124 하중 등급 마스터 테이블 생성 + 6개 row 삽입
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_load_classes.sql
-- 2026-04-09, 멱등 실행 가능

BEGIN;

CREATE TABLE IF NOT EXISTS load_classes (
    code          VARCHAR(8)    PRIMARY KEY,
    load_tons     DOUBLE PRECISION NOT NULL,
    use_case      VARCHAR(200)  NOT NULL,
    display_order INTEGER       NOT NULL
);

INSERT INTO load_classes (code, load_tons, use_case, display_order) VALUES
    ('A15',  1.5,  '보행자 전용 구역',                 1),
    ('B125', 12.5, '자전거·보행자 도로, 주차장',       2),
    ('C250', 25.0, '길가·갓길 (상용차 주차 가능)',     3),
    ('D400', 40.0, '일반 차도',                        4),
    ('E600', 60.0, '항만·산업 구역',                   5),
    ('F900', 90.0, '공항·특수 중하중 지역',            6)
ON CONFLICT (code) DO NOTHING;

COMMIT;
