"""재사용 가능한 UI 컴포넌트 라이브러리 — 토큰 기반 디자인 시스템 v2.

원칙:
- 컴포넌트는 setStyleSheet 를 직접 호출하지 않는다.
- 대신 objectName 또는 setProperty("variant", ...) 로 태그하고
  글로벌 QSS (app/styles/builder.py) 가 스타일을 결정한다.
- 테마 변경 시 자동으로 새 색이 적용된다 (QApplication.setStyleSheet 재호출).

진입점:
    from app.widgets.ui import (
        Button, KpiCard, Card, SectionTitle, StatusBadge, ToneLabel,
    )
"""

from __future__ import annotations

from app.widgets.ui.badge import StatusBadge
from app.widgets.ui.button import Button, IconButton
from app.widgets.ui.card import Card, KpiCard, SectionTitle
from app.widgets.ui.label import PageTitle, ToneLabel

__all__ = [
    "Button",
    "Card",
    "IconButton",
    "KpiCard",
    "PageTitle",
    "SectionTitle",
    "StatusBadge",
    "ToneLabel",
]
