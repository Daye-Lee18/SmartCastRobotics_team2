"""패턴 위치 조작 및 생산 시작 페이지.

APPR 발주를 선택하고 패턴 위치(1~3)를 수동으로 지정한 뒤,
해당 ord_id 에 패턴을 등록하거나 등록 후 생산 시작을 수행한다.
"""

from __future__ import annotations

from typing import Any

import sip
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.widgets.ui import StatusBadge


class _RefreshWorker(QObject):
    """주문 목록 + 패턴 맵을 백그라운드에서 조회."""

    data_ready = pyqtSignal(dict)

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api

    @pyqtSlot()
    def run(self) -> None:
        def _safe(fn, *args, **kwargs):
            try:
                return fn(*args, **kwargs) or []
            except Exception:  # noqa: BLE001
                return []

        data: dict[str, Any] = {
            "orders": _safe(self._api.get_smartcast_orders),
            "patterns": _safe(self._api.get_patterns),
        }
        self.data_ready.emit(data)


class PatternControlPage(QWidget):
    """패턴 위치 수동 조작 + 생산 시작 페이지."""

    _STATUS_ALIASES = {
        "APPROVED": "APPR",
        "IN_PRODUCTION": "MFG",
        "PRODUCTION": "MFG",
        "PRODUCTION_COMPLETED": "DONE",
        "SHIPPING_READY": "SHIP",
        "SHIPPED": "SHIP",
        "COMPLETED": "COMP",
    }

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._orders: list[dict[str, Any]] = []
        self._patterns: dict[int, int] = {}
        self._refresh_thread: QThread | None = None
        self._refresh_worker: _RefreshWorker | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel("패턴 위치 조작 및 생산 시작")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "승인(APPR)된 발주를 선택한 뒤 패턴 위치를 1~3 중에서 직접 지정하고, "
            "패턴 등록 또는 패턴 등록 후 생산 시작을 실행합니다."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)

        card = QGroupBox("수동 패턴 제어")
        grid = QGridLayout(card)
        grid.setSpacing(10)

        grid.addWidget(QLabel("발주:"), 0, 0)
        self._order_combo = QComboBox()
        self._order_combo.setMinimumWidth(320)
        self._order_combo.currentIndexChanged.connect(self._on_order_selected)
        grid.addWidget(self._order_combo, 0, 1, 1, 3)

        grid.addWidget(QLabel("패턴 위치 (수동):"), 1, 0)
        self._pattern_spin = QSpinBox()
        self._pattern_spin.setRange(1, 3)
        self._pattern_spin.setMinimumWidth(120)
        self._pattern_spin.valueChanged.connect(self._on_pattern_changed)
        grid.addWidget(self._pattern_spin, 1, 1)

        grid.addWidget(QLabel("현재 등록 패턴:"), 1, 2)
        self._registered_badge = StatusBadge("미등록", status="muted")
        self._registered_badge.setMinimumWidth(120)
        grid.addWidget(self._registered_badge, 1, 3)

        grid.addWidget(QLabel("선택 패턴:"), 2, 0)
        self._selected_badge = StatusBadge("1 (원형)", status="info")
        self._selected_badge.setMinimumWidth(120)
        grid.addWidget(self._selected_badge, 2, 1)

        grid.addWidget(QLabel("주문 상태:"), 2, 2)
        self._order_status_badge = StatusBadge("—", status="muted")
        self._order_status_badge.setMinimumWidth(120)
        grid.addWidget(self._order_status_badge, 2, 3)

        self._hint_label = QLabel(
            "패턴 등록은 선택한 ord_id 에 대해 저장됩니다. 생산 시작은 패턴이 등록된 APPR 발주에서만 가능합니다."
        )
        self._hint_label.setWordWrap(True)
        self._hint_label.setProperty("tone", "muted")
        grid.addWidget(self._hint_label, 3, 0, 1, 4)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self._register_btn = QPushButton("패턴 등록")
        self._register_btn.setProperty("variant", "secondary")
        self._register_btn.clicked.connect(self._on_register_pattern)
        action_row.addWidget(self._register_btn)

        self._register_start_btn = QPushButton("패턴 등록 후 생산 시작")
        self._register_start_btn.setProperty("variant", "primary")
        self._register_start_btn.clicked.connect(self._on_register_and_start)
        action_row.addWidget(self._register_start_btn)

        action_row.addStretch(1)
        grid.addLayout(action_row, 4, 0, 1, 4)

        root.addWidget(card)

        self._status_label = QLabel("주문 목록을 불러오는 중입니다...")
        self._status_label.setWordWrap(True)
        self._status_label.setProperty("tone", "muted")
        root.addWidget(self._status_label)

        root.addStretch(1)

    def refresh(self) -> None:
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return

        worker = _RefreshWorker(self._api)
        thread = QThread(self)
        self._refresh_worker = worker
        worker.moveToThread(thread)
        worker.data_ready.connect(self._on_refresh_done)
        worker.data_ready.connect(lambda _: thread.quit())
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_refresh_worker)
        self._refresh_thread = thread
        thread.start()

    @pyqtSlot(dict)
    def _on_refresh_done(self, data: dict) -> None:
        if self._is_ui_deleted():
            return

        orders = data.get("orders") or []
        patterns = data.get("patterns") or []

        self._orders = [self._normalize_order(item) for item in orders]
        self._orders = [order for order in self._orders if order["status"] == "APPR"]
        self._patterns = {
            int(p["ord_id"]): int(p.get("ptn_loc_id", p.get("ptn_id")))
            for p in patterns
            if p.get("ord_id") is not None and p.get("ptn_loc_id", p.get("ptn_id")) is not None
        }

        current_ord_id = self._current_ord_id()

        self._order_combo.blockSignals(True)
        self._order_combo.clear()
        for order in self._orders:
            label = f"ord_{order['ord_id']}  (user={order.get('user_id', '-')}, {order['status']})"
            self._order_combo.addItem(label, userData=order["ord_id"])
        self._order_combo.blockSignals(False)

        if self._order_combo.count() > 0:
            if current_ord_id is not None:
                idx = self._index_for_ord_id(current_ord_id)
                self._order_combo.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                self._order_combo.setCurrentIndex(0)
            self._sync_selection_view()
            self._status_label.setText(f"패턴 등록 대상 APPR 주문 {self._order_combo.count()}건을 불러왔습니다.")
        else:
            self._registered_badge.set_status("muted", text="미등록")
            self._selected_badge.set_status("muted", text="—")
            self._order_status_badge.set_status("muted", text="—")
            self._register_btn.setEnabled(False)
            self._register_start_btn.setEnabled(False)
            self._status_label.setText("표시할 APPR 주문이 없습니다.")

    @pyqtSlot()
    def _clear_refresh_worker(self) -> None:
        self._refresh_worker = None

    def _is_ui_deleted(self) -> bool:
        """Return True when the page or any required child widget has been destroyed."""
        if sip.isdeleted(self):
            return True
        for widget in (
            getattr(self, "_order_combo", None),
            getattr(self, "_pattern_spin", None),
            getattr(self, "_registered_badge", None),
            getattr(self, "_selected_badge", None),
            getattr(self, "_order_status_badge", None),
            getattr(self, "_register_btn", None),
            getattr(self, "_register_start_btn", None),
            getattr(self, "_status_label", None),
        ):
            if widget is None or sip.isdeleted(widget):
                return True
        return False

    def _current_ord_id(self) -> int | None:
        if self._is_ui_deleted():
            return None
        idx = self._order_combo.currentIndex()
        if idx < 0:
            return None
        ord_id = self._order_combo.itemData(idx)
        return int(ord_id) if ord_id is not None else None

    def _index_for_ord_id(self, ord_id: int) -> int:
        for idx in range(self._order_combo.count()):
            item_ord_id = self._order_combo.itemData(idx)
            if item_ord_id is not None and int(item_ord_id) == ord_id:
                return idx
        return -1

    def _normalize_order(self, item: dict[str, Any]) -> dict[str, Any]:
        ord_id = item.get("ord_id", item.get("order_id", item.get("id")))
        try:
            ord_id_int = int(ord_id)
        except (TypeError, ValueError):
            ord_id_int = 0

        raw_status = item.get("latest_stat", item.get("ord_stat", item.get("status", "RCVD")))
        status = self._normalize_status(str(raw_status or "RCVD"))
        return {
            "ord_id": ord_id_int,
            "user_id": item.get("user_id"),
            "status": status,
        }

    def _normalize_status(self, status: str) -> str:
        key = status.strip().upper()
        return self._STATUS_ALIASES.get(key, key)

    def _sync_selection_view(self) -> None:
        if self._is_ui_deleted():
            return

        ord_id = self._current_ord_id()
        if ord_id is None:
            return

        order = next((o for o in self._orders if o["ord_id"] == ord_id), None)
        if order is None:
            return

        pattern_id = self._patterns.get(ord_id)
        selected_pattern = self._pattern_spin.value()
        pattern_label_map = {1: "1 (원형)", 2: "2 (사각)", 3: "3 (타원형)"}
        status_label_map = {
            "RCVD": ("수신", "muted"),
            "APPR": ("승인", "ok"),
            "MFG": ("생산중", "info"),
            "DONE": ("완료", "ok"),
            "REJT": ("거절", "danger"),
            "CNCL": ("취소", "muted"),
        }

        if pattern_id is None:
            self._registered_badge.set_status("muted", text="미등록")
        else:
            self._registered_badge.set_status("ok", text=pattern_label_map.get(pattern_id, str(pattern_id)))

        self._selected_badge.set_status("info", text=pattern_label_map.get(selected_pattern, str(selected_pattern)))

        status_text, tone = status_label_map.get(order["status"], (order["status"], "muted"))
        self._order_status_badge.set_status(tone, text=status_text)

        self._register_btn.setEnabled(True)
        self._register_start_btn.setEnabled(order["status"] == "APPR")

        if pattern_id is None:
            self._status_label.setText(
                f"발주 {ord_id}: 패턴 미등록. 원하는 위치를 선택하고 '패턴 등록' 또는 "
                f"'패턴 등록 후 생산 시작'을 누르세요."
            )
        else:
            self._status_label.setText(
                f"발주 {ord_id}: 현재 등록 패턴은 {pattern_label_map.get(pattern_id, str(pattern_id))} 입니다. "
                "필요하면 새 위치로 다시 등록할 수 있습니다."
            )

    @pyqtSlot()
    def _on_order_selected(self) -> None:
        self._sync_selection_view()

    @pyqtSlot(int)
    def _on_pattern_changed(self, _value: int) -> None:
        self._sync_selection_view()

    def _register_pattern(self, ord_id: int, ptn_loc_id: int) -> dict[str, Any] | None:
        result = self._api.register_pattern(ord_id, ptn_loc_id)
        if isinstance(result, dict):
            self._patterns[ord_id] = ptn_loc_id
        return result if isinstance(result, dict) else None

    @pyqtSlot()
    def _on_register_pattern(self) -> None:
        ord_id = self._current_ord_id()
        if ord_id is None:
            return

        ptn_loc_id = self._pattern_spin.value()
        try:
            self._register_pattern(ord_id, ptn_loc_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "패턴 등록 실패", str(exc))
            return

        QMessageBox.information(
            self,
            "패턴 등록 완료",
            f"발주 {ord_id}\n패턴 위치 {ptn_loc_id} ({self._pattern_spin.text()}) 로 등록했습니다.",
        )
        self.refresh()

    @pyqtSlot()
    def _on_register_and_start(self) -> None:
        ord_id = self._current_ord_id()
        if ord_id is None:
            return

        ptn_loc_id = self._pattern_spin.value()
        try:
            self._register_pattern(ord_id, ptn_loc_id)
            result = self._api.start_production_one(ord_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "패턴 등록/생산 시작 실패", str(exc))
            return

        msg = (result or {}).get("message", "Started.")
        QMessageBox.information(
            self,
            "생산 시작 완료",
            f"발주 {ord_id}\n패턴 위치 {ptn_loc_id} ({self._pattern_spin.text()})\n{msg}",
        )
        self.refresh()

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("type", "")
        if event_type in ("order_update", "order_status_changed", "production_approved"):
            self.refresh()
