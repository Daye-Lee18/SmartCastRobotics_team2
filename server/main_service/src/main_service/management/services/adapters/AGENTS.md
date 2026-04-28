<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/management/services/adapters

로봇 어댑터 — robot_id prefix로 분기되는 HW 통신 레이어.

## Key Files

| File | Description |
|------|-------------|
| `ros2_adapter.py` | ROS2 로봇 어댑터 (DDS topic publish/subscribe, AMR/ARM) |
| `jetson_relay_adapter.py` | Jetson 릴레이 어댑터 (gRPC → ESP32 Serial, 컨베이어) |
| `jetcobot_adapter.py` | JetCobot 로봇 암 어댑터 (pymycobot SSH) |

## For AI Agents

### Working In This Directory
- `robot_executor.py`가 robot_id prefix로 어댑터 선택:
  - `AMR-*` → ros2_adapter
  - `CONV-*` → jetson_relay_adapter
  - `ARM-JETCOBOT-*` → jetcobot_adapter
- 새 로봇 타입 추가 시 adapter 클래스 + robot_executor 분기 로직 업데이트
- ROS2 미설치 시 mock 폴백 동작 (`ROS2_ENABLED=0`)

### Common Patterns
- Adapter 패턴: 공통 인터페이스, robot_id prefix로 다형성
- Mock 폴백: HW 없는 개발 환경에서 정상 동작
- Serial: 115200 baud (v5 컨베이어), 지수 백오프 재연결
