# 배포 런북: V6 canonical 정합 (Phase A ~ SPEC-C3) + SPEC-RFID-001 Wave 2

> 대상 브랜치: `feat/v6-phase-c2-proxy` (머지 대상 `main`)
> 커밋 범위: 8개 + SPEC-RFID-001 Wave 2 (2026-04-21, 작업 진행) · 2026-04-20 확정
> 배포 영향: Interface (FastAPI) · Management (gRPC) · PyQt (monitoring) · Jetson Publisher · DB (신규 `rfid_scan_log`)

---

## 1. 커밋 이력

```
(wip)    SPEC-RFID-001 Wave 2 · rfid_scan_log append-only + ReportRfidScan RPC (working tree)
1c33ae4  SPEC-C3 · Management 기동 복구 + smartcast Item 매핑
476e86b  Phase C-2 · smartcast TaskManager + Interface proxy (Option A backward-compat)
3d42c0a  SPEC-C2 Iteration 2 합의안
24e79ad  Phase D-2 · Jetson subscriber + EspBridge outbound
fb5536f  Phase D-1 · MQTT 제거 · Mgmt→Jetson gRPC relay
b3b185e  Phase C-1 · Mgmt gRPC client + Health proxy
a80e53f  Phase B   · ROS2 publisher Interface→Management
f27e3ea  Phase A   · PyQt WebSocket 경로 제거
```

## 2. 사전 준비

### 필수 접근

| 호스트 | 접속 | 용도 |
|---|---|---|
| Interface Service | 로컬 또는 현장 PC | FastAPI `:8000` 재시작 |
| Management Service | 로컬 또는 현장 PC | gRPC `:50051` 재시작 |
| Factory Operator PC | 현장 | PyQt 재기동 (`monitoring/`) |
| Jetson Orin NX | Tailscale `100.77.62.67` | `deploy.sh` · `/dev/ttyUSB0` ESP32 |
| DB 서버 (예진님 PC) | Tailscale `100.107.120.14` | TimescaleDB extension (별도 작업) |

### 환경변수 (.env.local 또는 systemd EnvironmentFile)

| 변수 | 기본 | 용도 |
|---|---|---|
| `INTERFACE_PROXY_START_PRODUCTION` | `0` | **모듈 import 시점 고정.** 1 로 flip 시 모든 FastAPI worker 재시작 필수 |
| `MANAGEMENT_GRPC_HOST` | `localhost` | Interface → Mgmt 연결 |
| `MANAGEMENT_GRPC_PORT` | `50051` | 동일 |
| `MGMT_GRPC_TLS_ENABLED` | `0` | 운영 시 1 권장 (현재 미적용) |
| `MGMT_ROS2_ENABLED` | `0` | 1 이면 FMS 시퀀서가 실 ROS2 publish (rclpy 설치 조건) |
| `FMS_AUTOPLAY` | `0` | 1 이면 Mgmt 가 FMS 시퀀서 daemon thread 기동 |
| `MGMT_COMMAND_STREAM_ENABLED` | `0` | Jetson 이 1 로 설정하면 `WatchConveyorCommands` 구독 |

### DB 상태 확인

```bash
psql -h 100.107.120.14 -U team2 -d smartcast_robotics -c \
  "SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';"
```

**미설치 상태**에서도 본 배포는 동작 (SLA alert 누적 기능만 영향, 시연 비차단).

## 3. 배포 순서

### 3.1 PR 머지

```bash
# 리뷰 완료 후
gh pr merge feat/v6-phase-c2-proxy --squash --delete-branch=false
# --delete-branch=false 권장: 머지 직후 핫픽스 필요 시 브랜치에서 재작업 가능
```

### 3.2 Interface Service 재시작 (FastAPI :8000)

```bash
cd /path/to/casting-factory
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt          # grpcio>=1.80, protobuf>=6.30 신규
# FastAPI uvicorn 재시작 (systemd 사용 시)
sudo systemctl restart casting-interface
# 또는 수동:
# pkill -f 'uvicorn.*app.main' && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**검증**:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"casting-factory-api"}
```

### 3.3 Management Service 재시작 (gRPC :50051)

```bash
cd /path/to/casting-factory
git pull origin main
cd backend/management
source venv/bin/activate                  # Python 3.12 필수
pip install -r requirements.txt          # paho-mqtt 제거됨 (Phase D-1)
make proto                                # management_pb2*.py 재생성 (SPEC-C2 backward-compat)
# Mgmt 재시작
sudo systemctl restart casting-management
# 또는 수동: pkill -f 'python server.py' && python server.py &
```

**검증**:
```bash
curl http://localhost:8000/api/management/health
# → {"status":"ok","service":"management","grpc":"localhost:50051"}
```

### 3.4 Factory Operator PC (PyQt monitoring)

```bash
cd /path/to/casting-factory
git pull origin main
cd monitoring
source venv/bin/activate                  # Python 3.12 (Apple Silicon 호환)
pip install -r requirements.txt          # websocket-client 제거, grpcio>=1.80
python scripts/gen_proto.sh               # pb2 재생성 (ConveyorCommand, StartProductionResult 반영)
# 재기동
python main.py
```

**검증 (GUI)**:
- 상태바 `gRPC: ready` 표시 (WS 표기 사라짐)
- schedule 페이지 [▶ 생산 시작] 클릭 → `StartProduction` gRPC 호출 성공
- 대시보드 실시간 alert 토스트 수신 (gRPC `WatchAlerts`)
- AMR 배터리/상태 폴링 동작

### 3.5 Jetson Orin NX (ESP32 Serial relay)

```bash
# 본인 PC (로컬) 에서
bash jetson_publisher/deploy.sh
# 또는 최초 설치:
bash jetson_publisher/deploy.sh --install
```

Jetson 쪽 `~/casting-image-publisher/env` 에 추가:
```
ESP_BRIDGE_ENABLED=1
ESP_BRIDGE_PORT=/dev/ttyUSB0
MGMT_COMMAND_STREAM_ENABLED=1
MGMT_COMMAND_SUBSCRIBER_ID=jetson-orin-nx-01
```

**검증**:
```bash
ssh jetson-conveyor "sudo systemctl restart casting-image-publisher && sleep 2 && sudo journalctl -u casting-image-publisher -n 30"
# 로그에 다음 라인 확인:
# CommandSubscriber 시작: target=localhost:50051 subscriber=jetson-orin-nx-01
# WatchConveyorCommands stream 개시
```

Mgmt 에서 테스트 명령 발사:
```bash
# 본인 PC 에서 (gRPC stub 활용)
grpcurl -plaintext -d '{"item_id":0,"robot_id":"CONV-01","command":"PING"}' \
  localhost:50051 casting.management.v1.ManagementService/ExecuteCommand
# Jetson 로그에 "gRPC → Jetson cmd: robot=CONV-01 command=PING" 확인
# ESP32 Serial 로 "PING\n" 전송 확인
```

### 3.6 SPEC-RFID-001 Wave 2 (RFID append-only 로그)

#### 3.6.1 DB migration 적용

```bash
# Interface/Management 호스트에서 (DATABASE_URL 환경변수 활성 상태)
psql "$DATABASE_URL" -f backend/scripts/migrate_rfid_scan_log.sql
# 기대 로그:
#   CREATE TABLE / CREATE INDEX (idx_rfid_scan_reader_time, idx_rfid_scan_item_time, idx_rfid_scan_idempotency)
#   NOTICE: SPEC-RFID-001: TimescaleDB hypertable 활성화  (확장 설치 시)
#   NOTICE: SPEC-RFID-001: TimescaleDB 미설치 — 일반 테이블로 운영  (미설치 시)

# 멱등성 검증: 재실행 해도 오류 없어야 함
psql "$DATABASE_URL" -f backend/scripts/migrate_rfid_scan_log.sql
```

#### 3.6.2 proto 재컴파일 (이미 Mgmt 재시작 시 수행됨)

`RfidScanEvent` / `RfidScanAck` / `ReportRfidScan` 이 `management_pb2*.py` 에 생성되어 있는지 재확인:

```bash
grep -n "RfidScanEvent\|ReportRfidScan" backend/management/management_pb2_grpc.py | head -4
grep -n "RfidScanEvent\|ReportRfidScan" monitoring/app/generated/management_pb2_grpc.py | head -4
grep -n "RfidScanEvent\|ReportRfidScan" jetson_publisher/generated/management_pb2_grpc.py | head -4
# 각 파일에서 매치가 보여야 함
```

누락 시 재생성:
- `backend/management/`: `cd backend/management && make proto`
- `monitoring/app/generated/`: `bash monitoring/scripts/gen_proto.sh`
- `jetson_publisher/generated/`: **별도 절차** — `jetson_publisher/README.md §prerequisites` 의 protoc 1.59.x venv 가이드 참조 (1.69+ 로 만들면 Jetson 에서 import 실패). 2026-04-21 기준 working tree 에서 이 stub 만 아직 재생성 전 상태로 확인됨 — Jetson 배포 직전 재컴파일 필요.

#### 3.6.3 Smoke 테스트

```bash
# 유닛 테스트 (FakeSession)
cd backend/management
pytest tests/test_rfid_service.py -v
# 5 케이스 (happy / bad_format / invalid_ts / duplicate_same / duplicate_conflict) PASS 기대

# RPC smoke (Management :50051 기동 상태)
grpcurl -plaintext -d '{
  "reader_id": "ESP-CONV-01",
  "zone": "conveyor_in",
  "raw_payload": "order_1_item_20260417_1",
  "scanned_at": {"iso8601": "2026-04-21T00:00:00Z"},
  "idempotency_key": "ESP-CONV-01:smoke-1"
}' localhost:50051 casting.management.v1.ManagementService/ReportRfidScan
# 기대 응답:
# {"accepted": true, "parseStatus": "ok", "reason": "parsed"}

# 동일 idempotency_key 재전송 → parse_status=duplicate
grpcurl -plaintext -d '{ ... "idempotency_key": "ESP-CONV-01:smoke-1" }' \
  localhost:50051 casting.management.v1.ManagementService/ReportRfidScan
# 기대: {"accepted": true, "parseStatus": "duplicate", ...}
```

#### 3.6.4 DB 확인

```bash
psql "$DATABASE_URL" -c "SELECT parse_status, count(*) FROM public.rfid_scan_log GROUP BY parse_status;"
# smoke 1건이 ok, duplicate 중복이 차단되어 row 추가 안됨 확인
```

#### 3.6.5 Jetson 측 설정 (후속 배포)

현재 Wave 2 범위는 **Management 측만**. Jetson 측 Serial → gRPC 브릿지는 별도 PR 로 분리 (SPEC 범위 외). Jetson 쪽에서 다음을 추가할 예정:

```
# jetson_publisher env 예정
RFID_BRIDGE_ENABLED=1
RFID_BRIDGE_PORT=/dev/ttyUSB1   # RC522 연결 ESP32 (컨베이어 ESP 와 별도 포트 권장)
```

## 4. Feature flag 점진 활성화 (SPEC-C2 §6.2)

### 4.1 스테이징 (Staging · INTERFACE_PROXY_START_PRODUCTION=1)

```bash
# Interface 호스트
sudo systemctl set-environment INTERFACE_PROXY_START_PRODUCTION=1
sudo systemctl restart casting-interface   # 모든 worker 재시작 필수
```

### 4.2 검증 (Interface 레벨)

```bash
# 패턴 등록된 ord_id 1 사용
curl -X POST http://localhost:8000/api/production/start \
     -H 'Content-Type: application/json' \
     -d '{"ord_id":1}'
# 기대 (flag ON · Mgmt proxy):
# {"ord_id":1,"item_id":N,"equip_task_txn_id":M,"message":"Production started: RA1/MM task queued."}

# Mgmt 로그 확인:
sudo journalctl -u casting-management -n 30 | grep start_production_single
```

### 4.3 운영 rollout

- 스테이징에서 24h 안정 후 운영 서버에 동일 환경변수 적용
- 운영 배포 런북에 **worker 재시작 필수** 강조

## 5. 롤백

### 5.1 Feature flag 만 OFF (코드 유지)

```bash
sudo systemctl set-environment INTERFACE_PROXY_START_PRODUCTION=0
sudo systemctl restart casting-interface
```

### 5.2 Git revert (전체 롤백)

```bash
git checkout main
git revert HEAD~7..HEAD    # 8 커밋 역순
# 또는 특정 Phase 만:
git revert 1c33ae4          # SPEC-C3 만
git push origin main
# 각 서비스 재시작
```

### 5.3 Jetson 롤백

```bash
ssh jetson-conveyor "sudo systemctl stop casting-image-publisher"
# 환경변수에서 MGMT_COMMAND_STREAM_ENABLED=0 로 설정 후 재기동
```

## 6. Post-deploy 검증 체크리스트

| 체크 | 명령 | 기대 |
|---|---|---|
| Interface health | `curl localhost:8000/health` | `{"status":"ok"}` |
| Mgmt proxy health | `curl localhost:8000/api/management/health` | `{"status":"ok","grpc":"localhost:50051"}` |
| Mgmt Health RPC | `grpcurl -plaintext localhost:50051 .../Health` | empty response |
| ListItems | `grpcurl -plaintext -d '{"limit":3}' localhost:50051 .../ListItems` | items 배열 |
| PyQt 기동 | `tail -f ~/casting-factory/monitoring/logs/*.log` | WS/MQTT 없음, gRPC stream 활성 |
| Jetson relay | `ssh jetson-conveyor "journalctl -u casting-image-publisher -n 10"` | `CommandSubscriber` 스레드 로그 |
| ESP32 컨베이어 | 물리 테스트 (ExecuteCommand CONV-01/RUN → 모터 회전) | 모터 기동 |
| RFID 테이블 | `psql -c "\d+ public.rfid_scan_log"` | 3 인덱스 + composite PK(id, scanned_at) |
| RFID RPC smoke | `grpcurl ... ReportRfidScan` (§3.6.3) | `parse_status=ok` 후 `parse_status=duplicate` |

## 7. 알려진 제약 (비차단)

| 항목 | 영향 | 후속 |
|---|---|---|
| SLA stage mapping 부분 불일치 | smartcast `cur_stat` 12 라벨 중 미매핑 스테이지는 SLA 감시 스킵 (크래시 없음, fallback 안전) | 별도 PR 에서 `_STAGE_TO_ENUM` 재설계 |
| pytest-postgresql fixture 미구성 | CI skipped 3개 테스트 | SPEC-C2 §13 DoD 잔여 (Task #9) |
| TimescaleDB extension 미설치 | SLA alerts hypertable 최적화 안됨 | 예진님 PC 출근 시 `install_timescaledb_local.sh` |
| Connection pool 부하 테스트 미실시 | 20 동시 생산 시작 시 병목 가능 | 스테이징에서 측정 후 조정 |
| `backend/app/services/execution_monitor` SLA 상수 | legacy stage 기준 SLA (QUE/MM/DM/...) 유지 | 별도 PR |

## 8. 긴급 연락 / 참조

- SPEC: `docs/SPEC-C2-schema-migration.md` (Iter 2 합의안)
- 컴포넌트 관계: `docs/management_components.html`
- canonical 아키텍처 원본: `/Downloads/image-20260420-053600.png`
- canonical 해석 규칙: memory `feedback_canonical_image_interpretation.md`
- 이전 V6 결정: memory `project_v6_grpc_decision.md`, `project_v6_complete.md`

---

**배포 완료 기준**: 본 런북 §6 체크리스트 7개 모두 ✅ 상태.
