"use client";

import { Factory, FileText, Image, Ruler } from "lucide-react";
import { CATEGORY_IMAGES, POST_PROCESSING_OPTIONS } from "../data/products";
import { formatCurrency } from "../lib/format";
import type { FormData, Product } from "../lib/types";

interface Step3QuoteReviewProps {
  formData: FormData;
  product: Product;
}

// Step 3: Quote Review (디자인 시안 + 옵션 미리보기).
// @MX:NOTE: 컴포넌트 이름의 "Step3" 는 historic naming 이며 실제 mount 단계는 step=4.
export function Step3QuoteReview({ formData, product }: Step3QuoteReviewProps) {
  const postProcessingTotal = formData.postProcessing.reduce((sum, id) => {
    const opt = POST_PROCESSING_OPTIONS.find((o) => o.id === id);
    return sum + (opt?.price ?? 0);
  }, 0);
  const unitPrice = product.basePrice + postProcessingTotal;
  const totalPrice = unitPrice * formData.quantity;

  const selectedPostProcessing = POST_PROCESSING_OPTIONS.filter((opt) =>
    formData.postProcessing.includes(opt.id)
  );

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">견적 확인</h2>
      <p className="text-sm text-gray-500 mb-6">주문 내용과 디자인 시안을 확인해 주세요.</p>

      <div className="space-y-4">
        {/* 디자인 시안 + 옵션 미리보기 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Image className="w-4 h-4 text-blue-600" />
            디자인 시안 미리보기
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* 디자인 시안 이미지 */}
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 flex flex-col items-center justify-center min-h-[200px]">
              {product.category !== "all" && CATEGORY_IMAGES[product.category] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={CATEGORY_IMAGES[product.category]}
                  alt={product.name}
                  className="w-32 h-32 object-contain mb-3"
                />
              ) : (
                <div className="w-28 h-28 bg-gray-200 rounded-full flex items-center justify-center mb-3">
                  <Factory className="w-14 h-14 text-gray-400" />
                </div>
              )}
              <p className="text-sm font-medium text-gray-700">{product.name}</p>
              <p className="text-xs text-gray-400 mt-1">기본 디자인 시안</p>
              <div className="mt-3 flex items-center gap-1.5 text-xs text-gray-400">
                <Ruler className="w-3 h-3" />
                <span>{formData.diameter} / {formData.thickness}</span>
              </div>
            </div>

            {/* 선택 옵션 요약 카드 */}
            <div className="space-y-3">
              {/* 규격 사양 */}
              <div className="bg-blue-50 rounded-lg px-4 py-3 border border-blue-100">
                <p className="text-[10px] uppercase tracking-wider text-blue-400 font-semibold mb-1">규격 사양</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">직경</span>
                    <p className="font-semibold text-gray-800">{formData.diameter}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">두께</span>
                    <p className="font-semibold text-gray-800">{formData.thickness}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">하중</span>
                    <p className="font-semibold text-gray-800">{formData.loadClass}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">재질</span>
                    <p className="font-semibold text-gray-800">{formData.material}</p>
                  </div>
                </div>
              </div>

              {/* 후처리 적용 내역 */}
              <div className="bg-amber-50 rounded-lg px-4 py-3 border border-amber-100">
                <p className="text-[10px] uppercase tracking-wider text-amber-500 font-semibold mb-2">후처리 적용</p>
                {selectedPostProcessing.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {selectedPostProcessing.map((opt) => {
                      const Icon = opt.icon;
                      return (
                        <span
                          key={opt.id}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-white border border-amber-200 text-amber-700"
                        >
                          <Icon className="w-3 h-3" />
                          {opt.label}
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">후처리 옵션 없음</p>
                )}
              </div>

              {/* 수량/납기 */}
              <div className="bg-green-50 rounded-lg px-4 py-3 border border-green-100">
                <p className="text-[10px] uppercase tracking-wider text-green-500 font-semibold mb-1">주문 수량</p>
                <p className="text-lg font-bold text-gray-800">
                  {formData.quantity.toLocaleString()}개
                </p>
                <p className="text-xs text-gray-500 mt-0.5">납기: {formData.desiredDelivery}</p>
              </div>
            </div>
          </div>
        </div>

        {/* 확정 견적 */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            확정 견적
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-600">
              <span>기준 단가</span>
              <span>{formatCurrency(product.basePrice)}</span>
            </div>
            {selectedPostProcessing.map((opt) => (
              <div key={opt.id} className="flex justify-between text-gray-600">
                <span>{opt.label} 추가</span>
                <span>+{formatCurrency(opt.price)}</span>
              </div>
            ))}
            <div className="flex justify-between text-gray-600 border-t border-gray-100 pt-2">
              <span>단가 합계</span>
              <span>{formatCurrency(unitPrice)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>수량</span>
              <span>{formData.quantity.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between text-lg font-bold text-gray-900 border-t border-gray-200 pt-3 mt-2">
              <span>확정 합계</span>
              <span className="text-blue-600">{formatCurrency(totalPrice)}</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex justify-between text-sm text-gray-600">
              <span>확정 납기</span>
              <span className="font-medium">주문 확정 후 약 2-3주</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
