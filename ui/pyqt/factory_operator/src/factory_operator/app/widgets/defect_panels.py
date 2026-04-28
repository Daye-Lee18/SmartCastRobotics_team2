"""불량 TOP3 배지 + 검사 기준 참조 패널."""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

TOP_COLORS = [
    ("#fee2e2", "#991b1b", "#ef4444"),  # 1위 빨강
    ("#fed7aa", "#9a3412", "#f97316"),  # 2위 주황
    ("#fef3c7", "#854d0e", "#f59e0b"),  # 3위 노랑
]


class TopDefectsPanel(QFrame):
    """주요 불량 유형 TOP 3."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tableCard")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        title = QLabel("주요 불량 유형 TOP 3")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._badges: list[tuple[QLabel, QLabel, QLabel]] = []
        for rank in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)

            rank_label = QLabel(f"{rank + 1}")
            rank_label.setFixedSize(26, 26)
            rank_label.setAlignment(Qt.AlignCenter)
            rank_label.setObjectName("rankBadge")
            rank_label.setProperty("rank", str(rank + 1))
            row.addWidget(rank_label)

            name_label = QLabel("-")
            name_label.setObjectName("defectName")
            row.addWidget(name_label, stretch=1)

            count_label = QLabel("0")
            count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            count_label.setProperty("tone", "muted")
            row.addWidget(count_label)

            layout.addLayout(row)
            self._badges.append((rank_label, name_label, count_label))

        layout.addStretch()

    def update_data(self, items: list[dict[str, Any]]) -> None:
        """items: [{'type':'기공','count':12}, ...] (내림차순)"""
        sorted_items = sorted(items, key=lambda x: int(x.get("count", 0)), reverse=True)
        for i, (_, name, count) in enumerate(self._badges):
            if i < len(sorted_items):
                row = sorted_items[i]
                name.setText(str(row.get("type", "-")))
                count.setText(f"{int(row.get('count', 0))} 건")
            else:
                name.setText("-")
                count.setText("0 건")


class InspectionStandardsPanel(QFrame):
    """검사 기준 참조 패널."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tableCard")
        self.setFrameShape(QFrame.StyledPanel)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 14)
        self._layout.setSpacing(10)

        title = QLabel("검사 기준 참조")
        title.setObjectName("sectionTitle")
        self._layout.addWidget(title)

        # 고정 기준 목록 (기본)
        self._items: list[dict[str, Any]] = []
        self._rows: list[QFrame] = []
        self.update_data(
            [
                {
                    "product": "맨홀뚜껑 M500",
                    "target": "Φ500 × H40 mm",
                    "tolerance": "±0.8 mm",
                    "threshold": "95%",
                },
                {
                    "product": "그레이팅 GR-A",
                    "target": "500 × 300 × 25 mm",
                    "tolerance": "±1.0 mm",
                    "threshold": "92%",
                },
            ]
        )

    def update_data(self, items: list[dict[str, Any]]) -> None:
        # 기존 행 제거
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()

        for item in items[:4]:
            row = self._make_row(item)
            self._layout.addWidget(row)
            self._rows.append(row)

        self._layout.addStretch()
        self._items = list(items)

    def _make_row(self, item: dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("defectStandardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        name = QLabel(str(item.get("product", "-")))
        name.setObjectName("defectStandardName")
        layout.addWidget(name)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)

        for label_text, value_text in (
            ("목표", item.get("target", "-")),
            ("허용 오차", item.get("tolerance", "-")),
            ("임계값", item.get("threshold", "-")),
        ):
            pair = QVBoxLayout()
            pair.setSpacing(0)
            lab = QLabel(label_text)
            lab.setObjectName("defectStandardLabel")
            val = QLabel(str(value_text))
            val.setObjectName("defectStandardValue")
            pair.addWidget(lab)
            pair.addWidget(val)
            meta_row.addLayout(pair)

        meta_row.addStretch()
        layout.addLayout(meta_row)

        return card


__all__ = ["TopDefectsPanel", "InspectionStandardsPanel"]
