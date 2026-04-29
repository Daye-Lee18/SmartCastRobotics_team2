# 주조 생산관리 관제 시스템 — GUI 설계 문서

> **프로젝트**: 주물 스마트 공장 관제 시스템 (Casting Factory MES)
> **버전**: v3.2 (2026-04-02)
> **기술 스택**: Next.js 16 + TypeScript + Tailwind CSS + FastAPI + PostgreSQL 16 + TimescaleDB + MQTT + WebSocket + Three.js
> **GitHub**: https://github.com/kiminbean/casting-factory

---

## 1. 시스템 개요

주물(맨홀 뚜껑/그레이팅) 생산 공장의 실시간 생산 관제, 주문 관리, 품질 검사, 물류/이송, 생산 스케줄링을 통합 관리하는 웹 기반 대시보드 시스템.

### 시스템 구성도

```
[브라우저] ←→ [Next.js 16 (포트 3000)] ←→ [FastAPI (포트 8000)] ←→ [PostgreSQL 16 + TimescaleDB]
                    ↕                              ↕                          ↕
           [Three.js 3D 맵]              [WebSocket /ws/dashboard]      [Redis Cache]
                                                   ↕
                                         [MQTT Broker (Mosquitto)]
                                                   ↕
                                   [ESP32 Conveyor / Cobot / AMR / Vision]
```

> DB 참고: 개발 초기(Phase 0) SQLite 로 시작 → Phase 1 부터 PostgreSQL 16 + TimescaleDB 로 이전. 다중 하드웨어 동시 쓰기, JSONB 저장, 시계열 하이퍼테이블 지원 때문.

### 접속 정보
- 프론트엔드: `http://localhost:3000` (LAN: `http://192.168.0.16:3000`)
- 백엔드 API: `http://localhost:8000` (Swagger: `http://localhost:8000/docs`)

---

## 2. 페이지 구성 (8개 라우트)

| # | 라우트 | 페이지명 | 레이아웃 | 상태 |
|---|--------|---------|---------|------|
| 1 | `/` | 대시보드 | 관리자 (사이드바) | 완료 |
| 2 | `/production` | 생산 모니터링 | 관리자 (사이드바) | 완료 |
| 3 | `/production/schedule` | **생산 계획** | 관리자 (사이드바) | **완료 (신규)** |
| 4 | `/orders` | 주문 관리 | 관리자 (사이드바) | 완료 |
| 5 | `/quality` | 품질 검사 | 관리자 (사이드바) | 완료 |
| 6 | `/logistics` | 물류/이송 | 관리자 (사이드바) | 완료 |
| 7 | `/customer` | 고객 발주 (5단계 폼) | 독립 레이아웃 | 완료 |
| 8 | `/customer/orders` | 고객 주문 조회 | 독립 레이아웃 | 완료 |

### 사이드바 네비게이션

```
┌──────────────────────┐
│  🏭 주물공장 관제     │
├──────────────────────┤
│  📊 대시보드          │  /
│  📈 생산 모니터링     │  /production
│  📅 생산 계획         │  /production/schedule  ← 신규
│  📋 주문 관리         │  /orders
│  🔬 품질 검사         │  /quality
│  🚛 물류/이송         │  /logistics
└──────────────────────┘
```

---

## 3. 페이지별 GUI 상세

### 3-1. 대시보드 (`/`)

**목적**: 공장 전체 현황을 한눈에 파악

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 요약 카드 (4개) | 생산 목표 달성률, 가동 로봇 수, 미처리 주문, 금일 알람 |
| 주간 생산 차트 | Recharts 라인 차트 (7일간 생산량/불량률) |
| 알림 패널 | 심각도 순 정렬 (critical → warning → info) |
| 최근 주문 | 최근 5건 요약 (주문번호, 회사명, 금액, 상태) |
| 설비 현황 | 설비 타입별 상태 (가동/유휴/점검/오류) |

**데이터 소스**: `GET /api/dashboard/stats`, `GET /api/alerts`, `GET /api/production/equipment`, `GET /api/orders`, `GET /api/production/metrics`

---

### 3-2. 생산 모니터링 (`/production`)

**목적**: 8단계 공정 흐름 실시간 감시 + 설비 제어

**공정 흐름 (5단계 통합 뷰)**:
```
원재료 투입/용해 → 조형 → 주탕 → 냉각/탈형 → 후처리/검사
```

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 공정 흐름 카드 | 5단계 카드 (상태별 색상: 가동=파랑, 완료=초록, 오류=빨강) |
| 용해로 온도 차트 | AreaChart (30분간 현재 온도 vs 목표 온도) |
| 냉각 진행률 | 원형 프로그레스 + 남은 시간 |
| 시간별 생산량 | BarChart (시간대별 생산/불량) |
| 설비 제어 패널 | 설비별 상태 버튼 (가동/유휴/충전/점검/오류) + 자동/수동 모드 토글 |
| 3D 공장 맵 | Three.js GLB 모델 (factory-map2.glb) + AMR 실시간 이동 |

**설비 타입**: 용해로(4), 조형기, 로봇팔(6), AMR(3), 컨베이어(2), 카메라, 분류기

**데이터 소스**: `GET /api/production/stages`, `GET /api/production/equipment`, `GET /api/production/metrics`

---

### 3-3. 생산 계획 (`/production/schedule`) — 신규

**목적**: 승인된 주문의 생산 우선순위 계산 + 공정 할당 + 생산 개시

**워크플로우**:
```
승인 주문 다중 선택 → 우선순위 계산 → 수동 순서 조정(선택) → 생산 시작
```

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 헤더 | "생산 계획" 타이틀 + 우선순위 계산 버튼 + 생산 시작 버튼 |
| 우선순위 결과 (상단) | 계산 결과 카드 목록 (순위, 점수, 사유, 요인별 점수 바) |
| 승인 주문 목록 (하단) | 체크박스 다중 선택 (주문번호, 회사명, 납기일, 금액) |

**우선순위 계산 엔진 (7가지 가중 요소, 100점 만점)**:

| 요소 | 배점 | 산출 방식 |
|------|------|----------|
| 납기일 긴급도 | 25점 | D-day 기준 (3일 이내=25, 7일=20, 14일=15, 30일=10) |
| 착수 가능 여부 | 20점 | 공정 idle + 용해로/조형기/AMR 가용성 |
| 주문 체류 시간 | 15점 | 승인 후 경과일 |
| 지연 위험도 | 15점 | 예상완료일 vs 납기일 마진 |
| 고객 중요도 | 10점 | 주문 금액 상위 20% 판별 |
| 수량 효율 | 10점 | 소량 우선 (빠른 회전) |
| 세팅 변경 비용 | 5점 | 직전 작업 제품 연속 시 보너스 |

**결과 카드 표시 항목**:
- 순위 번호 (↑↓ 수동 조정 버튼)
- 주문번호, 회사명, 제품명, 수량
- 총점 (/100), 지연 위험도 배지 (높음/보통/낮음)
- 착수 가능 여부 (불가 시 빨간 테두리 + 차단 사유)
- 추천 사유 (상위 2~3개 요인 조합)
- 요인별 점수 분석 바 (7개)

**수동 순서 변경**: ↑↓ 버튼 → 사유 입력 모달 (필수) → 변경 이력 API 기록

**생산 시작**: 확인 모달 → 배치 상태 전환 (approved → in_production) + ProductionJob 레코드 생성

**데이터 소스**: `GET /api/orders`, `POST /api/production/schedule/calculate`, `POST /api/production/schedule/start`, `POST /api/production/schedule/priority-log`

---

### 3-4. 주문 관리 (`/orders`)

**목적**: 전체 주문 현황 조회 + 승인/반려/생산 시작

**레이아웃**: 좌측 주문 목록 (380px) + 우측 주문 상세 패널

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 상태 탭 | 전체, 신규 주문, 검토 중, 승인, 생산 중, 완료 (탭별 건수 표시) |
| 주문 카드 목록 (좌측) | 주문번호, 회사명, 날짜, 금액, 상태 배지 |
| 주문 상세 (우측) | 제품 상세 테이블, 견적/납기 계산, 고객 정보, 주문 이력 |
| 액션 버튼 (하단) | 승인 / 수정 요청 / 반려 (pending/reviewing) 또는 생산 시작 (approved) |

**주문 상태 흐름**:
```
접수(pending) → 검토 중(reviewing) → 승인(approved) → 생산 중(in_production) → 출하 준비(shipping_ready) → 완료(completed)
                                    ↘ 반려(rejected)
```

**데이터 소스**: `GET /api/orders`, `GET /api/orders/{id}/details`, `PATCH /api/orders/{id}/status`, `PATCH /api/orders/{id}`

---

### 3-5. 품질 검사 (`/quality`)

**목적**: AI 비전 기반 실시간 품질 검사 현황 + 분류 장치 모니터링

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 검사 통계 카드 (4개) | 금일 총 검사 수, 양품률(%), 분류 장치 상태, 비전 검사 피드 |
| 불량 유형 분포 차트 | DefectTypeDistChart (파이/바 차트) |
| 불량률 추이 차트 | DefectRateChart (라인 차트) |
| 생산량 vs 불량 | ProductionVsDefectsChart (복합 차트) |
| 검사 기준 참조 | 제품별 목표 치수, 허용 오차, 판정 임계값 |
| 불량 검사 로그 테이블 | 불합격 검사 기록 (제품ID, 불량유형, 신뢰도, 검사일시) |

**불량 유형 7종**: 표면 기포, 수축 결함, 치수 미달, 균열, 표면 오염, 변형, 내부 결함

**데이터 소스**: `GET /api/quality/inspections`, `GET /api/quality/stats`, `GET /api/quality/standards`, `GET /api/quality/sorter-logs`

---

### 3-6. 물류/이송 (`/logistics`)

**목적**: 이송 큐 관리, AMR 플릿 관리, 창고 랙 맵, 출고 주문

**구성 요소**:

| 영역 | 설명 |
|------|------|
| 이송 작업 큐 | 우선순위 정렬 (긴급/보통/낮음), 출발-도착-품목-상태 표시 |
| AMR 플릿 관리 (3대) | 상태(유휴/작업중/충전필요/사용불가), 배터리 잔량 바, 현재 작업 |
| 창고 랙 맵 (6x4 그리드) | 슬롯 상태 색상 (빈/사용/예약/비가용), 마우스오버 상세 |
| 창고 통계 | 상태별 슬롯 수 요약 |
| 출고 주문 목록 | 제품명, 수량, 목적지, 정책(LIFO/FIFO), 완료 처리 버튼 |

**AMR 상태 4단계**: 유휴(idle), 작업중(running), 충전필요(배터리 <20%), 사용불가(maintenance/error)

**데이터 소스**: `GET /api/logistics/tasks`, `GET /api/production/equipment`, `GET /api/logistics/warehouse`, `GET /api/logistics/outbound-orders`

---

### 3-7. 고객 발주 (`/customer`)

**목적**: 고객이 직접 제품을 선택하여 주문하는 5단계 폼

**독립 레이아웃** (관리자 사이드바 없음)

**5단계 스텝**:

| 단계 | 화면 | 설명 |
|------|------|------|
| Step 1 | 제품 선택 | 카테고리 필터 (전체/맨홀/그레이팅) + 제품 카드 (재질/하중등급 표시) |
| Step 2 | 규격 입력 | 직경, 두께, 하중등급, 재질 선택 |
| Step 3 | 후처리/견적 | 아이콘 이미지 카드 선택 (표면 연마/방청 코팅/아연 도금/로고 삽입) + 디자인 시안 미리보기 + 자동 견적 계산 |
| Step 4 | 고객 정보 | 회사명, 담당자, 연락처, 이메일, 배송지, 납기 요청일, 비고 |
| Step 5 | 주문 완료 | 전체 요약 (제품/규격/후처리/비고/납기/배송지/이메일/예상금액) |

---

### 3-8. 고객 주문 조회 (`/customer/orders`)

**목적**: 고객이 자신의 주문 상태를 조회

**구성 요소**:
- 검색: 주문번호, 연락처, 회사명으로 검색
- 주문 카드: 주문번호, 회사명, 상태 배지, 날짜
- 6단계 상태 파이프라인: 접수 → 검토 → 승인 → 생산 중 → 출하 준비 → 완료
- 상세 보기: 제품 테이블, 견적/납기 정보

---

## 4. 공통 UI 패턴

### 4-1. 로딩/에러 처리

모든 페이지에 공통 적용:

| 상태 | UI |
|------|-----|
| 로딩 중 | 회전 스피너(Loader2) + "데이터를 불러오는 중..." 텍스트 |
| API 에러 | 경고 아이콘(AlertTriangle) + 에러 메시지 + "다시 시도" 버튼 |
| 빈 데이터 | 연한 아이콘 + "데이터가 없습니다" 안내 |

### 4-2. 디자인 시스템

| 요소 | 스펙 |
|------|------|
| 컬러 | Tailwind CSS 기본 팔레트 (blue-600 주색, gray-900 사이드바) |
| 카드 | `bg-white rounded-xl shadow-sm border border-gray-200 p-5` |
| 버튼 | `rounded-lg font-semibold` + 색상별 변형 (primary/success/danger/warning) |
| 배지 | `rounded-full px-2.5 py-0.5 text-sm font-semibold` |
| 아이콘 | Lucide React 라이브러리 |
| 차트 | Recharts (SSR 비활성화, 동적 임포트) |
| 3D 맵 | @react-three/fiber + drei (OrbitControls, 스페이스+좌클릭=Pan) |
| 폰트 | 시스템 기본 (sans-serif), 숫자는 font-mono |

### 4-3. 반응형 브레이크포인트

| 용도 | 해상도 |
|------|--------|
| 관제실 모니터 (주 타겟) | 1920x1080 이상 |
| 태블릿 대응 | 1024px+ |
| 모바일 대응 | 제한적 (관제실 전용) |

---

## 5. 백엔드 API 목록 (27개 + WebSocket)

### 대시보드
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/dashboard/stats` | 대시보드 요약 통계 |

### 주문 관리
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/orders` | 전체 주문 목록 |
| POST | `/api/orders` | 신규 주문 생성 |
| PATCH | `/api/orders/{id}/status` | 주문 상태 변경 |
| PATCH | `/api/orders/{id}` | 주문 필드 수정 (견적/납기/비고) |
| GET | `/api/orders/{id}/details` | 주문 상세 품목 목록 |
| POST | `/api/orders/{id}/details` | 주문 품목 추가 |
| GET | `/api/products` | 제품 마스터 목록 |

### 생산 모니터링
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/production/stages` | 공정 단계 목록 |
| PATCH | `/api/production/stages/{id}` | 공정 단계 업데이트 |
| GET | `/api/production/metrics` | 일별 생산 지표 |
| GET | `/api/production/equipment` | 설비 목록 |

### 생산 스케줄링 (신규)
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/production/schedule/calculate` | 우선순위 계산 |
| POST | `/api/production/schedule/start` | 생산 개시 (배치 상태 전환) |
| GET | `/api/production/schedule/jobs` | 생산 작업 목록 |
| POST | `/api/production/schedule/priority-log` | 우선순위 변경 이력 기록 |
| GET | `/api/production/schedule/priority-log/{id}` | 주문별 변경 이력 조회 |

### 품질 검사
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/quality/inspections` | 검사 기록 목록 |
| GET | `/api/quality/stats` | 품질 통계 |
| GET | `/api/quality/standards` | 검사 기준 목록 |
| GET | `/api/quality/sorter-logs` | 분류기 로그 |

### 물류/이송
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/logistics/tasks` | 이송 작업 목록 |
| POST | `/api/logistics/tasks` | 이송 작업 생성 |
| PATCH | `/api/logistics/tasks/{id}/status` | 이송 상태 변경 |
| GET | `/api/logistics/warehouse` | 창고 랙 목록 |
| GET | `/api/logistics/outbound-orders` | 출고 주문 목록 |
| PATCH | `/api/logistics/outbound-orders/{id}/complete` | 출고 완료 처리 |

### 알림
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/alerts` | 알림 목록 |

### WebSocket
| Endpoint | 설명 |
|----------|------|
| `ws://localhost:8000/ws/dashboard` | 실시간 브로드캐스트 (5초 간격) |

---

## 6. 데이터 모델 (15개 테이블)

| 테이블 | 설명 | 주요 필드 |
|--------|------|----------|
| orders | 주문 정보 | id, customer_name, company_name, status, total_amount, requested_delivery |
| order_details | 주문 품목 | order_id(FK), product_name, quantity, spec, material, post_processing |
| products | 제품 마스터 | name, category, base_price, option_pricing |
| process_stages | 공정 단계 | stage, status, temperature, progress, equipment_id |
| equipment | 설비 | name, type, status, pos_x/y/z, battery, speed |
| alerts | 알림 | type, severity, message, zone |
| inspection_records | 검사 기록 | result(pass/fail), defect_type, confidence |
| inspection_standards | 검사 기준 | product_id, tolerance_range, threshold |
| sorter_logs | 분류기 로그 | sort_direction, sorter_angle, success |
| transport_tasks | 이송 작업 | from/to, priority, status, assigned_robot_id |
| warehouse_racks | 창고 랙 | zone, rack_number, status, item_name |
| outbound_orders | 출고 주문 | product_name, quantity, policy(LIFO/FIFO) |
| production_metrics | 생산 통계 | date, production, defects, defect_rate |
| **production_jobs** | **생산 작업 (신규)** | order_id(FK), priority_score, priority_rank, assigned_stage, status |
| **priority_change_logs** | **우선순위 변경 이력 (신규)** | order_id, old_rank, new_rank, reason, changed_by |

---

## 7. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-03-30 | 초기 구현 — 5개 페이지 + Mock 데이터 |
| v2.0 | 2026-03-31 | SR v3 반영 — 공장 맵, 컨베이어/분류 장치 제어, 출고 관리 |
| v2.1 | 2026-04-01 | Three.js 실시간 3D 맵 (GLB) + FactoryMapEditor |
| v3.0 | 2026-04-01 | FastAPI 백엔드 + SQLite DB + WebSocket + REST API 22개 |
| v3.1 | 2026-04-02 | SPEC-API-001: 대시보드 Mock→API 전환 |
| v3.2 | 2026-04-02 | SPEC-API-002: 전체 5개 페이지 Mock→API 전환 (27개 엔드포인트) |
| v3.3 | 2026-04-02 | SPEC-CTL-001: 생산 스케줄링 모듈 (생산 계획 페이지 신규, 우선순위 7요소 계산 엔진) |
| **v3.4** | **2026-04-07** | **UI 분리: Next.js 관리자 웹(생산계획/주문/품질/입출고) + PyQt5 관제 모니터링 데스크톱 앱 분리 (Confluence 17956894)** |
