"use client";

import { CheckCircle, Eye, XCircle } from "lucide-react";
import type { InspectionRecord } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface VisionCameraFeedProps {
  latestInspection: InspectionRecord | null;
}

// 비전 카메라 시뮬레이션 (스캔라인 + 그리드 + 비네팅 + PASS/FAIL 배지 + REC).
export function VisionCameraFeed({ latestInspection }: VisionCameraFeedProps) {
  const isLatestPass = latestInspection?.result === "pass";
  const confidence =
    typeof latestInspection?.confidence === "number" && Number.isFinite(latestInspection.confidence)
      ? latestInspection.confidence
      : null;

  return (
    <div className="relative bg-gray-950 rounded-xl overflow-hidden aspect-video flex items-center justify-center border border-gray-800">
      {/* 스캔라인 효과 */}
      <div className="absolute inset-0 opacity-[0.07]">
        {Array.from({ length: 30 }).map((_, i) => (
          <div
            key={i}
            className="w-full border-t border-green-400"
            style={{ marginTop: `${i * 3.33}%` }}
          />
        ))}
      </div>
      {/* 그리드 오버레이 */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(34,197,94,1) 1px, transparent 1px), linear-gradient(90deg, rgba(34,197,94,1) 1px, transparent 1px)",
          backgroundSize: "20% 20%",
        }}
      />
      {/* 비네팅 효과 */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/30 via-transparent to-black/30" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30" />
      {/* 중앙 주물 이미지 플레이스홀더 */}
      <div className="relative z-10 flex flex-col items-center gap-2">
        <div className="w-24 h-24 rounded-full border-2 border-dashed border-gray-600 flex items-center justify-center bg-gray-900/50">
          <Eye className="w-8 h-8 text-gray-500" />
        </div>
        <span className="text-sm text-green-500/80 font-mono tracking-wider">
          CAM-001 | {latestInspection?.castingId ?? "---"}
        </span>
      </div>
      {/* PASS / FAIL 배지 */}
      <div className="absolute top-3 right-3 z-20">
        {isLatestPass ? (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-base font-bold bg-green-600 text-white shadow-lg shadow-green-600/40">
            <CheckCircle className="w-4 h-4" /> PASS
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-base font-bold bg-red-600 text-white shadow-lg shadow-red-600/40">
            <XCircle className="w-4 h-4" /> FAIL
          </span>
        )}
      </div>
      {/* REC 인디케이터 */}
      <div className="absolute top-3 left-3 z-20 flex items-center gap-1.5">
        <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
        <span className="text-[10px] font-mono text-red-400 font-bold tracking-wider">REC</span>
      </div>
      {/* 신뢰도 표시 */}
      <div className="absolute bottom-3 left-3 z-20">
        <span className="text-sm font-mono text-green-400 bg-black/70 px-2.5 py-1 rounded-md border border-green-900/50">
          신뢰도: {confidence === null ? "--" : `${confidence.toFixed(1)}%`}
        </span>
      </div>
      {/* 타임스탬프 */}
      <div className="absolute bottom-3 right-3 z-20">
        <span className="text-sm font-mono text-gray-400 bg-black/70 px-2.5 py-1 rounded-md border border-gray-700/50">
          {latestInspection ? formatDate(latestInspection.inspectedAt) : "--:--"}
        </span>
      </div>
    </div>
  );
}
