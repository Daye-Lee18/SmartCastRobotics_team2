"use client";

import { ClipboardList } from "lucide-react";
import type { ProcessStageData } from "@/lib/types";
import { cn, formatDate, processStatusMap } from "@/lib/utils";

interface ProcessParametersTableProps {
  processStages: ProcessStageData[];
}

// 5단계 공정의 파라미터(온도/압력/주탕각도/가열출력/냉각률/진행률) 이력 테이블.
export function ProcessParametersTable({ processStages }: ProcessParametersTableProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <ClipboardList className="w-5 h-5 text-indigo-500" />
        공정 파라미터 이력
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider rounded-tl-lg">공정</th>
              <th className="text-left py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">설비 ID</th>
              <th className="text-left py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">상태</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">온도 (°C)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">목표 온도 (°C)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">압력 (bar)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">주탕 각도 (°)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">가열 출력 (%)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">냉각률 (%)</th>
              <th className="text-right py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">진행률</th>
              <th className="text-left py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider">시작 시간</th>
              <th className="text-left py-2.5 px-3 font-semibold text-gray-600 uppercase tracking-wider rounded-tr-lg">확정 완료</th>
            </tr>
          </thead>
          <tbody>
            {processStages.map((stage) => {
              const statusInfo = processStatusMap[stage.status];
              return (
                <tr
                  key={stage.stage}
                  className="border-b border-gray-100 even:bg-gray-50 hover:bg-blue-50 transition-colors"
                >
                  <td className="py-2.5 px-3 font-semibold text-gray-800">{stage.label}</td>
                  <td className="py-2.5 px-3 text-gray-600 font-mono">{stage.equipmentId}</td>
                  <td className="py-2.5 px-3">
                    <span className="flex items-center gap-1.5">
                      <span className={cn("w-2 h-2 rounded-full", statusInfo.dot)} />
                      <span className={cn("font-medium", statusInfo.color)}>
                        {statusInfo.label}
                      </span>
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.temperature ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.targetTemperature ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.pressure ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.pourAngle ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.heatingPower ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{stage.coolingProgress ?? "-"}</td>
                  <td className="py-2.5 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <div className="w-12 bg-gray-200 rounded-full h-1.5">
                        <div
                          className={cn(
                            "h-1.5 rounded-full",
                            stage.status === "error"
                              ? "bg-red-500"
                              : stage.status === "running"
                              ? "bg-blue-500"
                              : stage.status === "completed"
                              ? "bg-green-500"
                              : "bg-gray-400"
                          )}
                          style={{ width: `${stage.progress}%` }}
                        />
                      </div>
                      <span className="font-mono w-8 text-right">{stage.progress}%</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-gray-500">
                    {stage.startTime ? formatDate(stage.startTime) : "-"}
                  </td>
                  <td className="py-2.5 px-3 text-gray-500">
                    {stage.estimatedEnd ? formatDate(stage.estimatedEnd) : "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
