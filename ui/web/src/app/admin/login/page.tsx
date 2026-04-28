"use client";

/**
 * 관리자 비밀번호 입력 페이지 (/admin/login).
 *
 * ⚠️ 보안 수준: NEXT_PUBLIC_ADMIN_PASSWORD 환경변수 기반 클라이언트 사이드 게이트.
 * 브라우저 번들에 비밀번호가 포함되어 누구나 DevTools 에서 확인 가능하다.
 * "실수로 관리자 페이지에 진입하는 것을 막는" 수준의 단순 차단이며,
 * 실제 인증 시스템은 Auth0/Clerk/JWT 등 별도 도입 필요.
 */

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Lock, ArrowLeft, AlertCircle } from "lucide-react";
import { SmartCastHeader } from "@/components/SmartCastHeader";

const EXPECTED_PASSWORD =
  process.env.NEXT_PUBLIC_ADMIN_PASSWORD ?? "admin1234";

export default function AdminLoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    // 최소한의 반응 시간 (짧게 대기해서 "제출 중" 피드백 느낌 주기)
    setTimeout(() => {
      if (password === EXPECTED_PASSWORD) {
        window.sessionStorage.setItem("admin_auth", "true");
        router.replace("/admin");
      } else {
        setError("비밀번호가 올바르지 않습니다.");
        setSubmitting(false);
      }
    }, 200);
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
      <SmartCastHeader variant="card" />

      <div className="flex min-h-screen items-center justify-center px-4 pt-24 pb-12">
        <div className="w-full max-w-md">
          {/* 뒤로 가기 */}
          <Link
            href="/"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 transition hover:text-gray-800"
          >
            <ArrowLeft className="h-4 w-4" />
            메인으로
          </Link>

          {/* 카드 */}
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-lg">
            <div className="mb-6 flex flex-col items-center">
              <div className="mb-3 rounded-full bg-gradient-to-br from-red-500 to-orange-500 p-3 text-white shadow-md">
                <Lock className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">관리자 로그인</h1>
              <p className="mt-1 text-sm text-gray-500">
                비밀번호를 입력해 주세요
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="admin-password"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  비밀번호
                </label>
                <input
                  id="admin-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={submitting}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-200 disabled:bg-gray-50"
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting || !password}
                className="w-full rounded-lg bg-gradient-to-r from-red-500 to-orange-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "확인 중..." : "로그인"}
              </button>
            </form>

            <p className="mt-4 text-center text-xs text-gray-400">
              기본 비밀번호: <code className="font-mono">admin1234</code> (개발용)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
