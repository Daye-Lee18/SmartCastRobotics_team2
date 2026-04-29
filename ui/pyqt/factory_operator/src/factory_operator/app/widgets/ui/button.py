"""버튼 컴포넌트 — variant + size 기반.

variant:
  primary (기본) | secondary | outline | ghost | danger | success | warn
size:
  sm | md (기본) | lg

QSS 룰은 app/styles/builder.py:_buttons() 가 담당.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QToolButton, QWidget

from app.widgets.ui._helpers import set_property


class Button(QPushButton):
    """범용 버튼 — variant/size property 만 설정하고 색은 글로벌 QSS 가 결정."""

    def __init__(
        self,
        text: str = "",
        *,
        variant: str = "primary",
        size: str = "md",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        # primary 는 default 룰이 처리하므로 property 미설정 (specificity 회피)
        if variant != "primary":
            set_property(self, "variant", variant)
        if size != "md":
            set_property(self, "size", size)

    def set_variant(self, variant: str) -> None:
        """런타임 variant 변경 (예: 활성/비활성에 따라 색 변경)."""
        set_property(self, "variant", variant if variant != "primary" else None)

    def set_size(self, size: str) -> None:
        set_property(self, "size", size if size != "md" else None)


class IconButton(QToolButton):
    """아이콘 전용 버튼 — 작은 사각 영역, 보더 없음."""

    def __init__(
        self,
        text: str = "",
        *,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        if tooltip:
            self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoRaise(True)
