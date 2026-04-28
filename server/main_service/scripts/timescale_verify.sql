-- =============================================
-- TimescaleDB 사후 검증 SQL
-- DBA 가 backend/scripts/timescale_install_guide.md 의 모든 단계를 완료한 뒤
-- team2 role 로 실행하여 hypertable + continuous aggregate 가 정상 동작하는지 확인.
-- =============================================

\echo '=== 1. extension 설치 확인 ==='
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'timescaledb';

\echo ''
\echo '=== 2. hypertable 목록 (4건 예상: equip_stat / equip_err_log / trans_err_log / ord_log) ==='
SELECT hypertable_name, num_chunks, compression_enabled
FROM timescaledb_information.hypertables
WHERE hypertable_schema = 'smartcast'
ORDER BY hypertable_name;

\echo ''
\echo '=== 3. continuous aggregate 목록 (1건 예상: item_hourly) ==='
SELECT view_name, materialization_hypertable_name, view_definition IS NOT NULL AS has_def
FROM timescaledb_information.continuous_aggregates
WHERE view_schema = 'smartcast';

\echo ''
\echo '=== 4. 압축 정책 / 보존 정책 ==='
SELECT j.application_name, j.schedule_interval, j.config
FROM timescaledb_information.jobs j
WHERE j.application_name LIKE 'Compression%' OR j.application_name LIKE 'Retention%'
ORDER BY j.application_name;

\echo ''
\echo '=== 5. backend 의 has_timescaledb() 와 동일 쿼리 ==='
SELECT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
) AS detected_by_backend;

\echo ''
\echo '=== 6. continuous aggregate 즉시 refresh (테스트 데이터 반영) ==='
-- DBA 작업 후 첫 실행 시 manual refresh 필요. 이후엔 자동 정책이 처리.
CALL refresh_continuous_aggregate('smartcast.item_hourly', NULL, NULL);

\echo ''
\echo '=== 7. /api/production/hourly 와 동일 쿼리 (TimescaleDB 경로) ==='
SELECT bucket, produced
FROM smartcast.item_hourly
WHERE bucket >= now() - INTERVAL '24 hours'
ORDER BY bucket;

\echo ''
\echo '=== 8. (대조) date_trunc 폴백 결과와 동일해야 함 ==='
SELECT date_trunc('hour', updated_at) AS bucket, COUNT(*) AS produced
FROM smartcast.item
WHERE updated_at >= now() - INTERVAL '24 hours'
GROUP BY bucket
ORDER BY bucket;

\echo ''
\echo '=== 검증 완료 ==='
\echo '백엔드 재시작 후 /api/dashboard/stats 응답에 timescaledb_enabled=true 확인 필요.'
\echo '재시작: PIDS=$(lsof -ti :8000); [ -n "$PIDS" ] && kill $PIDS; uvicorn ...'
