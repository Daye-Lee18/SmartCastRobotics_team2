<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# monitoring/app/pages

PyQt5 페이지 위젯 — 각 탭에 해당하는 화면.

## Key Files

| File | Description |
|------|-------------|
| `dashboard.py` | 대시보드 개요 페이지 |
| `operations.py` | 운영 관리 (패턴, 생산 시작, 후처리, 검사) |
| `map.py` | 팩토리 맵 시각화 페이지 |
| `production.py` | 생산 모니터링 페이지 |
| `schedule.py` | 생산 스케줄 페이지 |
| `quality.py` | 품질 검사 페이지 |
| `logistics.py` | 물류/자재 운송 페이지 |
| `storage.py` | 창고 랙 적재 현황 페이지 |

## For AI Agents

### Common Patterns
- 각 페이지는 QWidget 서브클래스
- `main_window.py`의 page_stack에 addWidget로 등록
- 새 페이지 추가 시 main_window.py에 import + 등록 코드 필요
- gRPC/REST 데이터는 workers/에서 비동기 fetch → 시그널로 UI 업데이트
