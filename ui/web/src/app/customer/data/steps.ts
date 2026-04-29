// 5단계 wizard 구성 정보 + 폼 초기값.
//
// @MX:NOTE: STEPS.id 와 컴포넌트 이름은 의도적으로 어긋난다.
//   step.id=1 → "주문자 정보" → Step4CustomerInfo 컴포넌트
//   step.id=2 → "제품 선택"   → Step1ProductSelection 컴포넌트
//   step.id=3 → "사양 입력"   → Step2SpecInput 컴포넌트
//   step.id=4 → "견적 확인"   → Step3QuoteReview 컴포넌트
//   step.id=5 → "주문 완료"   → Step5OrderComplete 컴포넌트
// 컴포넌트 이름은 historic naming (초기 wizard 순서) 를 보존한 것.

import { CircleCheck, FileText, Package, Settings, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { FormData } from "../lib/types";

export const STEPS: { id: number; label: string; icon: LucideIcon }[] = [
  { id: 1, label: "주문자 정보", icon: User },
  { id: 2, label: "제품 선택", icon: Package },
  { id: 3, label: "사양 입력", icon: Settings },
  { id: 4, label: "견적 확인", icon: FileText },
  { id: 5, label: "주문 완료", icon: CircleCheck },
];

export const INITIAL_FORM: FormData = {
  selectedProduct: null,
  diameter: "",
  thickness: "",
  loadClass: "",
  material: "",
  postProcessing: [],
  quantity: 10,
  desiredDelivery: "",
  companyName: "",
  contactPerson: "",
  phone: "",
  email: "",
  address: "",
};
