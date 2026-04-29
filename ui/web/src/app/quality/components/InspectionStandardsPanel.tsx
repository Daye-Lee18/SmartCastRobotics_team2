"use client";

import { Ruler } from "lucide-react";
import type { InspectionStandard } from "@/lib/types";

interface InspectionStandardsPanelProps {
  standards: InspectionStandard[];
}

// 검사 기준 참조 — 제품별 목표/허용오차/판정 임계값.
export function InspectionStandardsPanel({ standards }: InspectionStandardsPanelProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex-1">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
          <Ruler className="w-4 h-4 text-gray-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">검사 기준 참조</h2>
      </div>
      <div className="space-y-3">
        {standards.map((std) => (
          <div
            key={std.productId}
            className="bg-gray-50 rounded-xl p-4 border border-gray-200 text-base hover:bg-blue-50 transition-colors"
          >
            <p className="font-semibold text-gray-900 mb-2">{std.productName}</p>
            <div className="grid grid-cols-2 gap-1.5 text-sm text-gray-500">
              <span>목표 치수</span>
              <span className="text-gray-700 font-medium">{std.targetDimension}</span>
              <span>허용 오차</span>
              <span className="text-gray-700 font-medium">{std.toleranceRange}</span>
              <span>판정 임계값</span>
              <span className="text-gray-700 font-medium">{std.threshold}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
