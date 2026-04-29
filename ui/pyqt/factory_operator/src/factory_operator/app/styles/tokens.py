"""Design tokens — Light/Dark 테마용 frozen dataclass + WCAG AA 검증.

테마는 두 개의 Tokens 인스턴스 (LIGHT, DARK) 로 정의되며 import 시점에
주요 색상 쌍의 대비가 4.5:1 이상인지 assert 한다.

색상 명명 규칙:
- bg_*       — 배경 계층 (app → card → elevated → muted)
- border_*   — 보더 (기본 → 강조)
- text_*     — 글자 (primary → secondary → muted → inverse)
- brand_*    — 주 액션 색
- status_*   — 의미 색 (ok/warn/danger/defect)
- sidebar_*  — 사이드바 전용 (테마 무관 어두운 톤 유지)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

# ============================================================================
# Color contrast utilities (WCAG)
# ============================================================================


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(hex_color: str) -> float:
    def f(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 명도 대비 — 4.5:1 이상이 본문 AA 통과."""
    l1, l2 = _relative_luminance(fg), _relative_luminance(bg)
    light, dark = max(l1, l2), min(l1, l2)
    return (light + 0.05) / (dark + 0.05)


# ============================================================================
# Token dataclasses
# ============================================================================


@dataclass(frozen=True)
class ColorTokens:
    # 배경 계층
    bg_app: str = "#f0f2f5"
    bg_card: str = "#ffffff"
    bg_elevated: str = "#f8fafc"
    bg_muted: str = "#f1f5f9"

    # 보더
    border: str = "#e2e8f0"
    border_strong: str = "#cbd5e1"

    # 글자
    text_primary: str = "#0f172a"
    text_secondary: str = "#334155"
    text_muted: str = "#64748b"
    text_inverse: str = "#ffffff"

    # 브랜드 (주 액션)
    brand: str = "#2563eb"  # 버튼 배경 (white 대비 5.17:1 AA)
    brand_hover: str = "#1d4ed8"  # blue-700
    brand_subtle: str = "#dbeafe"  # 연파스텔 배경
    brand_text_on: str = "#ffffff"  # 버튼 위 글자
    brand_accent: str = "#1d4ed8"  # 라이트 배경 위 강조 텍스트/링크

    # 상태 (Industrial 의미색)
    ok: str = "#15803d"  # green-700 (AA)
    ok_subtle: str = "#dcfce7"
    warn: str = "#b45309"  # amber-700 (AA)
    warn_subtle: str = "#fef3c7"
    danger: str = "#b91c1c"  # red-700 (AA)
    danger_subtle: str = "#fee2e2"
    defect: str = "#7e22ce"  # purple-700 (AA)
    defect_subtle: str = "#f3e8ff"
    info: str = "#0369a1"  # sky-700
    info_subtle: str = "#e0f2fe"

    # 사이드바 (테마 무관 다크 톤 유지)
    sidebar_bg: str = "#0f172a"
    sidebar_bg_top: str = "#020617"
    sidebar_text: str = "#cbd5e1"
    sidebar_text_muted: str = "#64748b"
    sidebar_text_active: str = "#ffffff"
    sidebar_hover: str = "#1e293b"
    sidebar_active: str = "#1e40af"
    sidebar_accent: str = "#60a5fa"
    sidebar_border: str = "#1e293b"

    # 카메라/dark canvas
    canvas_bg: str = "#0f172a"
    canvas_border: str = "#1e293b"

    # 셀렉션
    selection_bg: str = "#dbeafe"
    selection_text: str = "#0f172a"


@dataclass(frozen=True)
class TypographyTokens:
    family: str = '"Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Segoe UI", sans-serif'
    family_mono: str = '"SF Mono", "Menlo", "Consolas", monospace'

    # 크기 (px)
    size_xs: int = 11  # 캡션, 메타
    size_sm: int = 12  # 보조
    size_base: int = 13  # 본문 기본
    size_md: int = 14  # 입력/버튼 라벨
    size_lg: int = 16  # 섹션
    size_xl: int = 20  # 페이지 부제
    size_2xl: int = 24  # 페이지 제목
    size_3xl: int = 32  # KPI 값


@dataclass(frozen=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class RadiusTokens:
    sm: int = 4
    md: int = 6
    lg: int = 8
    xl: int = 12
    full: int = 9999


@dataclass(frozen=True)
class Tokens:
    color: ColorTokens = field(default_factory=ColorTokens)
    typography: TypographyTokens = field(default_factory=TypographyTokens)
    spacing: SpacingTokens = field(default_factory=SpacingTokens)
    radius: RadiusTokens = field(default_factory=RadiusTokens)
    is_dark: bool = False


# ============================================================================
# Theme instances
# ============================================================================

LIGHT = Tokens(is_dark=False)

DARK = Tokens(
    is_dark=True,
    color=ColorTokens(
        bg_app="#0f172a",
        bg_card="#1e293b",
        bg_elevated="#334155",
        bg_muted="#1e293b",
        border="#334155",
        border_strong="#475569",
        text_primary="#f1f5f9",
        text_secondary="#cbd5e1",
        text_muted="#94a3b8",
        text_inverse="#0f172a",
        brand="#1d4ed8",  # 버튼 배경 — white 대비 7.66:1 AAA
        brand_hover="#2563eb",
        brand_subtle="#1e3a8a",
        brand_text_on="#ffffff",
        brand_accent="#93c5fd",  # 다크 배경 위 강조 텍스트 (밝은 블루)
        # 다크 배경에선 채도/명도 더 높임
        ok="#4ade80",
        ok_subtle="#14532d",
        warn="#fbbf24",
        warn_subtle="#78350f",
        danger="#f87171",
        danger_subtle="#7f1d1d",
        defect="#c084fc",
        defect_subtle="#581c87",
        info="#38bdf8",
        info_subtle="#075985",
        sidebar_bg="#020617",
        sidebar_bg_top="#000000",
        sidebar_text="#cbd5e1",
        sidebar_text_muted="#64748b",
        sidebar_text_active="#ffffff",
        sidebar_hover="#1e293b",
        sidebar_active="#1d4ed8",
        sidebar_accent="#60a5fa",
        sidebar_border="#0f172a",
        canvas_bg="#020617",
        canvas_border="#1e293b",
        selection_bg="#1e3a8a",
        selection_text="#f1f5f9",
    ),
)


# ============================================================================
# WCAG AA 검증 (import 시점, 4.5:1 기준)
# ============================================================================


def _assert_aa(tokens: Tokens, label: str) -> None:
    c = tokens.color
    pairs = [
        ("text_primary on bg_app", c.text_primary, c.bg_app),
        ("text_primary on bg_card", c.text_primary, c.bg_card),
        ("text_secondary on bg_card", c.text_secondary, c.bg_card),
        ("brand_text_on on brand", c.brand_text_on, c.brand),
        ("sidebar_text_active on sidebar_active", c.sidebar_text_active, c.sidebar_active),
        ("ok on bg_card", c.ok, c.bg_card),
        ("warn on bg_card", c.warn, c.bg_card),
        ("danger on bg_card", c.danger, c.bg_card),
    ]
    for name, fg, bg in pairs:
        ratio = contrast_ratio(fg, bg)
        if ratio < 4.5:
            raise AssertionError(
                f"WCAG AA 실패 [{label}] {name}: {fg} on {bg} = {ratio:.2f}:1 (< 4.5)"
            )


_assert_aa(LIGHT, "LIGHT")
_assert_aa(DARK, "DARK")


# ============================================================================
# Helper
# ============================================================================


def with_overrides(base: Tokens, **overrides: object) -> Tokens:
    """테스트용 토큰 일부 override (frozen dataclass replace)."""
    return replace(base, **overrides)  # type: ignore[arg-type]
