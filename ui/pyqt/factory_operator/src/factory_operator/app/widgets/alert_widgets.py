"""알림 관련 위젯 (v0.9 — 디자인 시스템 v2 마이그레이션 2026-04-26).

1. AlertListItem - severity 기반 색상 (글로벌 QSS 가 처리)
2. ToastNotification - critical 알람 토스트 팝업 (5초 자동 사라짐)

스타일은 모두 setProperty("severity", level) + objectName 으로 위임.
색은 builder.py 의 _alerts_widget() 섹션이 결정.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# severity → 표시 라벨 + 아이콘 (색은 글로벌 QSS 가 결정)
LEVEL_STYLE = {
    "critical": {"icon": "●", "label": "긴급"},
    "error": {"icon": "●", "label": "오류"},
    "warning": {"icon": "▲", "label": "경고"},
    "info": {"icon": "ℹ", "label": "정보"},
    "success": {"icon": "✓", "label": "완료"},
}


def _normalize_level(raw: str) -> str:
    s = (raw or "").lower()
    if s in ("critical", "fatal"):
        return "critical"
    if s in ("error", "danger"):
        return "error"
    if s in ("warn", "warning"):
        return "warning"
    if s in ("success", "ok"):
        return "success"
    return "info"


class AlertListItem(QFrame):
    """개별 알림 항목 - severity 기반 좌측 보더 + 배경 + 아이콘."""

    def __init__(self, alert: dict[str, Any]) -> None:
        super().__init__()
        self.setObjectName("alertItem")
        level = _normalize_level(str(alert.get("level", "info")))
        meta = LEVEL_STYLE[level]
        self.setProperty("severity", level)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(10)

        icon = QLabel(meta["icon"])
        icon.setObjectName("alertIcon")
        icon.setProperty("severity", level)
        icon.setFixedWidth(18)
        layout.addWidget(icon)

        # 본문 (레벨 라벨 + 메시지)
        body = QVBoxLayout()
        body.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(6)
        level_badge = QLabel(meta["label"])
        level_badge.setObjectName("alertLevelBadge")
        level_badge.setProperty("severity", level)
        top.addWidget(level_badge)

        source = alert.get("source", "")
        if source:
            src_label = QLabel(f"· {source}")
            src_label.setProperty("tone", "muted")
            top.addWidget(src_label)
        top.addStretch()

        ts = alert.get("created_at", "")
        if ts:
            ts_label = QLabel(str(ts))
            ts_label.setProperty("tone", "muted")
            top.addWidget(ts_label)
        body.addLayout(top)

        msg = QLabel(str(alert.get("message", "")))
        msg.setObjectName("alertMessage")
        msg.setWordWrap(True)
        body.addWidget(msg)

        layout.addLayout(body, stretch=1)


class ToastNotification(QWidget):
    """우상단에 뜨는 알람 토스트 (5초 자동 fadeout)."""

    FADE_IN_MS = 250
    DISPLAY_MS = 5000
    FADE_OUT_MS = 400

    def __init__(self, parent: QWidget, level: str, title: str, message: str) -> None:
        super().__init__(parent)
        level_key = _normalize_level(level)
        meta = LEVEL_STYLE[level_key]

        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QFrame(self)
        container.setObjectName("toastContainer")
        container.setProperty("severity", level_key)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 12, 18, 12)
        layout.setSpacing(12)

        icon = QLabel(meta["icon"])
        icon.setObjectName("toastIcon")
        icon.setProperty("severity", level_key)
        icon.setFixedWidth(26)
        layout.addWidget(icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)

        title_label = QLabel(f"{meta['label']} · {title}")
        title_label.setObjectName("toastTitle")
        title_label.setProperty("severity", level_key)
        text_box.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("toastMessage")
        msg_label.setWordWrap(True)
        msg_label.setMinimumWidth(260)
        msg_label.setMaximumWidth(340)
        text_box.addWidget(msg_label)

        layout.addLayout(text_box, stretch=1)

        self.adjustSize()
        self._position_top_right()

        # 페이드인
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in.setDuration(self.FADE_IN_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

        QTimer.singleShot(self.DISPLAY_MS, self._start_fade_out)

    def _position_top_right(self) -> None:
        parent = self.parent()
        if parent is None:
            return
        parent_geom = parent.geometry()
        x = parent_geom.width() - self.width() - 20
        y = 70
        self.move(x, y)

    def _start_fade_out(self) -> None:
        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out.setDuration(self.FADE_OUT_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.deleteLater)
        self._fade_out.start()


__all__ = [
    "AlertListItem",
    "ToastNotification",
    "LEVEL_STYLE",
    "_normalize_level",
]
