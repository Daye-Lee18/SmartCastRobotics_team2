# 02. 시스템 설계 문서

> **버전**: V6 canonical (2026-04-24 기준)
> **대상 독자**: 개발자, 아키텍트, 운영 담당자
> **상세 다이어그램**: `docs/architecture/*.md` (12 component docs) + `docs/*.html` (interactive)

---

## 1. 설계 원칙

### 1.1 V6 핵심 결정 (2026-04-14 확정)
- **프로세스 이원화**: Interface Service (FastAPI, HTTP) 와 Management Service (gRPC) 를 독립 프로세스로 분리
- **이유**: Interface 장애 / AWS 이관 시에도 공장 가동 유지 (SPOF 제거)
- **DB 단독**: PostgreSQL 16 + TimescaleDB (SQLite 폴백 완전 제거)

### 1.2 설계 품질 프레임워크 (TRUST 5)
- **T**ested: 85%+ 커버리지, 특성화 테스트
- **R**eadable: 명확한 명명, 영문 주석
- **U**nified: 일관 스타일, ruff/black 포맷팅
- **S**ecured: OWASP 준수, 입력 검증
- **T**rackable: Conventional commits, 이슈 참조

### 1.3 설계 분리 원칙
- **Interface** ↔ **Management** 간 교차 호출은 **명시적 RPC**만 허용 (shared-memory / DB-coupling 금지)
- HW 도메인(ROS2 / Serial / Jetson) 은 Management 쪽에서만 접근
- Next.js (고객/관리자) 는 Interface HTTP, PyQt(공장 운영자) 는 Management gRPC 직결

---

## 2. 전체 아키텍처

```
┌─────────────────────┐       ┌─────────────────────┐
│  Customer / Admin   │       │  Factory Operator   │
│     (Next.js 16)    │       │      (PyQt5)        │
└──────────┬──────────┘       └──────────┬──────────┘
           │ HTTP                        │ gRPC (:50051)
           ▼                             ▼
┌─────────────────────┐       ┌─────────────────────┐
│  Interface Service  │ gRPC  │ Management Service  │
│   FastAPI :8000     │◀──────▶│     gRPC :50051    │
│   (admin/customer)  │       │  (factory core)     │
└──────────┬──────────┘       └──────────┬──────────┘
           │                             │
           │                             │ gRPC streaming + unary
           │                             ├──────▶  Jetson (Vision/AI/Bridge)
           │                             ├──────▶  ROS2 DDS  (AMR, Arm)
           │                             └──────▶  Jetson Serial → ESP32 (Conveyor, RFID, Handoff)
           │
           ▼
┌────────────────────────────────────────────────────┐
│  PostgreSQL (Tailscale 100.107.120.14) + AWS RDS   │
│  · 로컬 public (v2, 22 tables) — 평소 개발           │
│  · 로컬 smartcast (ERP, 31 tables) — 참조용          │
│  · AWS RDS Casting (29 tables, ERP) — 특별 요청     │
└────────────────────────────────────────────────────┘
```

---

## 3. 서비스 상세 설계

### 3.1 Interface Service (`backend/app/`)
- **프레임워크**: FastAPI + SQLAlchemy + Pydantic
- **포트**: 8000 (HTTP)
- **책임**:
  - REST API 제공 (admin / customer / order / product)
  - WebSocket 푸시 (보조, Phase A 이후 PyQt 의존 제거)
  - Management Service 프록시 (`/api/management/*`)
- **사용 스키마**: 로컬 `public` (v2 스키마, 22 테이블)
- **문서**: `docs/management_service_design.md`, `docs/interface_service_audit.html`

주요 서브모듈:
| 디렉토리 | 역할 |
|---|---|
| `app/routes/` | FastAPI 라우터 (orders, products, admin, management proxy 등) |
| `app/routes/legacy/` | 구버전 호환 라우트 |
| `app/models/` | SQLAlchemy ORM 모델 (`models_mgmt.py` 는 선별 import) |
| `app/services/` | 도메인 서비스 (주문 처리, 상태 전이 등) |
| `app/database.py` | DATABASE_URL fail-fast 로직 |

### 3.2 Management Service (`backend/management/`)
- **프레임워크**: gRPC (`grpcio`) + SQLAlchemy
- **포트**: 50051
- **책임**:
  - 공정 실시간 제어 (주문 시작/중단, 장비 제어, AMR 배차)
  - HW 이벤트 수집 (RFID, 바코드, Handoff, 이미지 프레임)
  - EventBridge 라우팅
  - TaskManager / OrderManager / Ordering Service
- **사용 스키마**: 로컬 `public` (백엔드 코드 공용) + `smartcast` 스키마 (ERP 참조)

주요 서브모듈:
| 디렉토리 | 역할 |
|---|---|
| `management/server.py` | gRPC 서버 엔트리 (핫 패스 중 하나, 20+ 참조) |
| `management/proto/` | `management.proto` — 단일 소스, monitoring/jetson에서 재생성 |
| `management/services/` | Ordering, Order Manager, Interface/Management 클라이언트, EventBridge |
| `management/services/adapters/` | ROS2, Jetson Serial, JetCobot 어댑터 |
| `management/tests/` | 통합 테스트 (order pipeline 4seq 포함) |

### 3.3 Monitoring App (`monitoring/`)
- **프레임워크**: PyQt5 (Python 3.12 고정)
- **책임**: 공장 운영자용 실시간 대시보드
- **통신**: Management gRPC 직결 (api_client WebSocket 은 보조)
- **핫 패스**: `monitoring/app/main_window.py` (25+ 참조)

주요 뷰:
| 뷰 | 역할 |
|---|---|
| 메인 대시보드 | 전체 공정·AMR·장비 상태 |
| 주문 관리 | PENDING 주문 확인, 생산 시작 버튼 |
| AMR 관리 | Repair 버튼, Handoff 버튼 지원 |
| 알람 | 실시간 에러/경고 |

### 3.4 Jetson Publisher (`jetson_publisher/`)
- **HW**: Jetson Orin NX + C920 카메라 + ESP32 브릿지
- **책임**:
  - 이미지 프레임을 gRPC client streaming으로 Management에 전송
  - ESP32 Serial bridge (RFID, Handoff, 바코드 HID)
  - 지수 백오프 재연결 (1~60s, 32 이벤트 버퍼)
- **네트워크**: Tailscale `100.77.62.67` (SSH alias `jetson-conveyor`)

### 3.5 Frontend (`src/`)
- **프레임워크**: Next.js 16 (App Router) + React 19 + TypeScript strict
- **스타일**: Tailwind + shadcn/ui
- **책임**: 고객 / 관리자 웹 UI

주요 라우트 (Confluence GUI 6389916 기준, 8개):
| 경로 | 역할 |
|---|---|
| `/` | 랜딩 (SmartCast Robotics 소개) |
| `/login` | 로그인 |
| `/customer/order/new` | 고객 주문 작성 |
| `/customer/orders` | 고객 주문 상태 조회 |
| `/admin/orders` | 관리자 주문 검토·승인 |
| `/admin/dashboard` | 관리자 공정 요약 |
| `/admin/equipment` | 장비 관리 |
| `/admin/analytics` | 분석 리포트 |

---

## 4. 컴포넌트 설계

### 4.1 TaskManager (Management)
- `docs/architecture/task_manager.md`, `docs/task_manager_summary.html`
- 생산 작업의 큐잉·라우팅·상태 전이 담당
- 의사결정 규칙 A/B/C (대기시간/병목/배치) 구현

### 4.2 OrderManager / OrderingService
- `backend/management/services/order_manager.py`, `ordering_service.py`
- 주문 접수 → 승인 → 생산 트리거 파이프라인
- 4-stage 순차 테스트 `test_order_pipeline_4seq.py` 로 검증

### 4.3 EventBridge (`backend/management/services/event_bridge.py`)
- 569줄 contract + impl, 20 tests
- 상태 변화 이벤트 전파 전용 (pure router, stateless, thread-safe)
- CRUD / 조회 / 명령은 직접 호출 (판단 기준: 응답 필요? 1:1? 트랜잭션?)
- 설계 문서: `docs/event_bridge_design.html`

### 4.4 Fleet Traffic (AMR 제어)
- 설계: `docs/fleet_traffic_management.html`, `project_fleet_traffic_design.md`
- 1m × 2m 맵 + 0.12m AMR 3대
- Waypoint / Edge + nav2_route + Backtrack Yield
- ROS2 DDS 기반 다중 AMR 조율

### 4.5 Vision Service (Jetson)
- `ImagePublisherService/PublishFrames` gRPC client streaming
- C920 카메라 → ESP32 트리거 → 프레임 캡처 → Management 전송
- 하위 모듈: 비전 검출, AI 추론 요청

---

## 5. 데이터 모델

### 5.1 환경별 스키마 (2026-04-24 확정)

| 환경 | Host | DB | 스키마 | 테이블 수 | 용도 |
|---|---|---|---|---|---|
| **평소 개발 (default)** | 100.107.120.14 (Tailscale) | `smartcast_robotics` | `public` (v2) | 22 | 백엔드 기본 타겟 |
| 참조/실험 | 동일 | 동일 | `smartcast` (ERP) | 31 | 참조용, 제거 가능 |
| **특별 요청** | AWS RDS ap-northeast-2 | `Casting` | `public` (ERP) | 29 | Confluence 42270744 가이드 |

### 5.2 로컬 public (v2) 주요 테이블 (22개)
- **주문**: `orders`, `order_details`
- **제품**: `products`, `load_classes`, `inspection_standards`
- **공정**: `items`, `production_jobs`, `production_metrics`, `process_stages`, `work_orders`, `priority_change_logs`
- **장비/운반**: `equipment`, `transport_tasks`
- **검사**: `inspection_records`, `sorter_logs`
- **창고/출고**: `warehouse_racks`, `outbound_orders`
- **HW 이벤트**: `handoff_acks`, `rfid_scan_log`
- **알람/계정**: `alerts` (630K 행, 시계열), `team_members`, `test_messages`

### 5.3 AWS RDS public (ERP) 주요 테이블 (29개)
- **마스터**: `category` (CMH/RMH/EMH), `product`, `product_option`, `pattern`, `pp_options`, `user_account`, `zone` (CAST/PP/INSP/STRG/SHIP/CHG), `res` (RA/CONV/AMR)
- **장비**: `equip`, `equip_load_spec`, `equip_stat`, `equip_task_txn`, `equip_err_log`
- **운반**: `trans`, `trans_stat`, `trans_task_txn`, `trans_err_log`
- **위치**: `chg_location_stat`, `strg_location_stat`, `ship_location_stat`
- **주문**: `ord`, `ord_detail`, `ord_log`, `ord_pp_map`, `ord_stat`, `ord_txn`
- **실행**: `item`, `pp_task_txn`, `insp_task_txn`

### 5.4 스키마 호환성
두 스키마는 **호환되지 않음** — 네이밍/테이블 구조 다름. 코드 재사용 불가. 의도적 마이그레이션만 수행.

### 5.5 주요 상태 enum (ERP 스키마)
| 컬럼 | 유효 값 |
|---|---|
| `ord_stat.ord_stat` | RCVD / APPR / MFG / DONE / SHIP / COMP / REJT / CNCL |
| `ord_log.new_stat` | RCVD / APPR / MFG / DONE / SHIP / COMP / REJT / **CANCELED** ⚠ |
| `ord_txn.txn_type` | RCVD (default) / APPR / CNCL / REJT |
| `*_task_txn.txn_stat` | QUE / PROC / SUCC / FAIL |
| `strg_location_stat.status` | empty / reserved / occupied (CHECK: occupied ↔ item_id NOT NULL) |

---

## 6. API 설계

### 6.1 REST (Interface Service, HTTP :8000)
Confluence 22806540 (Interface Specification v46) 기준.

핵심 엔드포인트:
| 메소드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/orders` | 주문 생성 (Admin PC → Interface) |
| GET | `/api/orders` | 주문 목록 |
| GET | `/api/orders/{id}` | 주문 상세 |
| PATCH | `/api/orders/{id}/status` | 상태 전이 (승인/반려/수정 요청) |
| GET | `/api/products` | 제품 카탈로그 |
| GET | `/api/management/health` | Management Service 상태 확인 (Phase C-1) |
| GET | `/api/management/*` | Management 프록시 (SPEC-C2 `INTERFACE_PROXY_START_PRODUCTION` flag) |

### 6.2 gRPC (Management Service, :50051)
정의: `backend/management/proto/management.proto` (단일 소스)

핵심 RPC:
| RPC | 방향 | 용도 |
|---|---|---|
| `StartProduction` (unary) | UI → Mgmt | 생산 시작 버튼 |
| `WatchItems` (server stream) | Mgmt → UI | 실시간 아이템 상태 |
| `WatchConveyorCommands` (server stream) | Mgmt → Jetson | 컨베이어 명령 스트림 |
| `PublishFrames` (client stream) | Jetson → Mgmt | 이미지 프레임 업로드 |
| `ReportRfidScan` (unary) | Jetson → Mgmt | RFID / 바코드 이벤트 보고 |
| `ReportHandoffAck` (unary) | Jetson → Mgmt | Handoff 버튼 이벤트 |
| `TransitionAmrState` (unary) | UI → Mgmt | AMR FSM 전이 |
| `ResumeConveyor` (unary) | Mgmt → Jetson | 컨베이어 재개 명령 |

### 6.3 proto 재생성
- Management 호스트: `grpcio-tools 1.59.5`
- Jetson: **직접 재생성 필요** (protobuf 4.25.9 매칭)
- Monitoring: `monitoring/scripts/gen_proto.sh` 에서 absolute import → relative import 패치 수행

---

## 7. HW 아키텍처 (V6 canonical, 2026-04-22 기준)

### 7.1 통신 채널 요약
| HW | 프로토콜 | 경로 |
|---|---|---|
| **AMR-\*** / **ARM-\*** | ROS2 DDS | RPi5 / RPi4 노드 (`MGMT_ROS2_ENABLED=1`) |
| **CONV-\*** / **ESP-\*** | Mgmt gRPC → Jetson Serial(115200) → ESP32 | `WatchConveyorCommands` stream (MQTT 제거) |
| **Image Publisher** | gRPC streaming | `ImagePublisherService/PublishFrames` (client stream) |
| **RFID** (RC522) | SPI → Jetson Serial → gRPC unary | `ReportRfidScan` → `public.rfid_scan_log` append-only |
| **Barcode** (HID Keyboard) | `/dev/input/event*` → python-evdev → gRPC unary | `ReportRfidScan` 공용 (reader_id=`BARCODE-JETSON-01`) |
| **Handoff Button** | ESP32 GPIO 33 → Serial → Jetson bridge → gRPC unary | `ReportHandoffAck` → `public.handoff_acks` |

### 7.2 주요 HW 장비
| 종류 | 모델/사양 | 주요 용도 |
|---|---|---|
| AMR | 직경 ~0.12m × 3대 | 팔레트/개별 이송 |
| 로봇팔 | JetCobot 280 (Elephant Robotics) | 탈형, picking, 적재 |
| 컨베이어 | L298N + JGB37-555 + 2x TOF250 | 제품 이동, 비전 검사 |
| 비전 | Jetson Orin NX + Logitech C920 | 프레임 캡처, AI 추론 |
| ESP32 | v5.0 (v4.0 기반 WiFi/MQTT 제거) | 컨베이어·센서·버튼 제어 |
| RFID 리더 | RC522 (UART→Jetson) | 아이템 식별 |
| 바코드 리더 | `0483:0011` 저가 1D 레이저 (HID) | 아이템 식별 보조 |

### 7.3 SPEC 구현 현황
| SPEC | 내용 | 상태 |
|---|---|---|
| SPEC-AMR-001 | AMR 제어 + Handoff Button (Wave 3) | 🟢 배포 완료, 실물 버튼 push 잔존 |
| SPEC-RFID-001 Wave 2 | `rfid_scan_log` + `ReportRfidScan` + `RfidService` | 🟡 진행 |
| SPEC-RC522-001 | RC522 안정성 회귀 테스트 | ✅ PR #2 99%/70 tests 머지 |
| SPEC-ORD-001 | 주문 도메인 | ✅ |
| SPEC-CASTING-001 | 주조 공정 | ✅ |
| SPEC-API-001 / 002 | API 정의 | ✅ |
| SPEC-CTL-001 | 제어 인터페이스 | ✅ |
| SPEC-DB-V2-MIGRATION | v2 스키마 이관 | ✅ (PR #2~#13 squash-merge) |

---

## 8. 이벤트 흐름

### 8.1 주문 처리 흐름
```
Customer → Interface REST POST /api/orders
          → DB.orders INSERT (status='pending')
          → (관리자 검토)
          → PATCH status='approved'
          → Management.StartProduction (gRPC)
          → TaskManager 큐잉
          → AMR/Arm/Conveyor 협업
          → WatchItems stream (UI 실시간)
          → 검사 통과
          → status='production_completed' → 'shipped'
```

### 8.2 HW 이벤트 흐름 (Handoff Button 예시, SPEC-AMR-001 Wave 3)
```
ESP32 GPIO 33 (A접점 INPUT_PULLUP)
  ↓ rising edge
firmware pollHandoffButton()
  ↓ Serial HANDOFF_ACK 토큰 + JSON
Jetson jetson_publisher/esp_bridge.py
  ↓ gRPC unary ReportHandoffAck
Management ReportHandoffAck 핸들러
  ↓ INSERT public.handoff_acks
  ↓ UPDATE public.transport_tasks.status='handoff_complete'
  ↓ AMR FSM: AT_DESTINATION/UNLOADING → UNLOAD_COMPLETED
```

### 8.3 이미지 스트리밍
```
Jetson C920 → 프레임 캡처
  ↓ gRPC client stream PublishFrames
Management → ImagePublisherService 수신
  ↓ AI 추론 (Jetson / AI Server Phase 2)
  ↓ 검사 결과 insp_task_txn 기록
```

---

## 9. 배포 아키텍처

### 9.1 현재 배포 구성
- **Factory 로컬 네트워크**: Tailscale 메시
  - 사용자 Mac: `100.77.239.25` (kisoo)
  - 로컬 DB 서버: `100.107.120.14` (yejin-laptop, PG 16)
  - AI Server: `100.66.177.119` (team2)
  - Jetson: `100.77.62.67` (ssh alias `jetson-conveyor`)
  - JetCobot: `100.94.152.67`
- **AWS**: RDS PostgreSQL 18.3 ap-northeast-2 `teamdb.ct4cesagstqf.ap-northeast-2.rds.amazonaws.com`
- **FastDDS Bridge**: AMR ↔ Factory 네트워크 (`deploy/` 디렉토리)

### 9.2 배포 런북
- Phase A ~ C3: `docs/DEPLOY-phase-a-to-c3.md`
- Barcode 핸드오프: `docs/barcode_jetson_ready.md`

### 9.3 시작 순서 (권장)
1. DB 상태 확인 (Tailscale 접근성 `nc -zv 100.107.120.14 5432`)
2. Management Service 기동 (`backend/management/server.py`)
3. Interface Service 기동 (`uvicorn backend.app.main:app`)
4. Next.js dev server (`pnpm dev`)
5. Jetson Publisher + ESP bridge
6. PyQt Monitoring

---

## 10. 보안 설계

### 10.1 인증
- 관리자: 권한 기반 접근 (SR-ORD-03 비기능 요구사항)
- 고객: 이메일 기반 계정
- 공장 운영자: Factory Operator PC 물리적 접근 제한 + PyQt 세션

### 10.2 네트워크
- 모든 내부 통신: Tailscale 메시 (WireGuard 암호화)
- AWS RDS: SSL `verify-full` + RDS CA 번들 필수
- FastDDS: AMR ↔ Factory 격리 (`deploy/fastdds/`)

### 10.3 자격증명 관리
- 개발: `.env.local` 평문 허용 (프로덕션 전환 전까지)
- 프로덕션: SSH 키 + macOS Keychain 전환 예정
- Confluence API 토큰: Keychain `service=casting-factory-atlassian`

### 10.4 데이터 보호
- 고객 연락처·배송지: DB 안전 저장 (SR-ORD-03)
- RFID 스캔 로그: append-only (tamper evident)
- Confluence 원본: **READ-ONLY** (PUT/POST/DELETE 사용자 명시 허락 필수)

---

## 11. 참고 문서

### 11.1 아키텍처 상세 (`docs/architecture/`)
- 12개 컴포넌트 설계 문서 + index (4207줄)

### 11.2 HTML 다이어그램 (`docs/*.html`)
- `system_overview.html` — 시스템 전체 개요
- `component_relationship_clear.html` — 컴포넌트 관계도
- `event_bridge_flows.html` — EventBridge 이벤트 흐름
- `fleet_traffic_management.html` — AMR 경로 관리
- `manhole_state_diagram.html` — 맨홀 아이템 상태 다이어그램
- `production_planning_flowchart.html` — 생산 계획 플로우
- `interface_service_audit.html` — Interface Service 감사 리포트
- `interface_internal_structure_explained.html` — Interface 내부 구조
- `interface_service_cheatsheet.html` — Interface 치트시트
- `management_components.html` — Management 컴포넌트
- `task_manager_summary.html`, `task_allocator_summary.html` — TaskManager 요약
- `data_flow_report.html`, `data_flow_summary.html` — 데이터 흐름

### 11.3 SPEC (`.moai/specs/`)
- SPEC-AMR-001 / API-001 / API-002 / CASTING-001 / CTL-001 / DB-V2-MIGRATION / ORD-001 / RC522-001 / RFID-001

### 11.4 Confluence 원천
- `docs/CONFLUENCE_FACTS.md` (23K 줄, 22 페이지, launchd 매일 동기화)
- Interface Spec: Confluence 22806540
- Detailed Design: Confluence 6651919
- System Architecture: Confluence 3375131

---

## 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | V6 | 초기 작성. 이원화 아키텍처 · 29/22 테이블 스키마 · 8 RPC · HW 6채널 반영 |
