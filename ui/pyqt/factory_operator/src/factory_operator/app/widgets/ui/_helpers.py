"""공용 헬퍼 — variant/size property 변경 시 QSS 재적용 강제."""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget


def set_property(widget: QWidget, name: str, value: object) -> None:
    """setProperty + style().polish() 한 쌍 — Qt 의 QSS 재계산 트리거."""
    widget.setProperty(name, value)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()
