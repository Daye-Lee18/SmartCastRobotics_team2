"use client";

import { ArrowRightLeft, Gauge, Layers } from "lucide-react";
import type { ProcessStageData } from "@/lib/types";

interface MoldingPouringStatsProps {
  moldingStage?: ProcessStageData;
  pouringStage?: ProcessStageData;
}

// 조형/주탕 실시간 수치 (패턴 / 성형 압력 / 주탕 각도 / 주탕 온도).
export function MoldingPouringStats({ moldingStage, pouringStage }: MoldingPouringStatsProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Layers className="w-5 h-5 text-indigo-500" />
        조형 / 주탕 공정 데이터
      </h3>
      <div className="space-y-4">
        {/* 패턴 정보 */}
        <div className="bg-gray-50 rounded-lg p-3">
          <span className="text-sm text-gray-500">현재 패턴</span>
          <p className="text-base font-semibold text-gray-800 mt-0.5">
            맨홀 뚜껑 KS D-600 ({moldingStage?.equipmentId})
          </p>
        </div>

        {/* 성형 압력 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <Gauge className="w-3.5 h-3.5" />
              성형 압력
            </span>
            <span className="text-xl font-bold text-indigo-600">
              {moldingStage?.pressure ?? "-"}{" "}
              <span className="text-sm font-normal text-gray-400">bar</span>
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-500 rounded-full h-2 transition-all"
              style={{
                width: `${Math.min(100, ((moldingStage?.pressure ?? 0) / 120) * 100)}%`,
              }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
            <span>0</span>
            <span>120 bar</span>
          </div>
        </div>

        {/* 주탕 각도 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <ArrowRightLeft className="w-3.5 h-3.5" />
              주탕 각도
            </span>
            <span className="text-xl font-bold text-teal-600">
              {pouringStage?.pourAngle ?? "-"}
              <span className="text-sm font-normal text-gray-400">°</span>
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-teal-500 rounded-full h-2 transition-all"
              style={{
                width: `${Math.min(100, ((pouringStage?.pourAngle ?? 0) / 90) * 100)}%`,
              }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
            <span>0°</span>
            <span>90°</span>
          </div>
        </div>

        {/* 주탕 온도 */}
        <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
          <span className="text-sm text-gray-500">주탕 온도</span>
          <span className="text-base font-bold text-orange-600">
            {pouringStage?.temperature ?? "-"}°C
          </span>
        </div>
      </div>
    </div>
  );
}
