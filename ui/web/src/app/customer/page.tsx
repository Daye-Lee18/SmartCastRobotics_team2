"use client";

import { AlertCircle, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";
import { SmartCastHeader } from "@/components/SmartCastHeader";
import { Step1ProductSelection } from "./components/Step1ProductSelection";
import { Step2SpecInput } from "./components/Step2SpecInput";
import { Step3QuoteReview } from "./components/Step3QuoteReview";
import { Step4CustomerInfo } from "./components/Step4CustomerInfo";
import { Step5OrderComplete } from "./components/Step5OrderComplete";
import { StepIndicator } from "./components/StepIndicator";
import { POST_PROCESSING_OPTIONS, PRODUCTS } from "./data/products";
import { INITIAL_FORM, STEPS } from "./data/steps";
import { generateOrderNumber } from "./lib/format";
import type { FormData } from "./lib/types";
import { emailErrorMessage, isValidEmail } from "./lib/validation";

// 외부 호환을 위해 isValidEmail 을 그대로 re-export.
// (이전 모놀리식 page.tsx 시점에 named export 였음.)
export { isValidEmail };

export default function CustomerOrderPage() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [orderNumber, setOrderNumber] = useState("");
  // API 저장 상태
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedProduct = PRODUCTS.find((p) => p.id === formData.selectedProduct) ?? null;

  function handleChange(field: keyof FormData, value: string | string[] | number) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  }

  function validateStep(currentStep: number): boolean {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    if (currentStep === 1) {
      if (!formData.companyName) newErrors.companyName = "회사명을 입력해 주세요.";
      if (!formData.contactPerson) newErrors.contactPerson = "담당자명을 입력해 주세요.";
      if (!formData.phone) newErrors.phone = "연락처를 입력해 주세요.";
      if (!formData.email) {
        newErrors.email = "이메일을 입력해 주세요.";
      } else {
        // 형식 검증 (실제 발송 가능한 주소인지는 서버/발송 단계에서 추가 확인)
        const emailErr = emailErrorMessage(formData.email);
        if (emailErr) newErrors.email = emailErr;
      }
      if (!formData.address) newErrors.address = "배송지 주소를 입력해 주세요.";
    }

    if (currentStep === 2) {
      if (!formData.selectedProduct) {
        newErrors.selectedProduct = "제품을 선택해 주세요.";
        return false;
      }
    }

    if (currentStep === 3) {
      if (!formData.diameter) newErrors.diameter = "규격을 선택해 주세요.";
      if (!formData.thickness) newErrors.thickness = "두께를 선택해 주세요.";
      if (!formData.loadClass) newErrors.loadClass = "하중 등급을 선택해 주세요.";
      if (!formData.material) newErrors.material = "재질을 선택해 주세요.";
      if (!formData.desiredDelivery) newErrors.desiredDelivery = "희망 납기일을 입력해 주세요.";
      if (formData.quantity < 10) newErrors.quantity = "최소 주문 수량은 10개입니다.";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return false;
    }
    return true;
  }

  async function handleNext() {
    if (!validateStep(step)) return;

    // ─── Step 4(견적 확인) → 5(주문 완료): 백엔드 DB에 주문 저장 ───
    if (step === 4) {
      if (!selectedProduct) return;

      // 단가/합계 계산
      const postProcessingTotal = formData.postProcessing.reduce((sum, id) => {
        const opt = POST_PROCESSING_OPTIONS.find((o) => o.id === id);
        return sum + (opt?.price ?? 0);
      }, 0);
      const unitPrice = selectedProduct.basePrice + postProcessingTotal;
      const totalPrice = unitPrice * formData.quantity;

      const orderId = generateOrderNumber();
      try {
        setSubmitting(true);
        setSubmitError(null);

        // smartcast schema 전용 customer endpoint 한방 호출
        // (이메일로 user_account upsert + ord + ord_detail + ord_pp_map + RCVD 일괄)
        const customerRes = await fetch("/api/orders/customer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name: formData.companyName,
            customer_name: formData.contactPerson,
            phone: formData.phone,
            email: formData.email,
            shipping_address: formData.address,
            total_amount: totalPrice,
            requested_delivery: formData.desiredDelivery,
            details: [
              {
                product_id: selectedProduct.id,
                product_name: selectedProduct.name,
                quantity: formData.quantity,
                diameter: formData.diameter,
                thickness: formData.thickness,
                load_class: formData.loadClass,
                material: formData.material,
                post_processing_ids: formData.postProcessing,
                unit_price: unitPrice,
                subtotal: totalPrice,
              },
            ],
          }),
        });

        if (!customerRes.ok) {
          const errBody = await customerRes.json().catch(() => ({}));
          throw new Error(
            typeof errBody.detail === "string"
              ? errBody.detail
              : "주문 저장에 실패했습니다. 백엔드 서버를 확인해 주세요."
          );
        }

        const created = await customerRes.json();
        // 저장 성공 → 서버 확정 ID 사용 (예: "ord_7")
        setOrderNumber(created.id ?? orderId);
      } catch (err) {
        setSubmitError(
          err instanceof Error
            ? err.message
            : "알 수 없는 오류가 발생했습니다."
        );
        return; // 실패 시 Step 5로 넘어가지 않음
      } finally {
        setSubmitting(false);
      }
    }

    setStep((prev) => Math.min(prev + 1, 5));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handlePrev() {
    setErrors({});
    setStep((prev) => Math.max(prev - 1, 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleRestart() {
    setFormData(INITIAL_FORM);
    setErrors({});
    setStep(1);
    setOrderNumber("");
    setSubmitError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Step 1 (주문자 정보) 의 5개 필수 필드가 모두 채워지고
  // 이메일 형식도 유효해야 "다음" 버튼이 활성화된다.
  const isStep1Valid =
    formData.companyName.trim().length > 0 &&
    formData.contactPerson.trim().length > 0 &&
    formData.phone.trim().length > 0 &&
    isValidEmail(formData.email) &&
    formData.address.trim().length > 0;

  // 현재 단계 기준으로 "다음" / "주문 제출" 버튼을 비활성화해야 하는가?
  const nextDisabled = submitting || (step === 1 && !isStep1Valid);

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
      <SmartCastHeader variant="card" />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-8">
        {/* Step indicator */}
        <StepIndicator currentStep={step} />

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
          {step === 1 && (
            <Step4CustomerInfo
              formData={formData}
              onChange={(field, value) => handleChange(field, value)}
              errors={errors}
            />
          )}
          {step === 2 && (
            <Step1ProductSelection
              selectedProduct={formData.selectedProduct}
              onSelect={(id) => {
                handleChange("selectedProduct", id);
                setFormData((prev) => ({
                  ...prev,
                  selectedProduct: id,
                  diameter: "",
                  thickness: "",
                }));
              }}
            />
          )}
          {step === 3 && selectedProduct && (
            <Step2SpecInput
              formData={formData}
              product={selectedProduct}
              onChange={handleChange}
              errors={errors}
            />
          )}
          {step === 4 && selectedProduct && (
            <Step3QuoteReview formData={formData} product={selectedProduct} />
          )}
          {step === 5 && selectedProduct && (
            <Step5OrderComplete
              formData={formData}
              product={selectedProduct}
              orderNumber={orderNumber}
              onRestart={handleRestart}
            />
          )}

          {/* Navigation buttons */}
          {step < 5 && (
            <div className="mt-8 pt-6 border-t border-gray-100">
              {/* 에러 메시지 */}
              {submitError && (
                <div className="flex items-start gap-2 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{submitError}</span>
                </div>
              )}

              <div className="flex items-center justify-between">
                <button
                  onClick={handlePrev}
                  disabled={step === 1 || submitting}
                  className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all ${
                    step === 1 || submitting
                      ? "text-gray-300 cursor-not-allowed"
                      : "text-gray-600 hover:bg-gray-100 border border-gray-200"
                  }`}
                >
                  <ChevronLeft className="w-4 h-4" />
                  이전
                </button>

                <span className="text-xs text-gray-400">
                  {step} / {STEPS.length - 1}단계
                </span>

                <button
                  onClick={handleNext}
                  disabled={nextDisabled}
                  title={
                    step === 1 && !isStep1Valid
                      ? "주문자 정보 5가지 항목(회사명·담당자명·연락처·이메일·배송지 주소)을 모두 입력해 주세요."
                      : undefined
                  }
                  className={`inline-flex items-center gap-2 font-medium px-6 py-2.5 rounded-lg transition-all shadow-sm ${
                    nextDisabled
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700 text-white hover:shadow-md"
                  }`}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      저장 중...
                    </>
                  ) : (
                    <>
                      {step === 4 ? "주문 제출" : "다음"  /* step 4 = 견적 확인 → 주문 완료 */}
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
