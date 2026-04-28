"use client";

import { CheckCircle, Factory } from "lucide-react";
import { POST_PROCESSING_OPTIONS } from "../data/products";
import { formatCurrency } from "../lib/format";
import type { FormData, Product } from "../lib/types";

interface Step5OrderCompleteProps {
  formData: FormData;
  product: Product;
  orderNumber: string;
  onRestart: () => void;
}

// Step 5: Order Complete.
// 모든 선택 사양 + 주문자 정보를 한눈에 보여주는 최종 확인 화면.
export function Step5OrderComplete({ formData, product, orderNumber, onRestart }: Step5OrderCompleteProps) {
  const postProcessingTotal = formData.postProcessing.reduce((sum, id) => {
    const opt = POST_PROCESSING_OPTIONS.find((o) => o.id === id);
    return sum + (opt?.price ?? 0);
  }, 0);
  const unitPrice = product.basePrice + postProcessingTotal;
  const totalPrice = unitPrice * formData.quantity;

  return (
    <div className="text-center">
      <div className="flex justify-center mb-4">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
          <CheckCircle className="w-10 h-10 text-green-500" />
        </div>
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">주문이 접수되었습니다</h2>
      <p className="text-gray-500 mb-6">주문 상태를 이메일로 안내드리겠습니다.</p>

      <div className="bg-blue-50 border border-blue-200 rounded-xl px-6 py-4 mb-6 inline-block">
        <p className="text-sm text-blue-600 mb-1">주문 번호</p>
        <p className="text-2xl font-bold text-blue-800">{orderNumber}</p>
      </div>

      {/* 주문 요약 — 모든 선택 사양을 한눈에 */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 text-left mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">주문 요약</h3>
        <div className="space-y-2.5 text-sm">
          {/* 제품 정보 */}
          <div className="flex justify-between">
            <span className="text-gray-500">제품</span>
            <span className="font-medium text-gray-900">{product.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">규격 (직경/두께)</span>
            <span className="font-medium text-gray-900">
              {formData.diameter} / {formData.thickness}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">재질</span>
            <span className="font-medium text-gray-900">{formData.material}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">하중 등급</span>
            <span className="font-medium text-gray-900">{formData.loadClass}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">수량</span>
            <span className="font-medium text-gray-900">
              {formData.quantity.toLocaleString()}개
            </span>
          </div>

          {/* 후처리 */}
          <div className="flex justify-between">
            <span className="text-gray-500">후처리</span>
            <span className="font-medium text-gray-900">
              {formData.postProcessing.length > 0
                ? POST_PROCESSING_OPTIONS.filter((o) =>
                    formData.postProcessing.includes(o.id)
                  )
                    .map((o) => o.label)
                    .join(", ")
                : "없음"}
            </span>
          </div>

          {/* 희망 납기일 */}
          <div className="flex justify-between">
            <span className="text-gray-500">희망 납기일</span>
            <span className="font-medium text-gray-900">{formData.desiredDelivery}</span>
          </div>

          {/* 확정 금액 */}
          <div className="flex justify-between border-t border-gray-100 pt-2.5">
            <span className="text-gray-500">확정 금액</span>
            <span className="font-bold text-blue-600">{formatCurrency(totalPrice)}</span>
          </div>

          {/* 주문자 정보 */}
          <div className="border-t border-gray-100 pt-2.5 space-y-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">주문자 정보</p>
            <div className="flex justify-between">
              <span className="text-gray-500">회사명</span>
              <span className="font-medium text-gray-900">{formData.companyName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">담당자</span>
              <span className="font-medium text-gray-900">{formData.contactPerson}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">연락처</span>
              <span className="font-medium text-gray-900">{formData.phone}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">이메일</span>
              <span className="font-medium text-gray-900">{formData.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">배송지</span>
              <span className="font-medium text-gray-900 text-right max-w-[60%]">{formData.address}</span>
            </div>
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-500 mb-6">
        담당자가 확인 후 최종 견적을 이메일로 보내드리겠습니다.
        <br />
        문의사항은 고객센터(02-1234-5678)로 연락 주세요.
      </p>

      <button
        onClick={onRestart}
        className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-lg transition-colors"
      >
        <Factory className="w-4 h-4" />
        새 주문하기
      </button>
    </div>
  );
}
