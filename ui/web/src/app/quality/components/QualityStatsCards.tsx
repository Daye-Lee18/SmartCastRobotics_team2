"use client";

import { AlertTriangle, ClipboardList, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface Top3Defect {
  type: string;
  count: number;
  percentage: number;
  color: string;
}

interface QualityStatsCardsProps {
  total: number;
  passCount: number;
  failCount: number;
  passRate: number;
  top3Defects: Top3Defect[];
}

// TOP 4 카드 — 총 검사 수 / 양품률 / 주요 불량 유형 TOP 3.
export function QualityStatsCards({
  total,
  passCount,
  failCount,
  passRate,
  top3Defects,
}: QualityStatsCardsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {/* 금일 총 검사 수 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-base text-gray-500 font-medium">금일 총 검사 수</p>
            <p className="text-4xl font-bold text-gray-900 mt-1">{total}</p>
            <p className="text-sm text-gray-400 mt-1.5">
              양품 {passCount} / 불량 {failCount}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center">
            <ClipboardList className="w-6 h-6 text-gray-600" />
          </div>
        </div>
      </div>

      {/* 양품률 */}
      <div
        className={cn(
          "rounded-xl border p-5 shadow-sm",
          passRate >= 95
            ? "bg-green-50/50 border-green-200"
            : passRate >= 90
              ? "bg-yellow-50/50 border-yellow-200"
              : "bg-red-50/50 border-red-200"
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-base text-gray-500 font-medium">양품률</p>
            <p
              className={cn(
                "text-4xl font-bold mt-1",
                passRate >= 95
                  ? "text-green-600"
                  : passRate >= 90
                    ? "text-yellow-600"
                    : "text-red-600"
              )}
            >
              {passRate.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-400 mt-1.5">
              {passRate >= 95
                ? "정상 (목표 95% 이상)"
                : passRate >= 90
                  ? "주의 (목표 미달)"
                  : "위험 (즉시 조치 필요)"}
            </p>
          </div>
          <div
            className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center",
              passRate >= 95
                ? "bg-green-100"
                : passRate >= 90
                  ? "bg-yellow-100"
                  : "bg-red-100"
            )}
          >
            <ShieldCheck
              className={cn(
                "w-6 h-6",
                passRate >= 95
                  ? "text-green-600"
                  : passRate >= 90
                    ? "text-yellow-600"
                    : "text-red-600"
              )}
            />
          </div>
        </div>
      </div>

      {/* 주요 불량 유형 TOP 3 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm lg:col-span-2">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-xl font-bold text-gray-900">주요 불량 유형 TOP 3</p>
        </div>
        <div className="grid grid-cols-3 gap-5">
          {top3Defects.map((d, idx) => (
            <div
              key={d.type}
              className="text-center bg-gray-50 rounded-xl p-4 border border-gray-100"
            >
              <div
                className="inline-flex items-center justify-center w-10 h-10 rounded-full text-white text-base font-bold mb-2 shadow-sm"
                style={{ backgroundColor: d.color }}
              >
                {idx + 1}
              </div>
              <p className="text-base font-semibold text-gray-800">{d.type}</p>
              <p className="text-sm text-gray-500 mt-0.5">
                {d.count}건 ({d.percentage}%)
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
