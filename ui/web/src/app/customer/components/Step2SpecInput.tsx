"use client";

import { CheckCircle, Factory } from "lucide-react";
import { POST_PROCESSING_OPTIONS } from "../data/products";
import { formatCurrency } from "../lib/format";
import type { FormData, Product } from "../lib/types";

interface Step2SpecInputProps {
  formData: FormData;
  product: Product;
  onChange: (field: keyof FormData, value: string | string[] | number) => void;
  errors: Partial<Record<keyof FormData, string>>;
}

// Step 2: Specification Input (이미지 카드형 후처리).
// @MX:NOTE: 컴포넌트 이름의 "Step2" 는 historic naming 이며 실제 mount 단계는 step=3.
export function Step2SpecInput({ formData, product, onChange, errors }: Step2SpecInputProps) {
  function togglePostProcessing(id: string) {
    const current = formData.postProcessing;
    const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
    onChange("postProcessing", next);
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">사양 입력</h2>
      <p className="text-sm text-gray-500 mb-6">선택하신 제품의 상세 사양을 입력해 주세요.</p>

      {/* 선택 제품 정보 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-3">
        <Factory className="w-5 h-5 text-blue-600 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-blue-800">{product.name}</p>
          <p className="text-xs text-blue-600">{product.spec}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {/* 규격 (직경) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            규격 (직경) <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.diameter}
            onChange={(e) => onChange("diameter", e.target.value)}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.diameter ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          >
            <option value="">선택하세요</option>
            {product.diameterOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          {errors.diameter && <p className="mt-1 text-xs text-red-500">{errors.diameter}</p>}
        </div>

        {/* 두께 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            두께 <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.thickness}
            onChange={(e) => onChange("thickness", e.target.value)}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.thickness ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          >
            <option value="">선택하세요</option>
            {product.thicknessOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          {errors.thickness && <p className="mt-1 text-xs text-red-500">{errors.thickness}</p>}
        </div>

        {/* 하중 등급 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            하중 등급 <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.loadClass}
            onChange={(e) => onChange("loadClass", e.target.value)}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.loadClass ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          >
            <option value="">선택하세요</option>
            {product.loadClasses.map((cls) => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
          {errors.loadClass && <p className="mt-1 text-xs text-red-500">{errors.loadClass}</p>}
        </div>

        {/* 재질 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            재질 <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.material}
            onChange={(e) => onChange("material", e.target.value)}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.material ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          >
            <option value="">선택하세요</option>
            {product.materials.map((mat) => (
              <option key={mat} value={mat}>{mat}</option>
            ))}
          </select>
          {errors.material && <p className="mt-1 text-xs text-red-500">{errors.material}</p>}
        </div>

        {/* 수량 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            수량 (최소 10개) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            min={10}
            value={formData.quantity}
            onChange={(e) => onChange("quantity", Number(e.target.value))}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.quantity ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          />
          {errors.quantity && <p className="mt-1 text-xs text-red-500">{errors.quantity}</p>}
        </div>

        {/* 희망 납기일 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            희망 납기일 <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={formData.desiredDelivery}
            onChange={(e) => onChange("desiredDelivery", e.target.value)}
            min={new Date().toISOString().split("T")[0]}
            className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.desiredDelivery ? "border-red-400 bg-red-50" : "border-gray-300"
            }`}
          />
          {errors.desiredDelivery && (
            <p className="mt-1 text-xs text-red-500">{errors.desiredDelivery}</p>
          )}
        </div>
      </div>

      {/* 후처리 — 이미지 카드 형식 */}
      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">후처리 옵션 (선택)</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {POST_PROCESSING_OPTIONS.map((opt) => {
            const isChecked = formData.postProcessing.includes(opt.id);
            const Icon = opt.icon;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => togglePostProcessing(opt.id)}
                className={`relative flex flex-col items-center text-center rounded-xl border-2 p-4 transition-all ${
                  isChecked
                    ? "border-blue-500 bg-blue-50 shadow-sm"
                    : "border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm"
                }`}
              >
                {/* 아이콘 이미지 영역 */}
                <div
                  className={`w-14 h-14 rounded-xl flex items-center justify-center mb-3 ${
                    isChecked ? "bg-blue-100" : "bg-gray-100"
                  }`}
                >
                  <Icon className={`w-7 h-7 ${isChecked ? "text-blue-600" : "text-gray-400"}`} />
                </div>
                <p className={`text-xs font-semibold mb-1 ${isChecked ? "text-blue-700" : "text-gray-800"}`}>
                  {opt.label}
                </p>
                <p className="text-[10px] text-gray-400 leading-tight mb-2">{opt.description}</p>
                <span className={`text-xs font-medium ${isChecked ? "text-blue-600" : "text-gray-500"}`}>
                  +{formatCurrency(opt.price)}
                </span>
                {/* 선택 표시 */}
                {isChecked && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                    <CheckCircle className="w-3.5 h-3.5 text-white" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
