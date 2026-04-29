# 03. 공정 프로세스 문서

> **버전**: V6 (2026-04-24)
> **대상 독자**: 공정 기획·설계자, 공장 운영자, 개발자
> **원천**: Confluence `User_Requirements` (3375120), `Casting` (3375162), `Terminology` (3407906), `detailed_design` (6651919), `.moai/specs/SPEC-CASTING-001.md`

---

## 1. 공정 개요

SmartCast Robotics의 공정은 **주문 접수 → 생산 → 출고**의 end-to-end 파이프라인으로, 맨홀 뚜껑(20~80kg) 기준 **다품종 소량 생산** 방식이다.

### 1.1 공정 전체 흐름 (상위 레벨)

```
[고객 주문]        [관리자 승인]        [생산 시작]
     ↓                  ↓                  ↓
[원자재/용광로] → [주형 생성] → [용탕 주입] → [냉각] → [탈형]
                                                           ↓
     ↑                                                   [이송]
     ↑                                                     ↓
[출고]  ← [양품 적재] ← [분류] ← [검사] ← [후처리] ← [이송]
                                                           ↓
                                       [불량품 폐기 이송]
```

### 1.2 자동화 레벨
- **목표**: Level 4 (조건부 자율 + 예외 시 작업자 개입)
- **Required(R) 공정**: 무인 자동화 필수
- **Optional(O) 공정**: MVP 이후 또는 수동 병행

---

## 2. 8단계 공정 상세

### 2.1 [단계 1] 주문 접수 · 생산 계획 (UR_01)
- **입력**: 고객 주문 (제품, 수량, 규격, 납기, 후처리 옵션)
- **출력**: Order ID, BOM, 생산 스케줄
- **주체**: 고객(Next.js) → 관리자(Next.js admin)
- **상태 전이**: `RCVD` → `APPR` (관리자 승인) → `MFG` (생산 시작)
- **추적 엔티티**: Order ID, Quantity, Product/Customer Info
- **등급**: R (Required)

### 2.2 [단계 2] 원자재 투입 · 도가니 용광로
- **입력**: 원자재 (고체/액체), 목표 온도
- **출력**: 용탕 (Molten metal), 용광로 상태
- **주체**: 작업자 수동 (MVP), 자동 투입은 Optional
- **추적**: Material ID, Weight/Temperature, Furnace (Idle/Heating/Ready)
- **등급**: O (MVP에서 수동)

### 2.3 [단계 3] 주형 생성 (Mold Making)
- **입력**: 패턴(ptn) + 주조 사양
- **출력**: Mold (주형)
- **주체**: 주형 제작 장비 + 작업자
- **추적**: Mold ID, Ready/In-progress/Completed, Image
- **등급**: R
- **DB**: `pattern` 테이블 (ptn_id FK → ord_id, 주문별 전용 패턴 관리)

### 2.4 [단계 4] 용탕 주입 (Pouring)
- **입력**: 용탕 + 주형
- **출력**: 주물 (Casting)
- **주체**: 자동 주탕 장비 (Ladle) + Job ID 추적
- **추적**: Ladle, Mold, Pouring, Temperature, Flow Rate, Job ID
- **등급**: R

### 2.5 [단계 5] 냉각 (Cooling)
- **입력**: 고온 주물
- **출력**: 상온 주물 (탈형 가능)
- **주체**: 냉각장 + 온도 모니터링
- **추적**: Casting, Cooling/Completed, Temperature, Time
- **등급**: R
- **의사결정**: 규칙 A (대기시간 T_max 초과 시 이송 트리거)

### 2.6 [단계 6] 탈형 (Demolding · DM)
- **입력**: 냉각된 주물 + 주형
- **출력**: 주물 단독
- **주체**: 로봇팔 (JetCobot 280)
- **추적**: Robot Arm, Task ID
- **등급**: R

### 2.7 [단계 7-A] 이송 (Transport)
- **입력**: 탈형된 주물
- **출력**: 후처리 구역 대기열
- **주체**: AMR (3대, 직경 ~0.12m)
- **추적**: AMR, Pallet ID, Task ID
- **등급**: R
- **의사결정 규칙**:
  - 규칙 A — 대기시간 제한: `if waiting_time >= T_max then move`
  - 규칙 B — 병목 제한: `if waiting_cnt >= Q_max then stop_transferring`
  - 규칙 C — 배치 크기: 대기 수량이 일정 이상이면 묶어서 전송

### 2.8 [단계 7-B] 후처리 (Post-Processing · PP)
- **입력**: 주물
- **출력**: 버 제거 · 그라인딩 완료 주물
- **주체**: 후처리 구역 (MVP 기준 작업자 수동, 후처리 스위치 시나리오)
- **추적**: AMR, Active/Inactive (청소), Robot Arm · Task ID (후처리 → 검사 이송)
- **등급**: R (이송 부분), O (자체 자동화 MVP 이후)
- **참고**: Confluence `[시나리오]후처리 작업구역 스위치 도입 시나리오` (37160520)

### 2.9 [단계 8-A] 검사 (Inspection · INSP)
- **입력**: 후처리된 주물
- **출력**: 양품 / 불량품 판정
- **주체**: 컨베이어 + Jetson 비전 + AI 추론
- **추적**: Camera, Image, Image ID, `insp_task_txn` (txn_stat: QUE/PROC/SUCC/FAIL)
- **등급**: R

### 2.10 [단계 8-B] 분류 · 출하
- **양품**:
  - 로봇팔이 팔레트에 적재 → AMR이 출고 구역으로 이송
  - 추적: Robot Arm, Order Info, Pallet ID, AMR, Task ID
- **불량품**:
  - AMR이 폐기 구역으로 이송 (Optional: 불량품 적재)
  - 추적: AMR, Task ID
  - **재활용 금지** (산업 관례)

---

## 3. 주문 상태 전이 (ERP 스키마 기준)

### 3.1 상태 코드
Confluence 22806540 Interface Specification + DB check constraint 기준.

| 상태 | 코드 | 의미 | 전이 가능 |
|---|---|---|---|
| 접수 | `RCVD` | 고객이 제출, 관리자 검토 대기 | → APPR / REJT / CNCL |
| 승인 | `APPR` | 관리자 승인, 생산 시작 대기 | → MFG / CNCL |
| 생산 중 | `MFG` | 공정 진행 중 | → DONE / FAIL (예외) |
| 생산 완료 | `DONE` | 제품 생산 완료, 출고 준비 | → SHIP |
| 출고 중 | `SHIP` | 출고 진행 | → COMP |
| 완료 | `COMP` | 고객 인수 완료 | (종착) |
| 반려 | `REJT` | 승인 거절 | (종착) |
| 취소 | `CNCL` | 주문 취소 | (종착) |

**⚠ 주의**: `ord_log.new_stat` 에서는 취소를 `CANCELED` 로 표기 (CHECK 제약 불일치). `ord_stat.ord_stat` 은 `CNCL`. 쿼리 시 변환 필요.

### 3.2 상태 전이 다이어그램
```
  (신규)
    │ 고객 주문 제출
    ▼
  RCVD ────(관리자 반려)────▶ REJT
    │  ────(고객 취소)────▶ CNCL
    │ 관리자 승인
    ▼
  APPR ────(취소)────▶ CNCL
    │ 생산 시작 버튼
    ▼
  MFG ─────(예외/실패)────▶ [수동 개입]
    │ 검사 통과
    ▼
  DONE
    │ 출고 지시
    ▼
  SHIP
    │ 고객 인수
    ▼
  COMP
```

### 3.3 기록 추적
- `ord_stat`: 현재 상태 단일 행 유지 (stat_id + ord_id + user_id + ord_stat + updated_at)
- `ord_log`: 상태 전이 이력 (prev_stat, new_stat, changed_by, logged_at)
- `ord_txn`: 트랜잭션 이벤트 (txn_type: RCVD/APPR/CNCL/REJT, txn_at)

---

## 4. AMR 운반 플로우

### 4.1 AMR Task Txn 생명주기
`trans_task_txn.txn_stat` 전이:
```
QUE (대기)
  ↓ 태스크 할당
PROC (이동 중)
  ↓ 목적지 도착 + Handoff 완료
SUCC (성공)
또는 ↓
FAIL (실패, trans_err_log 기록)
```

### 4.2 AMR FSM (SPEC-AMR-001 기준)
Wave 3 기준 핵심 상태:
- `IDLE` → `MOVING` → `AT_DESTINATION` → `UNLOADING` → `UNLOAD_COMPLETED` → `IDLE`
- 예외: `FAILED` → (수리 완료 버튼) → `IDLE`

### 4.3 Handoff Button 흐름 (SPEC-AMR-001 Wave 3, 2026-04-22 배포)
실물 경로:
```
ESP32 GPIO 33 (A접점 INPUT_PULLUP)
  ↓ 버튼 rising edge
firmware pollHandoffButton()
  ↓ Serial "HANDOFF_ACK" 토큰 + JSON 페이로드
Jetson jetson_publisher/esp_bridge.py (지수 백오프 1~60s, 32 이벤트 버퍼)
  ↓ gRPC unary ReportHandoffAck
Management Service 핸들러
  ↓ INSERT public.handoff_acks
  ↓ UPDATE public.transport_tasks.status='handoff_complete'
  ↓ AMR FSM: AT_DESTINATION/UNLOADING → UNLOAD_COMPLETED
```

### 4.4 AMR 경로 관리
- Fleet 설계: `docs/fleet_traffic_management.html`
- 맵 크기: 1m × 2m
- AMR 3대, 직경 ~0.12m
- 제어: Waypoint / Edge 그래프 + nav2_route + Backtrack Yield

### 4.5 AMR Repair (복구) 플로우
2026-04-22 이전 기능:
- PyQt 에서 AMR 카드에 **수리 완료** 버튼 제공
- FSM: `FAILED` → `IDLE` 전이
- DB: `trans_stat.cur_stat` = 'IDLE', `trans_err_log` 마지막 행에 resolved_at 추가

---

## 5. HW 이벤트 흐름

### 5.1 RFID (SPEC-RFID-001 Wave 2)
```
RC522 (SPI)
  ↓
Jetson Serial
  ↓
Management gRPC unary ReportRfidScan
  ↓
INSERT public.rfid_scan_log (append-only)
  + 선택적 item lookup (Wave 2 제외)
```

### 5.2 Barcode (Code128 HID, 2026-04-22 실측 완료)
```
저가 1D 레이저 리더 (0483:0011)
  ↓ HID Keyboard Boot
Jetson /dev/input/event5
  ↓ python-evdev (tools/barcode_live_ingest.py)
Management gRPC unary ReportRfidScan (reader_id="BARCODE-JETSON-01")
  ↓
INSERT public.rfid_scan_log (공용)
```
특징:
- RfidService 무수정 재사용 (reader_id 로 구분)
- 50회 벤치마크 100% / 45ms
- `module_width=0.4mm` + quiet_zone 10mm (0.2mm는 디코딩 실패)

### 5.3 이미지 프레임 (Jetson Image Publisher)
```
C920 카메라
  ↓ 프레임 캡처
Jetson Image Publisher
  ↓ gRPC client streaming PublishFrames
Management ImagePublisherService
  ↓ JPEG 버퍼 + 메타 (frame_id, timestamp)
  ↓ AI 추론 요청 (Jetson 또는 AI Server Phase 2)
  ↓ insp_task_txn 결과 기록
```

### 5.4 Conveyor 명령 (Mgmt gRPC → Jetson Serial → ESP32)
2026-04-20 Phase D-1/D-2 이후 MQTT 완전 제거:
```
Management WatchConveyorCommands (server stream)
  ↓
Jetson Serial (115200 baud)
  ↓
ESP32 펌웨어 (v5.0, WiFi/MQTT 제거)
  ↓
L298N 드라이버 + JGB37-555 모터
```

---

## 6. 검사 프로세스

### 6.1 검사 파이프라인
1. 제품이 컨베이어에 올라옴
2. TOF250 센서가 제품 감지 (9600 ASCII UART)
3. ESP32가 Serial로 Jetson에 트리거 신호
4. Jetson이 C920으로 프레임 캡처
5. Management로 이미지 스트림
6. AI 추론 (불량 검출)
7. `insp_task_txn` 에 결과 저장 (txn_stat: SUCC/FAIL, result: boolean)

### 6.2 판정 결과
- **양품** (SUCC, result=true): 로봇팔 → 팔레트 적재 → AMR 출고 이송
- **불량품** (SUCC, result=false): AMR → 폐기 구역 (재활용 금지)
- **검사 실패** (FAIL): 재시도 또는 운영자 개입

### 6.3 검사 표준
- `public.inspection_standards` (v2 스키마): 제품별 허용 공차 정의
- Confluence `Scenarios` / `Casting` (3375162): 제품 특성 기반 표면 검사 기준

---

## 7. 에러 복구 프로세스

### 7.1 AMR 장애 (trans_err_log 기록)
```
AMR 태스크 실행 중 실패 감지
  ↓
UPDATE trans_stat.cur_stat='FAILED'
  ↓
INSERT trans_err_log (err_msg, battery_pct, occured_at)
  ↓
PyQt 알람 표시
  ↓
(운영자) 물리적 복구 후 PyQt "수리 완료" 버튼
  ↓
UPDATE trans_stat.cur_stat='IDLE'
  ↓
FSM: FAILED → IDLE
```

### 7.2 장비 장애 (equip_err_log)
동일 패턴으로 `equip_err_log` + `equip_stat.cur_stat` 처리.

### 7.3 재시도 정책
- Jetson ESP bridge: 지수 백오프 1~60s, 32 이벤트 버퍼
- gRPC: 기본 retry (grpcio 설정)
- DB: 트랜잭션 롤백 후 운영자 알림

### 7.4 SPOF 대응
- Interface Service 장애: Management 직접 접속 가능 (PyQt)
- AWS RDS 장애: 로컬 PG (100.107.120.14) 로 폴백 (수동 설정)
- Jetson 장애: ESP32 펌웨어가 STOPPED 상태 유지, 수동 복구 대기

---

## 8. 생산 계획 및 스케줄링

### 8.1 7요소 우선순위 엔진
Confluence 통합 팩트 시트 기준. 주문을 생산 순서로 정렬할 때:
1. **납기** (due_date) — 가까운 것 우선
2. **수량** (qty) — 큰 것 vs 작은 것
3. **하중 등급** (load class) — 복잡도
4. **재질** (material) — 전환 비용
5. **직경** (diameter) — 주형 세팅
6. **후처리 옵션** (pp_options)
7. **고객 우선순위** (customer tier)

구현 위치: Management OrderingService / TaskManager (추가 개발 여지).

### 8.2 MVP 스케줄링
현재는 **FIFO (APPR 순서대로 MFG 전이)** 기준. 고도화는 후속 SPEC.

### 8.3 주문 ↔ 생산 계획 매핑
- `ord_pp_map`: 주문과 생산 계획(후처리 옵션)을 연결
- `pp_options`: 후처리 옵션 카탈로그 (pp_nm, extra_cost)

---

## 9. 데이터 추적 (Job ID · Item ID)

### 9.1 ID 체계
- **Order ID**: 고객 주문 단위
- **Job ID**: 용탕 주입 단위 (주형 1회)
- **Item ID**: 개별 주물 단위
- **RFID UID**: 제품 물리 식별자 (또는 Barcode UID)

### 9.2 연결 관계
```
orders / ord (1)
  └─ order_details / ord_detail (N)
       └─ items / item (N, qty만큼)
            ├─ rfid_scan_log (아이템 식별 이벤트)
            ├─ insp_task_txn (검사)
            ├─ strg_location_stat (보관)
            └─ ship_location_stat (출고)
```

### 9.3 end-to-end tracking 쿼리 (v2 스키마 예)
```sql
SELECT o.id AS order_id, o.status, i.id AS item_id,
       i.current_stage, i.rfid_uid, sl.status AS storage_status
FROM orders o
JOIN items i ON i.order_id = o.id
LEFT JOIN warehouse_racks wr ON i.rack_id = wr.id
WHERE o.id = $1;
```

---

## 10. 예외 및 에지 케이스

### 10.1 Orphan Handoff
- ESP32 버튼이 눌렸지만 활성 AMR task가 없음
- `handoff_acks.orphan=true`, `amr_id=null`, `task_id=null`
- 로그 기록만 하고 FSM 전이 없음

### 10.2 중복 RFID 스캔
- 짧은 시간 내 동일 UID 재스캔
- `rfid_scan_log` 는 append-only 이므로 모두 기록
- 애플리케이션에서 debounce 로직 (Wave 2 범위)

### 10.3 AMR 배터리 부족
- `trans_stat.battery_pct` < 20% 감지
- 진행 중 task 종료 후 `chg_location_stat` 이동 태스크 자동 생성
- `trans_task_txn.task_type='CHARGE'` 로 구분

### 10.4 후처리 병목
- 의사결정 규칙 B (`waiting_cnt >= Q_max`) 발동
- 이송 일시 중단 + 운영자 알람
- 후처리 완료 후 자동 재개

---

## 11. Confluence 팩트 참조

주요 공정 관련 Confluence 페이지:
- `Casting` (3375162): 제품 특성, 최적화 목표, 의사결정 규칙
- `Logistics` (3637320): VDA 5050 (미채택, 자체 통신)
- `Terminology` (3407906): 용어 사전 (주조/이송/검사/후처리 등)
- `User_Requirements` (3375120): UR 테이블 15개 R/O 등급
- `System_Requirements_v3` (6258774): SR-ORD-01 ~ SR-INSP-* 등
- `Scenarios` (15729093): 빈 페이지 (도메인은 Casting 페이지 참조)
- `[시나리오]후처리 작업구역 스위치 도입` (37160520): 후처리 수동 병행 시나리오
- `AMR` (7438566), `Robot_Arm` (7438542), `Conveyor` (7700525): HW 상세

---

## 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | V6 | 초기 작성. 8 단계 공정 + 주문 상태 FSM + AMR FSM + HW 이벤트 + 검사 + 에러 복구 |
