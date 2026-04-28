"use client";

import {
  Calculator,
  CheckCircle,
  Factory,
  FileText,
  Layers,
  Loader2,
  MapPin,
  Phone,
  ThumbsDown,
  ThumbsUp,
  Truck,
  User,
} from "lucide-react";
import type { Order, OrderDetail, OrderStatus } from "@/lib/types";
import { cn, formatCurrency, formatDate, orderStatusMap } from "@/lib/utils";
import { OrderStatusStepper } from "./OrderStatusStepper";

interface OrderDetailPanelProps {
  order: Order;
  details: OrderDetail[];
  onStatusChange: (orderId: string, status: OrderStatus) => void;
  onApproveProduction: (orderId: string) => void;
  actionLoading: boolean;
}

// 우측 메인 영역 — 주문 상세 + 상태 스텝퍼 + 액션 버튼.
// 액션 버튼은 status 별로 다르게 렌더링 (pending→승인/반려, approved→생산 승인, ...).
export function OrderDetailPanel({
  order,
  details,
  onStatusChange,
  onApproveProduction,
  actionLoading,
}: OrderDetailPanelProps) {
  const statusInfo = orderStatusMap[order.status];

  return (
    <div className="flex-1 overflow-y-auto">
      {/* 상단 헤더 */}
      <div className="px-6 py-5 border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{order.id}</h2>
            <p className="text-base text-gray-500 mt-0.5">{order.companyName}</p>
          </div>
          <span
            className={cn(
              "inline-flex items-center px-3 py-1.5 rounded-full text-base font-semibold",
              statusInfo.color
            )}
          >
            {statusInfo.label}
          </span>
        </div>
      </div>

      <OrderStatusStepper status={order.status} />

      <div className="px-6 py-5 space-y-6">
        {/* 제품 상세 */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900 mb-4">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
              <Layers size={16} className="text-blue-600" />
            </div>
            제품 상세
          </h3>
          <div className="rounded-lg overflow-hidden border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    제품명
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    규격
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    재질
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    수량
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    단가
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600 uppercase tracking-wider">
                    소계
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {details.map((d) => (
                  <tr key={d.id} className="even:bg-gray-50 hover:bg-blue-50 transition-colors">
                    <td className="px-4 py-3 text-base text-gray-900 font-medium">
                      {d.productName}
                    </td>
                    <td className="px-4 py-3 text-base text-gray-600">{d.spec}</td>
                    <td className="px-4 py-3 text-base text-gray-600">{d.material}</td>
                    <td className="px-4 py-3 text-base text-gray-900 text-right">
                      {d.quantity.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-base text-gray-600 text-right">
                      {formatCurrency(d.unitPrice)}
                    </td>
                    <td className="px-4 py-3 text-base font-semibold text-gray-900 text-right">
                      {formatCurrency(d.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-100">
                  <td
                    colSpan={5}
                    className="px-4 py-3 text-base font-semibold text-gray-700 text-right"
                  >
                    합계
                  </td>
                  <td className="px-4 py-3 text-base font-bold text-blue-700 text-right">
                    {formatCurrency(order.totalAmount)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* 후처리 / 로고 정보 */}
          {details.some((d) => d.postProcessing || d.logoData) && (
            <div className="mt-4 space-y-2">
              {details.map((d) => (
                <div
                  key={d.id}
                  className="text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-100"
                >
                  <span className="font-medium text-gray-700">{d.productName}</span>
                  {d.postProcessing && (
                    <span className="ml-2">
                      후처리: <span className="text-gray-700">{d.postProcessing}</span>
                    </span>
                  )}
                  {d.logoData && (
                    <span className="ml-2">
                      로고: <span className="text-gray-700">{d.logoData}</span>
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 견적/납기 계산기 */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900">
              <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                <Calculator size={16} className="text-amber-600" />
              </div>
              견적 / 납기 계산
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
              <p className="text-sm text-blue-600 font-semibold mb-1">총 견적 금액</p>
              <p className="text-2xl font-bold text-blue-800">
                {formatCurrency(order.totalAmount)}
              </p>
              <p className="text-[11px] text-blue-500 mt-1.5">
                {details.reduce((s, d) => s + d.quantity, 0)}개 제품 기준
              </p>
            </div>
            <div className="bg-purple-50 border border-purple-100 rounded-xl p-5">
              <div className="flex items-center gap-1.5 mb-1">
                <Truck size={13} className="text-purple-600" />
                <p className="text-sm text-purple-600 font-semibold">확정 납기</p>
              </div>
              <p className="text-base font-semibold text-purple-800">
                {order.confirmedDelivery || "미정"}
              </p>
            </div>
          </div>
        </section>

        {/* 고객 정보 */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900 mb-4">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
              <User size={16} className="text-indigo-600" />
            </div>
            고객 정보
          </h3>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                <Factory size={14} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">회사명</p>
                <p className="text-base font-medium text-gray-900">{order.companyName}</p>
              </div>
            </div>
            <div className="border-t border-gray-100" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                <User size={14} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">담당자</p>
                <p className="text-base font-medium text-gray-900">{order.customerName}</p>
              </div>
            </div>
            <div className="border-t border-gray-100" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                <Phone size={14} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">연락처</p>
                <p className="text-base font-medium text-gray-900">{order.contact}</p>
              </div>
            </div>
            <div className="border-t border-gray-100" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                <FileText size={14} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">이메일</p>
                <p className="text-base font-medium text-gray-900">
                  {order.contact?.includes("@") ? order.contact : "-"}
                </p>
              </div>
            </div>
            <div className="border-t border-gray-100" />
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center shrink-0">
                <MapPin size={14} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm text-gray-500">배송 주소</p>
                <p className="text-base font-medium text-gray-900">{order.shippingAddress}</p>
              </div>
            </div>
          </div>
        </section>

        {/* 주문 이력 */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <h3 className="flex items-center gap-2 text-xl font-bold text-gray-900 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
              <FileText size={16} className="text-gray-600" />
            </div>
            주문 이력
          </h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-base">
              <div className="w-3 h-3 rounded-full bg-blue-500 shrink-0 ring-4 ring-blue-100" />
              <span className="text-gray-500 w-32 shrink-0">{formatDate(order.createdAt)}</span>
              <span className="text-gray-900 font-medium">주문 접수</span>
            </div>
            {order.status !== "pending" && (
              <div className="flex items-center gap-3 text-base">
                <div className="w-3 h-3 rounded-full bg-yellow-500 shrink-0 ring-4 ring-yellow-100" />
                <span className="text-gray-500 w-32 shrink-0">{formatDate(order.updatedAt)}</span>
                <span className="text-gray-900">
                  상태 변경: <span className="font-semibold">{statusInfo.label}</span>
                </span>
              </div>
            )}
            {order.confirmedDelivery && (
              <div className="flex items-center gap-3 text-base">
                <div className="w-3 h-3 rounded-full bg-green-500 shrink-0 ring-4 ring-green-100" />
                <span className="text-gray-500 w-32 shrink-0">{formatDate(order.updatedAt)}</span>
                <span className="text-gray-900">
                  납기 확정:{" "}
                  <span className="font-semibold">{order.confirmedDelivery}</span>
                </span>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* 하단 액션 버튼 */}
      {(order.status === "pending" ||
        order.status === "approved" ||
        order.status === "in_production" ||
        order.status === "production_completed" ||
        order.status === "shipping_ready") && (
        <div className="px-6 py-4 border-t border-gray-200 bg-white sticky bottom-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="flex gap-3">
            {order.status === "pending" && (
              <>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => onStatusChange(order.id, "approved")}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-green-600 text-white rounded-lg font-semibold text-base hover:bg-green-700 transition-colors shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <ThumbsUp size={16} />}
                  승인
                </button>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => onStatusChange(order.id, "rejected")}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-red-600 text-white rounded-lg font-semibold text-base hover:bg-red-700 transition-colors shadow-sm disabled:opacity-50"
                >
                  {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <ThumbsDown size={16} />}
                  반려
                </button>
              </>
            )}
            {order.status === "approved" && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => onApproveProduction(order.id)}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold text-base hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50"
                title="생산 대기열에 등록합니다. 실제 순위 계산과 착수는 PyQt5 생산 계획 페이지에서 수행됩니다."
              >
                {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <Factory size={16} />}
                생산 승인
              </button>
            )}
            {order.status === "in_production" && (
              <div className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg font-medium text-sm">
                <Factory size={16} className="text-yellow-600" />
                생산 진행 중 — 생산 완료는 공정 시스템(PyQt5)이 DB에 기록합니다
              </div>
            )}
            {order.status === "production_completed" && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => onStatusChange(order.id, "shipping_ready")}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-purple-600 text-white rounded-lg font-semibold text-base hover:bg-purple-700 transition-colors shadow-sm disabled:opacity-50"
                title="생산이 완료된 주문을 출고 단계로 전환합니다. 출고 시각이 자동 기록됩니다."
              >
                {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <Truck size={16} />}
                출고 처리
              </button>
            )}
            {order.status === "shipping_ready" && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => onStatusChange(order.id, "completed")}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-emerald-600 text-white rounded-lg font-semibold text-base hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50"
                title="출고가 완료되어 주문을 최종 완료 처리합니다."
              >
                {actionLoading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                출고 완료
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
