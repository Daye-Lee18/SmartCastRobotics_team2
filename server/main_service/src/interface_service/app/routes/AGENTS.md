<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/app/routes

FastAPI REST 라우트 핸들러 — smartcast v2 엔드포인트.

## Key Files

| File | Description |
|------|-------------|
| `dashboard.py` | 대시보드 통계 집계 (smartcast 스키마) |
| `orders.py` | 주문 관리 (ord, ord_detail 테이블) |
| `production.py` | 생산 모니터링 (equip_stat, equip_task_txn) |
| `quality.py` | 품질 검사 (insp_task_txn, insp_res) |
| `logistics.py` | 물류/운송 태스크 + 창고 관리 |
| `schedule.py` | 생산 스케줄링 및 관리 |
| `alerts.py` | 설비/운송 에러 로그 (equip_err_log, trans_err_log) |
| `management.py` | Management Service gRPC 프록시 (Phase C-1 health check) |
| `websocket.py` | WebSocket 실시간 업데이트 |
| `debug.py` | 개발 전용 디버그 엔드포인트 (APP_ENV=development) |

## For AI Agents

### Working In This Directory
- 각 파일이 FastAPI `APIRouter` 인스턴스
- `main.py`에서 prefix와 함께 등록
- smartcast v2 스키마 기반
- 새 엔드포인트 추가 시 routes/ + schemas/ 동시 업데이트

### Common Patterns
- Pydantic Request/Response 스키마로 입력/출력 검증
- async def 핸들러 + SQLAlchemy async session
- `management.py`는 gRPC 프록시 — 직접 DB 접근 없음
