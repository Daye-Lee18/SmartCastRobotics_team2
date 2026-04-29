"use client";

import { usePathname } from "next/navigation";
import { Bell } from "lucide-react";
import { useEffect, useState } from "react";

// 웹에서 접근 가능한 페이지만 타이틀 매핑 유지
// (생산 모니터링·생산 계획·물류/이송은 PyQt5 monitoring 앱으로 이관됨)
const PAGE_TITLES: Record<string, string> = {
  "/": "관리자 포털",
  "/orders": "주문 관리",
  "/quality": "품질 검사",
};

const ALERT_COUNT = 3;

function formatKoreanDateTime(date: Date): string {
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export default function Header() {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] ?? "주물공장 관제";

  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(formatKoreanDateTime(new Date()));
    }, 1000);

    // 초기값을 requestAnimationFrame으로 설정하여 cascading render 방지
    requestAnimationFrame(() => {
      setCurrentTime(formatKoreanDateTime(new Date()));
    });

    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      {/* Page title */}
      <h1 className="text-xl font-semibold text-gray-800">{title}</h1>

      {/* Right section */}
      <div className="flex items-center gap-5">
        {/* Current date/time */}
        <span className="text-sm text-gray-500 tabular-nums hidden sm:block">
          {currentTime}
        </span>

        {/* Alert bell */}
        <button
          type="button"
          aria-label={`알림 ${ALERT_COUNT}개`}
          className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
        >
          <Bell className="h-5 w-5" />
          {ALERT_COUNT > 0 && (
            <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white leading-none">
              {ALERT_COUNT}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
