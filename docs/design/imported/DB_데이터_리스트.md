# DB 데이터 리스트 — 주물 스마트 공장 관제 시스템

---

## 1. [주문 관리] 페이지 관련 데이터 (Order Management)

### 주문 마스터 (Order)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 주문 ID (예: ORD-2026-001) |
| customerId | string | 고객 ID |
| customerName | string | 고객 담당자명 |
| companyName | string | 회사명 |
| contact | string | 연락처 |
| shippingAddress | string | 배송지 주소 |
| totalAmount | number | 주문 합계 금액 (원) |
| status | OrderStatus | 주문 상태 (접수/검토/승인/생산/출하/완료/반려) |
| requestedDelivery | string | 희망 납기일 |
| confirmedDelivery | string | 실제 확정 납기일 |
| createdAt | string | 주문 접수 일시 |
| updatedAt | string | 최종 수정 일시 |
| notes | string | 비고 |

### 주문 상세 (OrderDetail)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 상세 ID |
| orderId | string (FK→Order) | 주문 ID |
| productId | string (FK→Product) | 제품 ID |
| productName | string | 제품명 |
| quantity | number | 수량 |
| spec | string | 선택 규격 (직경/두께/하중) |
| material | string | 재질 옵션 |
| postProcessing | string | 후처리 조건 |
| logoData | string | 로고/문구 데이터 |
| unitPrice | number | 단가 (원) |
| subtotal | number | 소계 (원) |

### 제품 마스터 (Product)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 제품 ID |
| name | string | 제품명 |
| category | string | 카테고리 |
| basePrice | number | 기본 단가 (원) |
| optionPricing | Record<string, number> | 옵션별 가산 금액 |
| designImageUrl | string | 기본 디자인 이미지 URL |
| model3dPath | string | 3D 모델링 파일 경로 |

---

## 2. [생산 모니터링] 페이지 관련 데이터 (Production Monitoring)

### 생산 로깅 (ProductionLog)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 로그 ID |
| processStage | ProcessStage | 공정 단계 (용해/조형/주탕/냉각/탈형/후처리/검사/분류) |
| startTime | string | 시작 시각 |
| endTime | string | 종료 시각 |
| status | "normal" \| "stopped" | 상태 (정상/중단) |
| equipmentId | string (FK→Equipment) | 담당 설비 ID |
| orderId | string (FK→Order) | 주문 ID |
| jobId | string | 작업 ID |

### 용해 데이터 (MeltingData)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| logId | string (FK→ProductionLog) | 로그 ID |
| rawMaterialWeight | number | 투입 원재료 중량 (kg) |
| currentTemp | number | 현재 온도 (°C) |
| targetTemp | number | 목표 온도 (°C) |
| heatingPower | number | 가열 출력값 (%) |
| meltingDuration | number | 용융 소요시간 (분) |

### 조형/주탕 데이터 (CastingData)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| logId | string (FK→ProductionLog) | 로그 ID |
| patternId | string | 패턴 ID |
| moldingPressure | number | 성형 압력값 (bar) |
| pourCoordX | number | 주입구 좌표 X |
| pourCoordY | number | 주입구 좌표 Y |
| pourAngleSequence | string | 주입 각도 시퀀스 |
| nozzlePosition | string | 노즐 위치 정보 |

### 냉각/탈형 데이터 (CoolingData)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| logId | string (FK→ProductionLog) | 로그 ID |
| currentCastingTemp | number | 현재 주물 온도 (°C) |
| coolingProgress | number | 냉각 진행률 (%) |
| demoldSuccess | boolean | 탈형 성공 여부 |
| targetCoolingTemp | number | 목표 냉각 온도 (°C) |

---

## 3. [통합 대시보드] 페이지 관련 데이터 (Global Dashboard)

### 설비 마스터 (Equipment)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 설비 ID |
| name | string | 설비명 |
| type | EquipmentType | 설비 유형 (로봇/컨베이어/용해로/카메라/분류기 등) |
| commId | string | 통신 ID (IP/Topic) |
| installLocation | string | 설치 위치 |
| status | EquipmentStatus | 현재 상태 (가동/대기/장애/정비/충전) |
| posX | number | 현재 좌표 X |
| posY | number | 현재 좌표 Y |
| posZ | number | 현재 좌표 Z |
| battery | number? | 배터리 잔량 (%, AMR 전용) |
| speed | number? | 현재 속도 (m/s, AMR 전용) |
| lastUpdate | string | 마지막 갱신 시각 |
| lastMaintenance | string | 마지막 정비일 |
| operatingHours | number | 가동 시간 |
| errorCount | number | 오류 발생 횟수 |

### 장애 알림 (Alert)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 알람 ID |
| equipmentId | string (FK→Equipment) | 설비 ID |
| type | AlertType | 장애 유형 |
| severity | AlertSeverity | 장애 등급 (Critical/Warning/Info) |
| errorCode | string | 장애 코드 |
| message | string | 장애 메시지 |
| abnormalValue | string | 이상 수치 내용 (SR-CTL-03) |
| zone | string | 발생 구역 |
| timestamp | string | 발생 시각 |
| resolvedAt | string? | 해제 시각 |
| acknowledged | boolean | 확인 여부 |

### 대시보드 통계 (DashboardStats)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| productionGoalRate | number | 생산 목표 달성률 (%) |
| activeRobots | number | 실시간 가동 로봇 수 |
| pendingOrders | number | 미처리 주문 건수 |
| todayAlarms | number | 금일 발생 알람 수 |
| todayProduction | number | 금일 생산량 |
| defectRate | number | 불량률 (%) |
| equipmentUtilization | number | 설비 가동률 (%) |
| completedToday | number | 금일 완료 건수 |

---

## 4. [품질 검사] 페이지 관련 데이터 (Quality Control)

### 검사 이력 (InspectionRecord)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 검사 ID |
| productId | string (FK→Product) | 제품 ID |
| castingId | string | 주물 개체 ID |
| orderId | string (FK→Order) | 주문 ID |
| result | InspectionResult | 판정 결과 (양품/불량) |
| defectTypeCode | string | 불량 유형 코드 |
| confidence | number | 신뢰도 (0-100%) |
| inspectorId | string | 검사자 ID / 비전 시스템 ID |
| imageId | string | 검사 이미지 ID |
| inspectedAt | string | 검사 일시 |
| defectType | string? | 불량 유형명 |
| defectDetail | string? | 상세 사유 (치수 미달, 기포 등) |

### 분류 장치 로그 (SorterLog)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| inspectionId | string (FK→InspectionRecord) | 검사 ID |
| sortDirection | "pass_line" \| "fail_line" | 분류 방향 (양품쪽/불량쪽) |
| sorterAngle | number | 분류 장치 각도 (deg) |
| success | boolean | 동작 성공 여부 |

### 검사 기준 (InspectionStandard)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| productId | string (FK→Product) | 제품 ID |
| productName | string | 제품명 |
| toleranceRange | string | 허용 오차 범위 |
| targetDimension | string | 목표 치수 |
| threshold | number | 판정 임계값 (%) |

---

## 5. [물류 및 이송] 페이지 관련 데이터 (Logistics & Fleet)

### 이송 태스크 (TransportTask)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | Task ID |
| fromName | string | 출발지명 |
| fromCoord | string | 출발지 좌표 (x,y) |
| toName | string | 도착지명 |
| toCoord | string | 도착지 좌표 (x,y) |
| itemId | string | 이송 물품 ID |
| itemName | string | 이송 물품명 |
| quantity | number | 수량 |
| priority | "high" \| "medium" \| "low" | 우선순위 (SR-TR-01) |
| status | TransportStatus | 현재 단계 (배정전~완료) |
| assignedRobotId | string | 배정 로봇 ID (SR-TR-02) |
| requestedAt | string | 요청 시각 |
| completedAt | string? | 완료 시각 |

### 창고 랙 관리 (WarehouseRack)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 위치 ID |
| zone | string | 구역명 |
| rackNumber | string | 랙 번호 |
| status | StorageSlotStatus | 현재 상태 (비어있음/점유/예약/불가) (SR-STO-03) |
| itemId | string? | 적재 물품 ID |
| itemName | string? | 적재 물품명 |
| quantity | number? | 적재 수량 |
| lastInboundAt | string? | 마지막 입고 일시 |
| row | number | 행 위치 |
| col | number | 열 위치 |

### 출고 지시 (OutboundOrder)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| id | string (PK) | 지시 ID |
| productId | string (FK→Product) | 제품 ID |
| productName | string | 제품명 |
| quantity | number | 출고 수량 |
| destination | string | 납품처명 |
| policy | "LIFO" \| "FIFO" | 출고 정책 |
| completed | boolean | 출고 완료 여부 |
| createdAt | string | 생성 일시 |

---

## 차트/통계용 데이터

### 생산 추이 (ProductionMetric)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| date | string | 날짜 |
| production | number | 생산량 |
| defects | number | 불량 수 |
| defectRate | number | 불량률 (%) |

### 시간별 생산 (HourlyProduction)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| hour | string | 시간대 |
| production | number | 생산량 |
| defects | number | 불량 수 |
| temperature | number | 용해로 온도 (°C) |

### 불량 유형 통계 (DefectTypeStat)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| type | string | 불량 유형명 |
| count | number | 건수 |
| percentage | number | 비율 (%) |
| color | string | 차트 색상 |

### 월별 생산 요약 (MonthlyProductionSummary)
| 필드명 | 타입 | 설명 |
|--------|------|------|
| month | string | 월 |
| totalProduction | number | 총 생산량 |
| totalDefects | number | 총 불량 수 |
| defectRate | number | 불량률 (%) |
| ordersFulfilled | number | 완료 주문 수 |
