"""상태 배지 — 둥근 캡슐 형태 + 색 + 보더.

status: ok | warn | danger | defect | info | muted
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QWidget

from app.widgets.ui._helpers import set_property


class StatusBadge(QLabel):
    """상태 배지 — QLabel[status=...] 글로벌 룰 적용."""

    def __init__(
        self,
        text: str = "",
        *,
        status: str = "muted",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        set_property(self, "status", status)

    def set_status(self, status: str, *, text: str | None = None) -> None:
        if text is not None:
            self.setText(text)
        set_property(self, "status", status)
