"""카드 컴포넌트 — 흰 배경/보더/라운드의 통일된 컨테이너.

KpiCard 는 KPI 표시 패턴 (제목/값/단위/델타).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.widgets.ui._helpers import set_property


class Card(QWidget):
    """기본 카드 — 흰 배경 + 보더 + 라운드. layout() 으로 자식 추가."""

    def __init__(
        self,
        *,
        padding: int = 16,
        spacing: int = 8,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("cardSection")  # 글로벌 QSS 룰 trigger
        layout = QVBoxLayout(self)
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(spacing)
        self._layout = layout

    def layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, w: QWidget) -> None:
        self._layout.addWidget(w)


class SectionTitle(QLabel):
    """섹션 제목 — #sectionTitle 글로벌 룰 적용."""

    def __init__(self, text: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("sectionTitle")


class KpiCard(QWidget):
    """KPI 카드: title + value (큰글씨) + unit + delta(상승/하락 색).

    예:
        kpi = KpiCard("일 생산량", "1,240", unit="개", delta="+12%", trend="up")
    """

    def __init__(
        self,
        title: str,
        value: str,
        *,
        unit: str = "",
        delta: str = "",
        trend: str = "flat",  # "up" | "down" | "flat"
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(4)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("kpiTitle")

        value_row = QHBoxLayout()
        value_row.setSpacing(6)
        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("kpiValue")
        value_row.addWidget(self._value_lbl, alignment=Qt.AlignBottom)
        if unit:
            self._unit_lbl = QLabel(unit)
            self._unit_lbl.setObjectName("kpiUnit")
            value_row.addWidget(self._unit_lbl, alignment=Qt.AlignBottom)
        else:
            self._unit_lbl = None  # type: ignore[assignment]
        value_row.addStretch(1)

        outer.addWidget(self._title_lbl)
        outer.addLayout(value_row)

        if delta:
            self._delta_lbl = QLabel(delta)
            self._delta_lbl.setObjectName("kpiDelta")
            set_property(self._delta_lbl, "trend", trend)
            outer.addWidget(self._delta_lbl)
        else:
            self._delta_lbl = None  # type: ignore[assignment]

    def set_value(self, value: str, *, unit: str | None = None) -> None:
        self._value_lbl.setText(value)
        if unit is not None and self._unit_lbl is not None:
            self._unit_lbl.setText(unit)

    def set_delta(self, delta: str, trend: str = "flat") -> None:
        if self._delta_lbl is None:
            return
        self._delta_lbl.setText(delta)
        set_property(self._delta_lbl, "trend", trend)
