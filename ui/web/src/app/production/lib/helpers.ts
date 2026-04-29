// 공정 상태별 시각 스타일.

import type { ProcessStatus } from "@/lib/types";

export function statusBg(status: ProcessStatus): string {
  switch (status) {
    case "running":
      return "bg-blue-500 text-white border-blue-600 shadow-blue-300/50 shadow-lg";
    case "completed":
      return "bg-green-500 text-white border-green-600";
    case "error":
      return "bg-red-500 text-white border-red-600 animate-pulse";
    case "waiting":
      return "bg-amber-400 text-amber-900 border-amber-500";
    case "idle":
      return "bg-gray-200 text-gray-500 border-gray-300";
    case "stopped":
      return "bg-red-300 text-red-800 border-red-400";
    default:
      return "bg-gray-200 text-gray-500 border-gray-300";
  }
}

export function arrowColor(status: ProcessStatus): string {
  switch (status) {
    case "running":
      return "text-blue-400";
    case "completed":
      return "text-green-400";
    case "error":
      return "text-red-400";
    default:
      return "text-gray-300";
  }
}
