-- orders.email 컬럼 추가 + notes 필드의 "이메일: xxx" 정규식 파싱해서 이관
-- 실행: psql $DATABASE_URL -f backend/scripts/migrate_add_email_to_orders.sql
-- 2026-04-09, 멱등 실행 가능

BEGIN;

-- 1. 컬럼 추가 (이미 존재하면 skip)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS email VARCHAR DEFAULT '';

-- 2. notes 에서 "이메일: xxxxx" 패턴 추출해 email 컬럼에 이관
--    - email 이 이미 채워져 있는 row 는 건너뜀
--    - notes 안의 이메일 다음 개행 또는 쉼표 전까지 캡처
--    - 일치하는 것이 없으면 빈 문자열 유지
UPDATE orders
SET email = (
    SELECT TRIM(matches[1])
    FROM regexp_matches(COALESCE(notes, ''), '이메일:\s*([^\s,;\n]+)', 'i') AS matches
    LIMIT 1
)
WHERE (email IS NULL OR email = '')
  AND notes IS NOT NULL
  AND notes ~ '이메일:';

-- 3. 인덱스 (email 정확 일치 검색용)
CREATE INDEX IF NOT EXISTS ix_orders_email ON orders (LOWER(email));

COMMIT;

-- 검증 쿼리
SELECT id, customer_name, email, notes FROM orders ORDER BY created_at DESC LIMIT 10;
