// ============================================================
// 주물 스마트 공장 관제 시스템 — 데이터 타입 정의
// System_Requirements.xlsx 기반 전면 재구성
// ============================================================

// ────────────────────────────────────────
// 1. 주문 관리 (Order Management)
// ────────────────────────────────────────

export type OrderStatus =
  | "pending"              // 접수
  | "approved"             // 승인
  | "in_production"        // 생산 (공정 진행 중)
  | "production_completed" // 생산 완료 (DB 에서만 전환, PyQt5 생산 시스템이 기록)
  | "shipping_ready"       // 출고 (출고 처리 완료, 배송 대기)
  | "completed"            // 완료 (고객 수령 완료)
  | "rejected";            // 반려

export interface Order {
  id: string;
  customerId: string;
  customerName: string;
  companyName: string;
  contact: string;
  /** 주문자 이메일 — /customer/lookup 의 이메일 기반 조회에 사용 (2026-04-09 추가) */
  email: string;
  shippingAddress: string;
  totalAmount: number;
  status: OrderStatus;
  requestedDelivery: string;
  confirmedDelivery: string;
  createdAt: string;
  updatedAt: string;
  /** 출고 처리 타임스탬프 — shipping_ready 전환 시 서버가 기록 (2026-04-09 추가) */
  shippedAt: string;
}

export interface OrderDetail {
  id: string;
  orderId: string;
  productId: string;
  productName: string;
  quantity: number;
  spec: string;           // 규격 (직경/두께/하중)
  material: string;       // 재질
  postProcessing: string; // 후처리 조건
  logoData: string;       // 로고/문구
  unitPrice: number;
  subtotal: number;
}

export interface Product {
  id: string;
  name: string;
  category: string;
  basePrice: number;
  optionPricing: Record<string, number>;
  designImageUrl: string;
  model3dPath: string;
}

// ────────────────────────────────────────
// 2. 생산 모니터링 (Production Monitoring)
// ────────────────────────────────────────

export type ProcessStage =
  | "melting"         // 용해
  | "molding"         // 주형 제작
  | "pouring"         // 주탕
  | "cooling"         // 냉각
  | "demolding"       // 탈형
  | "post_processing" // 후처리
  | "inspection"      // 검사
  | "classification"; // 분류

export type ProcessStatus = "idle" | "running" | "completed" | "error" | "waiting" | "stopped";

export interface ProductionLog {
  id: string;
  processStage: ProcessStage;
  startTime: string;
  endTime: string;
  status: "normal" | "stopped";
  equipmentId: string;
  orderId: string;
  jobId: string;
}

export interface MeltingData {
  logId: string;
  rawMaterialWeight: number;  // 투입 원재료 중량 (kg)
  currentTemp: number;        // 현재 온도
  targetTemp: number;         // 목표 온도
  heatingPower: number;       // 가열 출력값 (%)
  meltingDuration: number;    // 용융 소요시간 (분)
}

export interface CastingData {
  logId: string;
  patternId: string;
  moldingPressure: number;    // 성형 압력 (bar)
  pourCoordX: number;         // 주입구 X
  pourCoordY: number;         // 주입구 Y
  pourAngleSequence: string;  // 주입 각도 시퀀스
  nozzlePosition: string;     // 노즐 위치
}

export interface CoolingData {
  logId: string;
  currentCastingTemp: number; // 현재 주물 온도
  coolingProgress: number;    // 냉각 진행률 (%)
  demoldSuccess: boolean;     // 탈형 성공 여부
  targetCoolingTemp: number;  // 목표 냉각 온도
}

// UI 표시용 통합 공정 데이터
export interface ProcessStageData {
  stage: ProcessStage;
  label: string;
  status: ProcessStatus;
  temperature?: number;
  targetTemperature?: number;
  progress: number;
  startTime?: string;
  estimatedEnd?: string;
  equipmentId: string;
  orderId: string;
  jobId: string;
  // 공정별 상세 데이터
  pressure?: number;        // 성형 압력 (bar)
  pourAngle?: number;       // 주탕 각도 (deg)
  heatingPower?: number;    // 가열 출력 (%)
  coolingProgress?: number; // 냉각 진행률 (%)
}

// ────────────────────────────────────────
// 3. 통합 대시보드 (Global Dashboard)
// ────────────────────────────────────────

export type EquipmentType = "furnace" | "mold_press" | "robot_arm" | "amr" | "conveyor" | "camera" | "sorter";
export type EquipmentStatus = "idle" | "running" | "error" | "maintenance" | "charging";

export interface Equipment {
  id: string;
  name: string;
  type: EquipmentType;
  commId: string;         // 통신 ID (IP/Topic)
  installLocation: string;
  status: EquipmentStatus;
  posX: number;
  posY: number;
  posZ: number;
  battery?: number;       // AMR 배터리 잔량 (%)
  speed?: number;         // AMR 현재 속도 (m/s)
  lastUpdate: string;
  lastMaintenance: string;
  operatingHours: number;
  errorCount: number;
}

export type AlertSeverity = "info" | "warning" | "critical";
export type AlertType = "equipment_error" | "process_delay" | "defect_rate" | "transport_failure" | "system";

export interface Alert {
  id: string;
  equipmentId: string;
  type: AlertType;
  severity: AlertSeverity;
  errorCode: string;
  message: string;
  abnormalValue: string;   // 이상 수치 내용
  zone: string;
  timestamp: string;
  resolvedAt?: string;
  acknowledged: boolean;
}

export interface DashboardStats {
  productionGoalRate: number;  // 생산 목표 달성률 (%)
  activeRobots: number;        // 실시간 가동 로봇 수
  pendingOrders: number;       // 미처리 주문 건수
  todayAlarms: number;         // 금일 발생 알람 수
  todayProduction: number;
  defectRate: number;
  equipmentUtilization: number;
  completedToday: number;

  // smartcast schema (2026-04-19) — 신규 필드 (camelCase 변환됨)
  totalOrders?: number;
  ordersInProduction?: number;
  ordersCompleted?: number;
  ordersPending?: number;
  totalItems?: number;
  goodItems?: number;
  defectiveItems?: number;
  defectRatePct?: number;
  alertsToday?: number;
  activeResources?: number;
  snapshotAt?: string;
  /** TimescaleDB extension 가용 여부 — 대시보드 차트가 hypertable 사용 가능한지 표시 */
  timescaledbEnabled?: boolean;
}

// ────────────────────────────────────────
// 4. 품질 검사 (Quality Control)
// ────────────────────────────────────────

export type InspectionResult = "pass" | "fail";

export interface InspectionRecord {
  id: string;
  productId: string;
  castingId: string;
  orderId: string;
  result: InspectionResult;
  defectTypeCode: string;
  confidence: number;
  inspectorId: string;      // 검사자 ID 또는 비전 시스템 ID
  imageId: string;
  inspectedAt: string;
  defectType?: string;
  defectDetail?: string;    // 상세 사유 (치수 미달, 기포 등)
}

export interface SorterLog {
  inspectionId: string;
  sortDirection: "pass_line" | "fail_line";
  sorterAngle: number;
  success: boolean;
}

export interface InspectionStandard {
  productId: string;
  productName: string;
  toleranceRange: string;   // 허용 오차 범위
  targetDimension: string;  // 목표 치수
  threshold: number;        // 판정 임계값
}

// ────────────────────────────────────────
// 5. 물류 및 이송 (Logistics & Fleet)
// ────────────────────────────────────────

export type TransportStatus =
  | "unassigned"    // 배정 전
  | "assigned"      // 배정됨
  | "moving_to_pickup"
  | "arrived_pickup"
  | "loading"
  | "moving_to_dest"
  | "arrived_dest"
  | "unloading"
  | "completed"
  | "failed";

export interface TransportTask {
  id: string;
  fromName: string;
  fromCoord: string;        // "x,y" 좌표
  toName: string;
  toCoord: string;
  itemId: string;
  itemName: string;
  quantity: number;
  priority: "high" | "medium" | "low";
  status: TransportStatus;
  assignedRobotId: string;
  requestedAt: string;
  completedAt?: string;
}

export type StorageSlotStatus = "empty" | "occupied" | "reserved" | "unavailable";

export interface WarehouseRack {
  id: string;
  zone: string;
  rackNumber: string;
  status: StorageSlotStatus;
  itemId?: string;
  itemName?: string;
  quantity?: number;
  lastInboundAt?: string;
  row: number;
  col: number;
}

export interface OutboundOrder {
  id: string;
  productId: string;
  productName: string;
  quantity: number;
  destination: string;
  policy: "LIFO" | "FIFO";
  completed: boolean;
  createdAt: string;
}

// ────────────────────────────────────────
// 차트/통계용 타입
// ────────────────────────────────────────

export interface ProductionMetric {
  date: string;
  production: number;
  defects: number;
  defectRate: number;
}

export interface HourlyProduction {
  hour: string;
  production: number;
  defects: number;
  temperature: number;
}

export interface DefectTypeStat {
  type: string;
  count: number;
  percentage: number;
  color: string;
}

export interface MonthlyProductionSummary {
  month: string;
  totalProduction: number;
  totalDefects: number;
  defectRate: number;
  ordersFulfilled: number;
}

// ────────────────────────────────────────
// 7. 생산 스케줄링 (Production Scheduling)
// ────────────────────────────────────────

export interface PriorityFactor {
  name: string;
  score: number;
  maxScore: number;
  detail: string;
}

export interface PriorityResult {
  orderId: string;
  companyName: string;
  productSummary: string;
  totalQuantity: number;
  requestedDelivery: string | null;
  totalScore: number;
  rank: number;
  factors: PriorityFactor[];
  recommendationReason: string;
  delayRisk: "high" | "medium" | "low";
  readyStatus: "ready" | "not_ready";
  blockingReasons: string[];
  estimatedDays: number;
}

export interface ProductionJob {
  id: string;
  orderId: string;
  priorityScore: number;
  priorityRank: number;
  assignedStage: string;
  status: "queued" | "running" | "completed" | "cancelled";
  estimatedCompletion: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
}

export interface PriorityChangeLog {
  id: number;
  orderId: string;
  oldRank: number;
  newRank: number;
  reason: string;
  changedBy: string;
  changedAt: string;
}
