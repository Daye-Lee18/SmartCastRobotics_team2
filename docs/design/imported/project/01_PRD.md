# 01. 제품 요구사항 문서 (PRD)

> **프로젝트**: SmartCast Robotics — 주조 공장 스마트팩토리 통합 관제 시스템
> **버전**: v6 (2026-04-24 기준)
> **대상 독자**: SmartCast Robotics 내부 팀(기획, 개발, 운영)
> **원천 문서**: Confluence `addinedute` space + `docs/CONFLUENCE_FACTS.md` + `.moai/specs/`

---

## 1. 프로젝트 개요

### 1.1 비전
주문 접수부터 출고까지 **자동화 Level 4** 수준의 주조 공장 통합 관제 시스템을 구현한다. 맨홀 뚜껑(Manhole Cover)을 대상 제품으로 하여, 주형 제작 → 주조 → 냉각 → 탈형 → 후처리 → 검사 → 보관 → 출고 전 과정에서 AMR/로봇팔/컨베이어/비전 시스템을 조합한 무인화 공정을 시연한다.

### 1.2 목표
- **리드타임 최소화**: 냉각 완료된 주물을 후처리·검사 공정으로 이송할 때 전체 리드타임을 최소화
- **병목 제거**: 후처리 구역의 병목 및 재공품(WIP) 증가 방지
- **안정적 공정 흐름**: 장비/AMR/인력 장애 상황에서도 공정 중단 없이 복구 가능한 구조
- **SPOF 제거**: 클라우드(AWS) 이관·장애 상황에서도 공장 내부 가동 유지 (V6 이원화 아키텍처)

### 1.3 참고 기업
[기남금속](http://www.kinam.co.kr/) — 국내 맨홀 뚜껑 주조 전문업체. 제품 특성과 공정 레퍼런스.

---

## 2. 배경 및 문제 정의

### 2.1 도메인 특성 (Confluence 3375162 기준)
맨홀 뚜껑의 제품 특성:
- **무게**: 20 ~ 80 kg (인력 취급 시 부상 위험)
- **형상**: 단순 (원형 / 사각형)
- **디자인**: 다양 (고객 커스터마이즈 발생)
- **표면**: 후처리 필요 (버 제거, 그라인딩)
- **취급**: 충격에 강하나 긁힘/찍힘 발생 가능
- **생산 방식**: 동일 디자인 **소량 반복** → 다품종 소량 생산

### 2.2 기존 주조 공정의 고충
- **수작업 의존**: 냉각 → 탈형 → 후처리 이송이 사람 중심, 리드타임 편차 큼
- **후처리 병목**: 냉각 완료품의 후처리 대기열 통제 어려움
- **품질 편차**: 인력 교대/피로에 따른 검사 누락·오판
- **데이터 공백**: 공정 단계별 추적(Job ID) 미흡 → 원인 분석·개선 어려움

### 2.3 우리가 해결하는 것
- **무인 이송**: AMR + 로봇팔 조합으로 냉각장에서 후처리/검사장까지 자동 이송
- **흐름 제어**: 의사결정 규칙(대기시간 제한 / 병목 제한 / 배치 크기) 기반 자동 배차
- **전 공정 추적**: 주문 ID ↔ Job ID ↔ Item ID 연결된 end-to-end 데이터 기록
- **고객 투명성**: 원격 발주 + 상태 조회 기능으로 고객이 생산 진행도 실시간 확인

### 2.4 의사결정 규칙 (AMR 이송 트리거)
- **규칙 A — 대기시간 제한**: `if waiting_time >= T_max then move`
- **규칙 B — 병목 제한**: `if waiting_cnt >= Q_max then stop_transferring`
- **규칙 C — 배치 크기**: 대기 수량이 일정 이상이면 묶어서 전송

---

## 3. 타겟 사용자 (페르소나)

### 3.1 고객 (Customer)
- **대표 고객**: 광원건설, 포스코, LH, 한국도로공사, 한국수자원공사 등 19개 (로컬 DB `user_account` 기준)
- **사용 시스템**: Next.js 웹 대시보드 (customer 라우트)
- **핵심 니즈**: 표준 제품 조회 → 사양 선택 → 예상 견적/납기 확인 → 주문 제출 → 상태 조회

### 3.2 관리자 (Admin)
- **역할**: 고객 주문 검토, 승인/반려/수정 요청, 견적·납기 확정
- **사용 시스템**: Next.js 웹 대시보드 (admin 라우트)
- **핵심 니즈**: 주문 검토 화면, 생산 가능성 판단, 견적 수정, 승인 관리

### 3.3 공장 운영자 (Factory Operator)
- **역할**: 공정 실시간 모니터링, 생산 시작/중단, 설비 이상 대응, 수리 완료 처리
- **사용 시스템**: PyQt5 데스크톱 모니터링 앱 (Factory Operator PC)
- **핵심 니즈**: 공정 전체 상태 한눈에 보기, AMR/로봇팔/장비 상태 감시, 알람 대응

### 3.4 FMS (자동화 시스템)
- **역할**: AMR 다대 통제, 경로 할당, 충돌 회피
- **사용 시스템**: Management Service gRPC + ROS2 DDS
- **핵심 니즈**: 실시간 AMR 위치/배터리, 태스크 큐, Nav2 기반 경로 계획

### 3.5 비전 시스템 (Jetson)
- **역할**: 컨베이어 제품 검출, 이미지 캡처, AI 추론
- **사용 시스템**: Jetson Orin NX + C920 카메라 + ROS2
- **핵심 니즈**: Management Service로 이미지 스트리밍, ESP32 트리거 연동

---

## 4. 제품 범위 (In-scope / Out-of-scope)

### 4.1 In-scope (MVP)
- 원격 주문 시스템 (표준 제품 + 옵션 선택 + 견적 + 상태 조회)
- 관리자 주문 승인 워크플로우
- 주형 생성 / 용탕 주입 / 냉각 / 탈형 단계 공정 추적
- AMR 기반 팔레트·개별 이송
- 로봇팔 기반 picking / 파지 / 적재
- 컨베이어 기반 비전 검사 연동
- 양품·불량품 분류 및 출고
- 실시간 공정 모니터링 (PyQt)
- 8단계 공정 상태 추적 (주문 → 출고)

### 4.2 Out-of-scope (MVP 이후)
- 원자재 투입 자동화 (도가니 용광로 투입 등 O 등급)
- 불량품 재활용 (산업 관례상 금지)
- 후처리 자동화 (RA/AMR 기반 그라인딩·버 제거) — 후처리 작업자 스위치로 수동 처리
- 타 제품군 확장 (현재 맨홀 뚜껑만)
- 다국어 UI (한국어 전용)

### 4.3 가정·제약
- 저장 용기(파레트)는 실제 시연에서 AMR로 대체
- 자동화 Level 4를 목표로 Required(R) vs Optional(O) 구분 (Confluence 3375120 참조)

---

## 5. 기능 요구사항

### 5.1 주문 관련 (SR-ORD-*)

SR 원본: Confluence `System_Requirements_v3` (6258774)

| ID | 요구사항 | 핵심 기능 |
|---|---|---|
| SR-ORD-01 | 원격 발주 기능 | 표준 제품 조회 / 옵션 선택 / 디자인 미리보기 / 주문 가능 여부 검증 / 예상 견적·납기 안내 / 주문서 제출 |
| SR-ORD-01-01 | 표준 제품 조회 | 카테고리별 필터, 제품별 이미지·이름·재질·가격대·하중 등급 |
| SR-ORD-01-02 | 제품 옵션 선택 | 직경, 두께, 하중 등급, 재질, 후처리 옵션, 수량, 희망 납기 |
| SR-ORD-01-03 | 도면/디자인 확인 | 선택 사양 요약 + 기본 디자인 시안 + 미리보기 |
| SR-ORD-01-04 | 주문 가능성 검증 | 생산 가능 조합 여부 논리 검증, 불가 시 제출 차단 |
| SR-ORD-01-05 | 예상 견적·납기 | 기본 단가 + 옵션 가산비 + 수량 공식, 납기 범위 표시, 주문 ID 부여 |
| SR-ORD-01-06 | 주문서 제출 | 회사명·연락처·배송지·담당자·이메일 필수, 요약 페이지, 5단계 이내 완료 |
| SR-ORD-02 | 주문 상태 조회 | 6단계 상태(접수/검토/승인/생산/출하 준비/완료), 상태 변경 알림 |
| SR-ORD-03 | 관리자 검토·승인 | 상세 사양 확인, 생산 가능성 판단, 견적 수정, 승인/반려/수정 요청 |

### 5.2 공정·HW 관련 (Confluence 3375120 — UR 테이블)

R = Required (MVP 필수), O = Optional

| 공정 | 요구사항 | 등급 | Entity/Tracking |
|---|---|---|---|
| 주문/생산 계획 | 고객 주문·생산 오더 생성 (UR_01) | **R** | Order ID, Qty, Product/Customer, BOM |
| 원자재 | 원자재 투입 관리 | O | Material(고/액), Weight/Temp |
| 원자재 | 도가니 용광로 투입 | O | Furnace (Idle/Heating/Ready) |
| 주형/주조 | 주형 생성 | **R** | Mold ID, Ready/In-progress/Completed, Image |
| 주형/주조 | 용탕 주입 | **R** | Ladle, Mold, Pouring, Temp, Flow Rate, Job ID |
| 냉각/탈형 | 주물 냉각 모니터링 | **R** | Casting, Cooling/Completed, Temp, Time |
| 냉각/탈형 | 주물 탈형 | **R** | Robot Arm, Task ID |
| 이송 | 주물 팔레트 적재 | O | Pallet, Qty, Pallet ID |
| 이송 | 팔레트 구역 이송 | **R** | AMR, Pallet ID |
| 후처리 | 후처리 구역 청소 | O | AMR, Active/Inactive |
| 후처리 | 후처리→검사 이송 | **R** | Robot Arm, AMR, Task ID |
| 검사 | 주물 품질 검사 | **R** | Camera, Image, Image ID |
| 분류/출하 | 불량품 폐기 이송 | **R** | AMR, Task ID |
| 분류/출하 | 양품 팔레트 적재 | **R** | Robot Arm, Order Info |
| 분류/출하 | 양품 팔레트 이송 | **R** | AMR, Task ID |

**핵심 규칙**:
- 자동화 Level 4를 목표로 R/O 선정
- **불량품 재활용 금지** (산업 관례)
- FMS 도입 시 Job ID를 자동화 시스템 전반에 tracking

---

## 6. 비기능 요구사항 (NFR)

### 6.1 성능
- 주문 제출 절차 **최대 5단계** 이내 완료 (SR-ORD-01-06)
- 실시간 이미지 스트리밍 지연 ≤ 300ms (Jetson → Management gRPC)
- PyQt 대시보드 주기 갱신 ≤ 1s
- AMR 태스크 할당 응답 ≤ 500ms

### 6.2 안정성 / SPOF 제거 (V6 이원화)
- **Interface Service (FastAPI :8000)** 장애 시에도 **Management Service (gRPC :50051)** 로 공장 가동 유지
- AWS 이관·장애 중에도 Factory Operator PC 직결 유지
- DB: PostgreSQL 단독 (SQLite 폴백 제거)
- DATABASE_URL 미설정 시 fail-fast

### 6.3 보안
- 주문자 정보·연락처 안전 저장 (SR-ORD-03 비기능)
- 관리자 기능은 권한 있는 사용자만 접근
- AWS RDS 접속 SSL `verify-full` + RDS CA 번들 필수
- 개발 중에는 평문 자격증명 허용, 프로덕션 배포 전 SSH 키/Keychain 전환

### 6.4 추적성
- 주문 ID ↔ Job ID ↔ Item ID 전 경로 추적 가능
- 모든 task_txn 테이블에 req_at / start_at / end_at 기록
- 에러 로그: equip_err_log / trans_err_log 집계
- RFID / 바코드 스캔 이력 append-only (`public.rfid_scan_log`)

### 6.5 유지보수성
- TRUST 5 품질 프레임워크 (Tested/Readable/Unified/Secured/Trackable) 준수
- MoAI-ADK 거버넌스 (SPEC → Plan → Run → Sync)
- Confluence 공식 문서와 주 1회 수기 재검증 + launchd 매일 자동 동기화

### 6.6 확장성
- HW 추가 시 ROS2 DDS 네임스페이스로 AMR 확장
- 장비 추가 시 `res`/`equip` 테이블에 행 추가로 해결 (스키마 변경 불필요)

---

## 7. 성공 지표 (KPI)

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| 평균 리드타임 (냉각 완료 → 출고 준비) | ≤ 30분 | `item.updated_at` 시계열 분석 |
| 후처리 구역 대기열 길이 평균 | ≤ 3건 | `pp_task_txn` QUE 상태 집계 |
| AMR 가동률 | ≥ 80% | `trans_stat` cur_stat=MOVING 비율 |
| 주문 접수 → 승인 소요 시간 | ≤ 4시간 | `ord_log` RCVD→APPR 차이 |
| 검사 통과율 | ≥ 95% | `insp_task_txn.result=true / total` |
| 시스템 가동률 (Interface 장애 시 포함) | ≥ 99% | Management Service uptime |

---

## 8. MVP 스코프 및 우선순위

### 8.1 필수 (MVP Must-have)
1. 원격 주문 시스템 (SR-ORD-01/02/03)
2. AMR 기반 주물 팔레트 이송 (UR R 등급)
3. 로봇팔 기반 탈형 + picking + 양품 적재
4. 컨베이어 비전 검사 연동
5. PyQt 실시간 모니터링
6. V6 Interface/Management 이원화
7. 8단계 공정 상태 추적
8. 에러 복구 버튼 (Repair, Handoff Button)

### 8.2 권장 (Should-have, MVP 후속)
- 후처리 구역 청소 자동화
- 원자재 투입 자동화
- 불량품 폐기 이송

### 8.3 배제 (Won't-have, 현 단계)
- 후처리 자체 자동화 (작업자 스위치 도입 시나리오로 대체)
- VLA / LLM 기반 고급 인지 (현재는 기술 조사 단계, Confluence 7405754/7438588)
- 다국어 UI

---

## 9. 로드맵 (주요 단계)

실제 이행 이력은 `CLAUDE.md` 의 V6 Phase 상태 블록과 `docs/CONFLUENCE_FACTS.md` 참조.

| 단계 | 내용 | 상태 |
|---|---|---|
| Phase A | PyQt WebSocket 의존 제거 | ✅ 머지 |
| Phase B | ROS2 퍼블리셔 이관 | ✅ 머지 |
| Phase C-1 | Mgmt gRPC 클라이언트 + `/api/management/health` | ✅ 머지 |
| Phase C-2 | Interface Proxy (SPEC-C2) | ✅ 머지 |
| Phase C-3 | Management 기동 복구 + models_mgmt 선별 import | ✅ 머지 |
| Phase D-1/D-2 | MQTT 제거 + Jetson Serial relay | ✅ 머지 |
| SPEC-RFID-001 Wave 2 | RC522 → gRPC `ReportRfidScan` | 🟡 진행 |
| SPEC-AMR-001 Wave 3 | Handoff Button 배포 + DB 검증 | 🟢 배포 완료, 실물 버튼 push만 잔존 |
| Barcode HID 경로 | 바코드 실시간 적재 | 🟢 실측 완료 |
| Event Bridge Contract | services/event_bridge.py | ✅ 구현 완료 (569줄 + 20 tests) |

---

## 10. 관련 문서

- **시스템 설계**: [02_DESIGN.md](./02_DESIGN.md)
- **공정 프로세스**: [03_PROCESS.md](./03_PROCESS.md)
- **개발 가이드**: [04_DEVELOPMENT.md](./04_DEVELOPMENT.md)
- **교육 자료**: [05_TRAINING.md](./05_TRAINING.md)
- **사용자 매뉴얼**: [06_MANUAL.md](./06_MANUAL.md)

**원천 문서**:
- Confluence 팩트 수집본: [../CONFLUENCE_FACTS.md](../CONFLUENCE_FACTS.md)
- V6 아키텍처: [../../CLAUDE.md](../../CLAUDE.md)
- 아키텍처 다이어그램: [../architecture/](../architecture/)
- SPEC 디렉터리: [`.moai/specs/`](../../.moai/specs/)

---

## 변경 이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-04-24 | v6.0 | 초기 작성. Confluence 22 페이지 + `.moai/specs/` 9건 종합 |
