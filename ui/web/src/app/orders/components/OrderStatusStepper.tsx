"use client";

import {
  CheckCircle,
  Clock,
  Factory,
  PackageCheck,
  ThumbsDown,
  ThumbsUp,
  Truck,
} from "lucide-react";
import React from "react";
import type { OrderStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const ORDER_STATUS_STEPS = [
  { key: "pending",              label: "접수",    Icon: Clock        },
  { key: "approved",             label: "승인",    Icon: ThumbsUp     },
  { key: "in_production",        label: "생산",    Icon: Factory      },
  { key: "production_completed", label: "생산 완료", Icon: PackageCheck },
  { key: "shipping_ready",       label: "출고",    Icon: Truck        },
  { key: "completed",            label: "완료",    Icon: CheckCircle  },
] as const;

function getStepState(
  stepKey: string,
  currentStatus: OrderStatus
): "completed" | "active" | "future" {
  const ORDER = [
    "pending",
    "approved",
    "in_production",
    "production_completed",
    "shipping_ready",
    "completed",
  ];
  const currentIdx = ORDER.indexOf(currentStatus);
  const stepIdx = ORDER.indexOf(stepKey);

  if (stepIdx < currentIdx) return "completed";
  if (stepIdx === currentIdx) return "active";
  return "future";
}

// 주문 상세 상단의 6단계 진행 표시기 (반려 시 별도 메시지).
export function OrderStatusStepper({ status }: { status: OrderStatus }) {
  if (status === "rejected") {
    return (
      <div className="px-6 py-3 bg-red-50 border-b border-red-100 flex items-center gap-2 text-sm font-medium text-red-600">
        <ThumbsDown size={15} />
        주문이 반려되었습니다
      </div>
    );
  }

  return (
    <div className="px-6 py-5 bg-gray-50 border-b border-gray-100">
      <div className="flex items-start">
        {ORDER_STATUS_STEPS.map((step, idx) => {
          const state = getStepState(step.key, status);
          const Icon = step.Icon;
          const isLast = idx === ORDER_STATUS_STEPS.length - 1;

          return (
            <React.Fragment key={step.key}>
              {/* Step circle + label */}
              <div className="flex flex-col items-center gap-1.5 shrink-0">
                <div
                  className={cn(
                    "w-11 h-11 rounded-full flex items-center justify-center transition-all",
                    state === "active"    && "bg-blue-600 shadow-md shadow-blue-300",
                    state === "completed" && "bg-blue-500",
                    state === "future"    && "bg-gray-100",
                  )}
                >
                  <Icon
                    size={18}
                    className={cn(
                      state === "active"    && "text-white",
                      state === "completed" && "text-white",
                      state === "future"    && "text-gray-400",
                    )}
                  />
                </div>
                <span
                  className={cn(
                    "text-xs whitespace-nowrap",
                    state === "active"    && "text-blue-700 font-bold",
                    state === "completed" && "text-blue-700 font-semibold",
                    state === "future"    && "text-gray-400 font-medium",
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line — completed 단계 뒤에만 파란색, active 이후는 회색 */}
              {!isLast && (
                <div
                  className={cn(
                    "flex-1 h-[3px] mt-4 mx-1 rounded-full",
                    state === "completed" ? "bg-blue-500" : "bg-gray-200",
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
