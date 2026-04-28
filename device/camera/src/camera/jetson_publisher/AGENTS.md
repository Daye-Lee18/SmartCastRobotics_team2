<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# jetson_publisher

Jetson Orin NX 엣지 퍼블리셔 — C920 카메라 프레임 gRPC 스트리밍 + ESP32 Serial 브릿지.

## Key Files

| File | Description |
|------|-------------|
| `publisher.py` | Main image publisher — C920 capture → gRPC streaming to Management Service |
| `esp_bridge.py` | ESP32 Serial bridge (115200 baud) with exponential backoff + 32-event buffer |
| `command_subscriber.py` | Conveyor command subscriber |
| `run_bridge_standalone.py` | Standalone bridge runner (no camera) |
| `deploy.py` / `deploy.sh` | Remote deployment to Jetson via SSH/SCP |
| `requirements.txt` | Jetson dependencies |
| `env.example` | Environment variable template |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `generated/` | Protobuf generated code (management_pb2.py, _grpc.py) |
| `systemd/` | systemd service unit for auto-start |
| `tests/` | ESP bridge unit tests |

## For AI Agents

### Working In This Directory
- `python publisher.py` — start camera + gRPC streaming
- `python esp_bridge.py` — standalone ESP32 serial bridge
- Proto 재생성: `python -m grpc_tools.protoc` (grpcio-tools 1.59.5 고정)
- **중요**: Mac protoc ≠ Jetson protobuf 버전 — Jetson에서 재생성 필수

### Testing Requirements
- `cd jetson_publisher && python -m pytest tests/`

### Common Patterns
- gRPC client streaming for camera frames (ImagePublisherService/PublishFrames)
- Serial relay for ESP32 (conveyor commands, handoff ack, RFID scan)
- Exponential backoff 1~60s for serial reconnection
- systemd unit for Jetson 자동 시작

## Dependencies

### Internal
- `backend/management/proto/management.proto` — proto 소스

### External
- grpcio, grpcio-tools 1.59.5, protobuf 4.25.9
- opencv-python, pyserial
