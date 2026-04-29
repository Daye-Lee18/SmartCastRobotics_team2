import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AdminShell from "@/components/AdminShell";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "주물공장 생산 관제 시스템",
  description: "주물 생산 공정 실시간 모니터링 대시보드",
  // iOS Safari 의 Data Detectors (전화번호/날짜/주소/이메일 자동 링크화) 는 React 하이드레이션
  // 전에 DOM 에 속성을 주입해 "attributes didn't match" 에러를 일으킨다. 전부 차단.
  formatDetection: {
    telephone: false,
    date: false,
    address: false,
    email: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // suppressHydrationWarning: next/font/google 이 생성하는 className 해시는 SSR build 와 client
  // hydration 사이에 소량 차이가 날 수 있고, iOS Safari / 브라우저 확장이 <body> 에 속성을
  // 주입하기도 한다. 이 두 단계는 React 트리 아래로는 전파되지 않아 root 레벨에서 무시해도 안전.
  return (
    <html lang="ko" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <body className="h-full bg-gray-50 antialiased" suppressHydrationWarning>
        <AdminShell>{children}</AdminShell>
      </body>
    </html>
  );
}
