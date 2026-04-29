"use client";

import { ChevronRight, Factory, Loader2 } from "lucide-react";

interface ProductionApproveModalProps {
  orderId: string;
  actionLoading: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

// 생산 승인 확인 모달.
// onConfirm 클릭 → 백엔드 startProduction → ProductionJob 생성 + 주문 in_production 전이.
export function ProductionApproveModal({
  orderId,
  actionLoading,
  onCancel,
  onConfirm,
}: ProductionApproveModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={() => !actionLoading && onCancel()}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
            <Factory size={24} className="text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-gray-900">생산 승인 확인</h3>
            <p className="text-sm text-gray-500 mt-1">
              주문{" "}
              <span className="font-mono font-semibold text-gray-800">{orderId}</span>
              을 생산 대기열에 등록하시겠습니까?
            </p>
            <ul className="mt-3 space-y-1.5 text-xs text-gray-600">
              <li className="flex items-start gap-2">
                <ChevronRight size={14} className="text-gray-400 mt-0.5 shrink-0" />
                주문 상태가 <span className="font-semibold">생산 중</span>으로 전환됩니다.
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight size={14} className="text-gray-400 mt-0.5 shrink-0" />
                ProductionJob 레코드가 생성되어 PyQt5 생산 계획 페이지 풀에 들어갑니다.
              </li>
              <li className="flex items-start gap-2">
                <ChevronRight size={14} className="text-gray-400 mt-0.5 shrink-0" />
                우선순위 계산 · 순서 조정 · 실제 착수는{" "}
                <span className="font-semibold">PyQt5</span>에서 수행됩니다.
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            disabled={actionLoading}
            onClick={onCancel}
            className="flex-1 py-2.5 px-4 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            type="button"
            disabled={actionLoading}
            onClick={onConfirm}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50"
          >
            {actionLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Factory size={16} />
            )}
            생산 승인
          </button>
        </div>
      </div>
    </div>
  );
}
