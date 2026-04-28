"""디자인 시스템 — Light/Dark 테마 + 토큰 + QSS 빌더 + 테마 매니저.

진입점:
    from app.styles import ThemeManager, LIGHT, DARK
    tm = ThemeManager()
    tm.apply(QApplication.instance())
    tm.set_mode("dark")  # "system" | "light" | "dark"

설계 원칙:
- frozen dataclass 토큰 (불변, 테스트 가능)
- 섹션 함수 조합으로 QSS 빌드 (CSS variables 미지원 우회)
- macOS 시스템 다크모드 영향 차단을 위해 QApplication.setStyle("Fusion") 강제
- WCAG AA 대비 import 시점 assert (key pair만)
- 컴포넌트는 setStyleSheet 직접 호출 금지, setProperty(variant=...) + 글로벌 룰 사용
"""

from __future__ import annotations

from app.styles.builder import build_qss
from app.styles.theme import ThemeManager
from app.styles.tokens import (
    DARK,
    LIGHT,
    ColorTokens,
    SpacingTokens,
    Tokens,
    TypographyTokens,
    contrast_ratio,
)

__all__ = [
    "DARK",
    "LIGHT",
    "ColorTokens",
    "SpacingTokens",
    "ThemeManager",
    "Tokens",
    "TypographyTokens",
    "build_qss",
    "contrast_ratio",
]
