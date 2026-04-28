"""창고 랙 그리드 위젯 (3행 × 6열, 단일 구역).

랙 번호: 하단 좌측=1, 우측으로 증가 → 상단 우측=18.
    [13][14][15][16][17][18]   ← 최상단 (row 2)
    [ 7][ 8][ 9][10][11][12]
    [ 1][ 2][ 3][ 4][ 5][ 6]   ← 최하단 (row 0)
각 셀 hover 시 상세 정보 팝업.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# 랙 셀 치수 — 3행 × 6열 단일 그리드
CELL_W = 80
CELL_H = 50
GAP = 6
ROWS = 3
COLS = 6


# 점유 상태별 색상
STATUS_COLORS = {
    "empty": {"fill": "#f3f4f6", "border": "#d1d5db", "text": "#6b7280"},
    "partial": {"fill": "#fef3c7", "border": "#f59e0b", "text": "#92400e"},
    "full": {"fill": "#d1fae5", "border": "#10b981", "text": "#065f46"},
    "reserved": {"fill": "#dbeafe", "border": "#3b82f6", "text": "#1e40af"},
    "locked": {"fill": "#fee2e2", "border": "#ef4444", "text": "#991b1b"},
}


class RackCell(QGraphicsRectItem):
    """랙 셀 아이템 — 단일 구역."""

    def __init__(self, rack_id: str) -> None:
        super().__init__(0, 0, CELL_W, CELL_H)
        self._rack_id = rack_id
        self._status = "empty"
        self._content = ""

        self._id_label = QGraphicsSimpleTextItem(rack_id, self)
        self._id_label.setFont(QFont("Helvetica Neue", 11, QFont.Bold))
        self._id_label.setPos(8, 4)

        self._content_label = QGraphicsSimpleTextItem("", self)
        self._content_label.setFont(QFont("Helvetica Neue", 8))
        self._content_label.setPos(8, 24)

        self.setAcceptHoverEvents(True)
        self._apply_status()

    def set_data(self, status: str, content: str = "", qty: int = 0) -> None:
        self._status = status
        self._content = content
        text = content[:10] if content else "-"
        if qty:
            text = f"{text}\n×{qty}"
        self._content_label.setText(text)
        self._apply_status()
        self.setToolTip(
            f"랙 {self._rack_id}\n상태: {status}\n내용: {content or '비어있음'}\n수량: {qty}"
        )

    def _apply_status(self) -> None:
        colors = STATUS_COLORS.get(self._status, STATUS_COLORS["empty"])
        self.setBrush(QBrush(QColor(colors["fill"])))
        self.setPen(QPen(QColor(colors["border"]), 2))
        text_color = QColor(colors["text"])
        self._id_label.setBrush(QBrush(text_color))
        self._content_label.setBrush(QBrush(text_color))


class WarehouseRackScene(QGraphicsScene):
    """창고 랙 씬 — 단일 6×3 그리드.

    번호: 하단 좌측=1, 우측 +1 씩 증가 → 행이 한 행 위로 올라가면 +6.
    최상단 우측이 18.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setBackgroundBrush(QBrush(QColor("#ffffff")))

        total_w = COLS * CELL_W + (COLS - 1) * GAP + 40  # 40 = 좌우 여백
        total_h = ROWS * CELL_H + (ROWS - 1) * GAP + 20

        self.setSceneRect(0, 0, total_w, total_h)

        self._cells: dict[str, RackCell] = {}
        self._draw_cells()

    def _draw_cells(self) -> None:
        start_y = 10
        # row=0 이 화면상 최상단 (Qt 좌표). 사용자 요구는 하단 좌측=1 → 화면상 row=ROWS-1 에서 시작.
        for visual_row in range(ROWS):
            # logical row (하단 0) = ROWS - 1 - visual_row
            logical_row = ROWS - 1 - visual_row
            for col in range(COLS):
                rack_num = logical_row * COLS + col + 1  # 하단 좌측=1, 상단 우측=18
                rack_id = str(rack_num)
                cell = RackCell(rack_id)
                x = 20 + col * (CELL_W + GAP)
                y = start_y + visual_row * (CELL_H + GAP)
                cell.setPos(x, y)
                self.addItem(cell)
                self._cells[rack_id] = cell

    def update_racks(self, racks: list[dict[str, Any]]) -> None:
        """racks: [{'id':'1','status':'full','content':'맨홀뚜껑','qty':12}, ...].

        ID 는 정수 1..18 또는 그 문자열 형태. 다른 형식은 무시.
        """
        for rack in racks:
            rack_id = str(rack.get("id", "")).strip()
            cell = self._cells.get(rack_id)
            if cell:
                cell.set_data(
                    status=str(rack.get("status", "empty")),
                    content=str(rack.get("content", "")),
                    qty=int(rack.get("qty", 0) or 0),
                )


class WarehouseRackWidget(QFrame):
    """창고 랙 뷰 + 범례."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tableCard")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # 헤더 row: 제목 (좌) + 범례 (우)
        # 이전엔 view 아래에 범례가 있었는데 view 가 stretch 영역을 다 먹으면
        # 시각적으로 겹쳐 보이는 사고가 있었음 → 헤더 우측으로 옮겨서 분리.
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title = QLabel("창고 랙 (3행 × 6열)")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        legend_items = [
            ("비어있음", STATUS_COLORS["empty"]["fill"], STATUS_COLORS["empty"]["border"]),
            ("부분점유", STATUS_COLORS["partial"]["fill"], STATUS_COLORS["partial"]["border"]),
            ("점유", STATUS_COLORS["full"]["fill"], STATUS_COLORS["full"]["border"]),
            ("예약", STATUS_COLORS["reserved"]["fill"], STATUS_COLORS["reserved"]["border"]),
            ("잠김", STATUS_COLORS["locked"]["fill"], STATUS_COLORS["locked"]["border"]),
        ]
        for label, fill, border in legend_items:
            header_row.addWidget(_LegendItem(label, fill, border))

        layout.addLayout(header_row)

        self._scene = WarehouseRackScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setBackgroundBrush(QBrush(QColor("#ffffff")))
        # 3행 + A/B 라벨 + 여백이 모두 보이도록 최소 높이 보장 (fitInView 가 KeepAspectRatio
        # 로 작은 쪽에 맞추다 보니 외부 layout 이 height 를 좁히면 행이 잘리는 문제 회피)
        self._view.setMinimumHeight(220)
        layout.addWidget(self._view, stretch=1)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._view.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def update_racks(self, racks: list[dict[str, Any]]) -> None:
        self._scene.update_racks(racks)


class _LegendItem(QWidget):
    def __init__(self, label: str, fill: str, border: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        swatch = QLabel()
        swatch.setFixedSize(14, 10)
        swatch.setStyleSheet(
            f"background-color: {fill}; border: 1.5px solid {border}; border-radius: 2px;"
        )
        layout.addWidget(swatch)

        txt = QLabel(label)
        txt.setProperty("tone", "muted")
        layout.addWidget(txt)
