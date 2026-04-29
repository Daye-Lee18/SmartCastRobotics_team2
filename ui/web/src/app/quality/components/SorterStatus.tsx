"use client";

import { ArrowDownUp } from "lucide-react";
import type { SorterLog } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SorterStatusProps {
  latestSorter: SorterLog | null;
}

// 분류 장치 — 회전 다이얼 + 양품/불량 라인 라벨 + 4 카드 (각도/방향/성공/검사ID).
export function SorterStatus({ latestSorter }: SorterStatusProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
          <ArrowDownUp className="w-4 h-4 text-indigo-600" />
        </div>
        <h3 className="text-base font-bold text-gray-900">분류 장치 상태</h3>
      </div>

      {/* 분류기 시각화 */}
      <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
        <div className="flex items-center justify-center mb-4">
          <div className="relative w-40 h-40">
            {/* 분류기 원형 베이스 */}
            <div className="absolute inset-0 rounded-full border-4 border-gray-300 flex items-center justify-center">
              {/* 분류 방향 화살표 */}
              <div
                className="absolute w-1 bg-indigo-500 rounded-full origin-bottom"
                style={{
                  height: "45%",
                  bottom: "50%",
                  left: "calc(50% - 2px)",
                  transform: `rotate(${latestSorter?.sorterAngle ?? 0}deg)`,
                  transition: "transform 0.5s ease-in-out",
                }}
              />
              {/* 중앙 점 */}
              <div className="w-4 h-4 rounded-full bg-indigo-600 z-10 shadow-md" />
            </div>
            {/* 양품 라인 라벨 */}
            <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-sm font-semibold text-green-600">
              양품 (0deg)
            </span>
            {/* 불량 라인 라벨 */}
            <span className="absolute top-6 -right-10 text-sm font-semibold text-red-600">
              불량 (45deg)
            </span>
          </div>
        </div>

        {/* 분류기 상세 정보 */}
        <div className="grid grid-cols-2 gap-2 text-base">
          <div className="bg-white rounded-lg p-2.5 text-center border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">현재 각도</p>
            <p className="font-bold text-indigo-700">
              {latestSorter?.sorterAngle ?? 0}&deg;
            </p>
          </div>
          <div className="bg-white rounded-lg p-2.5 text-center border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">분류 방향</p>
            <p
              className={cn(
                "font-bold",
                latestSorter?.sortDirection === "pass_line"
                  ? "text-green-600"
                  : "text-red-600"
              )}
            >
              {latestSorter?.sortDirection === "pass_line" ? "양품 라인" : "불량 라인"}
            </p>
          </div>
          <div className="bg-white rounded-lg p-2.5 text-center border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">동작 성공</p>
            <p
              className={cn(
                "font-bold",
                latestSorter?.success ? "text-green-600" : "text-red-600"
              )}
            >
              {latestSorter?.success ? "성공" : "실패"}
            </p>
          </div>
          <div className="bg-white rounded-lg p-2.5 text-center border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">검사 ID</p>
            <p className="font-bold text-gray-700 font-mono text-sm">
              {latestSorter?.inspectionId ?? "-"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
