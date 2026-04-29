"use client";

import { ChevronRight, Zap } from "lucide-react";
import type { ProcessStageData, ProcessStatus } from "@/lib/types";
import { cn, processStatusMap } from "@/lib/utils";
import { PROCESS_FLOW } from "../data/processFlow";
import { arrowColor, statusBg } from "../lib/helpers";

interface ProcessFlowProps {
  stageDataMap: Record<string, ProcessStageData>;
}

// 5단계 공정 흐름 (용해 → 조형 → 주탕 → 냉각/탈형 → 후처리/검사).
// 각 단계 카드 + 화살표 연결 + 진행률 바.
export function ProcessFlow({ stageDataMap }: ProcessFlowProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Zap className="w-5 h-5 text-amber-500" />
        공정 흐름
      </h2>
      <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2">
        {PROCESS_FLOW.map((step, idx) => {
          const data = stageDataMap[step.key];
          const status: ProcessStatus = data?.status ?? "idle";
          const statusInfo = processStatusMap[status];
          const progress = data?.progress ?? 0;

          return (
            <div key={step.key} className="flex items-center flex-1 min-w-0">
              {/* 스텝 카드 */}
              <div
                className={cn(
                  "relative flex flex-col items-center justify-center rounded-xl border-2 px-4 py-3 w-full transition-all",
                  statusBg(status)
                )}
              >
                <div className="mb-1">{step.icon}</div>
                <span className="text-sm font-bold whitespace-nowrap">
                  {step.label}
                </span>
                <span className="text-[10px] mt-0.5 opacity-80">
                  {statusInfo.label}
                </span>
                {/* 진행률 바 */}
                {status === "running" && (
                  <div className="w-full mt-2 bg-white/30 rounded-full h-1.5">
                    <div
                      className="bg-white rounded-full h-1.5 transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                )}
                {status === "completed" && (
                  <div className="w-full mt-2 bg-white/30 rounded-full h-1.5">
                    <div className="bg-white rounded-full h-1.5 w-full" />
                  </div>
                )}
              </div>
              {/* 화살표 (마지막 제외) */}
              {idx < PROCESS_FLOW.length - 1 && (
                <ChevronRight
                  className={cn(
                    "w-6 h-6 flex-shrink-0 mx-1",
                    arrowColor(status)
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
