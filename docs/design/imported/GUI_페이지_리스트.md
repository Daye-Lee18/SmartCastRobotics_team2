# GUI 페이지 리스트 — 주물 스마트 공장 관제 시스템

---

## 1. 통합 대시보드 (Global Dashboard)
**경로:** `/`
**목적:** 공장 전체의 가동 현황을 한눈에 파악하고 이상 상황에 즉각 대응하기 위한 관제탑 페이지

### 상단 (Summary Cards)
- 오늘의 생산 목표 달성률 (%) — `productionGoalRate`
- 실시간 가동 로봇 수 — `activeRobots`
- 미처리 주문 건수 — `pendingOrders`
- 금일 발생 알람 수 — `todayAlarms`

### 중앙 (Main Map)
- 공정 레이아웃(Map): Blender 3D 렌더 기반 공장 도면, 로봇(AMR/Cobot) 실시간 위치 및 경로 시각화 (SR-CTL-01)
- 설비 상태 아이콘: 용해로, 조형기, 컨베이어의 상태(가동/정지/오류)를 색상으로 표시
- 장비 상태 범례 (가동 중/유휴/오류/정비 중/충전 중)

### 우측 (Incident Feed)
- 실시간 알림 리스트: severity 기준 정렬 (critical > warning > info) (SR-CTL-03)
- 장비명, 구역, 이상 수치, 발생 시각 표시
- 미확인 알림 pulse 인디케이터

### 하단
- 주간 생산 추이 차트 (Recharts AreaChart)
- 최근 주문 테이블 (고객사, 금액, 납기, 상태)

---

## 2. 생산 모니터링 (Production Control)
**경로:** `/production`
**목적:** 주물 생산 공정의 세부 데이터(용해~탈형)를 관리하고 설비를 제어하는 페이지

### 상단 (Process Flow)
- [원재료 투입/용해] → [조형] → [주탕] → [냉각/탈형] → [후처리/검사] 5단계 프로세스 인디케이터
- 단계별 상태 색상 + 진행률 바 + 화살표 연결

### 중앙 (Live Data Charts)
- 용해로: 현재 온도 실시간 그래프 및 목표 온도 도달 곡선 (Recharts AreaChart) (SR-CAST-01-02)
- 조형/주탕: 패턴 정보, 성형 압력(bar) 게이지, 주탕 각도(deg) 게이지, 주탕 온도 (SR-CAST-02)
- 시간별 생산량/불량 차트 (BarChart)

### 우측 (Equipment Control)
- 비상 정지(E-Stop) 버튼 (빨간색, 크고 눈에 잘 띄게)
- 냉각 진행률(%) 원형 프로그레스 + 현재/목표 온도 + 잔여 시간 타이머
- 설비별 제어 스위치 (Auto/Manual 토글)
- 설비 목록: 설비명, 설치 위치, 상태 표시

### 하단
- 공정 파라미터 이력 테이블 (8공정 × 온도/압력/각도/출력/냉각률/진행률/시간)

---

## 3. 주문 관리 (Order & Sales)
**경로:** `/orders`
**목적:** 고객의 원격 발주를 검토하고 전체 주문 라이프사이클을 관리하는 페이지

### 좌측 (Order List)
- 상태별 탭: 전체/신규 주문/검토 중/승인/생산 중/완료 (카운트 배지) (SR-ORD-02)
- 주문 카드: 회사명, 금액, 일시, 상태 배지

### 중앙 (Order Details)
- 제품 상세 테이블: OrderDetail 기반 (제품명, 규격, 재질, 수량, 단가, 소계, 후처리, 로고)
- 견적/납기 계산기: 총 견적 금액, 예상 생산 기간, 요청 납기, 확정 납기 (SR-ORD-03)
- 고객 정보: 담당자, 연락처, 배송주소, 비고
- 주문 이력 타임라인: 접수 → 상태변경 → 납기확정

### 하단
- 액션 버튼: 승인/반려 (pending/reviewing), 생산 시작 (approved)

---

## 4. 품질 검사 및 후처리 (Quality & Post-Processing)
**경로:** `/quality`
**목적:** 생산된 주물의 양품 여부를 판정하고 분류 장치를 제어하는 페이지

### 상단 (Inspection Stats)
- 금일 총 검사 수 (양품/불량 서브텍스트)
- 양품률(%) — 조건부 색상 (95%+:녹색, 90~95%:노란색, 90%-:빨간색) (SR-INS-01)
- 주요 불량 유형 TOP 3 (색상 뱃지)

### 중앙 (Vision/Sensor Feed)
- 검사 구간 카메라 시뮬레이션: 스캔라인 효과 + PASS/FAIL 오버레이 + 신뢰도/시각
- 분류 장치 상태: 원형 다이얼 (현재 각도), 분류 방향, 동작 성공 여부 (SR-INS-03)
- 불량률 추이 차트 (DefectRateChart)
- 생산량 vs 불량 차트 (ProductionVsDefectsChart)

### 우측
- 불량 유형 분포 PieChart (DefectTypeDistChart)
- 검사 기준 참조 패널 (제품명, 목표 치수, 허용 오차, 판정 임계값)

### 하단 (Defect Log)
- 불량 검사 기록 테이블: 이미지(플레이스홀더), 검사ID, 제품ID, 판정, 불량유형, 상세사유, 신뢰도(프로그레스바), 검사시각

---

## 5. 물류 및 이송 현황 (Logistics & Fleet)
**경로:** `/logistics`
**목적:** 이송 자원(AMR)의 임무 배정과 출고 지시를 관리하는 페이지

### 좌측 (Task Queue)
- 이송 작업 요청 리스트: priority 기준 정렬 (SR-TR-01)
- 우선순위 뱃지 (긴급=빨강, 보통=노랑, 낮음=회색)
- 경로(출발지→도착지), 물품/수량, 배정 AMR, 상태

### 중앙 (Fleet Management)
- AMR별 상태 카드 (SR-TR-02):
  - 배터리 잔량 (프로그레스 바, 20% 미만 경고)
  - 현재 속도 (m/s)
  - 적재 물품 정보 + Task ID
- 충전 상태 표시
- 이송 작업 클릭 시 해당 AMR 포커스 연동

### 하단
- 출고 지시 테이블: 제품명, 수량, 납품처, 정책(LIFO/FIFO), 완료 상태, "완료 처리" 버튼

---

## 6. 적재 현황 (Storage)
**경로:** `/storage`
**목적:** 물류/이송 화면에서 분리한 창고 랙 적재 상태 전담 페이지

### 상단
- 전체 랙, 점유 랙, 예약 랙, 점유율 KPI

### 중앙 (Storage Map)
- 창고 랙 그리드 (3행 × 6열): 위치별 점유 상태 색상 구분 (SR-STO-03)
- 랙 번호, 점유 물품/수량
- 호버 시 상세 정보 팝업
- 범례 + 상태별 통계

### 하단
- 랙 상세 테이블: 랙, 상태, 품목, 수량, 비고

---

## 7. 고객 발주 (Customer Order)
**경로:** `/customer`
**목적:** 고객이 직접 원격으로 발주를 접수하는 독립 페이지 (별도 레이아웃)

- 5단계 발주 폼 (제품 선택 → 규격 입력 → 후처리 → 배송 → 확인)
- 독립 레이아웃 (관리자 사이드바 없음)

---

## 공통 컴포넌트
| 컴포넌트 | 파일 | 사용 위치 |
|----------|------|----------|
| AdminShell | `src/components/AdminShell.tsx` | 전체 레이아웃 (사이드바+헤더) |
| Sidebar | `src/components/Sidebar.tsx` | 좌측 네비게이션 |
| Header | `src/components/Header.tsx` | 상단 헤더 |
| FactoryMap | `src/components/FactoryMap.tsx` | 대시보드 3D 렌더 맵 |
| WeeklyProductionChart | `src/components/charts/WeeklyProductionChart.tsx` | 대시보드 |
| DefectRateChart | `src/components/charts/DefectRateChart.tsx` | 품질 검사 |
| DefectTypeDistChart | `src/components/charts/DefectTypeDistChart.tsx` | 품질 검사 |
| ProductionVsDefectsChart | `src/components/charts/ProductionVsDefectsChart.tsx` | 품질 검사 |
