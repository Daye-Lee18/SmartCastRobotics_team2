-- orders.notes 컬럼 제거 (비고 기능 삭제)
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_drop_notes_column.sql
-- 2026-04-09, 멱등 실행 가능
--
-- ⚠️ 데이터 손실: 기존 notes 컬럼의 모든 값이 영구 삭제됩니다.
--    git 커밋 메시지에 삭제 직전 값 백업이 기록되어 있으니 필요 시 복원 참고.

BEGIN;

ALTER TABLE orders DROP COLUMN IF EXISTS notes;

COMMIT;
