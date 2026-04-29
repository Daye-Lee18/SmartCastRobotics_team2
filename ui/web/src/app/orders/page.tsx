"use client";

import {
  AlertTriangle,
  ChevronRight,
  ClipboardList,
  Loader2,
  Package,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  fetchOrderDetails,
  fetchOrders,
  startProduction,
  updateOrderStatus,
} from "@/lib/api";
import type { Order, OrderDetail, OrderStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { OrderCard } from "./components/OrderCard";
import { OrderDetailPanel } from "./components/OrderDetailPanel";
import { ProductionApproveBanner } from "./components/ProductionApproveBanner";
import { ProductionApproveModal } from "./components/ProductionApproveModal";
import { STATUS_TABS } from "./data/statusTabs";

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<OrderDetail[]>([]);
  const [activeTab, setActiveTab] = useState<OrderStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 생산 승인 확인 모달
  const [productionConfirmOrderId, setProductionConfirmOrderId] = useState<string | null>(null);
  const [productionApproveResult, setProductionApproveResult] = useState<{
    jobId: string;
    orderId: string;
  } | null>(null);

  // 주문 목록 로드
  const loadOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOrders();
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "주문 데이터를 불러오는 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

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

  // 상태 변경 (승인/반려 — 사무실 검토 단계)
  const handleStatusChange = useCallback(async (orderId: string, status: OrderStatus) => {
    try {
      setActionLoading(true);
      const updated = await updateOrderStatus(orderId, status);
      setOrders((prev) => prev.map((o) => (o.id === orderId ? updated : o)));
      setSelectedOrder(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "상태 변경 실패");
    } finally {
      setActionLoading(false);
    }
  }, []);

  // 생산 승인 요청 (확인 모달 오픈)
  const handleRequestApproveProduction = useCallback((orderId: string) => {
    setProductionConfirmOrderId(orderId);
  }, []);

  // 생산 승인 확정 (확인 모달에서 "승인" 클릭 시)
  //
  // 동작:
  // 1. POST /api/production/schedule/start — ProductionJob 생성 + 주문 상태 in_production 전이
  // 2. 백엔드가 ProductionJob 레코드를 생성해 PyQt5 생산 계획 페이지 풀에 들어감
  // 3. 우선순위 계산/순서 조정/실제 개시는 PyQt5에서 수행
  const handleConfirmApproveProduction = useCallback(async () => {
    if (!productionConfirmOrderId) return;
    const orderId = productionConfirmOrderId;
    try {
      setActionLoading(true);
      const jobs = await startProduction([orderId]);
      // 주문 목록/상세 갱신 (백엔드가 이미 in_production으로 전환함)
      const refreshed = await fetchOrders();
      setOrders(refreshed);
      const updatedOrder = refreshed.find((o) => o.id === orderId);
      if (updatedOrder) setSelectedOrder(updatedOrder);

      // 성공 결과 배너 (3초 후 자동 사라짐)
      if (jobs.length > 0) {
        setProductionApproveResult({ jobId: jobs[0].id, orderId });
        setTimeout(() => setProductionApproveResult(null), 5000);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "생산 승인 실패");
    } finally {
      setActionLoading(false);
      setProductionConfirmOrderId(null);
    }
  }, [productionConfirmOrderId]);

  // 탭 필터
  const filteredOrders =
    activeTab === "all"
      ? orders
      : orders.filter((o) => o.status === activeTab);

  // 탭별 카운트
  const tabCounts: Record<string, number> = { all: orders.length };
  for (const tab of STATUS_TABS) {
    if (tab.key !== "all") {
      tabCounts[tab.key] = orders.filter((o) => o.status === tab.key).length;
    }
  }

  // 로딩 화면
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={36} className="animate-spin text-blue-500" />
          <p className="text-base text-gray-500">주문 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 에러 화면
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle size={36} className="text-red-400" />
          <p className="text-base text-red-600">{error}</p>
          <button
            type="button"
            onClick={loadOrders}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 페이지 헤더 */}
      <div className="px-6 py-5 bg-white border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <ClipboardList className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">주문 관리</h1>
            <p className="text-base text-gray-500 mt-0.5">
              전체 주문 현황을 확인하고 관리합니다.
            </p>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 영역 (좌측 목록 + 우측 상세) */}
      <div className="flex-1 flex overflow-hidden">
        {/* -- 좌측: 주문 목록 -- */}
        <div className="w-[380px] shrink-0 border-r border-gray-200 bg-white flex flex-col">
          {/* 상태 탭 */}
          <div className="px-3 pt-3 pb-2 border-b border-gray-100 shrink-0">
            <div className="flex flex-wrap gap-1.5">
              {STATUS_TABS.map((tab) => {
                const isActive = activeTab === tab.key;
                const count = tabCounts[tab.key] || 0;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => {
                      setActiveTab(tab.key);
                      setSelectedOrder(null);
                      setSelectedDetails([]);
                    }}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold transition-colors",
                      isActive
                        ? "bg-blue-600 text-white shadow-sm"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    )}
                  >
                    {tab.icon}
                    {tab.label}
                    <span
                      className={cn(
                        "ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold",
                        isActive
                          ? "bg-blue-500 text-white"
                          : "bg-gray-200 text-gray-500"
                      )}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 주문 카드 목록 */}
          <div className="flex-1 overflow-y-auto">
            {filteredOrders.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <Package size={40} strokeWidth={1.5} />
                <p className="mt-2 text-base">해당 상태의 주문이 없습니다.</p>
              </div>
            ) : (
              filteredOrders.map((order) => (
                <OrderCard
                  key={order.id}
                  order={order}
                  isSelected={selectedOrder?.id === order.id}
                  onClick={() => handleSelectOrder(order)}
                />
              ))
            )}
          </div>

          {/* 목록 푸터 */}
          <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50 shrink-0">
            <p className="text-sm text-gray-500 font-medium">
              총 {filteredOrders.length}건
              {activeTab !== "all" && ` / 전체 ${orders.length}건`}
            </p>
          </div>
        </div>

        {/* -- 성공 배너 (생산 승인 완료) -- */}
        {productionApproveResult && (
          <ProductionApproveBanner
            jobId={productionApproveResult.jobId}
            orderId={productionApproveResult.orderId}
          />
        )}

        {/* -- 확인 모달 (생산 승인) -- */}
        {productionConfirmOrderId && (
          <ProductionApproveModal
            orderId={productionConfirmOrderId}
            actionLoading={actionLoading}
            onCancel={() => setProductionConfirmOrderId(null)}
            onConfirm={handleConfirmApproveProduction}
          />
        )}

        {/* -- 우측: 주문 상세 -- */}
        <div className="flex-1 bg-gray-50 flex flex-col">
          {selectedOrder ? (
            detailLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <Loader2 size={28} className="animate-spin text-blue-400" />
              </div>
            ) : (
              <OrderDetailPanel
                order={selectedOrder}
                details={selectedDetails}
                onStatusChange={handleStatusChange}
                onApproveProduction={handleRequestApproveProduction}
                actionLoading={actionLoading}
              />
            )
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
              <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
                <ChevronRight size={32} strokeWidth={1.5} className="text-gray-300" />
              </div>
              <p className="text-base text-gray-500">좌측 목록에서 주문을 선택하세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
