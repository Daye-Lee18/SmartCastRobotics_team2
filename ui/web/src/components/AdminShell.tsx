"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import DevHandoffAckButton from "@/components/DevHandoffAckButton";

/**
 * 관리자 Shell 래퍼.
 *
 * Public 경로 (Shell 미적용, children 만 렌더):
 *   - `/`                랜딩 페이지 (SmartCast Robotics 3 버튼)
 *   - `/admin/login`     관리자 비밀번호 입력
 *   - `/customer/**`     고객 포털 (발주, 조회, 조회 결과)
 *
 * 나머지 경로 (`/admin`, `/orders`, `/quality` 등) 는 Sidebar + Header 관리자 쉘 적용.
 */
export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const isPublic =
    pathname === "/" ||
    pathname === "/admin/login" ||
    pathname.startsWith("/customer");

  if (isPublic) {
    return (
      <>
        {children}
        <DevHandoffAckButton />
      </>
    );
  }

  return (
    <>
      <Sidebar />
      <div className="ml-64 flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
      <DevHandoffAckButton />
    </>
  );
}
