# Management Service 설계 (V6 아키텍처)

> 초안: 2026-04-14 · 최종 업데이트: 2026-04-21 · 버전: 1.0
> 기반 문서: `docs/fms_architecture_v2.html`, v6 canonical 이미지 (`/Downloads/image-20260420-053600.png`)
> 관련 배포 런북: [`docs/DEPLOY-phase-a-to-c3.md`](./DEPLOY-phase-a-to-c3.md)
> 관련 SPEC: [`docs/SPEC-C2-schema-migration.md`](./SPEC-C2-schema-migration.md), [`.moai/specs/SPEC-AMR-001/spec.md`](../.moai/specs/SPEC-AMR-001/spec.md), [`.moai/specs/SPEC-RFID-001/spec.md`](../.moai/specs/SPEC-RFID-001/spec.md)

---

## 1. 배경 및 결정 사항

### 1.1 문제 진술

기존 casting-factory 아키텍처는 FastAPI 백엔드가 Interface Service + Management Service 역할을 **한 프로세스에서 겸임**하고 있었다. 이 경우 아래 리스크가 존재한다.

| 리스크 | 영향 |
|---|---|
| FastAPI 프로세스 다운 | 공장 가동 즉시 정지 (SPOF) |
| FastAPI AWS 이관 중 | 현장 PyQt 클라이언트 접속 설정 변경 + 공장 일시 정지 |
| UI 프로토콜과 HW 프로토콜의 혼재 | 인증/방화벽/스케일링 정책 수립 난해 |

### 1.2 결정 (2026-04-14 팀 합의)

| 항목 | 결정 |
|---|---|
| Management Service 독립 프로세스화 | **확정** |
| 프로토콜 | **gRPC (Protocol Buffers)** |
| 포트 | **50051** |
| 네트워크 | 공장 내부망 전용 (외부 노출 금지) |
| PyQt (Factory Operator PC) 연결 | **Management Service 직결** (Interface Service 경유 금지) |
| Admin / Customer PC | Interface Service(FastAPI HTTP) 유지 |
| DB | Interface Service 와 동일 DB 공유 (PostgreSQL 16 + TimescaleDB **단독**, SQLite 폴백 제거 2026-04-14) |

### 1.3 배치 구조

```
공장 내부망 (Tailscale / LAN)                  AWS 또는 온프레미스
───────────────────────────                   ──────────────────
Factory Operator PC (PyQt)                    Admin / Customer PC
      │                                             │
      │ gRPC :50051                                 │ HTTPS :443
      ▼                                             ▼
┌──────────────────────────┐              ┌─────────────────────┐
│ Management Service        │ ◀─ gRPC ──▶  │ Interface Service   │
│ (관제 두뇌 · HW 제어)      │              │ (FastAPI · 외부 API) │
└────────┬─────────────────┘              └──────────┬──────────┘
         │                                            │
         └─────────── 공유 DB (PostgreSQL) ───────────┘

         │
         ├─ ROS2 DDS → Manufacturing / Stacking / Transport
         └─ MQTT     → HW Control (ESP32 Conveyor 등)
```

---

## 2. gRPC API 정의

`backend/management/proto/management.proto` 참조.

### 2.1 서비스 메서드 요약 (2026-04-21 기준)

| RPC | 유형 | 용도 | 소비자 |
|---|---|---|---|
| `StartProduction` | unary | smartcast v2 단건 발주 → `OrdStat MFG` + `Item` + `EquipTaskTxn` 3건 INSERT. Option A backward-compat (`order_ids` legacy, `ord_id` smartcast) | Interface `/api/production/start` proxy · PyQt schedule |
| `ListItems` | unary | 현재 item 상태 조회 (order/stage 필터) | PyQt 테이블 갱신 |
| `AllocateItem` | unary | 로봇 배정 스코어링 (NotImplementedError · SPEC-C3 이후) | 내부 / 재배정 |
| `PlanRoute` | unary | AMR 경로 계획 (Waypoint + Dijkstra + Backtrack Yield) | 내부 Executor |
| `ExecuteCommand` | unary | ROS2/Jetson-Serial 지령 송출 | 내부 |
| `WatchItems` | **server streaming** | Item 이벤트 실시간 푸시 (stage/robot) | PyQt 실시간 UI |
| `WatchAlerts` | **server streaming** | `alerts` INSERT push (severity 필터) | PyQt 토스트 (WebSocket 단종 대체) |
| `WatchCameraFrames` | **server streaming** | Jetson 카메라 프레임 push (JPEG, condvar 기반) | PyQt 영상 패널 |
| `WatchConveyorCommands` | **server streaming** | Mgmt → Jetson 컨베이어 명령 relay. Jetson 이 Serial(115200) 로 ESP32 에 재전송 (MQTT 대체, Phase D-2) | Jetson `CommandSubscriber` |
| `GetRobotStatus` | unary | AMR/Cobot 실시간 상태 (배터리, 좌표, task_state) | PyQt AMR 패널 |
| `TransitionAmrState` | unary | AMR FSM 외부 전이 (PyQt/RPi/시뮬레이터) | PyQt · 시뮬 |
| `ReportHandoffAck` | unary | SPEC-AMR-001. ESP32 버튼 → Jetson → Mgmt. 대기중 AMR 태스크 FIFO 해제 | Jetson `handoff_bridge` |
| `ReportRfidScan` | unary | SPEC-RFID-001 Wave 2. RC522 → Jetson Serial → Mgmt. `rfid_scan_log` append-only + payload 파싱 + idempotency. item lookup 은 후속 Wave | Jetson Serial 브릿지 |
| `Health` | unary | 헬스체크 | Interface `/api/management/health` · systemd |
| `PublishFrames` (별도 서비스 `ImagePublisherService`) | **client streaming** | Jetson → Mgmt 이미지 업로드 (JPEG sequence) | Jetson image publisher |

### 2.2 주요 메시지

- `StartProductionRequest` — `order_ids[]` (legacy) + `ord_id` (smartcast v2 단건 · Option A)
- `StartProductionResult` — `ord_id`, `item_id`, `equip_task_txn_id`, `message`
- `Item` — smartcast `Item` 1:1 매핑 (`id`, `order_id`, `cur_stage`, `curr_res`, `insp_id`, `mfg_at`)
- `ItemEvent` — 스트리밍 이벤트 (`item_id`, `stage`, `robot_id`, `message`, `at`)
- `AlertEvent` — `alerts` 테이블 row 변환 (`id`, `type`, `severity`, `error_code`, `message`, `equipment_id`, `zone`, `at`)
- `ConveyorCommand` — `robot_id`, `command` (RUN/STOP/PING/STATUS), `payload`, `item_id`, `issued_at`, `issued_by`
- `HandoffAckEvent` / `HandoffAckResponse` — SPEC-AMR-001 인수인계 페어
- `RfidScanEvent` / `RfidScanAck` — SPEC-RFID-001 Wave 2 페어 (`parse_status`: `ok` / `bad_format` / `duplicate`)
- `ImageFrame` / `ImageAck` — 이미지 업로드 스트리밍

---

## 3. 내부 모듈 (6개)

모두 `backend/management/services/` 에 위치.

| 모듈 | 파일 | 상태 (2026-04-21) | 책임 |
|---|---|---|---|
| Task Manager | task_manager.py | ✅ smartcast v2 이관 (SPEC-C2) | `start_production(ord_id)` → `OrdStat MFG` + `Item` + `EquipTaskTxn` 3-INSERT |
| RFID Service | rfid_service.py | 🟡 Wave 2 구현 (SPEC-RFID-001) | `ReportRfidScan` 핸들러. payload regex + `rfid_scan_log` append-only + idempotency. item lookup 제외 |
| Task Allocator | task_allocator.py | 🟢 스켈레톤 (NotImplementedError) | 거리·capability·배터리 스코어링 — 후속 SPEC |
| Traffic Manager | traffic_manager.py | ✅ 구현 완료 (Phase 6) | 8 노드/8 edge Waypoint + Dijkstra + Edge time-window 예약 + Backtrack Yield 3단계 |
| Robot Executor | robot_executor.py | ✅ 어댑터 분리 | `ros2_adapter` (인터페이스 · `MGMT_ROS2_ENABLED=1` 시 rclpy) + Jetson gRPC relay (`WatchConveyorCommands`). MQTT 경로 제거 (Phase D-1) |
| Execution Monitor | execution_monitor.py | ✅ SLA + streaming | 타임아웃·재시도 + `WatchItems` / `WatchAlerts` server-streaming. SLA stage mapping 중 smartcast `cur_stat` 12 라벨 부분 매핑 (비차단) |

---

## 4. 디렉터리 구조

```
backend/
├── app/                          ← Interface Service (기존 FastAPI)
│   ├── main.py
│   ├── routes/
│   ├── models/
│   └── schemas/
│
├── management/                   ← Management Service (신규)
│   ├── server.py                 ← gRPC 서버 진입점
│   ├── proto/
│   │   └── management.proto
│   ├── services/
│   │   ├── task_manager.py
│   │   ├── task_allocator.py
│   │   ├── traffic_manager.py
│   │   ├── robot_executor.py
│   │   └── execution_monitor.py
│   ├── requirements.txt
│   └── Makefile
│
└── casting_factory.db

monitoring/
└── app/
    ├── management_client.py      ← PyQt gRPC client (신규)
    ├── generated/                ← protoc 산출물 (git ignore)
    │   ├── management_pb2.py
    │   └── management_pb2_grpc.py
    ├── api_client.py             ← 기존 HTTP 클라이언트 (WebSocket + 레거시 조회 전용으로 축소)
    └── pages/
```

---

## 5. 실행 방법

### 5.1 Management Service 기동

```bash
cd backend/management
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# proto 컴파일 (management_pb2.py, management_pb2_grpc.py 생성)
make proto

# 실행
MANAGEMENT_GRPC_PORT=50051 python server.py
```

systemd 서비스 파일 예시 (`/etc/systemd/system/casting-management.service`):

```ini
[Unit]
Description=Casting Factory Management Service (gRPC)
After=network.target

[Service]
WorkingDirectory=/opt/casting-factory/backend/management
ExecStart=/opt/casting-factory/backend/management/venv/bin/python server.py
Environment="MANAGEMENT_GRPC_PORT=50051"
Environment="MANAGEMENT_DB_URL=postgresql+psycopg://..."
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 5.2 PyQt 클라이언트 측

```bash
cd monitoring
source venv/bin/activate

# 서버 쪽 proto 를 공유 (symlink 또는 복사) 후 컴파일
mkdir -p app/generated
python -m grpc_tools.protoc \
  -I ../backend/management/proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  ../backend/management/proto/management.proto

MANAGEMENT_GRPC_HOST=localhost python main.py
```

---

## 6. PyQt 쪽 이관 계획

### 6.1 기존 api_client.py 재정의 (2026-04-21 상태)

| 기능 | 이전 | 현재 | 비고 |
|---|---|---|---|
| 주문 조회 | HTTP GET | HTTP GET (Interface 유지) | 관리자/고객 포털과 공유, Mgmt 이관 불필요 |
| 승인 주문 풀 | HTTP GET /api/production/schedule/approved | HTTP GET (PyQt legacy) | Phase A-2 에서 Mgmt 이관 예정 |
| 생산 시작 | HTTP POST /api/production/schedule/start | **Management gRPC `StartProduction`** | SPEC-C2 Option A. PyQt schedule 페이지 `order_ids[]` + Interface proxy `ord_id` |
| 실시간 Item 상태 | WebSocket /ws/dashboard | **Management gRPC `WatchItems` streaming** | Phase A |
| 실시간 Alert | WebSocket /ws/dashboard | **Management gRPC `WatchAlerts` streaming** | Phase 8 + Phase A |
| 실시간 카메라 | WebSocket /ws/camera | **Management gRPC `WatchCameraFrames` streaming** | Stage B |
| 품질 검사 이력 | HTTP GET /api/quality/inspections | HTTP GET (Interface 유지) | 읽기 경로는 Interface 에서 충분 |
| AMR 상태 폴링 | HTTP GET | **Management gRPC `GetRobotStatus`** | Phase A |

> **WebSocket 단종 완료 (Phase 8 + Phase A)**. PyQt `ws_worker` 는 환경변수로 기본 비활성화. `websocket-client` 패키지도 `monitoring/requirements.txt` 에서 제거됨.

### 6.2 QThread + gRPC 통합 패턴

```python
# app/workers/management_worker.py
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from app.management_client import ManagementClient

class TaskStreamWorker(QObject):
    event_received = pyqtSignal(object)  # TaskEvent

    def __init__(self, client: ManagementClient, order_id: str | None):
        super().__init__()
        self._client = client
        self._order_id = order_id

    def run(self):
        for event in self._client.watch_tasks(self._order_id):
            self.event_received.emit(event)
```

---

## 7. Interface Service 쪽 이관 계획 (SPEC-C2 반영)

FastAPI routes 는 **gRPC proxy** 로 축소되었다. 대표 경로:

```python
# backend/app/routes/production.py (SPEC-C2 Option A)
from app.clients.management import ManagementClient, ManagementUnavailable

_PROXY_START_PRODUCTION = os.environ.get(
    "INTERFACE_PROXY_START_PRODUCTION", "0"
) in ("1", "true")  # 모듈 import 시점 고정 (worker 재시작 필요)

@router.post("/start")
def start_production(payload: ProductionStartRequest):
    if not _PROXY_START_PRODUCTION:
        return _legacy_db_path(payload)   # 즉시 롤백용
    try:
        result = ManagementClient.get().start_production(payload.ord_id)
    except ManagementUnavailable as e:
        raise HTTPException(503, f"Management Service unavailable: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "ord_id": result.ord_id,
        "item_id": result.item_id,
        "equip_task_txn_id": result.equip_task_txn_id,
        "message": result.message,
    }
```

Interface Service 자체 로직은 **인증 / rate-limit / 외부 API 게이트웨이 + read-heavy 조회 응답** 에 집중. Write 경로는 Management 가 단일 책임.

---

## 8. 마이그레이션 단계별 로드맵

| 단계 | 기간 | 산출 | 완료 조건 |
|---|---|---|---|
| **Phase 0 — 스캐폴드 (완료)** | 0.5일 | 본 문서 + proto + 스켈레톤 | 디렉터리 생성, proto 정의 |
| **Phase 1 — gRPC 서버 기동** | 1일 | Health RPC + Task Manager 기본 | `grpc_health_probe` 성공 |
| **Phase 2 — StartProduction 이전** | 1일 | `task_manager.start_production` 실구현 | PyQt → gRPC 로 생산 개시 성공 |
| **Phase 3 — WatchTasks 스트리밍** | 1일 | `execution_monitor.stream` 실구현 | PyQt 가 실시간 이벤트 수신 |
| **Phase 4 — Interface proxy** | 0.5일 | routes/schedule.py 가 gRPC client 로 동작 | Admin/Customer 영향 없음 확인 |
| **Phase 5 — Robot Executor + HW 연동** | ✅ 어댑터 분리 완료 (2026-04-14) | ros2_adapter (인터페이스) + mqtt_adapter (ESP32) + ImagePublisherService (gRPC streaming) | V6 통신 행렬 부합, RPi 배포 시 ROS2 활성화만 남음 |
| **Phase 6 — Traffic Manager 구현** | ✅ 완료 (2026-04-14) | 8 노드 / 8 edge Waypoint + Dijkstra + Edge time-window 예약 + Backtrack Yield (3단계 우회→대기) | 단위 테스트 5종 + gRPC PlanRoute E2E 통과 |
| **Phase 7 — Execution Monitor 고도화** | ✅ 완료 | 타임아웃·재시도·alerts 통합 | 장애 테스트 통과 |
| **Phase 8 — WebSocket 단종** | ✅ 완료 (2026-04-14) | WatchAlerts gRPC streaming 추가 + PyQt AlertStreamWorker + ws_worker 환경변수 비활성화 | DB INSERT → PyQt 토스트 1초 내 푸시 검증 |
| **Phase A — PyQt WebSocket 경로 제거** | ✅ 완료 (2026-04-20, `f27e3ea`) | monitoring canonical 정합 | PyQt 상태바 `gRPC: ready` 고정, WS 표기 제거 |
| **Phase B — ROS2 publisher Interface→Management 이관** | ✅ 완료 (`a80e53f`) | fms publisher 가 Mgmt 에서 기동 | Mgmt 가 ROS2 DDS 퍼블리시의 단일 주체 |
| **Phase C-1 — Interface → Management gRPC client + Health proxy** | ✅ 완료 (`b3b185e`) | `backend/app/clients/management.py` 싱글톤 + `/api/management/health` | 왕복 확인 명령 가능 |
| **Phase D-1 — MQTT 제거 · Mgmt→Jetson gRPC relay 스켈레톤** | ✅ 완료 (`fb5536f`) | paho-mqtt 의존성 제거 | ESP32 명령 채널이 gRPC(TCP) 로 단일화 |
| **Phase D-2 — Jetson subscriber + EspBridge outbound relay** | ✅ 완료 (`24e79ad`) | `WatchConveyorCommands` 구독 + Serial(115200) 재전송 | Mgmt → gRPC → Jetson → Serial → ESP32 체인 동작 |
| **SPEC-C2 — smartcast TaskManager + Interface proxy (Option A)** | ✅ 머지 (`476e86b`) | `INTERFACE_PROXY_START_PRODUCTION` flag · `StartProductionRequest { repeated order_ids; int32 ord_id }` backward-compat | 응답 shape 유지, 프론트엔드 무변경 |
| **SPEC-C3 — Management 기동 복구 + smartcast Item 매핑** | ✅ 머지 (`1c33ae4`) | `models_mgmt.py` 에 Alert/HandoffAck/TransportTask/RfidScanLog 선별 import | Mgmt/Interface ORM 공존, legacy import 충돌 회피 |
| **SPEC-RFID-001 Wave 2 — RFID append-only 로그** | 🟡 진행 | `rfid_scan_log` 테이블 + `ReportRfidScan` RPC + `RfidService` (파싱/idempotency) | item lookup / binding 은 Wave 3 이후 |
| **Phase A-2 — PyQt FastAPI legacy 호출 제거** | ⏳ 예정 | `CASTING_API_HOST` 환경변수 일소, Mgmt gRPC 단일 채널 | — |

**총 경과**: Phase 0~8 + Phase A~D + SPEC-C2/C3 완료 (2026-04-20 머지 대기 `feat/v6-phase-c2-proxy`). SPEC-RFID-001 Wave 2 진행 중.

---

## 9. 보안 / 운영 고려사항

| 항목 | 정책 |
|---|---|
| 네트워크 | 공장 내부망 전용. 외부 방화벽 50051 차단 |
| 인증 | 현 시점 insecure channel. 운영 전환 시 mTLS 도입 권장 |
| 로깅 | Python logging → journald → 집계 (loki/ELK) |
| 메트릭 | grpc-prometheus exporter (옵션) |
| 재기동 | systemd `Restart=on-failure`, 헬스체크 5초 주기 |
| 배포 | Interface Service 는 CD, Management Service 는 현장 수동 배포 (리스크 관리) |

---

## 10. 미결정 사항 (후속 논의 필요)

- [ ] Management 와 Interface 의 공유 DB 접근에서 **쓰기 경합 처리** 방식 (advisory lock vs. 서비스 책임 분리 · SPEC-C4 후보)
- [ ] PyQt 측 gRPC 연결 실패 시 **오프라인 모드** 동작 범위
- [ ] `ExecuteCommand.payload` 에 담을 JSON/Proto 스키마의 구체화
- [ ] ROS2 브릿지의 **세션 재사용** 전략 (rclpy 컨텍스트 공유)
- [ ] AI Service 가 생기면 Task Allocator 가 gRPC 로 호출할지, 내부 호출로 임베드할지
- [ ] `sys.path.insert(_BACKEND_DIR)` hack 중립화 → `backend/common/` 공유 패키지 (SPEC-C4 후보)
- [ ] SPEC-RFID-001 Wave 3: `item.rfid_tag` 컬럼 추가 + `rfid_scan_log.item_id` binding
- [ ] SPEC-RFID-001 Wave 4: `WatchRfidScans` server streaming → PyQt 실시간 스캔 UI
- [ ] pytest-postgresql fixture 구성으로 `/api/production/start` proxy 통합 테스트 CI 통과

### 해결된 결정 (2026-04-14 이후)

- ✅ HW 통신 채널 단일화: AMR/ARM → ROS2 DDS · CONV/ESP → Mgmt gRPC relay (MQTT 경로 제거, Phase D-1)
- ✅ DB 단일화: PostgreSQL 16 + TimescaleDB 단독. SQLite 폴백 완전 제거 (2026-04-14)
- ✅ mTLS 도입: `MGMT_GRPC_TLS_ENABLED` flag + `certs/` 디렉터리 (S-001 권장조치)
- ✅ WebSocket 단종: `WatchAlerts` gRPC streaming 으로 이관 (Phase 8)

---

## 11. 변경 이력

| 일자 | 내용 |
|---|---|
| 2026-04-14 | 초안 작성 (gRPC:50051 결정 반영) |
| 2026-04-14 | Phase 5/6/8 완료 + SPEC-RC522/DB-V2 머지 |
| 2026-04-20 | V6 canonical Phase A–D + SPEC-C2 (Option A backward-compat) + SPEC-C3 머지 대기 브랜치 |
| 2026-04-21 | **문서 개정**: 서비스 메서드 목록/내부 모듈 상태/마이그레이션 로드맵 · SPEC-AMR-001, SPEC-RFID-001 반영 |
