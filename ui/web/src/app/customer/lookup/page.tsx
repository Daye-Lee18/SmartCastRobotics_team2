"use client";

/**
 * 고객 주문 조회 - 이메일 입력 페이지 (/customer/lookup).
 *
 * 1) 랜딩 페이지에서 "주문 조회하기" 버튼을 누르면 여기로 이동.
 * 2) 이메일 입력 후 제출하면 /customer/orders?email=xxx 로 이동.
 * 3) 해당 이메일로 접수된 주문만 필터링 결과가 노출된다 (백엔드 GET /api/orders?email=).
 */

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, ArrowLeft, Search, AlertCircle, Loader2 } from "lucide-react";
import { SmartCastHeader } from "@/components/SmartCastHeader";
import { fetchOrdersByEmail } from "@/lib/api";

export default function CustomerLookupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) {
      setError("이메일을 입력해 주세요.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError("올바른 이메일 주소 형식이 아닙니다.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      // 핑크 GUI #1: 발주가 없으면 다음 페이지로 넘어가지 않음.
      // 빈 배열이면 "발주 기록 없음" 표시 후 lookup 페이지에 머무른다.
      const orders = await fetchOrdersByEmail(trimmed);
      if (orders.length === 0) {
        setError(`해당 이메일(${trimmed})로 접수된 발주 기록이 없습니다.`);
        return;
      }
      router.push(`/customer/orders?email=${encodeURIComponent(trimmed)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "조회 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
      <SmartCastHeader variant="card" />

      <div className="flex min-h-screen items-center justify-center px-4 pt-24 pb-12">
        <div className="w-full max-w-md">
          <Link
            href="/"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition hover:text-gray-800"
          >
            <ArrowLeft className="h-4 w-4" />
            메인으로
          </Link>

          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-lg">
            <div className="mb-6 flex flex-col items-center">
              <div className="mb-3 rounded-full bg-gradient-to-br from-amber-500 to-yellow-500 p-3 text-white shadow-md">
                <Search className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">주문 조회</h1>
              <p className="mt-1 text-center text-sm text-gray-500">
                주문 시 입력하신 이메일 주소로 조회할 수 있습니다.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="lookup-email"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  이메일 주소
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input
                    id="lookup-email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="example@company.com"
                    className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-4 text-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
                  />
                </div>
              </div>

              {error && (
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-amber-500 to-yellow-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    조회 중...
                  </>
                ) : (
                  "조회"
                )}
              </button>
            </form>

            <div className="mt-5 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-700">
              본인이 주문 시 입력한 이메일로만 조회됩니다. 이메일을 분실한 경우
              관리자에게 문의해 주세요.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
