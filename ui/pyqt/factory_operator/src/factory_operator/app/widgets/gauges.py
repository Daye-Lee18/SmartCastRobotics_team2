"""제어 / 게이지 위젯 (v0.3).

커스텀 QWidget.paintEvent 로 구현:
  1. CircularProgress  - 원형 프로그레스 (냉각 진행률)
  2. ArcGauge          - 반원 아크 게이지 (압력, 주탕 각도 등)
  3. ToggleSwitch      - Auto/Manual 슬라이드 토글
  4. EmergencyStopButton - 큰 빨간 비상 정지 버튼
  5. StatusPill        - 간단한 상태 배지
"""

from __future__ import annotations

from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QRadialGradient,
)
from PyQt5.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

# 공통 팔레트
PRIMARY = "#3b82f6"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#ef4444"
GRAY = "#9ca3af"
DARK = "#111827"
LIGHT = "#f3f4f6"
TRACK = "#e5e7eb"


# ==========================================================
# 1. Circular Progress (냉각 진행률)
# ==========================================================
class CircularProgress(QWidget):
    """원형 프로그레스 - 0~100%.

    중앙에 큰 숫자 + 단위 + 부제목.
    """

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        unit: str = "%",
        color: str = PRIMARY,
    ) -> None:
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self._unit = unit
        self._color = QColor(color)
        self._value: float = 0.0
        self._max: float = 100.0
        self.setMinimumSize(180, 180)

    def set_value(self, value: float, maximum: float | None = None) -> None:
        self._value = max(0.0, float(value))
        if maximum is not None:
            self._max = float(maximum)
        self.update()

    def set_subtitle(self, text: str) -> None:
        self._subtitle = text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 20
        cx = (w - size) / 2
        cy = (h - size) / 2 - 6
        rect = QRectF(cx, cy, size, size)

        # 배경 트랙
        track_pen = QPen(QColor(TRACK), 12, Qt.SolidLine, Qt.FlatCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 90 * 16, -360 * 16)

        # 진행 아크
        ratio = min(1.0, max(0.0, self._value / max(self._max, 1e-6)))
        arc_pen = QPen(self._color, 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, 90 * 16, int(-360 * 16 * ratio))

        # 중앙 제목
        if self._title:
            painter.setPen(QPen(QColor(GRAY)))
            painter.setFont(QFont("Helvetica Neue", 10))
            title_rect = QRectF(0, cy + size * 0.18, w, 18)
            painter.drawText(title_rect, Qt.AlignCenter, self._title)

        # 중앙 값
        painter.setPen(QPen(QColor(DARK)))
        painter.setFont(QFont("Helvetica Neue", 26, QFont.Bold))
        val_rect = QRectF(0, cy + size * 0.35, w, size * 0.25)
        painter.drawText(val_rect, Qt.AlignCenter, f"{self._value:.0f}{self._unit}")

        # 부제목
        if self._subtitle:
            painter.setPen(QPen(QColor(GRAY)))
            painter.setFont(QFont("Helvetica Neue", 9))
            sub_rect = QRectF(0, cy + size * 0.62, w, 18)
            painter.drawText(sub_rect, Qt.AlignCenter, self._subtitle)

        painter.end()


# ==========================================================
# 2. Arc Gauge (반원 아크)
# ==========================================================
class ArcGauge(QWidget):
    """반원 아크 게이지 - 압력 / 각도 / 온도 등."""

    def __init__(
        self,
        title: str = "",
        unit: str = "",
        minimum: float = 0.0,
        maximum: float = 100.0,
        warn_ratio: float = 0.7,
        danger_ratio: float = 0.9,
    ) -> None:
        super().__init__()
        self._title = title
        self._unit = unit
        self._min = minimum
        self._max = maximum
        self._warn_ratio = warn_ratio
        self._danger_ratio = danger_ratio
        self._value: float = minimum
        self.setMinimumSize(200, 160)

    def set_value(self, value: float) -> None:
        self._value = max(self._min, min(self._max, float(value)))
        self.update()

    def _value_color(self) -> QColor:
        span = self._max - self._min
        ratio = (self._value - self._min) / max(span, 1e-6)
        if ratio >= self._danger_ratio:
            return QColor(DANGER)
        if ratio >= self._warn_ratio:
            return QColor(WARNING)
        return QColor(SUCCESS)

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        pen_w = 14
        half_pen = pen_w / 2  # 7px — 아크 stroke가 rect 밖으로 넘치는 양

        # 영역 배분: 제목(28px) | pen여백(7px) | 반원 | pen여백(7px) | 라벨(20px)
        title_h = 28
        bottom_label_h = 20
        arc_avail = h - title_h - bottom_label_h - pen_w  # pen 상/하 overshoot 포함
        size = min(w - 20, arc_avail * 2)
        size = max(size, 40)

        cx = (w - size) / 2
        cy = title_h + half_pen  # 제목 아래 + pen 상단 여유
        center_y = cy + size / 2  # 반원 중심선 (수평 직선 위치)
        rect = QRectF(cx, cy, size, size)

        # 제목 (상단)
        if self._title:
            painter.setPen(QPen(QColor(GRAY)))
            painter.setFont(QFont("Helvetica Neue", 10))
            painter.drawText(QRectF(0, 2, w, title_h), Qt.AlignCenter, self._title)

        # 배경 아크 (180도)
        bg_pen = QPen(QColor(TRACK), pen_w, Qt.SolidLine, Qt.FlatCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 180 * 16, -180 * 16)

        # 값 아크
        ratio = (self._value - self._min) / max(self._max - self._min, 1e-6)
        ratio = max(0.0, min(1.0, ratio))
        arc_pen = QPen(self._value_color(), pen_w, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, 180 * 16, int(-180 * 16 * ratio))

        # 값 (반원 하단 근처)
        painter.setPen(QPen(QColor(DARK)))
        painter.setFont(QFont("Helvetica Neue", 22, QFont.Bold))
        painter.drawText(
            QRectF(0, center_y - 30, w, 32),
            Qt.AlignCenter,
            f"{self._value:.0f}",
        )

        # 최소/최대 + 단위 라벨 (반원 중심선 아래)
        label_y = center_y + half_pen + 2
        painter.setPen(QPen(QColor(GRAY)))
        painter.setFont(QFont("Helvetica Neue", 8))
        painter.drawText(
            QRectF(cx - 5, label_y, size / 2, 16),
            Qt.AlignLeft,
            f"{self._min:.0f}",
        )
        painter.drawText(
            QRectF(cx + size / 2, label_y, size / 2 + 5, 16),
            Qt.AlignRight,
            f"{self._max:.0f}",
        )

        if self._unit:
            painter.setFont(QFont("Helvetica Neue", 10))
            painter.drawText(QRectF(0, label_y, w, 16), Qt.AlignCenter, self._unit)

        painter.end()


# ==========================================================
# 3. Toggle Switch (Auto / Manual)
# ==========================================================
class ToggleSwitch(QAbstractButton):
    """슬라이드 토글 스위치 - 체크 상태에 따라 색상 변경."""

    toggled_changed = pyqtSignal(bool)

    def __init__(
        self,
        label_on: str = "ON",
        label_off: str = "OFF",
        color_on: str = SUCCESS,
        color_off: str = GRAY,
    ) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._label_on = label_on
        self._label_off = label_off
        self._color_on = QColor(color_on)
        self._color_off = QColor(color_off)
        self._thumb_pos = 2.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._on_toggled)
        self.setFixedSize(84, 32)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(84, 32)

    def _on_toggled(self, checked: bool) -> None:
        end = self.width() - 28 if checked else 2
        self._anim.stop()
        self._anim.setEndValue(float(end))
        self._anim.start()
        self.toggled_changed.emit(checked)

    @pyqtProperty(float)
    def thumbPos(self) -> float:  # noqa: N802
        return self._thumb_pos

    @thumbPos.setter  # type: ignore[no-redef]
    def thumbPos(self, value: float) -> None:  # noqa: N802
        self._thumb_pos = value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 배경 둥근 사각형
        bg_color = self._color_on if self.isChecked() else self._color_off
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(self.rect(), 16, 16)

        # 라벨
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Helvetica Neue", 9, QFont.Bold))
        if self.isChecked():
            painter.drawText(QRectF(6, 0, 40, self.height()), Qt.AlignCenter, self._label_on)
        else:
            painter.drawText(
                QRectF(self.width() - 46, 0, 40, self.height()),
                Qt.AlignCenter,
                self._label_off,
            )

        # 슬라이더 (thumb)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(QRectF(self._thumb_pos, 2, 28, 28))
        painter.end()


# ==========================================================
# 4. Emergency Stop Button
# ==========================================================
class EmergencyStopButton(QAbstractButton):
    """큰 원형 빨간 비상정지 버튼."""

    pressed_stop = pyqtSignal()

    def __init__(self, text: str = "비상정지\nE-STOP") -> None:
        super().__init__()
        self._text = text
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(150, 150)
        self._pressed = False
        self.clicked.connect(self.pressed_stop.emit)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(150, 150)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h) - 8
        cx = (w - size) / 2
        cy = (h - size) / 2
        outer_rect = QRectF(cx, cy, size, size)

        # 외곽 링 (회색)
        painter.setBrush(QBrush(QColor("#374151")))
        painter.setPen(QPen(QColor("#111827"), 2))
        painter.drawEllipse(outer_rect)

        # 빨간 본체 (radial gradient)
        inner = 14 if self._pressed else 10
        inner_rect = QRectF(cx + inner, cy + inner, size - inner * 2, size - inner * 2)

        gradient = QRadialGradient(
            outer_rect.center().x() - size * 0.15,
            outer_rect.center().y() - size * 0.15,
            size * 0.7,
        )
        if self._pressed:
            gradient.setColorAt(0.0, QColor("#dc2626"))
            gradient.setColorAt(1.0, QColor("#7f1d1d"))
        else:
            gradient.setColorAt(0.0, QColor("#fca5a5"))
            gradient.setColorAt(0.5, QColor("#ef4444"))
            gradient.setColorAt(1.0, QColor("#991b1b"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#7f1d1d"), 2))
        painter.drawEllipse(inner_rect)

        # 텍스트
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Helvetica Neue", 13, QFont.Bold))
        painter.drawText(outer_rect, Qt.AlignCenter, self._text)

        painter.end()


# ==========================================================
# 5. Status Pill (작은 배지)
# ==========================================================
class StatusPill(QLabel):
    """작은 상태 배지."""

    def __init__(self, text: str = "", color: str = PRIMARY) -> None:
        super().__init__(text)
        self._color = color
        self.setAlignment(Qt.AlignCenter)
        self.setContentsMargins(10, 4, 10, 4)
        self._apply_style()

    def set_status(self, text: str, color: str) -> None:
        self._color = color
        self.setText(text)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color};"
            "color: #ffffff;"
            "border-radius: 10px;"
            "padding: 4px 10px;"
            "font-size: 11px;"
            "font-weight: bold;"
        )


# ==========================================================
# 6. Control Panel 조합 위젯
# ==========================================================
class ControlPanel(QFrame):
    """제어 패널: E-Stop + Auto/Manual + 설명."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("controlPanel")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("제어 패널")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # E-Stop
        self.e_stop = EmergencyStopButton()
        layout.addWidget(self.e_stop, alignment=Qt.AlignCenter)

        # Auto/Manual
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_label = QLabel("모드")
        mode_label.setProperty("tone", "muted")
        mode_row.addWidget(mode_label)
        mode_row.addStretch()

        self.mode_toggle = ToggleSwitch(label_on="AUTO", label_off="MANUAL")
        self.mode_toggle.setChecked(True)
        mode_row.addWidget(self.mode_toggle)
        layout.addLayout(mode_row)

        self.mode_desc = QLabel("자동 모드: 공정이 스케줄대로 자동 실행됩니다.")
        self.mode_desc.setProperty("tone", "muted")
        self.mode_desc.setWordWrap(True)
        layout.addWidget(self.mode_desc)

        self.mode_toggle.toggled_changed.connect(self._on_mode_changed)

        layout.addStretch()

    def _on_mode_changed(self, auto: bool) -> None:
        if auto:
            self.mode_desc.setText("자동 모드: 공정이 스케줄대로 자동 실행됩니다.")
        else:
            self.mode_desc.setText("수동 모드: 오퍼레이터가 직접 장비를 조작합니다.")


__all__ = [
    "CircularProgress",
    "ArcGauge",
    "ToggleSwitch",
    "EmergencyStopButton",
    "StatusPill",
    "ControlPanel",
]
