"""분류 장치 원형 다이얼 위젯.

현재 분류 각도 + 분류 방향(양품/불량) + 동작 성공 여부.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

# 분류 방향 -> 각도
DIRECTION_ANGLE = {
    "left": 180.0,  # 양품 왼쪽 슈트
    "right": 0.0,  # 양품 오른쪽 슈트
    "up": 90.0,  # 중앙 통과
    "down": 270.0,  # 불량 아래 슈트
    "good": 90.0,
    "bad": 270.0,
}


class SorterDial(QWidget):
    """원형 다이얼 - 분류 각도 + 상태."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(220, 220)
        self._angle: float = 90.0  # 기본: 위
        self._direction: str = "good"  # good / bad
        self._success: bool = True
        self._count_good: int = 0
        self._count_bad: int = 0

    def set_state(
        self,
        *,
        angle: float | None = None,
        direction: str | None = None,
        success: bool | None = None,
        count_good: int | None = None,
        count_bad: int | None = None,
    ) -> None:
        if angle is not None:
            self._angle = float(angle)
        if direction is not None:
            self._direction = direction.lower()
            if angle is None:
                self._angle = DIRECTION_ANGLE.get(self._direction, 90.0)
        if success is not None:
            self._success = success
        if count_good is not None:
            self._count_good = int(count_good)
        if count_bad is not None:
            self._count_bad = int(count_bad)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 24
        cx = w / 2
        cy = h / 2

        # 외곽 링
        outer_rect = QRectF(cx - size / 2, cy - size / 2, size, size)
        painter.setPen(QPen(QColor("#d1d5db"), 2))
        painter.setBrush(QBrush(QColor("#f9fafb")))
        painter.drawEllipse(outer_rect)

        # 내부 링
        inner_r = size / 2 - 22
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(inner_rect)

        # 방향 라벨
        self._draw_direction_labels(painter, cx, cy, size / 2 - 6)

        # 포인터
        angle_rad = math.radians(-(self._angle - 90))
        needle_length = inner_r - 10
        x = cx + needle_length * math.cos(angle_rad)
        y = cy + needle_length * math.sin(angle_rad)

        direction_color = (
            QColor("#10b981")
            if self._direction in ("good", "up", "left", "right")
            else QColor("#ef4444")
        )
        pen = QPen(direction_color, 5, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx, cy), QPointF(x, y))

        # 중심 원
        painter.setBrush(QBrush(direction_color))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(QPointF(cx, cy), 8, 8)

        # 중앙 각도 텍스트
        painter.setPen(QPen(QColor("#111827")))
        painter.setFont(QFont("Helvetica Neue", 14, QFont.Bold))
        angle_text = f"{self._angle:.0f}°"
        painter.drawText(QRectF(0, cy + 16, w, 24), Qt.AlignCenter, angle_text)

        # 상태 표시
        status_color = QColor("#10b981") if self._success else QColor("#ef4444")
        status_text = "정상" if self._success else "오류"
        painter.setPen(QPen(status_color))
        painter.setFont(QFont("Helvetica Neue", 9, QFont.Bold))
        painter.drawText(QRectF(0, cy + 38, w, 18), Qt.AlignCenter, status_text)

        # 카운터 (좌상/우상)
        painter.setFont(QFont("Helvetica Neue", 9))
        painter.setPen(QPen(QColor("#10b981")))
        painter.drawText(QRectF(6, 6, 80, 16), Qt.AlignLeft, f"양품 {self._count_good}")
        painter.setPen(QPen(QColor("#ef4444")))
        painter.drawText(QRectF(w - 86, 6, 80, 16), Qt.AlignRight, f"불량 {self._count_bad}")

        painter.end()

    @staticmethod
    def _draw_direction_labels(painter: QPainter, cx: float, cy: float, r: float) -> None:
        painter.setPen(QPen(QColor("#6b7280")))
        painter.setFont(QFont("Helvetica Neue", 9))
        # N = 90 (양품 통과)
        painter.drawText(QRectF(cx - 22, cy - r + 4, 44, 14), Qt.AlignCenter, "양품")
        # S = 270 (불량 폐기)
        painter.drawText(QRectF(cx - 22, cy + r - 18, 44, 14), Qt.AlignCenter, "불량")
        # W = 180
        painter.drawText(QRectF(cx - r + 2, cy - 7, 30, 14), Qt.AlignLeft, "좌")
        # E = 0
        painter.drawText(QRectF(cx + r - 32, cy - 7, 30, 14), Qt.AlignRight, "우")


class SorterCard(QFrame):
    """SorterDial + 제목 + 설명을 감싼 카드."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tableCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        title = QLabel("분류 장치 상태")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.dial = SorterDial()
        layout.addWidget(self.dial, stretch=1)

        self._desc = QLabel("현재 방향: -")
        self._desc.setProperty("tone", "muted")
        self._desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._desc)

    def set_state(self, **kwargs) -> None:
        self.dial.set_state(**kwargs)
        direction = kwargs.get("direction", "")
        success = kwargs.get("success", True)
        text = f"현재 방향: {direction or '-'}"
        if success is not None:
            text += f" · {'정상' if success else '오류'}"
        self._desc.setText(text)


__all__ = ["SorterDial", "SorterCard"]
