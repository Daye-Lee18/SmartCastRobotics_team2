"""QSS 빌더 — 토큰을 받아 섹션 함수들의 결과를 합쳐 단일 QSS 문자열을 만든다.

CSS variables 미지원 회피를 위해 f-string 치환 패턴 사용.
섹션 함수들은 `app.styles.qss` sub-module 들에 책임별로 분산되어 있고,
본 모듈은 진입점 `build_qss(tokens)` 만 노출한다.
"""
from __future__ import annotations

from app.styles.qss import _SECTIONS
from app.styles.tokens import Tokens


def build_qss(tokens: Tokens) -> str:
    """토큰으로부터 전체 QSS 문자열 생성. QApplication.setStyleSheet() 에 직접 전달."""
    return "\n".join(section(tokens) for section in _SECTIONS)
