"use client";

import { useState } from "react";

/**
 * SPEC-AMR-001 FR-AMR-01-07: HW-less Handoff ACK 시뮬레이션 버튼.
 *
 * Dev 빌드에서만 렌더 (`process.env.NODE_ENV === 'development'`).
 * Production 빌드에서는 null 반환 → DOM 에 아예 출력되지 않음.
 *
 * 동작:
 *   1. 클릭 → `POST /api/debug/handoff-ack` 호출
 *   2. Backend (APP_ENV=development) 가 FIFO AMR 해제 + DB insert + WebSocket 브로드캐스트
 *   3. 결과 토스트 표시 (reason, task_id, amr_id, orphan 여부)
 *
 * 주의: 실제 버튼/ESP32 가 없는 로컬 개발·E2E 데모 전용 도구.
 */
export default function DevHandoffAckButton() {
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  async function handleClick() {
    setLoading(true);
    setLastResult(null);
    try {
      const res = await fetch("/api/debug/handoff-ack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          zone: "postprocessing",
          source_device: "SIM-DEV-UI",
        }),
      });
      if (!res.ok) {
        setLastResult(`❌ HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      // smartcast schema 응답: released / orphan / task_id / amr_id / item_id / ord_id / reason
      if (data.released) {
        const parts = [
          data.task_id ? `task=${data.task_id}` : "",
          data.amr_id ? `amr=${data.amr_id}` : "",
          data.item_id ? `item=${data.item_id}` : "",
          data.ord_id ? `ord=${data.ord_id}` : "",
        ].filter(Boolean).join(" ");
        setLastResult(`✓ released  ${parts}`);
      } else {
        setLastResult(`⚠ orphan  ${data.reason || ""}`.trim());
      }
    } catch (e) {
      setLastResult(`❌ ${String(e)}`);
    } finally {
      setLoading(false);
      setTimeout(() => setLastResult(null), 6000);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-700 disabled:bg-red-900 text-white text-sm font-semibold shadow-lg border-2 border-red-400 transition-colors"
        title="SPEC-AMR-001 dev 시뮬레이션 — 실제 버튼/ESP32 없이 handoff ACK 체인 트리거"
      >
        {loading ? "..." : "🔴 SIM Handoff ACK"}
      </button>
      {lastResult && (
        <div className="bg-gray-900 text-gray-100 text-xs px-3 py-1 rounded border border-gray-700 max-w-xs">
          {lastResult}
        </div>
      )}
      <div className="text-[10px] text-gray-500">DEV ONLY · SPEC-AMR-001</div>
    </div>
  );
}
