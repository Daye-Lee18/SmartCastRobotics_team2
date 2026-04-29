import type { Metadata } from "next";

/**
 * 고객 영역 전용 layout.
 *
 * ⚠️ Next.js 16 에서 html/body 는 루트 layout.tsx 에만 있어야 한다.
 * 이전에는 customer/layout.tsx 가 자체 html/body 를 렌더했지만 hydration
 * 오류를 일으키므로 pass-through 로 단순화했다.
 *
 * 각 customer 페이지(page.tsx, orders/page.tsx, lookup/page.tsx)는
 * 내부에서 `SmartCastHeader` 를 직접 배치해 우측 상단 브랜드를 노출한다.
 * (AdminShell 은 /customer/** 를 public 경로로 처리해 Sidebar/Header 가 안 붙음)
 */

export const metadata: Metadata = {
  title: "SmartCast Robotics — 온라인 발주",
  description: "SmartCast Robotics 주물 제품 온라인 발주 시스템",
};

export default function CustomerLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
