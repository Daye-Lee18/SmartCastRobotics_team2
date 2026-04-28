"""제목/메시지 라벨 — objectName 또는 tone property 로 색 결정."""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QWidget

from app.widgets.ui._helpers import set_property


class PageTitle(QLabel):
    """페이지 최상단 큰 제목."""

    def __init__(self, text: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("pageTitle")


class ToneLabel(QLabel):
    """톤 색상 라벨 — tone="ok"|"warn"|"danger"|"muted"|"primary".

    배경/보더 없는 일반 텍스트 (배지가 아님). 배지가 필요하면 StatusBadge 사용.
    """

    def __init__(
        self,
        text: str = "",
        *,
        tone: str = "muted",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        set_property(self, "tone", tone)

    def set_tone(self, tone: str) -> None:
        set_property(self, "tone", tone)
