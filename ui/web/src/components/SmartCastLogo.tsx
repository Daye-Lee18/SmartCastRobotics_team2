/**
 * SmartCast Robotics 로고 컴포넌트.
 *
 * 디자인: 주황/빨강 그라데이션 배경 (둥근 사각형) + 용광로 실루엣 +
 *         용융 금속 발광 + 상단 로봇 암 세그먼트.
 * 주제: Smart (로봇) + Casting (용광로) + Robotics.
 *
 * 사용법:
 *   <SmartCastLogo />            // 기본 40px
 *   <SmartCastLogo size={56} />  // 사이즈 지정
 *   <SmartCastLogo className="drop-shadow-lg" />
 */
type Props = {
  size?: number;
  className?: string;
  title?: string;
};

export function SmartCastLogo({
  size = 40,
  className,
  title = "SmartCast Robotics",
}: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <defs>
        <linearGradient id="scBg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#dc2626" />
          <stop offset="60%" stopColor="#ea580c" />
          <stop offset="100%" stopColor="#f97316" />
        </linearGradient>
        <radialGradient id="scGlow" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor="#fef3c7" stopOpacity="1" />
          <stop offset="55%" stopColor="#fbbf24" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* 배경 (둥근 사각형, 빨강→주황 그라데이션) */}
      <rect width="48" height="48" rx="11" fill="url(#scBg)" />

      {/* 용광로 (사다리꼴) — 상부가 좁은 크루시블 */}
      <path
        d="M12 38 L36 38 L33.5 20 L14.5 20 Z"
        fill="#1f2937"
        stroke="#ffffff"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />

      {/* 용융 금속 (상단 타원 — 글로우) */}
      <ellipse cx="24" cy="20" rx="9.5" ry="2.2" fill="url(#scGlow)" />

      {/* 용광로 하단 발광 (흐릿한 내부 빛) */}
      <ellipse cx="24" cy="33" rx="6" ry="1.5" fill="#fbbf24" opacity="0.35" />

      {/* 로봇 암 세그먼트 (상단, 3 관절) */}
      <g
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="#ffffff"
      >
        <path d="M24 18 L24 12 L18 8" fill="none" />
        <circle cx="24" cy="18" r="1.8" />
        <circle cx="24" cy="12" r="1.8" />
        <circle cx="18" cy="8" r="1.8" />
      </g>

      {/* 바깥 테두리 */}
      <rect
        width="48"
        height="48"
        rx="11"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.15"
        strokeWidth="1"
      />
    </svg>
  );
}
