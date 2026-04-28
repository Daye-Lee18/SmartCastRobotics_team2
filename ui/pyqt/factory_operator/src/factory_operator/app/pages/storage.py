"""적재 모니터링 페이지.

물류/이송 화면에서 분리한 창고 랙 현황을 전담한다.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.pages.dashboard import KpiCard
from app.widgets.warehouse_rack import WarehouseRackWidget

STATUS_TEXT = {
    "empty": "비어있음",
    "partial": "부분점유",
    "full": "점유",
    "reserved": "예약",
    "locked": "잠김",
}


class StoragePage(QWidget):
    """창고 랙 적재 상태 페이지."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._kpi_cards: dict[str, KpiCard] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("적재")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        kpi_items = [
            ("total", "전체 랙", "개"),
            ("occupied", "점유 랙", "개"),
            ("reserved", "예약 랙", "개"),
            ("occupancy_rate", "점유율", "%"),
        ]
        for key, label, unit in kpi_items:
            card = KpiCard(label, unit=unit)
            self._kpi_cards[key] = card
            kpi_row.addWidget(card, stretch=1)
        layout.addLayout(kpi_row)

        self._rack_widget = WarehouseRackWidget()
        layout.addWidget(self._rack_widget, stretch=3)

        detail_title = QLabel("랙 상세")
        detail_title.setObjectName("sectionTitle")
        layout.addWidget(detail_title)

        self._detail_table = QTableWidget(0, 5)
        self._detail_table.setHorizontalHeaderLabels(["랙", "상태", "품목", "수량", "비고"])
        self._detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._detail_table.setMaximumHeight(220)
        layout.addWidget(self._detail_table, stretch=1)

    def refresh(self) -> None:
        racks = self._api.get_warehouse_racks()
        self._rack_widget.update_racks(racks)
        self._update_kpis(racks)
        self._update_detail_table(racks)

    def _update_kpis(self, racks: list[dict[str, Any]]) -> None:
        total = len(racks)
        occupied = sum(
            1
            for rack in racks
            if str(rack.get("status", "")).lower() in ("full", "partial", "locked")
        )
        reserved = sum(1 for rack in racks if str(rack.get("status", "")).lower() == "reserved")
        occupancy_rate = occupied * 100 / total if total else 0

        self._kpi_cards["total"].update_value(total)
        self._kpi_cards["occupied"].update_value(occupied)
        self._kpi_cards["reserved"].update_value(reserved)
        self._kpi_cards["occupancy_rate"].update_value(f"{occupancy_rate:.0f}")

    def _update_detail_table(self, racks: list[dict[str, Any]]) -> None:
        sorted_racks = sorted(racks, key=_rack_sort_key)
        self._detail_table.setRowCount(len(sorted_racks))
        for row, rack in enumerate(sorted_racks):
            rack_id = str(rack.get("id", ""))
            status = str(rack.get("status", "empty")).lower()
            content = str(rack.get("content", "") or "-")
            qty = int(rack.get("qty", 0) or 0)
            note = "입고 가능" if status == "empty" else ""

            id_item = QTableWidgetItem(rack_id)
            id_item.setTextAlignment(Qt.AlignCenter)
            self._detail_table.setItem(row, 0, id_item)

            status_item = QTableWidgetItem(STATUS_TEXT.get(status, status))
            status_item.setTextAlignment(Qt.AlignCenter)
            self._detail_table.setItem(row, 1, status_item)

            self._detail_table.setItem(row, 2, QTableWidgetItem(content))

            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._detail_table.setItem(row, 3, qty_item)

            self._detail_table.setItem(row, 4, QTableWidgetItem(note))

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "warehouse_update":
            self.refresh()


def _rack_sort_key(rack: dict[str, Any]) -> tuple[int, str]:
    rack_id = str(rack.get("id", ""))
    try:
        return int(rack_id), rack_id
    except ValueError:
        return 10_000, rack_id
