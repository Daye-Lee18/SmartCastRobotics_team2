"""AMR 상태 카드 위젯 — 디자인 시스템 v2 (2026-04-26).

색상은 모두 글로벌 QSS 가 결정한다.
- task_state(0~10) 는 그룹화된 severity ('idle'/'moving'/'loading'/'done'/'failed') 로 매핑
- 배지/버튼/배터리 모두 setProperty 기반
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.widgets.ui._helpers import set_property

# task_state enum (proto AmrTaskState) → (severity, label)
TASK_STATE_LABEL: dict[int, tuple[str, str]] = {
    0: ("idle", "-"),
    1: ("idle", "대기"),
    2: ("moving", "출발지 이동"),
    3: ("waiting", "출발지 도착"),
    4: ("loading", "상차"),
    5: ("loading", "상차 완료"),
    6: ("moving", "도착지 이동"),
    7: ("waiting", "도착지 도착"),
    8: ("loading", "하차중"),
    9: ("done", "하차 완료"),
    10: ("failed", "실패"),
}

# fallback: connectivity status (online/offline 용)
STATUS_LABEL = {
    "running": ("moving", "이송 중"),
    "idle": ("idle", "대기"),
    "charging": ("loading", "충전 중"),
    "error": ("failed", "오류"),
}


def _status_key(s: str) -> str:
    s = (s or "").lower()
    if s in ("running", "active", "busy", "moving"):
        return "running"
    if s == "charging":
        return "charging"
    if s in ("error", "fault", "alarm"):
        return "error"
    return "idle"


def _battery_level_key(level: int) -> str:
    if level >= 60:
        return "high"
    if level >= 30:
        return "mid"
    return "low"


class AmrStatusCard(QFrame):
    """AMR 한 대의 상태 카드."""

    def __init__(self, amr_id: str = "-") -> None:
        super().__init__()
        self.setObjectName("amrCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(210)
        self._amr_id = amr_id
        self._current_task_state = 1  # IDLE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # 상단: ID + 상태 배지
        header = QHBoxLayout()
        header.setSpacing(8)

        self._id_label = QLabel(amr_id)
        self._id_label.setObjectName("amrIdLabel")
        header.addWidget(self._id_label)

        header.addStretch()

        self._status_badge = QLabel("-")
        self._status_badge.setObjectName("amrStatusBadge")
        self._status_badge.setProperty("severity", "idle")
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setFixedHeight(22)
        self._status_badge.setContentsMargins(10, 0, 10, 0)
        header.addWidget(self._status_badge)

        layout.addLayout(header)

        # 배터리
        bat_row = QHBoxLayout()
        bat_row.setSpacing(8)
        bat_label = QLabel("배터리")
        bat_label.setProperty("tone", "muted")
        bat_label.setFixedWidth(46)
        bat_row.addWidget(bat_label)

        self._battery_bar = QProgressBar()
        self._battery_bar.setObjectName("batteryBar")
        self._battery_bar.setProperty("level", "high")
        self._battery_bar.setRange(0, 100)
        self._battery_bar.setValue(0)
        self._battery_bar.setTextVisible(True)
        self._battery_bar.setFormat("%p%")
        self._battery_bar.setFixedHeight(18)
        bat_row.addWidget(self._battery_bar, stretch=1)

        layout.addLayout(bat_row)

        # 정보 그리드 (속도 / 위치)
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self._speed_label = self._info_label("속도", "0.0 m/s")
        info_row.addWidget(self._speed_label, stretch=1)

        self._loc_label = self._info_label("위치", "-")
        info_row.addWidget(self._loc_label, stretch=2)

        layout.addLayout(info_row)

        # 현재 작업
        self._task_label = QLabel("현재 작업: -")
        self._task_label.setProperty("tone", "muted")
        self._task_label.setWordWrap(True)
        layout.addWidget(self._task_label)

        self.update_from_dict({"id": amr_id})

    def _info_label(self, title: str, value: str) -> QWidget:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        t = QLabel(title)
        t.setObjectName("amrInfoTitle")
        t.setProperty("tone", "muted")
        v.addWidget(t)

        val = QLabel(value)
        val.setObjectName("amrInfoValue")
        v.addWidget(val)

        return box

    def update_from_dict(self, data: dict[str, Any]) -> None:
        amr_id = str(data.get("id", "-"))
        self._amr_id = amr_id
        self._id_label.setText(amr_id)

        # 상태 배지
        task_state = data.get("task_state", 0)
        if isinstance(task_state, int) and task_state in TASK_STATE_LABEL:
            self._current_task_state = task_state
            severity, label = TASK_STATE_LABEL[task_state]
        else:
            status = _status_key(str(data.get("status", "idle")))
            severity, label = STATUS_LABEL.get(status, ("idle", "대기"))
            self._current_task_state = 1
        self._status_badge.setText(label)
        set_property(self._status_badge, "severity", severity)

        # 배터리
        try:
            battery = int(data.get("battery", 0) or 0)
        except (TypeError, ValueError):
            battery = 0
        self._battery_bar.setValue(battery)
        set_property(self._battery_bar, "level", _battery_level_key(battery))

        # 속도
        speed = data.get("speed", 0)
        try:
            speed_text = f"{float(speed):.1f} m/s"
        except (TypeError, ValueError):
            speed_text = "-"
        self._info_value(self._speed_label, speed_text)

        # 위치
        location = str(data.get("location", data.get("install_location", "-"))) or "-"
        self._info_value(self._loc_label, location)

        # 현재 작업
        task = data.get("current_task") or data.get("task_id") or "-"
        cargo = data.get("cargo") or data.get("loaded_item") or ""
        task_text = f"현재 작업: {task}"
        if cargo:
            task_text += f" ({cargo})"
        self._task_label.setText(task_text)

    @staticmethod
    def _info_value(container: QWidget, text: str) -> None:
        value = container.findChild(QLabel, "amrInfoValue")
        if value:
            value.setText(text)


__all__ = ["AmrStatusCard", "STATUS_LABEL", "TASK_STATE_LABEL"]
