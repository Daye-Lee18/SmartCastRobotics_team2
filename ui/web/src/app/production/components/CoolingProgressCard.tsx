"use client";

import { Timer, Wind } from "lucide-react";
import type { ProcessStageData } from "@/lib/types";

interface CoolingProgressCardProps {
  coolingStage?: ProcessStageData;
}

// 냉각 진행률 카드 (원형 SVG 게이지 + 현재/목표 온도 + 잔여 시간).
export function CoolingProgressCard({ coolingStage }: CoolingProgressCardProps) {
  const coolingProgress = coolingStage?.coolingProgress ?? 0;
  // 잔여 시간 — 원본 page.tsx 와 동일한 render-time 계산 (페이지 새로 마운트될 때 갱신).
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();
  const coolingRemainingMin = coolingStage?.estimatedEnd
    ? Math.max(0, Math.round((new Date(coolingStage.estimatedEnd).getTime() - now) / 60000))
    : 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Wind className="w-5 h-5 text-cyan-500" />
        냉각 진행률
      </h3>
      <div className="flex items-center gap-4">
        {/* 원형 진행률 */}
        <div className="relative w-20 h-20 flex-shrink-0">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="34" stroke="#e5e7eb" strokeWidth="8" fill="none" />
            <circle
              cx="40"
              cy="40"
              r="34"
              stroke="#06b6d4"
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={`${(coolingProgress / 100) * 213.6} 213.6`}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-base font-bold text-cyan-700">
            {coolingProgress}%
          </span>
        </div>
        <div className="space-y-1.5 text-sm flex-1">
          <div className="flex justify-between">
            <span className="text-gray-500">현재 온도</span>
            <span className="font-semibold text-gray-800">
              {coolingStage?.temperature ?? "-"}°C
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">목표 온도</span>
            <span className="font-semibold text-gray-800">
              {coolingStage?.targetTemperature ?? "-"}°C
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 flex items-center gap-1">
              <Timer className="w-3 h-3" />
              잔여 시간
            </span>
            <span className="font-semibold text-cyan-700">
              약 {coolingRemainingMin > 0 ? `${coolingRemainingMin}분` : "완료 임박"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
