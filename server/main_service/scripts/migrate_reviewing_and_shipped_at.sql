-- reviewing 상태 제거 + shipped_at 출고 타임스탬프 컬럼 추가
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_reviewing_and_shipped_at.sql
-- 2026-04-09, 멱등 실행 가능
--
-- 변경:
--   1. orders.shipped_at VARCHAR 컬럼 추가 (출고 처리 타임스탬프)
--   2. status='reviewing' row 를 'pending' 으로 롤백 (검토 중 상태 폐기)
--   3. 새 파이프라인: pending(접수) → approved(승인) → in_production(생산)
--                     → shipping_ready(출고) → completed(완료) (+ rejected)

BEGIN;

-- 1. shipped_at 컬럼 추가
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipped_at VARCHAR DEFAULT '';

-- 2. 기존 reviewing row 를 pending 으로 롤백 (이력 보존 차원)
UPDATE orders SET status = 'pending' WHERE status = 'reviewing';

COMMIT;

-- 검증
SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status;
