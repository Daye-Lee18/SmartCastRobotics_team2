"""factory_map 위젯 — Views (FactoryMapView, MiniFactoryMapView).

FactoryMapView: 메인 공장 맵 페이지 (드래그/줌/리사이즈, sim 활성 기본).
MiniFactoryMapView: 대시보드용 축소 맵 (sim 비활성, 인터랙션 없음).

2026-04-27: factory_map.py (1069 LOC) 분할 산출.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPainter
from PyQt5.QtWidgets import QGraphicsView

from ._constants import BG_COLOR
from .scene import FactoryMapScene


class FactoryMapView(QGraphicsView):
    """공장 맵 뷰 — 드래그/줌/리사이즈."""

    def __init__(self, enable_sim: bool = True) -> None:
        super().__init__()
        self._scene = FactoryMapScene(enable_sim=enable_sim)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(BG_COLOR)))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def fit(self) -> None:
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.fit()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.fit()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def update_equipment(self, equipment: list[dict[str, Any]]) -> None:
        self._scene.update_equipment(equipment)


class MiniFactoryMapView(FactoryMapView):
    """대시보드용 축소 맵.

    2026-04-27: enable_sim=False 기본값. mini map 은 대시보드 + map 페이지가
    동시에 표시될 수 있어 _SimController 두 개가 background tick → CPU 누적.
    """

    def __init__(self) -> None:
        super().__init__(enable_sim=False)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setInteractive(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(300)
        self.setMaximumHeight(600)

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()
