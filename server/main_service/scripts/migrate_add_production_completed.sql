-- 주문 상태 파이프라인에 production_completed 단계 추가
-- 2026-04-09, 멱등 실행 가능
--
-- 배경:
--   orders.status 는 String 컬럼이라 enum 제약이 없어 스키마 변경은 불필요.
--   그러나 새 값 'production_completed' 의 존재를 DB 레벨에서 알리고,
--   웹 테스트용으로 기존 in_production 주문 중 1건을 production_completed 로 이동한다.
--
-- 파이프라인:
--   pending → approved → in_production → production_completed → shipping_ready → completed
--   (+ rejected 예외 분기)
--
-- 전환 주체:
--   pending → approved          : 관리자 (관리자 '승인' 버튼)
--   approved → in_production    : 관리자 (관리자 '생산 승인' 버튼)
--   in_production → production_completed : **PyQt5 공정 시스템** (웹에서는 전환 불가)
--   production_completed → shipping_ready : 관리자 ('출고 처리' 버튼, shipped_at 자동 기록)
--   shipping_ready → completed  : 관리자 ('출고 완료' 버튼)

BEGIN;

-- 기존 in_production 주문 중 가장 오래된 1건을 production_completed 로 업데이트
-- (웹에서 '출고 처리' 버튼을 테스트하기 위한 샘플 데이터)
-- 주의: updated_at 은 Pydantic datetime 이 파싱할 수 있는 ISO-8601 포맷이어야 함.
--       NOW()::text 는 "2026-04-09 18:29:49+09" 같은 공백 구분 포맷을 생성해 파싱 실패하므로
--       to_char 로 'YYYY-MM-DD"T"HH24:MI:SS.USOF:00' 형식을 강제한다.
UPDATE orders
SET status = 'production_completed',
    updated_at = to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.USOF:00')
WHERE id = (
    SELECT id FROM orders
    WHERE status = 'in_production'
    ORDER BY created_at ASC
    LIMIT 1
);

COMMIT;

-- 검증: 상태 분포
SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status;
