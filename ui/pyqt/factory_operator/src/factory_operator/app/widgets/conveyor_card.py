"""컨베이어 상태 카드 — 디자인 시스템 v2 (2026-04-26).

토픽 conveyor/<id>/status 의 JSON 페이로드를 시각화한다.
색상은 모두 글로벌 QSS 가 결정 — setProperty 기반.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from app.widgets.ui._helpers import set_property

# state → (severity, label) 매핑 (색은 QSS)
STATE_LABEL: dict[str, tuple[str, str]] = {
    "idle": ("idle", "대기"),
    "running": ("ok", "이송 중"),
    "stopped": ("warn", "검사 대기"),
    "post_run": ("info", "후처리"),
    "clearing": ("defect", "배출 중"),
    "error": ("danger", "오류"),
    "offline": ("offline", "오프라인"),
}


def _sensor_status(mm: int, detected: bool) -> str:
    if detected:
        return "online"
    if mm and mm > 0 and mm < 200:
        return "warn"
    return "offline"


class ConveyorCard(QFrame):
    """컨베이어 상태 카드 한 대."""

    def __init__(self, conveyor_id: str) -> None:
        super().__init__()
        self.setObjectName("tableCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(180)

        self._conveyor_id = conveyor_id
        self._online = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # 상단: ID + 상태 배지
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel(f"Conveyor #{conveyor_id}")
        title.setObjectName("convCardTitle")
        header.addWidget(title)
        header.addStretch()

        self._connection_dot = QLabel("●")
        self._connection_dot.setObjectName("statusDot")
        self._connection_dot.setProperty("status", "offline")
        header.addWidget(self._connection_dot)

        self._state_badge = QLabel("offline")
        self._state_badge.setObjectName("convStateBadge")
        self._state_badge.setProperty("severity", "offline")
        self._state_badge.setAlignment(Qt.AlignCenter)
        self._state_badge.setFixedHeight(22)
        header.addWidget(self._state_badge)

        root.addLayout(header)

        # 중단: 모터 + 카운트 (gridy)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(2)

        motor_lbl = QLabel("모터")
        motor_lbl.setObjectName("convMetricLabel")
        self._motor_val = QLabel("-")
        self._motor_val.setObjectName("convMetricValue")
        self._motor_val.setProperty("state", "off")
        grid.addWidget(motor_lbl, 0, 0)
        grid.addWidget(self._motor_val, 1, 0)

        count_lbl = QLabel("사이클")
        count_lbl.setObjectName("convMetricLabel")
        self._count_val = QLabel("0")
        self._count_val.setObjectName("convMetricValue")
        grid.addWidget(count_lbl, 0, 1)
        grid.addWidget(self._count_val, 1, 1)

        speed_lbl = QLabel("속도")
        speed_lbl.setObjectName("convMetricLabel")
        self._speed_val = QLabel("-")
        self._speed_val.setObjectName("convMetricValue")
        grid.addWidget(speed_lbl, 0, 2)
        grid.addWidget(self._speed_val, 1, 2)

        root.addLayout(grid)

        # 하단: TOF 센서 2개
        tof_row = QHBoxLayout()
        tof_row.setSpacing(14)

        self._tof1_label, self._tof1_value, self._tof1_dot = self._make_tof_row("TOF1 (입구)")
        tof_row.addLayout(self._tof1_label)

        self._tof2_label, self._tof2_value, self._tof2_dot = self._make_tof_row("TOF2 (출구)")
        tof_row.addLayout(self._tof2_label)

        root.addLayout(tof_row)
        root.addStretch()

        self._apply_state("offline")

    def _make_tof_row(self, name: str):
        layout = QVBoxLayout()
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(4)

        dot = QLabel("●")
        dot.setObjectName("statusDot")
        dot.setProperty("status", "offline")
        header.addWidget(dot)

        lbl = QLabel(name)
        lbl.setObjectName("convMetricLabel")
        header.addWidget(lbl)
        header.addStretch()

        layout.addLayout(header)

        value = QLabel("-")
        value.setObjectName("convTofValue")
        layout.addWidget(value)

        return layout, value, dot

    def _apply_state(self, state: str) -> None:
        severity, label = STATE_LABEL.get(state, STATE_LABEL["offline"])
        self._state_badge.setText(label)
        set_property(self._state_badge, "severity", severity)

    def set_online(self, online: bool) -> None:
        self._online = online
        set_property(self._connection_dot, "status", "online" if online else "offline")

    def update_from_payload(self, payload: dict[str, Any]) -> None:
        state = str(payload.get("state", "offline"))
        self._apply_state(state)

        # 모터
        motor = payload.get("motor")
        if isinstance(motor, dict):
            running = bool(motor.get("running"))
            speed = motor.get("speed", motor.get("spd", 0))
            direction = motor.get("dir", "")
        else:
            running = bool(motor)
            speed = payload.get("speed", 0)
            direction = ""

        self._motor_val.setText("ON" if running else "OFF")
        set_property(self._motor_val, "state", "on" if running else "off")
        speed_text = f"{speed}"
        if direction:
            speed_text += f" ({direction})"
        self._speed_val.setText(speed_text)

        # 카운트
        count = payload.get("count", 0)
        self._count_val.setText(str(count))

        # TOF1, TOF2
        self._update_tof(self._tof1_value, self._tof1_dot, payload.get("tof1", {}))
        self._update_tof(self._tof2_value, self._tof2_dot, payload.get("tof2", {}))

    @staticmethod
    def _update_tof(value_label: QLabel, dot_label: QLabel, tof: dict[str, Any]) -> None:
        mm = tof.get("mm", -1)
        det = bool(tof.get("det", False))
        try:
            mm_int = int(mm)
        except (TypeError, ValueError):
            mm_int = -1

        if mm_int < 0:
            value_label.setText("-- mm")
            set_property(dot_label, "status", "offline")
            return

        value_label.setText(f"{mm_int} mm" + (" · 감지" if det else ""))
        set_property(dot_label, "status", _sensor_status(mm_int, det))

    def mark_offline(self) -> None:
        self._apply_state("offline")
        self.set_online(False)
        self._motor_val.setText("-")
        set_property(self._motor_val, "state", "off")
        self._count_val.setText("0")
        self._speed_val.setText("-")


__all__ = ["ConveyorCard"]
