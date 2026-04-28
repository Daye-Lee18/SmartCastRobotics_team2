// API 클라이언트 — 백엔드 REST API 호출 + snake_case→camelCase 자동 변환
import type {
  DashboardStats,
  Alert,
  Equipment,
  Order,
  OrderDetail,
  ProductionMetric,
  ProcessStageData,
  InspectionRecord,
  InspectionStandard,
  SorterLog,
  TransportTask,
  WarehouseRack,
  OutboundOrder,
  OrderStatus,
  PriorityResult,
  ProductionJob,
  PriorityChangeLog,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "";

// snake_case → camelCase 재귀 변환
function toCamelCase(str: string): string {
  return str.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());
}

function convertKeys<T>(obj: unknown): T {
  if (Array.isArray(obj)) {
    return obj.map((item) => convertKeys(item)) as T;
  }
  if (obj !== null && typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[toCamelCase(key)] = convertKeys(value);
    }
    return result as T;
  }
  return obj as T;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API 오류: ${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  return convertKeys<T>(data);
}

// =====================================================================
// smartcast → legacy shape adapters
// 백엔드는 신규 smartcast schema (ord/ord_detail/user_account/ord_stat)
// 응답을 내보내고, 기존 admin/customer 페이지는 legacy Order 타입을 기대한다.
// 두 세계를 이어주는 어댑터.
// =====================================================================

/** smartcast ord_stat 문자열 → legacy OrderStatus 로 매핑
 *  legacy 에는 cancelled 타입이 없어 REJT/CNCL 모두 rejected 로 압축.
 */
const ORD_STAT_TO_LEGACY: Record<string, OrderStatus> = {
  RCVD: "pending",
  APPR: "approved",
  MFG: "in_production",
  DONE: "production_completed",
  SHIP: "shipping_ready",
  COMP: "completed",
  REJT: "rejected",
  CNCL: "rejected",
};

type SmartcastOrdFull = {
  ordId: number;
  userId: number;
  createdAt: string | null;
  detail?: {
    prodId?: number | null;
    diameter?: number | string | null;
    thickness?: number | string | null;
    material?: string | null;
    loadClass?: string | null;
    qty?: number | null;
    finalPrice?: number | string | null;
    dueDate?: string | null;
    shipAddr?: string | null;
  } | null;
  ppOptions?: Array<{ ppId: number; ppNm?: string | null; extraCost?: number | string | null }>;
  latestStat?: string | null;
  userCoNm?: string | null;
  userNm?: string | null;
  userPhone?: string | null;
  userEmail?: string | null;
};

function adaptOrdToLegacy(o: SmartcastOrdFull): Order {
  const legacyStatus: OrderStatus = ORD_STAT_TO_LEGACY[o.latestStat ?? "RCVD"] ?? "pending";
  return {
    id: `ord_${o.ordId}`,
    customerId: String(o.userId),
    customerName: o.userNm ?? "",
    companyName: o.userCoNm ?? "",
    contact: o.userPhone ?? "",
    email: o.userEmail ?? "",
    shippingAddress: o.detail?.shipAddr ?? "",
    totalAmount: Number(o.detail?.finalPrice ?? 0),
    status: legacyStatus,
    requestedDelivery: o.detail?.dueDate ?? "",
    confirmedDelivery: o.detail?.dueDate ?? "",
    createdAt: o.createdAt ?? "",
    updatedAt: o.createdAt ?? "",
    shippedAt: "",  // ord_stat SHIP 타임스탬프는 별도 조회 필요. 현재는 빈 값.
  };
}

function adaptOrdDetails(o: SmartcastOrdFull): OrderDetail[] {
  const d = o.detail;
  if (!d) return [];
  const qty = d.qty ?? 0;
  const unit = Number(d.finalPrice ?? 0) / Math.max(1, qty);
  const ppNames = (o.ppOptions ?? []).map((p) => p.ppNm ?? "").filter(Boolean).join(", ");
  return [{
    id: `ord_${o.ordId}_d1`,
    orderId: `ord_${o.ordId}`,
    productId: d.prodId ? String(d.prodId) : "",
    productName: d.material ?? "맨홀",
    quantity: qty,
    spec: `∅${d.diameter ?? "-"}mm × t${d.thickness ?? "-"}mm / ${d.loadClass ?? "-"}`,
    material: d.material ?? "",
    postProcessing: ppNames,
    logoData: "",
    unitPrice: unit,
    subtotal: Number(d.finalPrice ?? 0),
  }];
}

async function apiPatch<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── API 함수 ──

export function fetchDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/dashboard/stats");
}

export function fetchAlerts(): Promise<Alert[]> {
  return apiFetch<Alert[]>("/api/alerts");
}

export function fetchEquipment(): Promise<Equipment[]> {
  return apiFetch<Equipment[]>("/api/production/equipment");
}

export async function fetchOrders(): Promise<Order[]> {
  const raw = await apiFetch<SmartcastOrdFull[]>("/api/orders");
  return raw.map(adaptOrdToLegacy);
}

/** 특정 이메일로 접수된 주문만 반환. /customer/lookup 흐름에서 사용.
 *  smartcast schema: GET /api/orders/lookup?email=... — 결과 없으면 빈 배열.
 */
export async function fetchOrdersByEmail(email: string): Promise<Order[]> {
  const raw = await apiFetch<SmartcastOrdFull[]>(
    `/api/orders/lookup?email=${encodeURIComponent(email)}`,
  );
  return raw.map(adaptOrdToLegacy);
}

export function fetchProductionMetrics(): Promise<ProductionMetric[]> {
  return apiFetch<ProductionMetric[]>("/api/production/metrics");
}

// ── 생산 모니터링 ──

export function fetchProcessStages(): Promise<ProcessStageData[]> {
  return apiFetch<ProcessStageData[]>("/api/production/stages");
}

// ── 품질 검사 ──

export function fetchInspections(): Promise<InspectionRecord[]> {
  return apiFetch<InspectionRecord[]>("/api/quality/inspections");
}

export function fetchQualityStats(): Promise<{
  total: number;
  passed: number;
  failed: number;
  defectRate: number;
  defectTypes: Record<string, number>;
  defectTypeCodes: Record<string, number> | null;
  inspectorStats: Record<string, { total: number; passed: number; failed: number }> | null;
}> {
  return apiFetch("/api/quality/stats");
}

export function fetchInspectionStandards(): Promise<InspectionStandard[]> {
  return apiFetch<InspectionStandard[]>("/api/quality/standards");
}

export function fetchSorterLogs(): Promise<SorterLog[]> {
  return apiFetch<SorterLog[]>("/api/quality/sorter-logs");
}

// ── 물류/이송 ──

export function fetchTransportTasks(): Promise<TransportTask[]> {
  return apiFetch<TransportTask[]>("/api/logistics/tasks");
}

export function fetchWarehouseRacks(): Promise<WarehouseRack[]> {
  return apiFetch<WarehouseRack[]>("/api/logistics/warehouse");
}

export function fetchOutboundOrders(): Promise<OutboundOrder[]> {
  return apiFetch<OutboundOrder[]>("/api/logistics/outbound-orders");
}

// ── 주문 상세/관리 ──

/** orderId: "ord_{n}" 형태 → ord_id 추출 후 OrdFull 로부터 legacy OrderDetail[] 변환. */
export async function fetchOrderDetails(orderId: string): Promise<OrderDetail[]> {
  const numericId = orderId.replace(/^ord_/, "");
  const full = await apiFetch<SmartcastOrdFull>(`/api/orders/${numericId}`);
  return adaptOrdDetails(full);
}

/** 신규 API 는 POST /api/orders/{id}/status?new_stat=...&user_id=... — legacy OrderStatus → ord_stat 매핑 */
const LEGACY_TO_ORD_STAT: Record<OrderStatus, string> = {
  pending: "RCVD",
  approved: "APPR",
  in_production: "MFG",
  production_completed: "DONE",
  shipping_ready: "SHIP",
  completed: "COMP",
  rejected: "REJT",
};

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus,
): Promise<Order> {
  const numericId = orderId.replace(/^ord_/, "");
  const newStat = LEGACY_TO_ORD_STAT[status];
  const res = await fetch(
    `${API_BASE}/api/orders/${numericId}/status?new_stat=${newStat}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(`API 오류: ${res.status} ${res.statusText}`);
  // 응답이 OrdStat — 최신 상태만 반환됨. 전체 Order 재조회.
  const full = await apiFetch<SmartcastOrdFull>(`/api/orders/${numericId}`);
  return adaptOrdToLegacy(full);
}

export function updateOrder(
  orderId: string,
  data: { total_amount?: number; confirmed_delivery?: string },
): Promise<Order> {
  return apiPatch<Order>(`/api/orders/${orderId}`, data);
}

// ── 생산 스케줄링 ──

export function calculatePriority(
  orderIds: string[],
): Promise<{ results: PriorityResult[] }> {
  return apiFetch("/api/production/schedule/calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_ids: orderIds }),
  });
}

export function startProduction(
  orderIds: string[],
): Promise<ProductionJob[]> {
  return apiFetch("/api/production/schedule/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_ids: orderIds }),
  });
}

export function fetchProductionJobs(): Promise<ProductionJob[]> {
  return apiFetch<ProductionJob[]>("/api/production/schedule/jobs");
}

export function createPriorityLog(data: {
  order_id: string;
  old_rank: number;
  new_rank: number;
  reason: string;
}): Promise<PriorityChangeLog> {
  return apiFetch("/api/production/schedule/priority-log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
