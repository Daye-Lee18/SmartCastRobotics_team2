"use client";

import { Suspense, useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Factory,
  CheckCircle,
  Package,
  Search,
  Clock,
  Bell,
  ClipboardList,
  Eye,
  ArrowLeft,
  X,
  Truck,
  ShieldCheck,
  PackageCheck,
  Loader2,
  AlertTriangle,
  Mail,
} from "lucide-react";
import { fetchOrderDetails, fetchOrdersByEmail } from "@/lib/api";
import { orderStatusMap, formatDate, formatCurrency as formatKRW } from "@/lib/utils";
import type { Order, OrderDetail, OrderStatus } from "@/lib/types";
import { SmartCastHeader } from "@/components/SmartCastHeader";

// ─────────────────────────────────────────────
// 6단계 상태 파이프라인 (rejected 제외)
// ─────────────────────────────────────────────

const ORDER_STATUS_PIPELINE: OrderStatus[] = [
  "pending",
  "approved",
  "in_production",
  "production_completed",
  "shipping_ready",
  "completed",
];

const STATUS_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  pending: ClipboardList,
  approved: ShieldCheck,
  in_production: Factory,
  production_completed: CheckCircle,
  shipping_ready: Truck,
  completed: PackageCheck,
};

// ─────────────────────────────────────────────
// Status Timeline Component
// ─────────────────────────────────────────────

function OrderStatusTimeline({ status }: { status: OrderStatus }) {
  const currentIndex = ORDER_STATUS_PIPELINE.indexOf(status);

  return (
    <div className="flex items-center justify-between w-full">
      {ORDER_STATUS_PIPELINE.map((s, index) => {
        const Icon = STATUS_ICONS[s] ?? Clock;
        const info = orderStatusMap[s];
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <div key={s} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm transition-all ${
                  isCompleted
                    ? "bg-blue-600 text-white"
                    : isCurrent
                    ? "bg-blue-600 text-white ring-4 ring-blue-100"
                    : "bg-gray-100 text-gray-400"
                }`}
              >
                {isCompleted ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <span
                className={`mt-1.5 text-[10px] font-medium whitespace-nowrap ${
                  isCurrent
                    ? "text-blue-600"
                    : isCompleted
                    ? "text-gray-600"
                    : "text-gray-400"
                }`}
              >
                {info.label}
              </span>
            </div>
            {index < ORDER_STATUS_PIPELINE.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-1 mb-5 transition-all ${
                  index < currentIndex ? "bg-blue-600" : "bg-gray-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────
// Order Detail Panel
// ─────────────────────────────────────────────

function OrderDetailPanel({
  order,
  details,
  onBack,
}: {
  order: Order;
  details: OrderDetail[];
  onBack: () => void;
}) {
  const info = orderStatusMap[order.status];

  // 시뮬레이션: 최근 상태 변경 알림 (updatedAt이 3일 이내)
  const updatedDate = new Date(order.updatedAt);
  const now = new Date();
  const daysDiff = (now.getTime() - updatedDate.getTime()) / (1000 * 60 * 60 * 24);
  const recentlyChanged = daysDiff <= 3;

  return (
    <div>
      {/* 상태 변경 알림 배너 */}
      {recentlyChanged && (
        <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-5">
          <Bell className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-800">상태 변경 알림</p>
            <p className="text-xs text-blue-600 mt-0.5">
              주문 상태가 &quot;{info.label}&quot;(으)로 변경되었습니다. ({formatDate(order.updatedAt)})
            </p>
          </div>
        </div>
      )}

      {/* 뒤로 가기 */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        목록으로 돌아가기
      </button>

      {/* 주문 기본 정보 */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-gray-900">{order.id}</h3>
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${info.color}`}>
            {info.label}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">회사명</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.companyName}</p>
          </div>
          <div>
            <span className="text-gray-500">담당자</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.customerName}</p>
          </div>
          <div>
            <span className="text-gray-500">연락처</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.contact}</p>
          </div>
          <div>
            <span className="text-gray-500">이메일</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.contact?.includes("@") ? order.contact : "-"}</p>
          </div>
          <div>
            <span className="text-gray-500">주문일</span>
            <p className="font-medium text-gray-900 mt-0.5">{formatDate(order.createdAt)}</p>
          </div>
          <div>
            <span className="text-gray-500">요청 납기</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.requestedDelivery || "-"}</p>
          </div>
          <div>
            <span className="text-gray-500">확정 납기</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.confirmedDelivery || "-"}</p>
          </div>
          <div>
            <span className="text-gray-500">배송지</span>
            <p className="font-medium text-gray-900 mt-0.5">{order.shippingAddress || "-"}</p>
          </div>
          <div>
            <span className="text-gray-500">확정 금액</span>
            <p className="font-medium text-blue-600 mt-0.5">{formatKRW(order.totalAmount)}</p>
          </div>
        </div>
      </div>

      {/* 상태 타임라인 */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-600" />
          진행 상태
        </h3>
        <OrderStatusTimeline status={order.status} />
      </div>

      {/* 주문 상세 (제품 정보) */}
      {details.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Package className="w-4 h-4 text-blue-600" />
            주문 상세
          </h3>
          <div className="space-y-3">
            {details.map((d) => (
              <div key={d.id} className="border border-gray-100 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-gray-900">{d.productName}</p>
                  <p className="text-sm font-bold text-blue-600">{formatKRW(d.subtotal)}</p>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-gray-600">
                  <div>
                    <span className="text-gray-400">규격</span>
                    <p className="mt-0.5">{d.spec}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">재질</span>
                    <p className="mt-0.5">{d.material}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">후처리</span>
                    <p className="mt-0.5">{d.postProcessing || "-"}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">수량</span>
                    <p className="mt-0.5">{d.quantity.toLocaleString()}개</p>
                  </div>
                  <div>
                    <span className="text-gray-400">단가</span>
                    <p className="mt-0.5">{formatKRW(d.unitPrice)}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">로고/문구</span>
                    <p className="mt-0.5">{d.logoData || "-"}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 pt-3 border-t border-gray-200 text-sm">
            <span className="font-medium text-gray-700">합계</span>
            <span className="font-bold text-blue-600">{formatKRW(order.totalAmount)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────

function CustomerOrdersInner() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email")?.trim() ?? "";

  const [orders, setOrders] = useState<Order[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<OrderDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    if (!email) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOrdersByEmail(email);
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "주문 데이터를 불러오는 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, [email]);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  // 주문 선택 시 상세 로드
  const handleSelectOrder = useCallback(async (order: Order) => {
    setSelectedOrder(order);
    try {
      setDetailLoading(true);
      const details = await fetchOrderDetails(order.id);
      setSelectedDetails(details);
    } catch {
      setSelectedDetails([]);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // 이메일 필터 결과 내에서 추가로 주문번호/회사명 검색
  const filteredOrders = useMemo(() => {
    if (!searchQuery.trim()) return orders;
    const q = searchQuery.trim().toLowerCase();
    return orders.filter(
      (order) =>
        order.id.toLowerCase().includes(q) ||
        order.companyName.toLowerCase().includes(q)
    );
  }, [searchQuery, orders]);

  // 이메일 파라미터 없음 → 안내 + lookup 유도
  if (!email) {
    return (
      <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
        <SmartCastHeader variant="card" />
        <div className="flex min-h-screen items-center justify-center px-4 pt-24 pb-12">
          <div className="max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-lg">
            <Mail className="mx-auto h-10 w-10 text-amber-500" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">이메일이 필요합니다</h1>
            <p className="mt-2 text-sm text-gray-600">
              주문 조회 페이지는 이메일 파라미터가 있어야 접근할 수 있습니다.
            </p>
            <Link
              href="/customer/lookup"
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90"
            >
              이메일로 조회하기
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
        <SmartCastHeader variant="card" />
        <div className="flex min-h-screen items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 size={36} className="animate-spin text-orange-500" />
            <p className="text-base text-gray-500">주문 데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
        <SmartCastHeader variant="card" />
        <div className="flex min-h-screen items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-center">
            <AlertTriangle size={36} className="text-red-400" />
            <p className="text-base text-red-600">{error}</p>
            <button type="button" onClick={loadOrders} className="mt-2 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600">다시 시도</button>
          </div>
        </div>
      </div>
    );
  }

  // 주문 상세 보기
  if (selectedOrder) {
    return (
      <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
        <SmartCastHeader variant="card" />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-12">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={28} className="animate-spin text-orange-400" />
              </div>
            ) : (
              <OrderDetailPanel
                order={selectedOrder}
                details={selectedDetails}
                onBack={() => { setSelectedOrder(null); setSelectedDetails([]); }}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
      <SmartCastHeader variant="card" />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-12">
        <Link
          href="/customer/lookup"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          다른 이메일로 조회
        </Link>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
          <div className="mb-6 flex items-center gap-2 text-sm text-gray-500">
            <Mail className="h-4 w-4 text-amber-500" />
            <span>조회 이메일:</span>
            <span className="font-medium text-gray-800">{email}</span>
          </div>

          <h2 className="text-xl font-bold text-gray-900 mb-2">내 주문 목록</h2>
          <p className="text-sm text-gray-500 mb-6">
            {orders.length === 0
              ? "해당 이메일로 접수된 주문이 없습니다."
              : `총 ${orders.length}건의 주문이 있습니다.`}
          </p>

          {/* 결과 내 추가 검색 (주문번호, 회사명) */}
          {orders.length > 0 && (
            <div className="relative mb-6">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="주문번호 또는 회사명으로 좁히기"
                className="w-full rounded-lg border border-gray-300 pl-10 pr-10 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          )}

          {/* 검색 결과 */}
          {filteredOrders.length === 0 ? (
            <div className="text-center py-12">
              <Search className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">
                {orders.length === 0
                  ? "해당 이메일로 접수된 주문이 없습니다."
                  : "검색 조건에 맞는 주문이 없습니다."}
              </p>
              {orders.length === 0 && (
                <Link
                  href="/customer"
                  className="mt-4 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-red-500 to-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90"
                >
                  새 주문 접수하기
                </Link>
              )}
            </div>
          ) : (
          <div className="space-y-3">
            {filteredOrders.map((order) => {
              const info = orderStatusMap[order.status];
              return (
                <button
                  key={order.id}
                  onClick={() => handleSelectOrder(order)}
                  className="w-full text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-gray-900">{order.id}</span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${info.color}`}>
                        {info.label}
                      </span>
                    </div>
                    <Eye className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>{order.companyName}</span>
                    <span>{order.customerName}</span>
                    <span>{formatDate(order.createdAt)}</span>
                    <span className="ml-auto font-medium text-gray-700">
                      확정 {formatKRW(order.totalAmount)}
                    </span>
                  </div>
                  {/* 미니 타임라인 */}
                  <div className="mt-3">
                    <OrderStatusTimeline status={order.status} />
                  </div>
                </button>
              );
            })}
          </div>
        )}
        </div>
      </div>
    </div>
  );
}

export default function CustomerOrdersPage() {
  return (
    <Suspense
      fallback={
        <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
          <SmartCastHeader variant="card" />
          <div className="flex min-h-screen items-center justify-center">
            <Loader2 size={36} className="animate-spin text-orange-500" />
          </div>
        </div>
      }
    >
      <CustomerOrdersInner />
    </Suspense>
  );
}
