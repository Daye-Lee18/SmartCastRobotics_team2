"use client";

import { CheckCircle, Factory, Gem, Weight } from "lucide-react";
import { useMemo, useState } from "react";
import { CATEGORIES, CATEGORY_IMAGES, PRODUCTS } from "../data/products";
import type { Category, ProductId } from "../lib/types";

interface Step1ProductSelectionProps {
  selectedProduct: ProductId | null;
  onSelect: (id: ProductId) => void;
}

// Step 1: Product Selection (카테고리 필터 + 재질/하중등급).
// @MX:NOTE: 컴포넌트 이름의 "Step1" 은 historic naming 이며 실제 mount 단계는 step=2.
export function Step1ProductSelection({ selectedProduct, onSelect }: Step1ProductSelectionProps) {
  const [category, setCategory] = useState<Category>("all");

  const filteredProducts = useMemo(() => {
    if (category === "all") return PRODUCTS;
    return PRODUCTS.filter((p) => p.category === category);
  }, [category]);

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">제품 선택</h2>
      <p className="text-sm text-gray-500 mb-6">주문하실 제품을 선택해 주세요.</p>

      {/* 카테고리 필터 */}
      <div className="flex items-center gap-2 mb-6">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              category === cat.id
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* 제품 그리드 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {filteredProducts.map((product) => {
          const isSelected = selectedProduct === product.id;
          return (
            <button
              key={product.id}
              onClick={() => onSelect(product.id)}
              className={`text-left rounded-xl border-2 p-5 transition-all hover:shadow-md ${
                isSelected
                  ? "border-blue-600 bg-blue-50 shadow-md"
                  : "border-gray-200 bg-white hover:border-blue-300"
              }`}
            >
              {/* 제품 이미지 (카테고리별 대표 이미지) */}
              <div className="w-full h-36 bg-white rounded-lg mb-4 relative overflow-hidden">
                {product.category !== "all" && CATEGORY_IMAGES[product.category] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={CATEGORY_IMAGES[product.category]}
                    alt={product.name}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center">
                    <Factory
                      className={`w-10 h-10 mb-1 ${isSelected ? "text-blue-500" : "text-gray-400"}`}
                    />
                    <span className="text-xs text-gray-400">제품 이미지</span>
                  </div>
                )}
                {/* 카테고리 뱃지 */}
                <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/80 text-gray-700 border border-gray-200 backdrop-blur">
                  {product.categoryLabel}
                </span>
              </div>

              <h3 className={`font-semibold text-sm mb-1 ${isSelected ? "text-blue-700" : "text-gray-900"}`}>
                {product.name}
              </h3>
              <p className="text-xs text-gray-500 mb-3">{product.spec}</p>

              {/* 재질 + 하중등급 정보 */}
              <div className="space-y-1.5 mb-3">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Gem className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                  <span>재질: {product.materials.join(", ")}</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Weight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                  <span>하중: {product.loadClassRange}</span>
                </div>
              </div>

              <p className={`text-xs font-medium ${isSelected ? "text-blue-600" : "text-gray-400"}`}>
                기준가 {product.priceRange}
              </p>
              {isSelected && (
                <div className="mt-3 flex items-center gap-1 text-blue-600">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-xs font-medium">선택됨</span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
