<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/management/proto

gRPC 서비스 정의 — ManagementService + ImagePublisherService.

## Key Files

| File | Description |
|------|-------------|
| `management.proto` | gRPC 서비스/메시지 정의 (전체 API 계약) |

## For AI Agents

### Working In This Directory
- 이 파일이 **protobuf 소스 오브 트루스**
- 수정 후 3곳에서 재생성 필요:
  1. `backend/management/` — grpcio-tools로 Python stub
  2. `monitoring/app/generated/` — `bash monitoring/scripts/gen_proto.sh`
  3. `jetson_publisher/generated/` — Jetson에서 grpcio-tools로 재생성 (Mac protoc 버전 불일치)
- **절대 protoc 직접 호출 금지** — gen_proto.sh 사용 (relative import sed 패치 포함)

### Key Services Defined
- `ManagementService` — WatchConveyorCommands, ReportRfidScan, ReportHandoffAck, TransitionAmrState, etc.
- `ImagePublisherService` — PublishFrames (client streaming)

### Common Patterns
- 모든 HW 통신 경로가 이 proto에 정의됨
- 새 RPC 추가 시 3곳 재생성 + server.py 핸들러 + client stub 업데이트
