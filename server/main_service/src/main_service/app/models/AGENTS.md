<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/app/models

SQLAlchemy ORM 모델 — smartcast v2 스키마 + Management 테이블.

## Key Files

| File | Description |
|------|-------------|
| `models.py` | smartcast v2 스키마 27테이블 ORM (Confluence 32342045 v59 기반) |
| `models_mgmt.py` | Management Service 전용 테이블 (TransportTask, HandoffAck, Alert, RfidScanLog) |
| `models_legacy.py` | Legacy mock 데이터 모델 (개발/테스트용) |

## For AI Agents

### Working In This Directory
- **절대 전체 import 금지**: `from models import *` 시 legacy Item/Order가 smartcast와 충돌
- **선별 import**: `from models.models_mgmt import TransportTask, HandoffAck`
- `models.py` = 소스 오브 트루스 (Confluence 스키마와 동기화)
- 새 테이블 추가: smartcast 스키마 → `models.py`, Management 전용 → `models_mgmt.py`

### Common Patterns
- SQLAlchemy declarative_base 공유
- TimescaleDB hypertable: `__table_args__` 에 `timescaledb` 설정
- `models_mgmt.py`는 Management Service에서만 사용 (Interface는 참조 금지)
