<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# monitoring/app/workers

QThread 백그라운드 워커 — gRPC streaming, REST polling.

## Key Files

| File | Description |
|------|-------------|
| `alert_stream_worker.py` | 알림 스트림 처리 (gRPC/REST) |
| `amr_status_worker.py` | AMR 상태 폴링 (gRPC) |
| `item_stream_worker.py` | 아이템 스트림 처리 |
| `start_production_worker.py` | 생산 시작 명령 워커 (gRPC) |

## For AI Agents

### Common Patterns
- QThread 서브클래싱, `run()` 메서드에 메인 루프
- 시그널(pyqtSignal)로 UI 스레드에 데이터 전달
- **중요**: closeEvent에서 모든 워커 stop/quit/wait 누락 시 exit 134 (SIGABRT)
- 새 워커 추가 시 main_window.py의 closeEvent에 정리 코드 추가 필수
