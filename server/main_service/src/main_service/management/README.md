# Management Service (gRPC :50051)

V6 아키텍처의 공장 관제 핵심. FastAPI(Interface Service)와 **별도 프로세스**로 동작하며, Factory Operator PC(PyQt)가 직접 gRPC 로 호출한다.

## 왜 분리했나

- Interface Service 장애 시에도 공장 가동 지속 (SPOF 제거)
- Interface Service AWS 이관 시 현장 PC 설정 변경 없이 공장 운영 유지

상세 설계: [`docs/management_service_design.md`](../../docs/management_service_design.md)

## 빠른 시작

```bash
cd backend/management
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
make proto        # protoc 실행
make run          # server.py 실행 (:50051)
```

## 테스트

```bash
source venv/bin/activate
pytest tests/ --cov=services --cov-report=term-missing
```

현재 커버리지 (2026-04-14 베이스라인):
- traffic_manager.py: 97% (Phase 6 완전 검증)
- adapters/__init__.py: 93% (V6 라우터 매트릭스)
- 전체 services/: 32%

미테스트 모듈 (향후 보강):
- task_manager (DB fixture 필요), execution_monitor (mock+thread)
- mqtt_adapter (broker mock), ros2_adapter (rclpy stub)
- image_sink, task_allocator, robot_executor

## 포함 모듈

| 파일 | 역할 | 상태 |
|---|---|---|
| `server.py` | gRPC 서버 진입점 | 스켈레톤 |
| `proto/management.proto` | API 계약 | 초안 확정 |
| `services/task_manager.py` | 주문 → Task DAG 분해 | 스켈레톤 |
| `services/task_allocator.py` | 로봇 배정 스코어링 | 스켈레톤 |
| `services/traffic_manager.py` | AMR 경로 계획 (Waypoint+Dijkstra+Backtrack Yield) | ✅ Phase 6 완료 |
| `services/robot_executor.py` | ROS2/MQTT 지령 | 스켈레톤 |
| `services/execution_monitor.py` | 감시·이벤트 스트림 | 스켈레톤 |

## 환경 변수

| 변수 | 기본값 | 용도 |
|---|---|---|
| `MANAGEMENT_GRPC_HOST` | `0.0.0.0` | gRPC 바인딩 주소 |
| `MANAGEMENT_GRPC_PORT` | `50051` | gRPC 포트 |
| `MGMT_GRPC_TLS_ENABLED` | `0` | **★ V6 S-001: 1 이면 mTLS 활성** |
| `MGMT_TLS_CERT_DIR` | `./certs` | cert 디렉터리 |
| `MGMT_TLS_SERVER_KEY` | `./certs/server.key` | 서버 private key |
| `MGMT_TLS_SERVER_CRT` | `./certs/server.crt` | 서버 cert |
| `MGMT_TLS_CA_CRT` | `./certs/ca.crt` | CA cert (클라이언트 검증) |
| `MGMT_TLS_REQUIRE_CLIENT_CERT` | `1` | 1=mTLS, 0=server-only TLS |
| ~~`MGMT_MQTT_*`~~ | — | **Phase D (2026-04-20) 에서 제거**. ESP32 경로는 Jetson Serial 경유(`WatchConveyorCommands` gRPC stream → Jetson → /dev/ttyUSB0) 로 통일됨. |
| `MGMT_ADAPTIVE_POLLING` | `1` | **★ V6 P-001: ExecutionMonitor 적응형 polling** |
| `MGMT_POLL_QUIET_CYCLES` | `5` | quiet 사이클 N건 누적 시 backoff |
| `MGMT_POLL_BACKOFF_FACTOR` | `2.0` | backoff 시 interval 곱셈 |
| `MGMT_MAX_POLL_INTERVAL_SEC` | `8.0` | adaptive interval 상한 |
| `MGMT_AI_HOST` | (미설정) | **★ V6 AI Server (Phase 1 SSH 업로드): 호스트 (예: `100.66.177.119`)** |
| `MGMT_AI_USER` | (미설정) | AI Server 사용자명 (예: `team2`) |
| `MGMT_AI_PORT` | `22` | SSH 포트 |
| `MGMT_AI_PASS` | (미설정) | SSH 비밀번호 — **env 전용, 커밋 금지** |
| `MGMT_AI_SSH_KEY` | (미설정) | SSH private key 경로 (password 대신 권장) |
| `MGMT_AI_REMOTE_DIR` | `/home/team2/datasets/inspection` | 업로드 베이스 디렉터리 |
| `MGMT_JETSON_HOST` | (미설정) | **★ V6 Image Publishing Service (Jetson Orin NX 16GB) 호스트 (예: `100.77.62.67`)** |
| `MGMT_JETSON_USER` | (미설정) | Jetson 사용자명 (예: `jetson`) |
| `MGMT_JETSON_PORT` | `22` | SSH 포트 |
| `MGMT_JETSON_PASS` | (미설정) | SSH 비밀번호 — **env 전용, 커밋 금지** |
| `MGMT_JETSON_SSH_KEY` | (미설정) | SSH private key 경로 (password 대신 권장) |
| `MGMT_IMAGE_SPOOL_DIR` | `/tmp/casting-image-spool` | 로컬 스풀 (IP 진입 스냅샷) |
| `MGMT_IMAGE_BATCH_SEC` | `30` | image_forwarder 배치 업로드 주기(초) |
| `MGMT_IMAGE_BATCH_MAX` | `50` | 1회 flush 최대 파일 수 |
| `MGMT_IMAGE_SPOOL_MAX_FILES` | `5000` | 스풀 보관 한도 (초과 시 oldest drop) |
| `MGMT_IP_CAMERA_ID` | `CAM-INSP-01` | IP 진입 시 스냅샷 대상 카메라 ID |
| `FMS_AUTOPLAY` | `0` | **★ V6 Phase B (2026-04-20 Interface→Management 이관):** 1 이면 자동 진행 시퀀서 daemon thread 기동. 실기 연동 시 0 권장 |
| `FMS_ERROR_RATE` | `0.0` | 시퀀서 오류 주입 확률 (0.0~1.0). 데모 시나리오용 |
| `FMS_ROS2` | `0` | **Deprecated** — `MGMT_ROS2_ENABLED` 로 대체됨 (하위 호환 유지) |

## MQTT 인증 설정 (운영 환경 권장)

```bash
# 1) mosquitto 인증 설정 (한 번만)
bash scripts/setup_mosquitto_auth.sh
# → backend/management/mosquitto/{mosquitto.conf, passwd} 생성
# → 비밀번호 1회 출력 (별도 보관)

# 2) mosquitto 재시작 (인증 모드)
pkill -f mosquitto
mosquitto -c backend/management/mosquitto/mosquitto.conf -d

# 3) Mgmt 서버 인증 환경변수
export MGMT_MQTT_USER=casting
export MGMT_MQTT_PASS='<발급받은-비밀번호>'
python server.py

# 4) ESP32 펌웨어 동기화 (PubSubClient.connect 에 user/pass 추가)
```

검증:
- 익명 publish → `Connection Refused: not authorised`
- 인증 publish → 정상

## AI Server 연동 (Phase 1: 검사 이미지 SSH 업로드)

AI Server (100.66.177.119, Tailscale) 로 검사 카메라 이미지를 전송해 학습 데이터셋을 구축한다.

### 옵션 A — SSH 키 (권장)

```bash
# 1) 키 생성 (한 번만, passphrase 비움)
ssh-keygen -t ed25519 -f ~/.ssh/ai_server_team2 -N ""

# 2) AI Server 에 공개키 등록
ssh-copy-id -i ~/.ssh/ai_server_team2.pub team2@100.66.177.119

# 3) 환경변수
export MGMT_AI_HOST=100.66.177.119
export MGMT_AI_USER=team2
export MGMT_AI_SSH_KEY=~/.ssh/ai_server_team2
```

### 옵션 B — 비밀번호 (env 전용, 키 등록 불가 시)

```bash
export MGMT_AI_HOST=100.66.177.119
export MGMT_AI_USER=team2
export MGMT_AI_PASS='<비밀번호>'      # ★ git 커밋 금지 (.gitignore 확인)
```

### 사용 예시

```python
from services.ai_client import AIUploader, AIServerConfig

uploader = AIUploader(AIServerConfig.from_env())
if uploader.enabled and uploader.health_check():
    uploader.upload_image(
        local_path="/tmp/frame_cam01_001.jpg",
        remote_subdir="CAM-01/2026-04-15",
    )
```

Phase 2 (추후): AI Server 추론 gRPC 엔드포인트 확정 후 별도 client 추가 예정.

## Jetson Orin NX (Image Publishing Service) 접속

V6 아키텍처에서 Jetson Orin NX 16GB 가 검사 카메라 프레임을 gRPC client streaming(`ImagePublisherService/PublishFrames`)으로 Management Server(:50051)에 push 한다. 서버가 클라이언트가 아니므로 **런타임에 Jetson 으로 호출할 일은 없음**. 아래 SSH 변수는 다음 용도에만 사용된다:

- 원격 배포 (scp, rsync 로 publisher 코드/설정 업데이트)
- 헬스체크·로그 수집
- 부팅 시 자동 기동 스크립트 등록

### 설정 (AI Server 와 동일한 env 패턴)

```bash
# 옵션 A — SSH 키 (권장)
ssh-keygen -t ed25519 -f ~/.ssh/jetson_orin -N ""
ssh-copy-id -i ~/.ssh/jetson_orin.pub jetson@100.77.62.67
export MGMT_JETSON_HOST=100.77.62.67
export MGMT_JETSON_USER=jetson
export MGMT_JETSON_SSH_KEY=~/.ssh/jetson_orin

# 옵션 B — 비밀번호 (env 전용)
export MGMT_JETSON_HOST=100.77.62.67
export MGMT_JETSON_USER=jetson
export MGMT_JETSON_PASS='<비밀번호>'
```

`backend/.env.local` 에 슬롯이 준비되어 있으며, `.gitignore` 로 보호된다.

## mTLS 설정 (운영 환경 권장)

```bash
# 1) cert 발급 (한 번만)
bash scripts/gen_certs.sh

# 2) 서버 기동 (mTLS)
MGMT_GRPC_TLS_ENABLED=1 python server.py

# 3) PyQt 클라이언트 (mTLS)
cd ../../monitoring
MGMT_GRPC_TLS_ENABLED=1 python main.py
```

cert 디렉터리는 `.gitignore` 처리됨. 운영 배포 시 별도 채널로 cert 전달 (Tailscale, scp, secret manager 등).

DATABASE_URL 은 `backend/.env.local` 에서 자동 로딩 (Interface Service 와 공유).

## V6 통신 채널 (어댑터 라우팅)

`robot_id` prefix 가 단일 진실. `services/adapters/` 하위에서 분기:

| robot_id prefix | 어댑터 | 채널 | 대상 |
|---|---|---|---|
| `AMR-*` | `ros2_adapter` | 🟢 ROS2 DDS | Transport (RPi4) |
| `ARM-*` | `ros2_adapter` | 🟢 ROS2 DDS | Manufacturing/Stacking (RPi5) |
| `CONV-*` | `mqtt_adapter` | 🔵 MQTT | HW Control Service (ESP32 컨베이어) |
| `ESP-*` | `mqtt_adapter` | 🔵 MQTT | HW Control Service (기타 ESP32) |
| 그 외 | `unknown` | (거부) | `unknown_robot_prefix` 에러 |

### MQTT (ESP32) 토픽 표준

| 방향 | Topic | 비고 |
|---|---|---|
| Server → ESP32 | `casting/esp/{robot_id}/cmd` | V6 표준 |
| ESP32 → Server | `casting/esp/{robot_id}/status` | (구독자 별도 구현 예정) |
| ESP32 → Server | `casting/esp/{robot_id}/event` | 이벤트 단발 |
| 레거시 호환 (옵션) | `conveyor/{robot_id}/cmd` | `MGMT_MQTT_LEGACY_CONVEYOR=1` 시 동시 publish |

Payload (JSON):
```json
{ "command": "start", "item_id": 200, "robot_id": "ESP-001",
  "issued_at": "2026-04-14T...", "payload": {"rate_hz": 5} }
```

### ROS2 토픽 / 액션 표준 (배포 시점에 활성)

| 대상 | Endpoint | 메시지 |
|---|---|---|
| AMR navigate | Action `/{robot_id}/navigate_to_pose` | `nav2_msgs/NavigateToPose` |
| ARM move | Action `/{robot_id}/move_to` (custom) | `casting_msgs/MoveTo` (TBD) |
| 일반 명령 | Topic `/{robot_id}/cmd` | `std_msgs/String` (JSON payload) |

활성화: `MGMT_ROS2_ENABLED=1` + Ubuntu 24.04 + ROS2 Jazzy + `rclpy` 설치.

### Image Publishing (Jetson → Server)

| Endpoint | 프로토콜 | 메시지 |
|---|---|---|
| `ImagePublisherService/PublishFrames` | gRPC client streaming :50051 | `ImageFrame` (camera_id, encoding, width, height, data, sequence) |

이미지 수신은 `services/image_sink.py` 의 글로벌 `sink` 가 카메라별 최신 1프레임 보관.

## 클라이언트 예시

PyQt: [`monitoring/app/management_client.py`](../../monitoring/app/management_client.py)

```python
from app.management_client import ManagementClient

c = ManagementClient()                  # :50051
jobs = c.start_production(["ORD-045"])  # 동기 호출
for evt in c.watch_tasks():             # server streaming
    print(evt.task_id, evt.status)
```
