<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/management/tests

Management Service 테스트 스위트 — 14개 테스트 파일.

## Key Files

| File | Description |
|------|-------------|
| `conftest.py` | Pytest 설정 및 공유 픽스처 |
| `test_task_manager_smartcast.py` | Task Manager smartcast v2 테스트 |
| `test_task_allocator_summary.py` | Task Allocator 할당 스코어링 테스트 |
| `test_traffic_manager.py` | Traffic Manager 라우팅/충돌 회피 테스트 |
| `test_adapters_router.py` | 어댑터 라우팅 분기 테스트 |
| `test_amr_state_machine.py` | AMR 상태 기계 전이 테스트 |
| `test_rfid_service.py` | RFID/Barcode 서비스 테스트 |
| `test_event_bridge.py` | Event Bridge 이벤트 전파 테스트 |
| `test_image_forwarder.py` | 이미지 포워딩 테스트 |
| `test_ai_client.py` | AI Server 클라이언트 테스트 |
| `test_order_pipeline_4seq.py` | 4-시퀀스 오더 파이프라인 통합 테스트 |
| `test_interface_service_client.py` | Interface Service HTTP 클라이언트 테스트 |
| `test_management_service_client.py` | Management gRPC 클라이언트 테스트 |

## For AI Agents

### Working In This Directory
- `python -m pytest backend/management/tests/ -v`
- `--expected-taps` 플래그로 RFID 탭 횟수 제어
- conftest.py에서 gRPC mock, DB mock, test client 제공
