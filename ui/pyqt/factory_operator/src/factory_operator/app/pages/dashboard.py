"""대시보드 페이지 - KPI 카드 + 주간 차트 + 최근 주문 + 실시간 알림."""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.widgets.alert_widgets import AlertListItem
from app.widgets.charts import WeeklyProductionChart
from app.widgets.conveyor_card import ConveyorCard
from app.widgets.factory_map import MiniFactoryMapView
from app.widgets.ui._helpers import set_property


class KpiCard(QFrame):
    """KPI 표시 카드."""

    def __init__(self, title: str, value: str = "-", unit: str = "") -> None:
        super().__init__()
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.StyledPanel)

        self._title = QLabel(title)
        self._title.setObjectName("kpiTitle")

        self._value = QLabel(value)
        self._value.setObjectName("kpiValue")

        self._unit = QLabel(unit)
        self._unit.setObjectName("kpiUnit")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)
        layout.addWidget(self._title)

        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        bottom.addWidget(self._value, alignment=Qt.AlignBottom)
        bottom.addWidget(self._unit, alignment=Qt.AlignBottom)
        bottom.addStretch()
        layout.addLayout(bottom)

    def update_value(self, value: str | int | float, unit: str = "") -> None:
        self._value.setText(str(value))
        if unit:
            self._unit.setText(unit)


class DashboardPage(QWidget):
    """대시보드 페이지 - KPI + 주간 차트 + 주문 테이블 + 알림."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._kpi_cards: dict[str, KpiCard] = {}
        self._build_ui()
        self.refresh()

        # 미니맵 전용 갱신 타이머.
        # 2026-04-27 성능 패치: 500ms → 3000ms.
        # 이전: 초당 2회 동기 HTTP /api/production/equipment 호출 → 백엔드 지연 시
        # 메인 스레드 1초씩 freeze. 대시보드 KPI/주간 차트는 8초 주기로 충분하므로
        # 미니맵도 3초로 통일 (AMR 위치는 mini map 이라 정밀도 불필요).
        self._fast_map_timer = QTimer(self)
        self._fast_map_timer.setInterval(3000)
        self._fast_map_timer.timeout.connect(self._refresh_mini_map)
        self._fast_map_timer.start()

    def _refresh_mini_map(self) -> None:
        # 페이지가 화면에 보이지 않을 때는 HTTP 호출 자체를 스킵 → 백그라운드 부하 0.
        if not self.isVisible():
            return
        equipment = self._api.get_equipment_raw() or []
        self._mini_map.update_equipment(equipment)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 제목
        title = QLabel("대시보드")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # KPI 그리드 (4칸)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)
        kpi_items = [
            ("production_rate", "생산량", "개"),
            ("defect_rate", "불량률", "%"),
            ("oee", "설비 가동률", "%"),
            ("active_orders", "진행 주문", "건"),
        ]
        for idx, (key, title_text, unit) in enumerate(kpi_items):
            card = KpiCard(title_text, unit=unit)
            self._kpi_cards[key] = card
            kpi_grid.addWidget(card, 0, idx)
        layout.addLayout(kpi_grid)

        # 컨베이어 실시간 상태 (한 줄 간략 표시)
        self._conveyor_cards: dict[str, ConveyorCard] = {}
        self._conveyor_bar = QFrame()
        self._conveyor_bar.setObjectName("tableCard")
        self._conveyor_bar.setFrameShape(QFrame.StyledPanel)
        self._conveyor_bar.setFixedHeight(40)
        conv_bar_layout = QHBoxLayout(self._conveyor_bar)
        conv_bar_layout.setContentsMargins(14, 4, 14, 4)
        conv_bar_layout.setSpacing(12)
        conv_bar_label = QLabel("컨베이어")
        conv_bar_label.setObjectName("convBarLabel")
        conv_bar_layout.addWidget(conv_bar_label)

        self._conv_status_dot = QLabel("●")
        self._conv_status_dot.setObjectName("statusDot")
        self._conv_status_dot.setProperty("status", "offline")
        conv_bar_layout.addWidget(self._conv_status_dot)

        self._conv_status_text = QLabel("오프라인")
        self._conv_status_text.setObjectName("convStatusText")
        conv_bar_layout.addWidget(self._conv_status_text)

        self._conv_motor_text = QLabel("모터: -")
        self._conv_motor_text.setObjectName("convMetaText")
        conv_bar_layout.addWidget(self._conv_motor_text)

        self._conv_count_text = QLabel("사이클: 0")
        self._conv_count_text.setObjectName("convMetaText")
        conv_bar_layout.addWidget(self._conv_count_text)

        self._conv_tof_text = QLabel("TOF1: -  TOF2: -")
        self._conv_tof_text.setObjectName("convMetaText")
        conv_bar_layout.addWidget(self._conv_tof_text)

        conv_bar_layout.addStretch()

        # ConveyorCard 호환용 (MQTT 메시지 처리에 사용)
        default_card = ConveyorCard("1")
        default_card.setVisible(False)
        self._conveyor_cards["1"] = default_card

        layout.addWidget(self._conveyor_bar)

        # 중단: 공장 맵(왼쪽 50%) | 주간 차트 + 최근 주문(오른쪽 50%)
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        # -- 왼쪽: 공장 현황 맵 --
        map_container = QFrame()
        map_container.setObjectName("tableCard")
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(12, 10, 12, 12)
        map_layout.setSpacing(6)

        map_title = QLabel("공장 현황 맵")
        map_title.setObjectName("sectionTitle")
        map_layout.addWidget(map_title)

        self._mini_map = MiniFactoryMapView()
        self._mini_map.setMinimumHeight(300)
        self._mini_map.setMaximumHeight(16777215)
        map_layout.addWidget(self._mini_map, stretch=1)

        mid_row.addWidget(map_container, stretch=1)

        # -- 오른쪽: 주간 차트(위) + 최근 주문(아래) --
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self._weekly_chart = WeeklyProductionChart()
        self._weekly_chart.setMinimumHeight(180)
        right_col.addWidget(self._weekly_chart, stretch=1)

        # 최근 주문 테이블
        orders_container = QFrame()
        orders_container.setObjectName("tableCard")
        orders_layout = QVBoxLayout(orders_container)
        orders_layout.setContentsMargins(12, 10, 12, 12)
        orders_layout.setSpacing(8)

        orders_title = QLabel("최근 주문")
        orders_title.setObjectName("sectionTitle")
        orders_layout.addWidget(orders_title)

        self._orders_table = QTableWidget(0, 4)
        self._orders_table.setHorizontalHeaderLabels(["고객사", "금액", "납기", "상태"])
        self._orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._orders_table.verticalHeader().setVisible(False)
        self._orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_layout.addWidget(self._orders_table)

        right_col.addWidget(orders_container, stretch=1)

        mid_row.addLayout(right_col, stretch=1)
        layout.addLayout(mid_row, stretch=4)

        # 알림 목록 (하단) - severity 아이콘/색상 위젯
        alert_title = QLabel("실시간 알림")
        alert_title.setObjectName("sectionTitle")
        layout.addWidget(alert_title)

        self._alert_scroll = QScrollArea()
        self._alert_scroll.setObjectName("alertScroll")
        self._alert_scroll.setWidgetResizable(True)
        self._alert_scroll.setFrameShape(QFrame.NoFrame)
        self._alert_scroll.setMaximumHeight(200)

        self._alert_container = QWidget()
        self._alert_layout = QVBoxLayout(self._alert_container)
        self._alert_layout.setContentsMargins(0, 0, 0, 0)
        self._alert_layout.setSpacing(6)
        self._alert_layout.addStretch()

        self._alert_scroll.setWidget(self._alert_container)
        layout.addWidget(self._alert_scroll)

    def refresh(self) -> None:
        """REST API 에서 최신 데이터 갱신."""
        stats = self._api.get_dashboard_stats()
        if stats:
            self._kpi_cards["production_rate"].update_value(stats.get("today_production", 0))
            self._kpi_cards["defect_rate"].update_value(f"{stats.get('defect_rate', 0):.1f}")
            self._kpi_cards["oee"].update_value(
                f"{stats.get('equipment_utilization', stats.get('oee', 0)):.1f}"
            )
            self._kpi_cards["active_orders"].update_value(
                stats.get("active_orders", stats.get("pending_orders", 0))
            )

        # 공장 미니맵
        equipment = self._api.get_equipment_raw() or []
        self._mini_map.update_equipment(equipment)

        # 주간 차트
        weekly = self._api.get_weekly_production()
        self._weekly_chart.update_data(weekly)

        # 최근 주문 테이블
        orders = self._api.get_recent_orders()
        self._update_orders_table(orders)

        # 알림
        alerts = self._api.get_alerts() or []
        self._rebuild_alerts(alerts[:20])
        self._emit_critical_alerts(alerts)

    def _emit_critical_alerts(self, alerts: list[dict[str, Any]]) -> None:
        """critical/error 알림을 MainWindow 토스트로 전달."""
        # MainWindow 인스턴스 찾기 (tree 위로 탐색)
        win = self.window()
        show_toast = getattr(win, "_maybe_show_toast_for_alert", None)
        if show_toast is None:
            return
        for alert in alerts[:5]:  # 최근 5개만
            show_toast(alert)

    def _rebuild_alerts(self, alerts: list[dict[str, Any]]) -> None:
        # 기존 항목 제거 (마지막 stretch 제외)
        while self._alert_layout.count() > 1:
            item = self._alert_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.deleteLater()
        # 새 항목 추가
        for alert in alerts:
            widget = AlertListItem(alert)
            self._alert_layout.insertWidget(self._alert_layout.count() - 1, widget)

    def _update_orders_table(self, orders: list[dict[str, Any]]) -> None:
        self._orders_table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            self._orders_table.setItem(row, 0, QTableWidgetItem(str(order.get("customer", "-"))))
            amount = order.get("amount", 0) or 0
            try:
                amt_str = f"₩{int(amount):,}"
            except (TypeError, ValueError):
                amt_str = str(amount)
            self._orders_table.setItem(row, 1, QTableWidgetItem(amt_str))
            self._orders_table.setItem(row, 2, QTableWidgetItem(str(order.get("due_date", ""))))
            status_item = QTableWidgetItem(str(order.get("status", "")))
            status_item.setTextAlignment(Qt.AlignCenter)
            self._orders_table.setItem(row, 3, status_item)

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        """WebSocket 실시간 이벤트 수신 처리."""
        if payload.get("type") in (
            "dashboard_update",
            "order_update",
            "production_update",
        ):
            self.refresh()

    def handle_mqtt_message(self, topic: str, payload: dict[str, Any]) -> None:
        """MQTT 메시지 수신 - 컨베이어 한 줄 바 실시간 갱신."""
        parts = topic.split("/")
        if len(parts) < 2:
            return
        if parts[0] != "conveyor":
            return
        conveyor_id = parts[1]
        subtype = parts[2] if len(parts) > 2 else ""

        card = self._conveyor_cards.get(conveyor_id)
        if card is None:
            card = ConveyorCard(conveyor_id)
            card.setVisible(False)
            self._conveyor_cards[conveyor_id] = card

        if subtype == "status":
            card.update_from_payload(payload)
            card.set_online(True)
            self._update_conveyor_bar(payload)
        elif subtype == "heartbeat":
            value = str(payload.get("value", "")).lower()
            online = value == "online" or "alive" in payload
            card.set_online(online)
            if not online:
                set_property(self._conv_status_dot, "status", "offline")
                self._conv_status_text.setText("오프라인")
            else:
                set_property(self._conv_status_dot, "status", "online")
        elif subtype == "event":
            card.set_online(True)
            set_property(self._conv_status_dot, "status", "online")

    def _update_conveyor_bar(self, payload: dict[str, Any]) -> None:
        """컨베이어 상태를 한 줄 바에 반영."""
        state = str(payload.get("state", "offline"))
        state_labels = {
            "idle": "대기",
            "running": "이송 중",
            "stopped": "검사 대기",
            "post_run": "후처리",
            "clearing": "배출 중",
            "error": "오류",
        }
        self._conv_status_text.setText(state_labels.get(state, state))
        if state == "running":
            set_property(self._conv_status_dot, "status", "online")
        elif state == "idle":
            set_property(self._conv_status_dot, "status", "offline")
        else:
            set_property(self._conv_status_dot, "status", "warn")

        motor = payload.get("motor")
        if isinstance(motor, dict):
            running = bool(motor.get("running"))
        else:
            running = bool(motor)
        self._conv_motor_text.setText(f"모터: {'ON' if running else 'OFF'}")

        count = payload.get("count", 0)
        self._conv_count_text.setText(f"사이클: {count}")

        tof1 = payload.get("tof1", {})
        tof2 = payload.get("tof2", {})
        t1 = f"{tof1.get('mm', '-')}mm" if tof1 else "-"
        t2 = f"{tof2.get('mm', '-')}mm" if tof2 else "-"
        self._conv_tof_text.setText(f"TOF1: {t1}  TOF2: {t2}")

    @staticmethod
    def _format_alert(alert: dict[str, Any]) -> str:
        level = alert.get("level", "info").upper()
        ts = alert.get("created_at", "")
        msg = alert.get("message", "")
        return f"[{level}] {ts}  {msg}"
