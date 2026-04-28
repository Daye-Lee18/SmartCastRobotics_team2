"use client";

import { AlertCircle } from "lucide-react";
import { emailErrorMessage, isValidEmail } from "../lib/validation";
import type { FormData } from "../lib/types";

interface Step4CustomerInfoProps {
  formData: FormData;
  onChange: (field: keyof FormData, value: string) => void;
  errors: Partial<Record<keyof FormData, string>>;
}

// Step 4: Customer Info.
// @MX:NOTE: 컴포넌트 이름의 "Step4" 는 historic naming 이며 실제 mount 단계는 step=1.
// 이메일은 "입력 완료" 기준에 형식 검증까지 포함한다 (allFilled).
export function Step4CustomerInfo({ formData, onChange, errors }: Step4CustomerInfoProps) {
  const fields: {
    key: keyof FormData;
    label: string;
    type: string;
    placeholder: string;
    required: boolean;
  }[] = [
    { key: "companyName", label: "회사명", type: "text", placeholder: "주식회사 예시", required: true },
    { key: "contactPerson", label: "담당자명", type: "text", placeholder: "홍길동", required: true },
    { key: "phone", label: "연락처", type: "tel", placeholder: "010-1234-5678", required: true },
    { key: "email", label: "이메일", type: "email", placeholder: "example@company.com", required: true },
    { key: "address", label: "배송지 주소", type: "text", placeholder: "서울특별시 강남구 ...", required: true },
  ];

  // 모든 필수 필드가 입력되었는지 확인 (공백만 있는 경우도 비어있는 것으로 취급).
  const allFilled = fields.every((f) => {
    const v = formData[f.key];
    if (typeof v !== "string" || v.trim().length === 0) return false;
    if (f.key === "email") return isValidEmail(v);
    return true;
  });

  // 이메일 필드 실시간 형식 에러 (입력 중에 바로 피드백)
  const liveEmailError = emailErrorMessage(formData.email);

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">주문자 정보 입력</h2>
      <p className="text-sm text-gray-500 mb-4">주문자 정보를 입력해 주세요.</p>

      {/* 필수 입력 안내 배너 — 모든 필드가 입력되어야 "다음" 버튼이 활성화됨 */}
      <div
        className={`mb-6 flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
          allFilled
            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
            : "border-amber-200 bg-amber-50 text-amber-800"
        }`}
        role="status"
      >
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <p className="leading-relaxed">
          {allFilled ? (
            <>
              주문자 정보 <strong>5가지 항목</strong>이 모두 입력되었습니다. 하단의{" "}
              <strong>&quot;다음&quot;</strong> 버튼을 눌러 다음 단계로 진행해 주세요.
            </>
          ) : (
            <>
              <strong>주문자 정보 5가지 항목(회사명·담당자명·연락처·이메일·배송지 주소)</strong>
              을 모두 입력해야 <strong>&quot;다음&quot;</strong> 버튼이 활성화됩니다.
            </>
          )}
        </p>
      </div>

      <div className="space-y-4">
        {fields.map((field) => {
          // 이메일 필드: 형식 에러는 실시간, 그 외는 validateStep 결과만
          const fieldError =
            field.key === "email"
              ? errors.email ?? liveEmailError ?? null
              : errors[field.key] ?? null;
          const showError = Boolean(fieldError);

          return (
            <div key={field.key}>
              <label
                htmlFor={`customer-${field.key}`}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              <input
                id={`customer-${field.key}`}
                type={field.type}
                value={formData[field.key] as string}
                onChange={(e) => onChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                autoComplete={field.key === "email" ? "email" : undefined}
                inputMode={field.key === "email" ? "email" : undefined}
                aria-invalid={showError}
                aria-describedby={showError ? `customer-${field.key}-error` : undefined}
                className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  showError ? "border-red-400 bg-red-50" : "border-gray-300"
                }`}
              />
              {showError && (
                <p
                  id={`customer-${field.key}-error`}
                  className="mt-1 text-xs text-red-500"
                >
                  {fieldError}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
