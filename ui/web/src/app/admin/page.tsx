"use client";

/**
 * 관리자 포털 허브 (/admin).
 *
 * 기존 /src/app/page.tsx 의 내용을 옮긴 것. 공개 랜딩 페이지(/) 에서
 * "관리자" 버튼 → /admin/login → 비밀번호 통과 후 이 페이지로 이동한다.
 *
 * 진입 가드: sessionStorage.admin_auth === "true" 가 없으면 /admin/login 으로 리다이렉트.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BarChart3, ClipboardList, FlaskConical, Monitor, LogOut } from "lucide-react";

const cards = [
  {
    href: "/admin/dashboard",
    label: "운영 대시보드",
    desc: "smartcast 기반 KPI + 시간대별/주간 생산 + err_log 트렌드 (10초 자동 갱신)",
    icon: BarChart3,
    color: "from-blue-500 to-indigo-600",
  },
  {
    href: "/orders",
    label: "주문 관리",
    desc: "주문 검토·승인·생산 승인 (우선순위 계산 대상 등록)",
    icon: ClipboardList,
    color: "from-emerald-500 to-teal-600",
  },
  {
    href: "/quality",
    label: "품질 관리",
    desc: "검사 기준 설정, 불량 분석, 품질 리포트",
    icon: FlaskConical,
    color: "from-purple-500 to-pink-600",
  },
] as const;

export default function AdminHomePage() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    // 클라이언트 사이드 단순 게이트 (NEXT_PUBLIC_* 기반이라 진짜 인증은 아님).
    // sessionStorage 동기 read → conditional setAuthorized 는 mount 1회만 실행되며
    // SSR-safe useState 로 표현 불가하므로 본 effect 패턴 의도적.
    if (typeof window !== "undefined") {
      const ok = window.sessionStorage.getItem("admin_auth") === "true";
      if (!ok) {
        router.replace("/admin/login");
      } else {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setAuthorized(true);
      }
    }
  }, [router]);

  const handleLogout = () => {
    window.sessionStorage.removeItem("admin_auth");
    router.replace("/");
  };

  if (!authorized) {
    return (
      <div className="p-8 text-center text-gray-500">인증 확인 중...</div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">관리자 포털</h1>
          <p className="mt-2 text-gray-600">
            주물공장 관제 시스템 관리자 웹. 실시간 모니터링과 생산 계획(우선순위 계산)은
            관제실 PyQt5 데스크톱 앱을 사용하세요.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm transition hover:bg-gray-50"
          aria-label="로그아웃"
        >
          <LogOut className="h-4 w-4" />
          로그아웃
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {cards.map(({ href, label, desc, icon: Icon, color }) => (
          <Link
            key={href}
            href={href}
            className="group relative overflow-hidden rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:shadow-lg hover:-translate-y-0.5"
          >
            <div
              className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${color}`}
            />
            <div className="flex items-start gap-4">
              <div
                className={`rounded-lg bg-gradient-to-br ${color} p-3 text-white`}
              >
                <Icon className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-gray-900">{label}</h2>
                <p className="mt-1 text-sm text-gray-600">{desc}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-blue-600 p-3 text-white">
            <Monitor className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-blue-900">
              관제 모니터링 앱 (PyQt5 데스크톱)
            </h2>
            <p className="mt-1 text-sm text-blue-700">
              실시간 대시보드, 생산 모니터링, <strong>생산 계획(우선순위 계산)</strong>,
              품질 검사, 물류 이송 화면은 관제실 PyQt5 데스크톱 앱에서 제공됩니다.
            </p>
            <div className="mt-3 rounded-md bg-white px-4 py-3 font-mono text-xs text-gray-700 border border-blue-100">
              cd monitoring && python main.py
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
