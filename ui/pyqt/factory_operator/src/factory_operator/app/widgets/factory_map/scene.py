"""factory_map 위젯 — FactoryMapScene (5구역 그리기 + AMR 마커 보간 애니메이션).

5구역: Postprocessing, Outbound, Storage, Charging, Casting.
update_equipment(amrs) → AMR 마커 위치/색상 갱신 + _tick_animation 가 100ms 마다 보간.
enable_sim=True 면 _SimController 시작 (메인 맵에서만 활성).

2026-04-27: factory_map.py (1069 LOC) 분할 산출.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from ._constants import (
    BG_COLOR,
    CHARGING_BG,
    CONVEYOR_COLOR,
    MOLD_COLOR,
    OUTBOUND_GRAD_BOT,
    OUTBOUND_GRAD_TOP,
    RED_BLOCK,
    SCENE_H,
    SCENE_W,
    STATUS_COLORS,
    _status_key,
)
from ._drawing import _add_box, _add_cobot, _add_label, _add_worker, _add_zone
from .sim import _SimController


class FactoryMapScene(QGraphicsScene):
    """공장 레이아웃 씬 — 이미지 기반 5구역 배치."""

    # 2026-04-27 성능 패치: 30ms(33fps) → 100ms(10fps). AMR 마커 보간 애니메이션은
    # 사람 눈에 60fps 가 필요 없고, 두 개의 mini map + 메인 맵이 동시에 돌면
    # CPU 4 ~ 8% 상시 점유 → GUI 전체 레이턴시 증가. 10fps 로 충분히 부드러움.
    ANIMATION_INTERVAL_MS = 100
    ANIMATION_STEP = 0.12

    def __init__(self, enable_sim: bool = True) -> None:
        super().__init__()
        self.setBackgroundBrush(QBrush(QColor(BG_COLOR)))
        self.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self._amr_state: dict[str, dict[str, Any]] = {}

        self._draw_all()

        self._anim_timer = QTimer()
        self._anim_timer.setInterval(self.ANIMATION_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._tick_animation)
        self._anim_timer.start()

        # 시뮬레이션은 메인 맵에서만 — mini map 은 enable_sim=False 로 비활성화.
        # _SimController 는 200ms 주기로 FSM tick + 다수의 그래픽 아이템 업데이트 →
        # mini map 두 개 (대시보드 + map page background) 가 동시에 돌면 부하 누적.
        self._sim: _SimController | None = None
        if enable_sim:
            self._sim = _SimController(self)
            self._sim.start()

    # ------------------------------------------------------------------
    # 전체 그리기
    # ------------------------------------------------------------------
    def _draw_all(self) -> None:
        # 전체 외곽선
        outer = QGraphicsRectItem(5, 5, SCENE_W - 10, SCENE_H - 10)
        outer.setPen(QPen(QColor("#333333"), 2))
        outer.setBrush(QBrush(Qt.NoBrush))
        outer.setZValue(0)
        self.addItem(outer)

        self._draw_postprocessing_zone()
        self._draw_outbound_zone()
        self._draw_storage_zone()
        self._draw_charging_zone()
        self._draw_casting_zone()

    # ------------------------------------------------------------------
    # 1) Postprocessing zone (좌상단)
    # ------------------------------------------------------------------
    def _draw_postprocessing_zone(self) -> None:
        zx, zy, zw, zh = 20, 25, 680, 210
        _add_zone(self, zx, zy, zw, zh, "Postprocessing zone")

        # Worker 구역 (회색 박스)
        wx, wy, ww, wh = 40, 65, 160, 150
        worker_box = QGraphicsRectItem(wx, wy, ww, wh)
        worker_box.setBrush(QBrush(QColor("#c8c8c8")))
        worker_box.setPen(QPen(QColor("#999999"), 1))
        worker_box.setZValue(5)
        self.addItem(worker_box)

        _add_worker(self, 90, 75, "Unloading\nWorker")
        _add_worker(self, 160, 75, "Postprocessing\nWorker")

        # 컨베이어 (초록 직사각형)
        conv = QGraphicsRectItem(220, 95, 280, 45)
        conv.setBrush(QBrush(QColor(CONVEYOR_COLOR)))
        conv.setPen(QPen(QColor("#1a6b1a"), 2))
        conv.setZValue(10)
        self.addItem(conv)

        # Conveyor Waiting Zone 라벨
        _add_label(self, 520, 85, "Conveyor\nWaiting\nZone")

    # ------------------------------------------------------------------
    # 2) Outbound zone (우상단)
    # ------------------------------------------------------------------
    def _draw_outbound_zone(self) -> None:
        zx, zy, zw, zh = 1050, 25, 230, 190
        _add_zone(self, zx, zy, zw, zh, "Outbound zone")

        # 은색 그라데이션 사각형
        grad_rect = QGraphicsRectItem(1070, 55, 190, 140)
        gradient = QLinearGradient(1070, 55, 1260, 195)
        gradient.setColorAt(0, QColor(OUTBOUND_GRAD_TOP))
        gradient.setColorAt(1, QColor(OUTBOUND_GRAD_BOT))
        grad_rect.setBrush(QBrush(gradient))
        grad_rect.setPen(QPen(QColor("#888888"), 1))
        grad_rect.setZValue(10)
        self.addItem(grad_rect)

    # ------------------------------------------------------------------
    # 3) Storage zone (좌하단)
    # ------------------------------------------------------------------
    def _draw_storage_zone(self) -> None:
        zx, zy, zw, zh = 20, 280, 420, 345
        _add_zone(self, zx, zy, zw, zh, "Storage zone")

        # Defect Box
        _add_box(self, 45, 320, 80, 50, "Defect\nBox", 8)

        # 빨간 사각형 (불량품)
        red1 = QGraphicsRectItem(145, 370, 55, 40)
        red1.setBrush(QBrush(QColor(RED_BLOCK)))
        red1.setPen(QPen(QColor("#cc0000"), 1))
        red1.setZValue(10)
        self.addItem(red1)

        # Outbound Waiting Zone
        _add_label(self, 255, 310, "Outbound\nWaiting\nZone")

        # Putaway Waiting Zone
        _add_label(self, 275, 400, "Putaway\nWaiting\nZone")

        # Cobot B
        _add_cobot(self, 170, 450, 35, "B")

        # Good product storage rack (호 모양 — 간략화: 큰 반원)
        path = QPainterPath()
        path.moveTo(45, 560)
        path.cubicTo(45, 480, 145, 480, 145, 560)
        path_item = self.addPath(path, QPen(QColor("#333333"), 2), QBrush(QColor("#ffffff")))
        path_item.setZValue(10)

        # Good product storage rack 라벨
        font = QFont("Sans", 7)
        rack_txt = QGraphicsSimpleTextItem("Good product\nstorage rack")
        rack_txt.setFont(font)
        rack_txt.setBrush(QBrush(QColor("#000000")))
        rack_txt.setPos(50, 565)
        rack_txt.setZValue(11)
        self.addItem(rack_txt)

    # ------------------------------------------------------------------
    # 4) Charging zone (중앙 하단)
    # ------------------------------------------------------------------
    def _draw_charging_zone(self) -> None:
        zx, zy, zw, zh = 480, 440, 380, 175
        _add_zone(self, zx, zy, zw, zh, "Charging zone")

        # 충전 스테이션 배경 (회색)
        station = QGraphicsRectItem(500, 470, 340, 125)
        station.setBrush(QBrush(CHARGING_BG))
        station.setPen(QPen(QColor("#999999"), 1))
        station.setZValue(5)
        self.addItem(station)

        # AMR 3대는 _SimAMR(AMR-001/002/003)이 시뮬레이션에서 관리

    # ------------------------------------------------------------------
    # 5) Casting zone (우측, 세로)
    # ------------------------------------------------------------------
    def _draw_casting_zone(self) -> None:
        zx, zy, zw, zh = 900, 250, 380, 375
        _add_zone(self, zx, zy, zw, zh, "Casting zone")

        # Casting Waiting Zone (노란 라벨)
        _add_label(self, 940, 280, "Casting\nWaiting\nZone")

        # Melting Furnace (파란 테두리 박스)
        _add_box(self, 1190, 275, 75, 50, "Melting\nFurnace", 8, bg="#dce8f5", border="#6688aa")

        # Mold (하늘색 세로 직사각형)
        mold = QGraphicsRectItem(910, 430, 35, 100)
        mold.setBrush(QBrush(QColor(MOLD_COLOR)))
        mold.setPen(QPen(QColor("#7799bb"), 1))
        mold.setZValue(10)
        self.addItem(mold)
        mold_txt = QGraphicsSimpleTextItem("Mold")
        mold_txt.setFont(QFont("Sans", 7))
        mold_txt.setBrush(QBrush(QColor("#000000")))
        mold_txt.setPos(912, 470)
        mold_txt.setZValue(11)
        mold_txt.setRotation(90)
        self.addItem(mold_txt)

        # Cobot A
        _add_cobot(self, 1080, 430, 30, "A")

        # 빨간 사각형 (주조물)
        red2 = QGraphicsRectItem(1140, 410, 45, 50)
        red2.setBrush(QBrush(QColor(RED_BLOCK)))
        red2.setPen(QPen(QColor("#cc0000"), 1))
        red2.setZValue(10)
        self.addItem(red2)

        # 작은 원 2개 (소형 장비)
        for cy in [395, 445]:
            sm = QGraphicsEllipseItem(1000 - 8, cy - 8, 16, 16)
            sm.setBrush(QBrush(QColor("#ffffff")))
            sm.setPen(QPen(QColor("#333333"), 1))
            sm.setZValue(10)
            self.addItem(sm)

        # Patterns (작은 박스 3개 + 라벨)
        for py in [500, 530, 560]:
            _add_box(self, 1130, py, 50, 22, "", 7)
        patterns_txt = QGraphicsSimpleTextItem("Patterns")
        patterns_txt.setFont(QFont("Sans", 8))
        patterns_txt.setBrush(QBrush(QColor("#000000")))
        patterns_txt.setPos(1195, 535)
        patterns_txt.setZValue(11)
        self.addItem(patterns_txt)

    # ------------------------------------------------------------------
    # 장비 갱신 (외부 호출)
    # ------------------------------------------------------------------
    def update_equipment(self, equipment: list[dict[str, Any]]) -> None:
        # AMR actors are owned by _SimController. Drawing equipment AMRs here
        # creates a second fleet on top of the simulation map.
        self._clear_equipment_amr_markers()

    def _update_amr_markers(self, amrs: list[dict[str, Any]]) -> None:
        seen: set[str] = set()
        # Charging zone 좌표 기준
        charge_x_start, charge_y = 560, 520
        charge_spacing = 110

        for idx, amr in enumerate(amrs):
            amr_id = str(amr.get("id", ""))
            if not amr_id:
                continue
            seen.add(amr_id)

            status = str(amr.get("status", ""))
            status_key = _status_key(status)
            color_info = STATUS_COLORS.get(status_key, STATUS_COLORS["idle"])
            color = color_info["dot"]

            pos_x_m = amr.get("pos_x")
            pos_y_m = amr.get("pos_y")
            if pos_x_m is not None and pos_y_m is not None:
                target_x = 50 + (float(pos_x_m) / 32.0) * (SCENE_W - 100)
                target_y = 50 + (float(pos_y_m) / 12.0) * (SCENE_H - 100)
            else:
                target_x = charge_x_start + idx * charge_spacing
                target_y = charge_y

            state = self._amr_state.get(amr_id)
            if state is None:
                marker = QGraphicsRectItem(-20, -12, 40, 24)
                marker.setBrush(QBrush(QColor(color)))
                marker.setPen(QPen(QColor(color_info["border"]), 2))
                marker.setZValue(50)
                self.addItem(marker)

                label = QGraphicsSimpleTextItem(amr_id, marker)
                label.setFont(QFont("Sans", 7, QFont.Bold))
                label.setBrush(QBrush(QColor("#111111")))
                lr = label.boundingRect()
                label.setPos(-lr.width() / 2, -lr.height() / 2)

                trail = self.addLine(
                    target_x, target_y, target_x, target_y, QPen(QColor(color), 2, Qt.DashLine)
                )
                trail.setZValue(40)

                marker.setPos(target_x, target_y)
                self._amr_state[amr_id] = {
                    "marker": marker,
                    "label": label,
                    "trail": trail,
                    "current": QPointF(target_x, target_y),
                    "target": QPointF(target_x, target_y),
                    "color": color,
                    "data": amr,
                }
            else:
                state["target"] = QPointF(target_x, target_y)
                state["color"] = color
                state["data"] = amr
                state["marker"].setBrush(QBrush(QColor(color)))
                tp = state["trail"].pen()
                tp.setColor(QColor(color))
                state["trail"].setPen(tp)

            st = self._amr_state[amr_id]
            battery = amr.get("battery")
            tooltip = f"{amr_id}\nstatus: {status}"
            if battery is not None:
                tooltip += f"\nbattery: {battery}%"
            st["marker"].setToolTip(tooltip)

        for amr_id in list(self._amr_state.keys()):
            if amr_id not in seen:
                st = self._amr_state.pop(amr_id)
                self.removeItem(st["marker"])
                self.removeItem(st["trail"])

    def _clear_equipment_amr_markers(self) -> None:
        for st in self._amr_state.values():
            self.removeItem(st["marker"])
            self.removeItem(st["trail"])
        self._amr_state.clear()

    def _tick_animation(self) -> None:
        for state in self._amr_state.values():
            current: QPointF = state["current"]
            target: QPointF = state["target"]
            dx = target.x() - current.x()
            dy = target.y() - current.y()
            if dx * dx + dy * dy < 0.25:
                continue
            new_x = current.x() + dx * self.ANIMATION_STEP
            new_y = current.y() + dy * self.ANIMATION_STEP
            state["current"] = QPointF(new_x, new_y)
            state["marker"].setPos(new_x, new_y)
            state["trail"].setLine(new_x - dx, new_y - dy, new_x, new_y)
