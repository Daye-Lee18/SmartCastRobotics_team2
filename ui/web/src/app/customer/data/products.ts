// 국내 주물 제조사 표준 KS 규격 맨홀뚜껑 제품 카탈로그 + 후처리 옵션.
//
// product.id prefix (R/S/O) 는 backend `derive_ptn_loc()` 의 자동 패턴 매핑
// (R→1, S→2, O→3) 과 결합되어 동작한다. id 변경 시 backend orders.py 의
// 매핑 룰도 함께 갱신할 것.

import { Layers, Paintbrush, ShieldCheck, Stamp } from "lucide-react";
import type { Category, PostProcessingOption, Product } from "../lib/types";

export const CATEGORIES: { id: Category; label: string }[] = [
  { id: "all", label: "전체" },
  { id: "round", label: "원형 맨홀뚜껑" },
  { id: "square", label: "사각 맨홀뚜껑" },
  { id: "oval", label: "타원형 맨홀뚜껑" },
];

// @MX:NOTE: 카테고리별 제품 대표 이미지. "all"은 렌더링에 사용되지 않음.
export const CATEGORY_IMAGES: Record<Exclude<Category, "all">, string> = {
  round: "/products/round.jpg",
  square: "/products/square.jpg",
  oval: "/products/oval.jpg",
};

// @MX:NOTE: 국내 주물 제조사 표준 KS 규격 맨홀뚜껑 제품군 9종.
// 원형(round) / 사각(square) / 타원형(oval) 각 3종. 가격은 기준가(basePrice)로
// 후처리 옵션 추가 시 합산됨.
export const PRODUCTS: Product[] = [
  // ─── 원형 맨홀뚜껑 (3종) ───
  {
    id: "R-D450",
    name: "원형 맨홀뚜껑 KS D-450",
    category: "round",
    categoryLabel: "원형 맨홀뚜껑",
    spec: "직경 450mm, KS 규격",
    priceRange: "75,000원",
    basePrice: 75000,
    diameterOptions: ["450mm"],
    thicknessOptions: ["25mm", "30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },
  {
    id: "R-D500",
    name: "원형 맨홀뚜껑 KS D-500",
    category: "round",
    categoryLabel: "원형 맨홀뚜껑",
    spec: "직경 500mm, KS 규격",
    priceRange: "82,000원",
    basePrice: 82000,
    diameterOptions: ["500mm"],
    thicknessOptions: ["25mm", "30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },
  {
    id: "R-D550",
    name: "원형 맨홀뚜껑 KS D-550",
    category: "round",
    categoryLabel: "원형 맨홀뚜껑",
    spec: "직경 550mm, KS 규격",
    priceRange: "90,000원",
    basePrice: 90000,
    diameterOptions: ["550mm"],
    thicknessOptions: ["30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },

  // ─── 사각 맨홀뚜껑 (3종) ───
  {
    id: "S-400",
    name: "사각 맨홀뚜껑 KS S-400",
    category: "square",
    categoryLabel: "사각 맨홀뚜껑",
    spec: "400x400mm, KS 규격",
    priceRange: "68,000원",
    basePrice: 68000,
    diameterOptions: ["400x400mm"],
    thicknessOptions: ["25mm", "30mm", "35mm"],
    materials: ["FC200", "FC250"],
    loadClassRange: "A15 ~ C250",
  },
  {
    id: "S-450",
    name: "사각 맨홀뚜껑 KS S-450",
    category: "square",
    categoryLabel: "사각 맨홀뚜껑",
    spec: "450x450mm, KS 규격",
    priceRange: "78,000원",
    basePrice: 78000,
    diameterOptions: ["450x450mm"],
    thicknessOptions: ["25mm", "30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },
  {
    id: "S-500",
    name: "사각 맨홀뚜껑 KS S-500",
    category: "square",
    categoryLabel: "사각 맨홀뚜껑",
    spec: "500x500mm, KS 규격",
    priceRange: "88,000원",
    basePrice: 88000,
    diameterOptions: ["500x500mm"],
    thicknessOptions: ["30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },

  // ─── 타원형 맨홀뚜껑 (3종) ───
  {
    id: "O-450",
    name: "타원형 맨홀뚜껑 KS O-450",
    category: "oval",
    categoryLabel: "타원형 맨홀뚜껑",
    spec: "450x300mm, KS 규격",
    priceRange: "72,000원",
    basePrice: 72000,
    diameterOptions: ["450x300mm"],
    thicknessOptions: ["25mm", "30mm", "35mm"],
    materials: ["FC200", "FC250"],
    loadClassRange: "A15 ~ C250",
  },
  {
    id: "O-500",
    name: "타원형 맨홀뚜껑 KS O-500",
    category: "oval",
    categoryLabel: "타원형 맨홀뚜껑",
    spec: "500x350mm, KS 규격",
    priceRange: "80,000원",
    basePrice: 80000,
    diameterOptions: ["500x350mm"],
    thicknessOptions: ["25mm", "30mm", "35mm"],
    materials: ["FC200", "FC250"],
    loadClassRange: "A15 ~ C250",
  },
  {
    id: "O-550",
    name: "타원형 맨홀뚜껑 KS O-550",
    category: "oval",
    categoryLabel: "타원형 맨홀뚜껑",
    spec: "550x400mm, KS 규격",
    priceRange: "88,000원",
    basePrice: 88000,
    diameterOptions: ["550x400mm"],
    thicknessOptions: ["30mm", "35mm", "40mm"],
    materials: ["FC200", "FC250", "GCD450"],
    loadClassRange: "B125 ~ D400",
  },
];

export const LOAD_CLASSES = ["EN124 B125", "EN124 C250", "EN124 D400", "EN124 E600", "EN124 F900"];
export const MATERIALS = ["FC200", "FC250", "GCD450", "GCD500"];

export const POST_PROCESSING_OPTIONS: PostProcessingOption[] = [
  {
    id: "polish",
    label: "표면 연마",
    description: "매끄러운 표면 처리로 외관 품질 향상",
    price: 5000,
    icon: Paintbrush,
  },
  {
    id: "rustProof",
    label: "방청 코팅",
    description: "부식 방지 코팅으로 내구성 강화",
    price: 3000,
    icon: ShieldCheck,
  },
  {
    id: "zinc",
    label: "아연 도금",
    description: "아연 도금 처리로 장기 부식 방지",
    price: 8000,
    icon: Layers,
  },
  {
    id: "logo",
    label: "로고/문구 삽입",
    description: "회사 로고 또는 식별 문구 양각 삽입",
    price: 7000,
    icon: Stamp,
  },
];
