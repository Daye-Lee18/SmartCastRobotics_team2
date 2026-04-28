// 고객 주문 마법사 도메인 타입.
// 5단계 wizard 가 공유하는 핵심 모델.

import type { LucideIcon } from "lucide-react";

export type ProductId = string;

export type Category = "all" | "round" | "square" | "oval";

export interface Product {
  id: ProductId;
  name: string;
  category: Category;
  categoryLabel: string;
  spec: string;
  priceRange: string;
  basePrice: number;
  diameterOptions: string[];
  thicknessOptions: string[];
  materials: string[];
  loadClassRange: string;
}

export interface FormData {
  // Step 1
  selectedProduct: ProductId | null;
  // Step 2
  diameter: string;
  thickness: string;
  loadClass: string;
  material: string;
  postProcessing: string[];
  quantity: number;
  desiredDelivery: string;
  // Step 4
  companyName: string;
  contactPerson: string;
  phone: string;
  email: string;
  address: string;
}

export interface PostProcessingOption {
  id: string;
  label: string;
  description: string;
  price: number;
  icon: LucideIcon;
}
