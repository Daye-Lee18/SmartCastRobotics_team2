/**
 * SmartCast Robotics 공용 브랜드 헤더.
 *
 * 사용 페이지 (모두 우측 상단에 동일하게 노출):
 *   - `/` 랜딩
 *   - `/customer` 발주 포털
 *   - `/customer/lookup` 주문 조회 이메일 입력
 *   - `/customer/orders` 고객 주문 조회 결과
 *   - `/admin/login` 관리자 비밀번호 입력
 *
 * 홈(/) 링크를 포함하므로 어디서든 랜딩 페이지로 돌아올 수 있다.
 */
import Link from "next/link";
import { SmartCastLogo } from "./SmartCastLogo";

type Props = {
  /** 오른쪽 정렬(기본) 대신 왼쪽에 배치할 때 true */
  leftAligned?: boolean;
  /** 배경 투명(랜딩) 또는 흰색 카드(폼 페이지) 스타일 */
  variant?: "transparent" | "card";
};

export function SmartCastHeader({
  leftAligned = false,
  variant = "transparent",
}: Props) {
  const wrapperClass =
    variant === "card"
      ? "flex items-center gap-3 rounded-xl bg-white/90 px-4 py-2 shadow-sm ring-1 ring-gray-200 backdrop-blur"
      : "flex items-center gap-3";

  const content = (
    <Link
      href="/"
      className={`${wrapperClass} transition-opacity hover:opacity-80`}
      aria-label="SmartCast Robotics 홈으로 이동"
    >
      <SmartCastLogo size={40} />
      <div className="flex flex-col leading-tight">
        <span className="text-base font-bold text-gray-900">
          SmartCast Robotics
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wider text-orange-600">
          Smart Casting · Automation
        </span>
      </div>
    </Link>
  );

  return (
    <div
      className={`absolute top-5 z-20 ${
        leftAligned ? "left-5" : "right-5"
      }`}
    >
      {content}
    </div>
  );
}
