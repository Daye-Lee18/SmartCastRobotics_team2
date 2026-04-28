"use client";

import { CheckCircle } from "lucide-react";

interface ProductionApproveBannerProps {
  jobId: string;
  orderId: string;
}

// 생산 승인 후 5초간 노출되는 우상단 토스트 배너.
export function ProductionApproveBanner({ jobId, orderId }: ProductionApproveBannerProps) {
  return (
    <div className="fixed top-6 right-6 z-50 max-w-sm bg-white rounded-xl shadow-lg border border-green-200 p-4 animate-in slide-in-from-top-2">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center shrink-0">
          <CheckCircle size={18} className="text-green-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-gray-900">생산 승인 완료</p>
          <p className="text-xs text-gray-500 mt-0.5">
            주문 <span className="font-mono">{orderId}</span>
          </p>
          <p className="text-xs text-gray-500">
            생산 작업 ID: <span className="font-mono">{jobId}</span>
          </p>
          <p className="text-[11px] text-gray-400 mt-1">
            PyQt5 생산 계획 페이지에서 우선순위 계산 및 실제 착수를 진행하세요.
          </p>
        </div>
      </div>
    </div>
  );
}
