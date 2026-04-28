"use client";

/**
 * 공개 랜딩 페이지 (/).
 *
 * 사용자 진입점: 우측 상단 SmartCast Robotics 브랜드 + 중앙 3 카드.
 *   1. 관리자   → /admin/login (비밀번호 입력)
 *   2. 주문하기 → /customer (발주 폼)
 *   3. 주문 조회하기 → /customer/lookup (이메일 입력 후 /customer/orders)
 */

import Link from "next/link";
import { ShieldCheck, ShoppingBag, Search, ArrowRight } from "lucide-react";
import { SmartCastHeader } from "@/components/SmartCastHeader";

const entries = [
  {
    href: "/admin/login",
    label: "관리자",
    desc: "주문/품질/생산 관리를 위한 관리자 포털 (비밀번호 필요)",
    icon: ShieldCheck,
    accent: "from-slate-700 to-slate-900",
    hoverAccent: "group-hover:from-slate-800 group-hover:to-slate-950",
  },
  {
    href: "/customer",
    label: "주문하기",
    desc: "맨홀 뚜껑·그레이팅 등 주물 제품을 온라인으로 발주",
    icon: ShoppingBag,
    accent: "from-red-500 to-orange-500",
    hoverAccent: "group-hover:from-red-600 group-hover:to-orange-600",
  },
  {
    href: "/customer/lookup",
    label: "주문 조회하기",
    desc: "이메일 주소로 내 주문 현황을 실시간 조회",
    icon: Search,
    accent: "from-amber-500 to-yellow-500",
    hoverAccent: "group-hover:from-amber-600 group-hover:to-yellow-600",
  },
] as const;

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-orange-50 to-red-50">
      {/* 배경 장식 */}
      <div className="pointer-events-none absolute -right-40 -top-40 h-96 w-96 rounded-full bg-orange-200 opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-red-200 opacity-30 blur-3xl" />

      {/* 우측 상단 공용 브랜드 헤더 */}
      <SmartCastHeader />

      {/* 본문 */}
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-20">
        {/* 히어로 */}
        <div className="mb-12 max-w-3xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-orange-200 bg-white/60 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-orange-600 backdrop-blur">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-orange-500" />
            Smart Casting · Robotics · Automation
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            SmartCast Robotics
          </h1>
          <p className="mt-4 text-base text-gray-600 sm:text-lg">
            주물 생산 전 공정을 자동화하는 스마트 공장 관제 시스템.
            <br className="hidden sm:block" />
            원하는 서비스를 선택해 주세요.
          </p>
        </div>

        {/* 3 카드 버튼 */}
        <div className="grid w-full max-w-5xl grid-cols-1 gap-5 sm:grid-cols-3">
          {entries.map(({ href, label, desc, icon: Icon, accent, hoverAccent }) => (
            <Link
              key={href}
              href={href}
              className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-md transition-all duration-200 hover:-translate-y-1 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              {/* 상단 컬러바 */}
              <div
                className={`absolute left-0 right-0 top-0 h-1.5 bg-gradient-to-r ${accent}`}
              />

              {/* 아이콘 */}
              <div
                className={`mb-4 inline-flex rounded-xl bg-gradient-to-br ${accent} ${hoverAccent} p-3.5 text-white shadow-sm transition`}
              >
                <Icon className="h-7 w-7" />
              </div>

              {/* 텍스트 */}
              <h2 className="text-xl font-bold text-gray-900">{label}</h2>
              <p className="mt-2 min-h-[3rem] text-sm leading-relaxed text-gray-600">
                {desc}
              </p>

              {/* 화살표 */}
              <div className="mt-4 flex items-center justify-between text-sm font-semibold text-gray-700">
                <span className="opacity-0 transition group-hover:opacity-100">
                  바로가기
                </span>
                <ArrowRight className="h-5 w-5 translate-x-0 text-gray-400 transition group-hover:translate-x-1 group-hover:text-orange-500" />
              </div>
            </Link>
          ))}
        </div>

        {/* 푸터 */}
        <div className="mt-16 text-center text-xs text-gray-400">
          © 2026 SmartCast Robotics. 주물 공장 스마트 관제 시스템.
        </div>
      </div>
    </main>
  );
}
