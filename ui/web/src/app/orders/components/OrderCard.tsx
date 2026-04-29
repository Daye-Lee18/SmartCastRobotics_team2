"use client";

import type { Order } from "@/lib/types";
import { cn, formatCurrency, formatDate, orderStatusMap } from "@/lib/utils";

interface OrderCardProps {
  order: Order;
  isSelected: boolean;
  onClick: () => void;
}

// 좌측 목록의 한 줄 = 한 주문 카드.
export function OrderCard({ order, isSelected, onClick }: OrderCardProps) {
  const statusInfo = orderStatusMap[order.status];
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left px-4 py-3.5 border-b border-gray-100 transition-all duration-200",
        isSelected
          ? "bg-blue-50 border-l-4 border-l-blue-500 ring-2 ring-blue-500 ring-inset"
          : "hover:bg-blue-50/50 border-l-4 border-l-transparent"
      )}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-mono text-gray-400">{order.id}</span>
        <span
          className={cn(
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-semibold",
            statusInfo.color
          )}
        >
          {statusInfo.label}
        </span>
      </div>
      <p className="text-base font-semibold text-gray-900 truncate">
        {order.companyName}
      </p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-sm text-gray-500">
          {formatDate(order.createdAt)}
        </span>
        <span className="text-base font-bold text-gray-800">
          {formatCurrency(order.totalAmount)}
        </span>
      </div>
    </button>
  );
}
