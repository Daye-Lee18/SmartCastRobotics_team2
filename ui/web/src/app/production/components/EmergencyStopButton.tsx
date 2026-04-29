"use client";

import { OctagonX } from "lucide-react";

// E-STOP — 비상 정지 요청 (현재 alert 만, 백엔드 hookup 미구현).
export function EmergencyStopButton() {
  return (
    <button
      type="button"
      className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800 text-white rounded-xl border-2 border-red-700 p-5 flex items-center justify-center gap-3 shadow-lg shadow-red-200 transition-all"
      onClick={() => alert("비상 정지가 요청되었습니다.")}
    >
      <OctagonX className="w-7 h-7" />
      <span className="text-xl font-bold tracking-wide">
        비상 정지 (E-STOP)
      </span>
    </button>
  );
}
