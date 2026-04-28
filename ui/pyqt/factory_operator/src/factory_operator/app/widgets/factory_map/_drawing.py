"""factory_map 위젯 — Scene 그리기 헬퍼.

`_add_label`, `_add_box`, `_add_cobot`, `_add_worker`, `_add_zone` —
FactoryMapScene 의 5구역 _draw_*_zone 메서드들이 사용.

2026-04-27: factory_map.py (1069 LOC) 분할 산출.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPen
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from ._constants import (
    EQUIP_BG,
    LABEL_BG,
    LABEL_TEXT,
    WORKER_COLOR,
    ZONE_BG,
    ZONE_BORDER,
)


def _add_label(
    scene: QGraphicsScene, x: float, y: float, text: str, font_size: int = 9, bg: str = LABEL_BG
) -> None:
    """노란 라벨 (테두리 + 텍스트)."""
    font = QFont("Sans", font_size, QFont.Bold)
    txt = QGraphicsSimpleTextItem(text)
    txt.setFont(font)
    txt.setBrush(QBrush(QColor(LABEL_TEXT)))
    tr = txt.boundingRect()
    pad_x, pad_y = 6, 3
    rect = QGraphicsRectItem(x, y, tr.width() + pad_x * 2, tr.height() + pad_y * 2)
    rect.setBrush(QBrush(QColor(bg)))
    rect.setPen(QPen(QColor("#333333"), 1))
    rect.setZValue(10)
    scene.addItem(rect)
    txt.setPos(x + pad_x, y + pad_y)
    txt.setZValue(11)
    scene.addItem(txt)


def _add_box(
    scene: QGraphicsScene,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    font_size: int = 9,
    bg: str = EQUIP_BG,
    border: str = "#333333",
) -> QGraphicsRectItem:
    """흰색 박스 + 텍스트."""
    rect = QGraphicsRectItem(x, y, w, h)
    rect.setBrush(QBrush(QColor(bg)))
    rect.setPen(QPen(QColor(border), 1))
    rect.setZValue(10)
    scene.addItem(rect)
    if text:
        font = QFont("Sans", font_size)
        txt = QGraphicsSimpleTextItem(text)
        txt.setFont(font)
        txt.setBrush(QBrush(QColor("#000000")))
        tr = txt.boundingRect()
        txt.setPos(x + (w - tr.width()) / 2, y + (h - tr.height()) / 2)
        txt.setZValue(11)
        scene.addItem(txt)
    return rect


def _add_cobot(scene: QGraphicsScene, cx: float, cy: float, r: float, label: str) -> None:
    """원형 Cobot (흰색 원 + 라벨)."""
    ellipse = QGraphicsEllipseItem(cx - r, cy - r, r * 2, r * 2)
    ellipse.setBrush(QBrush(QColor(EQUIP_BG)))
    ellipse.setPen(QPen(QColor("#333333"), 2))
    ellipse.setZValue(10)
    scene.addItem(ellipse)
    font = QFont("Sans", 18, QFont.Bold)
    txt = QGraphicsSimpleTextItem(label)
    txt.setFont(font)
    txt.setBrush(QBrush(QColor("#000000")))
    tr = txt.boundingRect()
    txt.setPos(cx - tr.width() / 2, cy - tr.height() / 2)
    txt.setZValue(11)
    scene.addItem(txt)


def _add_worker(scene: QGraphicsScene, cx: float, base_y: float, label: str) -> None:
    """스틱맨 작업자."""
    pen = QPen(QColor(WORKER_COLOR), 2)
    head_r = 8
    # head
    head = QGraphicsEllipseItem(cx - head_r, base_y, head_r * 2, head_r * 2)
    head.setPen(pen)
    head.setBrush(QBrush(QColor("#ffffff")))
    head.setZValue(12)
    scene.addItem(head)
    # body
    body = scene.addLine(cx, base_y + head_r * 2, cx, base_y + head_r * 2 + 25, pen)
    body.setZValue(12)
    # arms
    arms = scene.addLine(cx - 12, base_y + head_r * 2 + 10, cx + 12, base_y + head_r * 2 + 10, pen)
    arms.setZValue(12)
    # legs
    scene.addLine(cx, base_y + head_r * 2 + 25, cx - 10, base_y + head_r * 2 + 40, pen).setZValue(
        12
    )
    scene.addLine(cx, base_y + head_r * 2 + 25, cx + 10, base_y + head_r * 2 + 40, pen).setZValue(
        12
    )
    # label
    font = QFont("Sans", 7)
    txt = QGraphicsSimpleTextItem(label)
    txt.setFont(font)
    txt.setBrush(QBrush(QColor("#000000")))
    tr = txt.boundingRect()
    txt.setPos(cx - tr.width() / 2, base_y + head_r * 2 + 44)
    txt.setZValue(12)
    scene.addItem(txt)


def _add_zone(scene: QGraphicsScene, x: float, y: float, w: float, h: float, title: str) -> None:
    """구역 (파선 테두리 + 반투명 배경 + 제목 라벨)."""
    rect = QGraphicsRectItem(x, y, w, h)
    rect.setBrush(QBrush(ZONE_BG))
    pen = QPen(ZONE_BORDER, 2, Qt.DashLine)
    rect.setPen(pen)
    rect.setZValue(1)
    scene.addItem(rect)
    # 제목 라벨 (상단 중앙)
    font = QFont("Sans", 10)
    txt = QGraphicsSimpleTextItem(title)
    txt.setFont(font)
    txt.setBrush(QBrush(QColor("#000000")))
    tr = txt.boundingRect()
    # 흰색 배경 + 테두리
    pad = 4
    lbl_rect = QGraphicsRectItem(
        x + (w - tr.width()) / 2 - pad,
        y - tr.height() / 2 - pad / 2,
        tr.width() + pad * 2,
        tr.height() + pad,
    )
    lbl_rect.setBrush(QBrush(QColor("#ffffff")))
    lbl_rect.setPen(QPen(QColor("#333333"), 1))
    lbl_rect.setZValue(2)
    scene.addItem(lbl_rect)
    txt.setPos(x + (w - tr.width()) / 2, y - tr.height() / 2 - pad / 2 + 1)
    txt.setZValue(3)
    scene.addItem(txt)
