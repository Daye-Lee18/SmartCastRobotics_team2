# main_service 마이그레이션 가이드

팀장이 만든 sample 8 파일을 팀원이 나눠서 직접 작성하는 작업의 reference.

## 배경

`main_service/management/server.py` 는 V6 Management Service 의 monolithic 구현
(844 LOC). 팀장의 8 파일 디자인은 이 monolithic 의 책임을 다음처럼 분할한다.
팀원이 각 sample 파일을 작성할 때 아래 reference 코드 위치를 참고하면 빠르게
시작할 수 있다.

## 작업 분담 + reference 매핑

| 담당 | sample 파일 (작성 자리) | reference (참고 코드) | 책임 |
|------|------------------------|----------------------|------|
| A | `src/main_service/task_manager.py` | `management/services/task_manager.py` 통째 | 단건 생산 개시, MM/POUR/DM/ToINSP equip_task_txn 진행 체인, 발주 → item 변환 (SPEC-C2) |
| B | `src/main_service/task_allocator.py` | `management/services/task_allocator.py` 통째 | 거리·capability·배터리 기반 로봇 배정, AMR pickup with_for_update skip_locked |
| C | `src/main_service/traffic_manager.py` | `management/services/traffic_manager.py` 통째 | AMR 경로 계획 + 충돌 회피 (Backtrack Yield 알고리즘) |
| D | `src/main_service/event_bridge.py` | `management/services/event_bridge.py` 통째 | gRPC ↔ DB 이벤트 브리지 (handoff/RFID/TOF1/TOF2 ingest) |
| E | `src/main_service/task_executor.py` | `management/services/robot_executor.py` 참고 | robot_id prefix 기반 어댑터 라우터 (RA1/RA2/AMR-001 등 → 실제 어댑터 호출) |
| F | `src/main_service/monitor_agent.py` | `management/services/execution_monitor.py` 참고 | item 상태 변경 감지 + SLA 타임아웃 + alert 발행 |
| G | `src/main_service/robot_adapter.py` | `management/services/adapters/` 폴더 (ROS2/Serial/JetCobot 어댑터들) | 실제 HW 통신 어댑터 layer — ROS2 DDS, Jetson Serial, JetCobot SDK |
| H | `src/main_service/state_manager.py` | `management/services/amr_state_machine.py` + `management/services/fms_sequencer.py` 일부 | AMR 운송 FSM + item.cur_stat 전이 + asyncio 시퀀서 |
| (orchestrator) | `src/main_service/main.py` | `management/server.py` 의 `serve()` 함수 (line 795) + `ManagementServicer` (line 70) + `ImagePublisherServicer` (line 653) | gRPC 서버 부트스트랩, 8 모듈 조립, lifespan 관리 |

## 작업 절차

1. 본인 담당 sample 파일을 빈 상태로 시작 (현재 팀장 stub 그대로).
2. 위 매핑 표의 reference 위치를 읽는다.
3. 자신의 디자인으로 재구현 (단순 복사 X — 인터페이스 정리 + 책임 명확화).
4. 단위 테스트는 `tests/unit/test_<module>.py` 에 작성.
5. 통합 테스트 reference: `management/tests/test_<module>_*.py` 들이 존재 — 인터페이스 합의 후 수정 가능.
6. 모든 sample 8 파일이 완성되면 `main.py` 가 8 모듈을 import 하도록 작성:

```python
# src/main_service/main.py 최종 모습 (참고)
from main_service.task_manager import TaskManager
from main_service.task_allocator import TaskAllocator
from main_service.traffic_manager import TrafficManager
from main_service.event_bridge import EventBridge
from main_service.task_executor import TaskExecutor
from main_service.monitor_agent import MonitorAgent
from main_service.robot_adapter import RobotAdapter
from main_service.state_manager import StateManager

def serve():
    state    = StateManager()
    adapter  = RobotAdapter()
    executor = TaskExecutor(adapter)
    allocator= TaskAllocator()
    traffic  = TrafficManager()
    monitor  = MonitorAgent(state)
    bridge   = EventBridge(state, monitor)
    tasks    = TaskManager(state, allocator, executor, traffic)
    # gRPC server bootstrap …
```

## 마이그레이션 단계 (점진)

| Stage | sample 자리 (`src/main_service/`) | management/server.py 호출 |
|-------|----------------------------------|---------------------------|
| 0 (현재) | 빈 stub | `from main_service.management.server import serve` 로 그대로 동작 |
| 1 | 일부 팀원 완료 | 작성된 모듈은 main.py 에서 import, 미완성은 management/server 폴백 |
| 2 (목표) | 8 모듈 + main.py 완료 | management/server.py 폐기. management/services/ 는 reference 보관 |

## reference 코드 보존 정책

`management/services/` 와 `management/server.py` 는 stage 2 완료까지 **삭제 금지**.
팀원이 자기 모듈을 작성하다 다른 책임 영역의 인터페이스가 필요하면 reference 에서 확인 가능.

## 테스트

reference 테스트 위치: `management/tests/test_*.py`

| reference test | 대응 sample 모듈 |
|---------------|----------------|
| test_task_manager_smartcast.py | task_manager.py |
| test_traffic_manager.py | traffic_manager.py |
| test_event_bridge.py | event_bridge.py |
| test_amr_state_machine.py | state_manager.py |
| test_ordering_service.py + test_order_manager.py | task_manager.py 보조 |
| test_order_pipeline_4seq.py | event_bridge.py 통합 |
| test_rfid_service.py | event_bridge.py 일부 |
| test_image_forwarder.py | (별도, image 파이프라인) |

신규 단위 테스트는 `tests/unit/test_<module>.py` 에 자유롭게 작성.

## 외부 의존성

8 sample 모듈 모두 다음에 의존:

- `management/db_session.py` — SQLAlchemy 세션 팩토리
- `management/management_pb2.py` / `management_pb2_grpc.py` — gRPC 자동 생성
- `management/proto/management.proto` — proto 정의 (Single source of truth)

이들은 stage 2 후에도 유지. proto 변경 시 `python -m grpc_tools.protoc ...` 로 재생성.
