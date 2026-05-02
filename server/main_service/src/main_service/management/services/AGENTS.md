<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/management/services

Management Service 비즈니스 로직 — 22개 서비스 모듈 + 3개 어댑터.

## Key Files

| File | Description |
|------|-------------|
| `task_manager.py` | smartcast v2 단일 아이템 생산 시작 (SPEC-C2) |
| `task_allocator.py` | 로봇 할당 스코어링 (거리, 능력, 배터리) |
| `traffic_manager.py` | AMR 경로 계획 + Backtrack Yield 충돌 회피 |
| `robot_executor.py` | 로봇 명령 라우터 — robot_id prefix로 어댑터 디스패치 |
| `execution_monitor.py` | 아이템 상태 변화 감지 + SLA 타임아웃 + 알림 |
| `amr_state_machine.py` | AMR 운송 상태 기계 (transport task 상태 전이) |
| `amr_battery.py` | AMR 배터리 상태 폴링 (ROS2 DDS 또는 SSH 폴백) |
| `rfid_service.py` | RFID/Barcode 스캔 수집 (ReportRfidScan RPC) |
| `command_queue.py` | Management → Jetson 컨베이어 명령 큐 (Phase D) |
| `image_sink.py` | Image Publisher 프레임 수신 (condvar pub/sub) |
| `image_forwarder.py` | 최신 프레임 AI Server 배치 업로드 (SSH/SCP) |
| `ai_client.py` | AI Server SSH 업로드 클라이언트 |
| `ros2_publisher.py` | ROS2 퍼블리셔 (mock 폴백 포함) |
| `event_bridge.py` | Interface ↔ Management 이벤트 전파 컨트랙트 (569줄) |
| `order_manager.py` | Interface 주문 관리 컨트랙트 |
| `ordering_service.py` | Interface 오더링 서비스 컨트랙트 |
| `interface_service_client.py` | HTTP 클라이언트 — Management → Interface 콜백 |
| `management_service_client.py` | 내부 gRPC 클라이언트 래퍼 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `adapters/` | 로봇 어댑터 (ROS2, Jetson Serial, JetCobot) |

## For AI Agents

### Working In This Directory
- `server.py`에서 모든 서비스를 ManagementServicer에 주입
- 새 서비스 추가 시 server.py에도 등록 필요
- 어댑터 패턴: `robot_executor.py`가 robot_id prefix로 분기
- Event Bridge: 상태 변화 전파만 — CRUD/조회/명령은 직접 호출

### Testing Requirements
- `python -m pytest backend/management/tests/` — 14개 테스트 파일

## Dependencies

### Internal
- `smart_cast_db.models` — ORM 모델 export
- `backend/management/proto/` — gRPC 메시지 정의
