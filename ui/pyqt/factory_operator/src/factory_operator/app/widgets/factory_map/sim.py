"""factory_map 위젯 — 시뮬레이션 (주물 이동).

`_CastingItem` (보라색 원형 주물), `_SimAMR` (시뮬 전용 AMR 마커),
`_SimController` (step 기반 FSM, 18 step 사이클).

FactoryMapScene 이 enable_sim=True 일 때만 _SimController 가 가동.

2026-04-27: factory_map.py (1069 LOC) 분할 산출. SIM_TICK_MS 200ms (5Hz) +
SIM_SPEED 10px 보정으로 메인 맵에 한 번만 가동되도록 (mini map 은 enable_sim=False).
"""

from __future__ import annotations

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QPen
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from ._constants import (
    _POS,
    AMR_COLOR,
    CASTING_COLOR,
    CASTING_RADIUS,
    SIM_SPEED,
    SIM_TICK_MS,
    _move_toward,
)


class _CastingItem:
    """보라색 원형 주물 — 20Hz 깜빡임."""

    def __init__(self, scene: QGraphicsScene, x: float, y: float) -> None:
        r = CASTING_RADIUS
        self._ellipse = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        self._ellipse.setBrush(QBrush(QColor(CASTING_COLOR)))
        self._ellipse.setPen(QPen(QColor("#7c22ce"), 2))
        self._ellipse.setZValue(60)
        self._ellipse.setPos(x, y)
        scene.addItem(self._ellipse)
        self._visible = True
        self._scene = scene

    def move_to(self, x: float, y: float) -> None:
        self._ellipse.setPos(x, y)

    def pos(self) -> tuple[float, float]:
        p = self._ellipse.pos()
        return p.x(), p.y()

    def toggle_blink(self) -> None:
        self._visible = not self._visible
        self._ellipse.setOpacity(1.0 if self._visible else 0.3)

    def remove(self) -> None:
        self._scene.removeItem(self._ellipse)

    def show(self) -> None:
        self._ellipse.setVisible(True)

    def hide(self) -> None:
        self._ellipse.setVisible(False)


class _SimAMR:
    """시뮬레이션 전용 AMR 마커."""

    def __init__(self, scene: QGraphicsScene, label: str, x: float, y: float) -> None:
        self._marker = QGraphicsRectItem(-20, -12, 40, 24)
        self._marker.setBrush(QBrush(QColor(AMR_COLOR)))
        self._marker.setPen(QPen(QColor("#b8a000"), 2))
        self._marker.setZValue(55)
        self._marker.setPos(x, y)
        scene.addItem(self._marker)

        txt = QGraphicsSimpleTextItem(label, self._marker)
        txt.setFont(QFont("Sans", 7, QFont.Bold))
        txt.setBrush(QBrush(QColor("#111111")))
        tr = txt.boundingRect()
        txt.setPos(-tr.width() / 2, -tr.height() / 2)

        self._scene = scene
        self._x, self._y = x, y
        self._waypoints: list[tuple[float, float]] = []
        self._cargo: _CastingItem | None = None

    def pos(self) -> tuple[float, float]:
        return self._x, self._y

    def set_waypoints(self, wps: list[tuple[float, float]]) -> None:
        self._waypoints = list(wps)

    def attach_cargo(self, item: _CastingItem) -> None:
        self._cargo = item

    def detach_cargo(self) -> _CastingItem | None:
        c = self._cargo
        self._cargo = None
        return c

    def tick(self, speed: float) -> bool:
        """한 프레임 이동. 모든 waypoint 도착 시 True 반환."""
        if not self._waypoints:
            return True
        tx, ty = self._waypoints[0]
        self._x, self._y, arrived = _move_toward(self._x, self._y, tx, ty, speed)
        self._marker.setPos(self._x, self._y)
        if self._cargo:
            self._cargo.move_to(self._x, self._y)
        if arrived:
            self._waypoints.pop(0)
        return not self._waypoints


class _SimController:
    """공정 시뮬레이션 컨트롤러 — step 기반 FSM.

    18 step 사이클:
        0   Mold 에서 주물 생성
        1   주물 → Casting Waiting Zone
        2   AMR-001 Casting 도착 대기
        3   AMR-001 + 주물 → Unloading Worker
        4   Unloading Worker 하차 → AMR-001 복귀
        5   주물 → PP Worker → 컨베이어 좌측
        6   컨베이어 좌→우 수평 이동
        7   컨베이어 끝 3초 대기
        8   Conveyor Waiting Zone 이동
        9   AMR-003 Conveyor Pickup
        10  AMR-003 → Putaway
        11  주물 → Good product storage rack
        12  rack 카운트 + 풀 검사
        13  AMR-003 rack 에서 주물 2개 로드
        14  AMR-003 → Outbound
        15  Outbound 하차
        16  AMR-003 복귀
        17  리셋 → 반복

    SIM_TICK_MS=200ms 마다 _tick() 호출. AMR/주물 모두 같은 timer 에 의해 보간 이동.
    """

    def __init__(self, scene: QGraphicsScene) -> None:
        self._scene = scene
        self._step = 0
        self._tick_count = 0
        self._wait_ticks = 0
        self._blink_counter = 0

        # 시뮬레이션 전용 AMR 3대
        self._amr1 = _SimAMR(scene, "AMR-001", *_POS["amr1_home"])
        self._amr2 = _SimAMR(scene, "AMR-002", *_POS["amr2_home"])
        self._amr3 = _SimAMR(scene, "AMR-003", *_POS["amr3_home"])

        # 주물 목록
        self._castings: list[_CastingItem] = []
        self._current: _CastingItem | None = None
        self._rack_count = 0  # rack에 쌓인 주물 수
        self._outbound_items: list[_CastingItem] = []

        self._timer = QTimer()
        self._timer.setInterval(SIM_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._step = 0
        self._timer.start()

    def _new_casting(self, x: float, y: float) -> _CastingItem:
        c = _CastingItem(self._scene, x, y)
        self._castings.append(c)
        return c

    def _tick(self) -> None:
        self._tick_count += 1

        # 20Hz 깜빡임 (50ms tick = 자동 20Hz)
        self._blink_counter += 1
        if self._blink_counter >= 1:
            self._blink_counter = 0
            for c in self._castings:
                c.toggle_blink()

        # 대기 중이면 카운트다운
        if self._wait_ticks > 0:
            self._wait_ticks -= 1
            return

        # step FSM
        if self._step == 0:
            self._step_0_create_casting()
        elif self._step == 1:
            self._step_1_casting_to_wait()
        elif self._step == 2:
            self._step_2_amr1_to_casting()
        elif self._step == 3:
            self._step_3_load_and_move_to_pp()
        elif self._step == 4:
            self._step_4_unload_at_pp()
        elif self._step == 5:
            self._step_5_move_to_conveyor()
        elif self._step == 6:
            self._step_6_conveyor_transport()
        elif self._step == 7:
            self._step_7_wait_at_conv_end()
        elif self._step == 8:
            self._step_8_to_conv_wait()
        elif self._step == 9:
            self._step_9_amr3_pickup()
        elif self._step == 10:
            self._step_10_amr3_to_putaway()
        elif self._step == 11:
            self._step_11_to_rack()
        elif self._step == 12:
            self._step_12_check_rack_full()
        elif self._step == 13:
            self._step_13_amr3_load_from_rack()
        elif self._step == 14:
            self._step_14_amr3_to_outbound()
        elif self._step == 15:
            self._step_15_unload_outbound()
        elif self._step == 16:
            self._step_16_amr3_return()
        elif self._step == 17:
            self._step_17_reset()

    # --- Step 0: Mold에서 주물 생성 ---
    def _step_0_create_casting(self) -> None:
        self._current = self._new_casting(*_POS["mold"])
        self._wait_ticks = int(2000 / SIM_TICK_MS)  # 2초 대기
        self._step = 1
        # AMR-001 출발 (동시에)
        self._amr1.set_waypoints(
            [
                _POS["corridor_charge_exit_1"],
                (850, 440),
                (850, 320),
                _POS["cast_pickup"],
            ]
        )
        # AMR-002 미리 Conveyor Waiting Zone 쪽으로 (나중에 필요)

    # --- Step 1: 주물 → Casting Waiting Zone ---
    def _step_1_casting_to_wait(self) -> None:
        if self._current is None:
            self._step = 2
            return
        cx, cy = self._current.pos()
        tx, ty = _POS["cast_wait"]
        nx, ny, arrived = _move_toward(cx, cy, tx, ty, SIM_SPEED)
        self._current.move_to(nx, ny)
        # AMR-001도 동시 이동
        self._amr1.tick(SIM_SPEED)
        if arrived:
            self._step = 2

    # --- Step 2: AMR-001이 Casting 도착 대기 ---
    def _step_2_amr1_to_casting(self) -> None:
        done = self._amr1.tick(SIM_SPEED)
        if done:
            # 주물을 AMR에 로드
            if self._current:
                self._current.move_to(*self._amr1.pos())
                self._amr1.attach_cargo(self._current)
            # AMR-001 경로: Casting → Unloading Worker (zone 밖 통로)
            self._amr1.set_waypoints(
                [
                    (850, 250),
                    (700, 250),
                    (200, 250),
                    (90, 250),
                    _POS["unload_worker"],
                ]
            )
            self._step = 3

    # --- Step 3: AMR-001+주물 → Unloading Worker ---
    def _step_3_load_and_move_to_pp(self) -> None:
        done = self._amr1.tick(SIM_SPEED)
        if done:
            self._step = 4

    # --- Step 4: Unloading Worker에서 하차 → AMR-001 복귀 ---
    def _step_4_unload_at_pp(self) -> None:
        cargo = self._amr1.detach_cargo()
        if cargo:
            cargo.move_to(*_POS["unload_worker"])
        # AMR-001 Charging으로 복귀
        self._amr1.set_waypoints(
            [
                (90, 250),
                (450, 250),
                (562, 440),
                _POS["amr1_home"],
            ]
        )
        self._step = 5

    # --- Step 5: 주물 → Postprocessing Worker → 컨베이어 왼쪽 ---
    def _step_5_move_to_conveyor(self) -> None:
        self._amr1.tick(SIM_SPEED)  # AMR-001 복귀 (백그라운드)
        if self._current is None:
            self._step = 6
            return
        cx, cy = self._current.pos()
        tx, ty = _POS["conv_left"]
        # 먼저 pp_worker로 → 그 다음 conv_left로
        if cy > 130:
            # pp_worker로 이동
            nx, ny, arrived = _move_toward(cx, cy, 160, 130, SIM_SPEED)
            self._current.move_to(nx, ny)
        else:
            nx, ny, arrived = _move_toward(cx, cy, tx, ty, SIM_SPEED)
            self._current.move_to(nx, ny)
            if arrived:
                self._step = 6

    # --- Step 6: 컨베이어 위 좌→우 수평 이동 ---
    def _step_6_conveyor_transport(self) -> None:
        self._amr1.tick(SIM_SPEED)  # AMR-001 복귀 계속
        if self._current is None:
            self._step = 7
            return
        cx, cy = self._current.pos()
        tx, ty = _POS["conv_right"]
        nx, ny, arrived = _move_toward(cx, cy, tx, ty, SIM_SPEED * 0.6)
        self._current.move_to(nx, ny)
        if arrived:
            self._wait_ticks = int(3000 / SIM_TICK_MS)  # 3초 대기
            self._step = 7
            # AMR-002 출발 → Conveyor Waiting Zone
            self._amr2.set_waypoints(
                [
                    _POS["corridor_charge_exit_2"],
                    (672, 250),
                    _POS["conv_pickup"],
                ]
            )

    # --- Step 7: 컨베이어 끝에서 3초 대기 ---
    def _step_7_wait_at_conv_end(self) -> None:
        self._amr2.tick(SIM_SPEED)  # AMR-002 이동
        # wait_ticks 가 0이면 자동으로 다음 step
        self._step = 8

    # --- Step 8: Conveyor Waiting Zone으로 이동 ---
    def _step_8_to_conv_wait(self) -> None:
        self._amr2.tick(SIM_SPEED)
        if self._current is None:
            self._step = 9
            return
        cx, cy = self._current.pos()
        tx, ty = _POS["conv_wait"]
        nx, ny, arrived = _move_toward(cx, cy, tx, ty, SIM_SPEED)
        self._current.move_to(nx, ny)
        if arrived:
            # 주물을 AMR-002 위치로 이동 (대기 중인 AMR 근처)
            self._current.move_to(*_POS["conv_pickup"])
            self._step = 9

    # --- Step 9: AMR-003 출발 → Conveyor Pickup ---
    def _step_9_amr3_pickup(self) -> None:
        # AMR-002 도착 확인
        amr2_done = self._amr2.tick(SIM_SPEED)
        if not amr2_done:
            return
        # AMR-003 출발
        self._amr3.set_waypoints(
            [
                _POS["corridor_charge_exit_3"],
                (782, 250),
                _POS["conv_pickup"],
            ]
        )
        self._step = 10
        # AMR-002 복귀
        self._amr2.set_waypoints(
            [
                (672, 250),
                (672, 440),
                _POS["amr2_home"],
            ]
        )

    # --- Step 10: AMR-003 → Putaway Waiting Zone ---
    def _step_10_amr3_to_putaway(self) -> None:
        self._amr2.tick(SIM_SPEED)  # AMR-002 복귀
        done = self._amr3.tick(SIM_SPEED)
        if done:
            # 주물 탑재
            if self._current:
                self._amr3.attach_cargo(self._current)
            self._amr3.set_waypoints(
                [
                    (600, 250),
                    (450, 250),
                    (450, 430),
                    _POS["putaway"],
                ]
            )
            self._step = 11

    # --- Step 11: 주물 → Good product storage rack ---
    def _step_11_to_rack(self) -> None:
        self._amr2.tick(SIM_SPEED)
        done = self._amr3.tick(SIM_SPEED)
        if done:
            # 하차
            cargo = self._amr3.detach_cargo()
            if cargo:
                cargo.move_to(*_POS["putaway"])
                self._current = cargo
            # AMR-003 대기 (rack 근처)
            self._amr3.set_waypoints(
                [
                    (310, 530),
                    _POS["rack_pickup"],
                ]
            )
            self._step = 12

    # --- Step 12: 주물이 rack으로 천천히 이동 + rack 카운트 ---
    def _step_12_check_rack_full(self) -> None:
        self._amr3.tick(SIM_SPEED * 0.5)
        if self._current is None:
            self._step = 13
            return
        cx, cy = self._current.pos()
        tx, ty = _POS["rack"]
        nx, ny, arrived = _move_toward(cx, cy, tx, ty, SIM_SPEED * 0.4)
        self._current.move_to(nx, ny)
        if arrived:
            self._rack_count += 1
            self._current.hide()
            self._current = None
            if self._rack_count < 2:
                # 2번째 주물을 위해 새 사이클 시작 (빠른 생성)
                c2 = self._new_casting(*_POS["rack"])
                c2.hide()
                self._rack_count = 2  # 즉시 2개로
            self._step = 13

    # --- Step 13: AMR-003이 rack에서 주물 2개 로드 ---
    def _step_13_amr3_load_from_rack(self) -> None:
        done = self._amr3.tick(SIM_SPEED)
        if done:
            # 주물 2개 생성 (시각적)
            c1 = self._new_casting(*self._amr3.pos())
            c2 = self._new_casting(self._amr3.pos()[0] + 5, self._amr3.pos()[1] + 5)
            self._amr3.attach_cargo(c1)
            self._outbound_items = [c1, c2]
            self._amr3.set_waypoints(
                [
                    _POS["rack_pickup"],
                    _POS["corridor_storage_bot"],
                    _POS["corridor_top"],
                    _POS["corridor_right"],
                    _POS["corridor_outbound_r"],
                    _POS["corridor_outbound_up"],
                    _POS["outbound"],
                ]
            )
            self._step = 14

    # --- Step 14: AMR-003 → Outbound ---
    def _step_14_amr3_to_outbound(self) -> None:
        done = self._amr3.tick(SIM_SPEED)
        # c2도 따라감
        if len(self._outbound_items) > 1:
            ax, ay = self._amr3.pos()
            self._outbound_items[1].move_to(ax + 5, ay + 5)
        if done:
            self._step = 15

    # --- Step 15: Outbound에서 하차 ---
    def _step_15_unload_outbound(self) -> None:
        self._amr3.detach_cargo()
        # 주물 2개를 Outbound zone에 배치
        ox, oy = _POS["outbound"]
        for i, c in enumerate(self._outbound_items):
            c.move_to(ox - 15 + i * 20, oy)
        self._wait_ticks = int(1000 / SIM_TICK_MS)  # 1초
        # AMR-003 Charging으로 복귀
        self._amr3.set_waypoints(
            [
                _POS["corridor_outbound_up"],
                _POS["corridor_outbound_r"],
                (782, 250),
                (782, 440),
                _POS["amr3_home"],
            ]
        )
        self._step = 16

    # --- Step 16: AMR-003 복귀 ---
    def _step_16_amr3_return(self) -> None:
        done = self._amr3.tick(SIM_SPEED)
        if done:
            self._step = 17

    # --- Step 17: 리셋 → 반복 ---
    def _step_17_reset(self) -> None:
        # 기존 주물 모두 제거
        for c in self._castings:
            c.remove()
        self._castings.clear()
        self._outbound_items.clear()
        self._current = None
        self._rack_count = 0
        self._wait_ticks = int(2000 / SIM_TICK_MS)  # 2초 대기 후 반복
        self._step = 0
