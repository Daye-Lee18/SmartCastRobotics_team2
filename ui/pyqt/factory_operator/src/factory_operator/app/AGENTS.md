<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# monitoring/app

PyQt5 관제 애플리케이션 핵심 코드 — 메인 윈도우, 페이지, 위젯, 워커.

## Key Files

| File | Description |
|------|-------------|
| `main_window.py` | QMainWindow — 사이드바 내비게이션 + QStackedWidget 페이지 스택 (진입점) |
| `api_client.py` | REST API client for Interface Service |
| `management_client.py` | gRPC Management Service 클라이언트 (싱글톤) |
| `mock_data.py` | 개발용 mock 데이터 생성기 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `pages/` | 페이지 위젯 (dashboard, operations, map, production, schedule, quality, logistics) |
| `widgets/` | 재사용 UI 위젯 (AMR card, camera view, charts, gauges, conveyor card...) |
| `workers/` | QThread 백그라운드 워커 (alert stream, AMR status, camera frame, item stream) |
| `generated/` | Protobuf 생성 코드 (management_pb2.py, _grpc.py) |

## For AI Agents

### Working In This Directory
- `main_window.py` 에서 모든 페이지 로드 — 새 페이지 추가 시 여기에 등록
- `workers/` 는 QThread — closeEvent에서 정리 누락 시 exit 134 (SIGABRT)
- `generated/` 재생성: `bash monitoring/scripts/gen_proto.sh`

### Testing Requirements
- `cd monitoring && python -m pytest`

### Common Patterns
- Page = QWidget 서브클래스, main_window의 page_stack에 추가
- Worker = QThread 서브클래스, gRPC streaming 또는 REST polling
- Widget = 재사용 가능한 UI 컴포넌트 (AMR, 컨베이어, 차트)

## Dependencies

### Internal
- `backend/management/` — gRPC 서버
- `backend/app/` — REST 서버 (보조)

### External
- PyQt5, grpcio, protobuf
