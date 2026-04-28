"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardList, FlaskConical, Factory } from "lucide-react";

// 관리자 웹 페이지 (Next.js).
// 모니터링 관련 페이지(대시보드/생산 모니터링/품질 검사/물류 이송/생산 계획)는
// PyQt5 데스크톱 앱(monitoring/)으로 분리됨.
// @MX:NOTE: Confluence 17956894 결정 — UI 분리 정책
// 2026-04-08: 생산 계획(우선순위 계산)·입출고 내역 페이지를 PyQt5로 이관
const navItems = [
  { href: "/orders", label: "주문 관리", icon: ClipboardList },
  { href: "/quality", label: "품질 관리", icon: FlaskConical },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 text-white flex flex-col z-30">
      {/* Logo area */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-700">
        <Factory className="h-7 w-7 text-blue-400 shrink-0" />
        <span className="text-lg font-bold tracking-tight text-white">
          주물공장 관제
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <ul className="space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive = href === "/" ? pathname === "/" : pathname === href;
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={[
                    "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:bg-gray-800 hover:text-white",
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
