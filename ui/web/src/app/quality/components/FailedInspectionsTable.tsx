"use client";

import { ImageIcon, XCircle } from "lucide-react";
import type { InspectionRecord } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

interface FailedInspectionsTableProps {
  failedInspections: InspectionRecord[];
}

// 불량 검사 로그 테이블 — 이미지/검사ID/제품ID/판정/유형/사유/신뢰도/시각.
export function FailedInspectionsTable({ failedInspections }: FailedInspectionsTableProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
            <XCircle className="w-4 h-4 text-red-500" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">불량 검사 로그</h2>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-red-100 text-red-700">
          총 {failedInspections.length}건
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead className="sticky top-0 bg-gray-100 z-10">
            <tr>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">이미지</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">검사ID</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">제품ID</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">판정</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">불량유형</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">상세사유</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">신뢰도</th>
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-600 uppercase tracking-wider">검사시각</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {failedInspections.map((ins) => {
              const confidence =
                typeof ins.confidence === "number" && Number.isFinite(ins.confidence)
                  ? ins.confidence
                  : 0;

              return (
              <tr key={ins.id} className="even:bg-gray-50 hover:bg-blue-50 transition-colors">
                {/* 이미지 플레이스홀더 */}
                <td className="px-4 py-3">
                  <div className="w-10 h-10 bg-gray-100 rounded-lg border border-gray-200 flex items-center justify-center">
                    <ImageIcon className="w-4 h-4 text-gray-400" />
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-sm text-gray-600">{ins.id}</td>
                <td className="px-4 py-3 font-mono text-sm text-gray-600">{ins.castingId}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-red-100 text-red-700">
                    <XCircle className="w-3 h-3" /> 불량
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-base text-gray-800 font-medium">
                    {ins.defectType ?? "-"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 text-sm max-w-[200px] truncate">
                  {ins.defectDetail ?? "-"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div
                        className={cn(
                          "h-1.5 rounded-full transition-all",
                          confidence >= 95
                            ? "bg-green-500"
                            : confidence >= 90
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        )}
                        style={{ width: `${confidence}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-700">
                      {confidence.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-500 text-sm whitespace-nowrap">
                  {formatDate(ins.inspectedAt)}
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
