<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-24 | Updated: 2026-04-24 -->

# backend/management (Management Service)

gRPC Management Service (:50051) — 공장 운영 핵심 로직.
PyQt 모니터링, Jetson 퍼블리셔, ROS2 노드가 직결.

## Key Files

| File | Description |
|------|-------------|
| `server.py` | gRPC server entry — ManagementServicer + ImagePublisherServicer, TLS, FMS sequencer thread |
| `requirements.txt` | gRPC/DB dependencies |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `proto/` | gRPC service definitions (management.proto) |
| `scripts/` | TLS 인증서 생성 스크립트 |
| `services/` | 비즈니스 로직 (22 files) + adapters/ (3 files) |
| `tests/` | Pytest 테스트 스위트 (14 files) |

## For AI Agents

### Working In This Directory
- `python -m backend.management.server` — gRPC 서버 기동
- `bash backend/management/scripts/gen_certs.sh` — TLS 인증서 생성
- Python 3.12 필수

### Testing Requirements
- `python -m pytest backend/management/tests/`
- `--expected-taps` 플래그로 RFID 탭 횟수 제어 가능

### Common Patterns
- FMS Sequencer: asyncio 백그라운드 태스크로 자동 생산 시퀀싱
- AMR State Machine: transport task 상태 전이 추적
- Traffic Manager: Backtrack Yield 충돌 회피
- Adapter 패턴: robot_id prefix로 ROS2/Jetson/JetCobot 어댑터 라우팅
- Event Bridge: Interface ↔ Management 이벤트 전파 (상태 변화만)
- Execution Monitor: 아이템 상태 변화 감지 + SLA 타임아웃 + 알림

## Dependencies

### Internal
- `backend/app/models/` — 공유 SQLAlchemy ORM (smartcast v2)
- `backend/management/proto/management.proto` — API 계약

### External
- grpcio, grpcio-tools 1.59.5, protobuf 4.25.9
- SQLAlchemy, asyncpg, psycopg2
