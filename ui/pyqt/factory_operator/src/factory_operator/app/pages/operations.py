"""실시간 운영 모니터링 (Realtime Operations Monitoring) 페이지.

2026-04-27 통합 — 이전 '운영 관리' + '생산 모니터링' 두 페이지를 하나로 합쳤다.

자동 패턴 매핑 (2026-04-27):
  발주 시 frontend product_id 첫 글자로 ptn_loc 가 backend 에서 자동 결정·DB 등록.
  R-* (원형) → 1, S-* (사각) → 2, O-* (타원형) → 3.
  PyQt 운영자는 SpinBox 로 입력하지 않는다 — 표시 전용.

레이아웃:
  ┌─────── 상단: 발주 운영 (자동 ptn_loc 표시 + 생산 시작) ───────┐
  ├─────── 본문 좌: 선택 발주 item 목록 + 설비 단계 진행 ────────┤
  ├─────── 본문 우: 검사 요약 (양품/불량/미검사) ─────────────────┤
  ├─────── 공정 단계 테이블 (실시간) ─────────────────────────────┤
  ├─────── 주문별 제품 실시간 위치 (gRPC ListItems) ─────────────┤
  ├─────── 최근 24H mini-summary (timescale 분기) ──────────────┤
  └─────── AMR 핸드오프 ACK 패널 (SPEC-AMR-001) ─────────────────┘

비동기 구조 (2026-04-28):
  HTTP 호출을 QThread 워커(_RefreshWorker, _OrdItemsWorker)로 분리해
  메인 GUI 스레드 블로킹을 제거.
  - _RefreshWorker: 8개 API 전체 조회 → data_ready 시그널
  - _OrdItemsWorker: 선택 발주 item + PP + equip_task 조회 → data_ready 시그널
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient

# 주문/아이템 진행 테이블 컬럼 — production.py 에서 통합
ITEM_STAGE_COLUMNS: list[str] = ["대기", "주탕", "탈형", "후처리", "검사", "적재"]


# ---------------------------------------------------------------------------
# 백그라운드 워커 — GUI 스레드 블로킹 방지
# ---------------------------------------------------------------------------

class _RefreshWorker(QObject):
    """전체 페이지 갱신에 필요한 API 8건을 백그라운드 스레드에서 일괄 호출."""

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
            "orders":        _safe(self._api.get_smartcast_orders),
            "patterns":      _safe(self._api.get_patterns),
            "summary":       _safe(self._api.get_inspection_summary),
            "stages":        _safe(self._api.get_process_stages),
            "item_progress": _safe(self._api.get_order_item_progress),
            "hourly":        _safe(self._api.get_hourly_production_v2, hours=24),
            "err_trend":     _safe(self._api.get_err_log_trend, hours=24),
        }
        try:
            data["dashboard"] = self._api.get_dashboard_stats_v2() or {}
        except Exception:  # noqa: BLE001
            data["dashboard"] = {}

        self.data_ready.emit(data)


class _OrdItemsWorker(QObject):
    """선택 발주의 item + PP 요건 + 활성 equip_task 를 백그라운드에서 일괄 조회."""

    # ord_id, list[{item, item_id, pp_data, active_txn}]
    data_ready = pyqtSignal(int, list)

    def __init__(self, api: ApiClient, ord_id: int) -> None:
        super().__init__()
        self._api = api
        self._ord_id = ord_id

    @pyqtSlot()
    def run(self) -> None:
        items = self._api.get_smartcast_items(ord_id=self._ord_id) or []
        enriched: list[dict[str, Any]] = []
        for it in items:
            item_id = int(it.get("item_id"))
            try:
                pp_data = self._api.get_item_pp_requirements(item_id)
            except Exception:  # noqa: BLE001
                pp_data = None
            try:
                active_txn = self._api.get_active_equip_task_for_item(item_id)
            except Exception:  # noqa: BLE001
                active_txn = None
            enriched.append({"item": it, "item_id": item_id, "pp_data": pp_data, "active_txn": active_txn})
        self.data_ready.emit(self._ord_id, enriched)


# ---------------------------------------------------------------------------
# 페이지 위젯
# ---------------------------------------------------------------------------

class OperationsPage(QWidget):
    """실시간 운영 모니터링 통합 페이지."""

    refresh_requested = pyqtSignal()

    def __init__(self, api: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._api = api
        self._patterns: dict[int, int] = {}  # ord_id → ptn_loc (자동 등록 결과 표시용)
        self._item_stage_cache: dict[int, str] = {}  # item_id → stage_code (gRPC stream)
        # QThread 참조 보관 — GC 방지 + 중복 실행 방지
        self._refresh_thread: QThread | None = None
        self._ord_thread: QThread | None = None
        self._build_ui()
        self.refresh()
        self._start_item_stream()

    # ------------------------------------------------------------------
    # gRPC ItemStream (production.py 에서 통합)
    # ------------------------------------------------------------------
    def _start_item_stream(self) -> None:
        try:
            from app.workers.item_stream_worker import (
                ItemStreamThread,
                ItemStreamWorker,
            )
        except ImportError:
            return
        self._stream_worker = ItemStreamWorker(order_filter=None)
        self._stream_worker.item_event.connect(self._on_item_event)
        self._stream_thread = ItemStreamThread(self._stream_worker)
        self._stream_thread.start()

    def _on_item_event(self, item_id: int, stage_code: str, robot_id: str, at_iso: str) -> None:
        prev = self._item_stage_cache.get(item_id)
        self._item_stage_cache[item_id] = stage_code
        if prev != stage_code:
            self._update_item_row(item_id, stage_code)

    def _update_item_row(self, item_id: int, stage_code: str) -> None:
        if not hasattr(self, "_item_progress_table"):
            return
        target = f"I-{item_id}"
        for row in range(self._item_progress_table.rowCount()):
            cell = self._item_progress_table.item(row, 2)
            if cell and cell.text() == target:
                self._render_item_row_stage(row, stage_code)
                return

    def _render_item_row_stage(self, row: int, stage_code: str) -> None:
        code_to_label = {
            "QUE": "대기",
            "MM": "주탕",
            "DM": "탈형",
            "PP": "후처리",
            "TR_PP": "후처리",
            "IP": "검사",
            "TR_LD": "적재",
            "SH": "적재",
        }
        target_label = code_to_label.get(stage_code, "대기")
        try:
            current_idx = ITEM_STAGE_COLUMNS.index(target_label)
        except ValueError:
            return
        current_color = QColor("#2563eb")
        done_color = QColor("#9ca3af")
        bold = QFont()
        bold.setBold(True)
        for col_offset in range(len(ITEM_STAGE_COLUMNS)):
            col = 3 + col_offset
            if col_offset < current_idx:
                cell = QTableWidgetItem("✓")
                cell.setForeground(QBrush(done_color))
            elif col_offset == current_idx:
                cell = QTableWidgetItem("●")
                cell.setForeground(QBrush(current_color))
                cell.setFont(bold)
            else:
                cell = QTableWidgetItem("")
            cell.setTextAlignment(Qt.AlignCenter)
            self._item_progress_table.setItem(row, col, cell)

    def _fetch_items_via_grpc(self) -> list[dict[str, Any]] | None:
        try:
            from app.management_client import ManagementClient
        except ImportError:
            return None
        client = None
        try:
            client = ManagementClient()
            items = client.list_items(limit=200)
        except Exception:  # noqa: BLE001
            return None
        finally:
            if client is not None:
                client.close()
        STAGE_INT_TO_LABEL = {
            1: "대기",
            2: "주탕",
            3: "탈형",
            4: "후처리",
            5: "후처리",
            6: "검사",
            7: "적재",
            8: "적재",
        }
        rows: list[dict[str, Any]] = []
        for it in items:
            rows.append(
                {
                    "order_id": it.order_id,
                    "product": "-",
                    "item": f"I-{it.id}",
                    "stage": STAGE_INT_TO_LABEL.get(int(it.cur_stage), "대기"),
                }
            )
        return rows

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------
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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("실시간 운영 모니터링")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ---- 상단: 발주 선택 + 자동 ptn_loc 표시 + 라인 투입 ----
        ctrl_box = QGroupBox("발주 운영 (패턴 자동 매핑 → 라인 투입)")
        grid = QGridLayout(ctrl_box)
        grid.setSpacing(8)

        grid.addWidget(QLabel("발주:"), 0, 0)
        self._ord_combo = QComboBox()
        self._ord_combo.setMinimumWidth(280)
        self._ord_combo.currentIndexChanged.connect(self._on_ord_selected)
        grid.addWidget(self._ord_combo, 0, 1)

        # 자동 매핑된 ptn_loc 표시 (입력 불가 — 라벨 only)
        grid.addWidget(QLabel("패턴 위치 (자동):"), 0, 2)
        self._ptn_loc_display = QLabel("—")
        self._ptn_loc_display.setObjectName("ptnLocDisplay")
        self._ptn_loc_display.setProperty("variant", "badge")
        self._ptn_loc_display.setMinimumWidth(60)
        self._ptn_loc_display.setAlignment(Qt.AlignCenter)
        grid.addWidget(self._ptn_loc_display, 0, 3)

        self._btn_start = QPushButton("▶ 라인 투입")
        self._btn_start.setProperty("variant", "primary")
        self._btn_start.setToolTip(
            "선택 발주 1건을 RA1/MM 라인에 즉시 투입 (Item + EquipTaskTxn 생성).\n"
            "스케줄 큐 등록은 [생산 계획] 페이지에서 먼저 진행하세요."
        )
        self._btn_start.clicked.connect(self._on_start_production)
        grid.addWidget(self._btn_start, 0, 4)
        self._btn_start.setEnabled(False)

        # 두 endpoint 차이 안내 (운영자 혼동 방지 — 2026-04-27)
        flow_hint = QLabel(
            "📋 운영 흐름: ① [생산 계획] 페이지에서 우선순위 계산·다건 큐 등록 → "
            "② 여기서 단건씩 라인 투입 (Item + MM task 생성)"
        )
        flow_hint.setProperty("tone", "muted")
        flow_hint.setWordWrap(True)
        grid.addWidget(flow_hint, 1, 0, 1, 5)

        self._status_label = QLabel("")
        self._status_label.setProperty("tone", "muted")
        self._status_label.setWordWrap(True)
        grid.addWidget(self._status_label, 2, 0, 1, 5)

        root.addWidget(ctrl_box)

        # ---- 본문: item 목록 + 검사 요약 ----
        body = QHBoxLayout()
        body.setSpacing(12)

        items_box = QGroupBox("선택 발주의 item 목록 + 필요 후처리")
        items_v = QVBoxLayout(items_box)
        self._items_table = QTableWidget(0, 6)
        self._items_table.setHorizontalHeaderLabels(
            ["item_id", "cur_stat", "res", "is_defective", "필요 후처리", "설비 단계 진행"]
        )
        self._items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._items_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._items_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._items_table.setMinimumHeight(220)
        items_v.addWidget(self._items_table)
        body.addWidget(items_box, 2)

        sum_box = QGroupBox("발주별 검사 요약 (양품 / 불량 / 미검사)")
        sum_v = QVBoxLayout(sum_box)
        self._summary_table = QTableWidget(0, 5)
        self._summary_table.setHorizontalHeaderLabels(["ord_id", "total", "GP", "DP", "미검사"])
        self._summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._summary_table.setMinimumHeight(220)
        sum_v.addWidget(self._summary_table)
        body.addWidget(sum_box, 1)

        root.addLayout(body)

        # ---- 공정 단계 (production.py 통합) ----
        stages_box = QGroupBox("공정 단계 (실시간)")
        stages_v = QVBoxLayout(stages_box)
        self._stages_table = QTableWidget(0, 3)
        self._stages_table.setHorizontalHeaderLabels(["단계", "상태", "담당 설비"])
        self._stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._stages_table.verticalHeader().setVisible(False)
        self._stages_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._stages_table.setAlternatingRowColors(True)
        self._stages_table.setMaximumHeight(220)
        stages_v.addWidget(self._stages_table)
        root.addWidget(stages_box)

        # ---- 주문별 제품 실시간 위치 (gRPC ListItems) ----
        item_pos_box = QGroupBox("주문별 제품 실시간 위치 (gRPC)")
        item_pos_v = QVBoxLayout(item_pos_box)
        item_columns = ["주문", "제품", "Item"] + ITEM_STAGE_COLUMNS
        self._item_progress_table = QTableWidget(0, len(item_columns))
        self._item_progress_table.setHorizontalHeaderLabels(item_columns)
        header = self._item_progress_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self._item_progress_table.verticalHeader().setVisible(False)
        self._item_progress_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._item_progress_table.setAlternatingRowColors(True)
        self._item_progress_table.setMaximumHeight(260)
        item_pos_v.addWidget(self._item_progress_table)
        root.addWidget(item_pos_box)

        # ---- 최근 24H mini-summary ----
        ts_box = QGroupBox("최근 24H 요약")
        ts_v = QHBoxLayout(ts_box)
        self._ts_hourly = QLabel("hourly 생산: -")
        ts_v.addWidget(self._ts_hourly, stretch=1)
        self._ts_err = QLabel("err_log trend: -")
        ts_v.addWidget(self._ts_err, stretch=1)
        self._ts_badge = QLabel("TS: -")
        self._ts_badge.setProperty("status", "muted")
        ts_v.addWidget(self._ts_badge, stretch=0)
        root.addWidget(ts_box)

        # ---- AMR 핸드오프 ACK ----
        handoff_box = QGroupBox("AMR 핸드오프 ACK (운영자 확인)")
        handoff_v = QHBoxLayout(handoff_box)
        handoff_info = QLabel(
            "후처리존(ToPP) 도착 AMR 이 WAIT_HANDOFF 로 정지하면 가장 오래된 1건을 풀어줍니다.\n"
            "(시퀀서가 활성(FMS_AUTOPLAY=1)일 때만 ToPP 가 자동으로 WAIT_HANDOFF 상태에 도달합니다.)"
        )
        handoff_info.setWordWrap(True)
        handoff_info.setProperty("tone", "muted")
        handoff_v.addWidget(handoff_info, stretch=2)
        self._btn_handoff = QPushButton("🔔 후처리 ACK 발행")
        self._btn_handoff.setProperty("variant", "danger")
        self._btn_handoff.clicked.connect(self._on_handoff_ack)
        handoff_v.addWidget(self._btn_handoff, stretch=0)
        self._handoff_result = QLabel("")
        self._handoff_result.setWordWrap(True)
        self._handoff_result.setProperty("tone", "ok")
        handoff_v.addWidget(self._handoff_result, stretch=2)
        root.addWidget(handoff_box)

        # 새로고침 버튼
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.refresh)
        root.addWidget(refresh_btn, alignment=Qt.AlignRight)

        root.addStretch(1)

    # ------------------------------------------------------------------
    # Refresh — 비동기 (QThread)
    # ------------------------------------------------------------------
    @pyqtSlot()
    def refresh(self) -> None:
        """페이지 전체 갱신 — HTTP 호출은 _RefreshWorker 스레드에서 수행."""
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return  # 이전 호출 진행 중이면 skip

        worker = _RefreshWorker(self._api)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.data_ready.connect(self._on_refresh_done)
        worker.data_ready.connect(lambda _: thread.quit())
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        self._refresh_thread = thread
        thread.start()

    @pyqtSlot(dict)
    def _on_refresh_done(self, data: dict) -> None:
        """_RefreshWorker 완료 후 GUI 스레드에서 UI 일괄 갱신."""
        orders = data.get("orders") or []
        patterns = data.get("patterns") or []
        summary = data.get("summary") or []
        stages = data.get("stages") or []
        item_progress = data.get("item_progress") or []
        ds = data.get("dashboard") or {}
        hourly = data.get("hourly") or []
        err_trend = data.get("err_trend") or []

        self._patterns = {int(p["ptn_id"]): int(p["ptn_loc"]) for p in patterns}

        # 발주 콤보 갱신
        self._ord_combo.blockSignals(True)
        self._ord_combo.clear()
        for o in orders:
            ord_id = o.get("ord_id")
            user_id = o.get("user_id")
            stat = o.get("latest_stat", "RCVD")
            label = f"ord_{ord_id}  (user={user_id}, {stat})"
            self._ord_combo.addItem(label, userData=ord_id)
        self._ord_combo.blockSignals(False)
        if self._ord_combo.count() > 0:
            self._ord_combo.setCurrentIndex(0)
            self._on_ord_selected()

        # 검사 요약
        self._summary_table.setRowCount(len(summary))
        for row, s in enumerate(summary):
            cells = [
                str(s.get("ord_id", "")),
                str(s.get("total_items", 0)),
                str(s.get("good_count", 0)),
                str(s.get("defective_count", 0)),
                str(s.get("pending_count", 0)),
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._summary_table.setItem(row, col, item)

        # 공정 단계
        self._stages_table.setRowCount(len(stages))
        for row, stage in enumerate(stages):
            self._stages_table.setItem(row, 0, QTableWidgetItem(str(stage.get("name", ""))))
            status_item = QTableWidgetItem(str(stage.get("status", "")))
            status_item.setTextAlignment(Qt.AlignCenter)
            self._stages_table.setItem(row, 1, status_item)
            self._stages_table.setItem(row, 2, QTableWidgetItem(str(stage.get("equipment", ""))))

        # 주문별 제품 실시간 위치 (gRPC 우선 → HTTP fallback)
        grpc_rows = self._fetch_items_via_grpc()
        self._render_item_progress(grpc_rows or item_progress)

        # 시계열 mini-summary
        try:
            from app.widgets.ui._helpers import set_property as _sp
            ts_enabled = ds.get("timescaledb_enabled", False)
            self._ts_badge.setText(
                "TimescaleDB: ON" if ts_enabled else "TimescaleDB: OFF (date_trunc 폴백)"
            )
            _sp(self._ts_badge, "status", "ok" if ts_enabled else "muted")
        except Exception:  # noqa: BLE001
            self._ts_badge.setText("TS: ?")

        total_h = sum(int(h.get("produced", 0)) for h in hourly)
        peak = max((int(h.get("produced", 0)) for h in hourly), default=0)
        self._ts_hourly.setText(
            f"hourly 생산 (24h): 합계 {total_h} 개 / 시간대 {len(hourly)}개 / 피크 {peak} 개"
        )

        equip_total = sum(int(t.get("count", 0)) for t in err_trend if t.get("source") == "equip")
        trans_total = sum(int(t.get("count", 0)) for t in err_trend if t.get("source") == "trans")
        self._ts_err.setText(f"err_log (24h): equip {equip_total} 건 / trans {trans_total} 건")

    def _render_item_progress(self, rows: list[dict[str, Any]]) -> None:
        """item 진행 현황 테이블 렌더 (데이터 조회 없음, rows 만 받아 표시)."""
        rows = sorted(rows, key=lambda r: (str(r.get("order_id", "")), str(r.get("item", ""))))
        self._item_progress_table.setRowCount(len(rows))
        current_color = QColor("#2563eb")
        done_color = QColor("#9ca3af")
        bold = QFont()
        bold.setBold(True)

        for row, info in enumerate(rows):
            order_id = str(info.get("order_id", ""))
            product = str(info.get("product", ""))
            item_id = str(info.get("item", ""))
            stage = str(info.get("stage", "대기"))

            self._item_progress_table.setItem(row, 0, QTableWidgetItem(order_id))
            self._item_progress_table.setItem(row, 1, QTableWidgetItem(product))
            item_cell = QTableWidgetItem(item_id)
            item_cell.setFont(bold)
            item_cell.setTextAlignment(Qt.AlignCenter)
            self._item_progress_table.setItem(row, 2, item_cell)

            current_idx = ITEM_STAGE_COLUMNS.index(stage) if stage in ITEM_STAGE_COLUMNS else 0
            for col_offset in range(len(ITEM_STAGE_COLUMNS)):
                col = 3 + col_offset
                if col_offset < current_idx:
                    cell = QTableWidgetItem("✓")
                    cell.setForeground(QBrush(done_color))
                elif col_offset == current_idx:
                    cell = QTableWidgetItem("●")
                    cell.setForeground(QBrush(current_color))
                    cell.setFont(bold)
                else:
                    cell = QTableWidgetItem("")
                cell.setTextAlignment(Qt.AlignCenter)
                self._item_progress_table.setItem(row, col, cell)

    # ------------------------------------------------------------------
    # 발주 선택 — 비동기 (QThread)
    # ------------------------------------------------------------------
    def _current_ord_id(self) -> int | None:
        idx = self._ord_combo.currentIndex()
        if idx < 0:
            return None
        ord_id = self._ord_combo.itemData(idx)
        return int(ord_id) if ord_id is not None else None

    @pyqtSlot()
    def _on_ord_selected(self) -> None:
        """발주 콤보 변경 시 ptn_loc 즉시 표시, item 목록은 비동기 조회."""
        ord_id = self._current_ord_id()
        if ord_id is None:
            return

        # ptn_loc 는 캐시(_patterns)에 있으므로 동기 OK
        registered = ord_id in self._patterns
        loc_label_map = {1: "1 (원형)", 2: "2 (사각)", 3: "3 (타원형)"}
        try:
            from app.widgets.ui._helpers import set_property as _sp
            if registered:
                loc = self._patterns[ord_id]
                self._ptn_loc_display.setText(loc_label_map.get(loc, str(loc)))
                _sp(self._ptn_loc_display, "tone", "ok")
                self._btn_start.setEnabled(True)
                self._status_label.setText(
                    f"발주 {ord_id}: 패턴 위치 {loc} 자동 등록됨 → 라인 투입 가능. (item 목록 로딩 중…)"
                )
            else:
                self._ptn_loc_display.setText("미등록")
                _sp(self._ptn_loc_display, "tone", "warn")
                self._btn_start.setEnabled(False)
                self._status_label.setText(
                    f"발주 {ord_id}: Pattern 자동 등록 실패. product_id prefix(R/S/O) 인식 안 됨."
                )
        except Exception:  # noqa: BLE001
            pass

        # item 목록 + PP + equip_task → 비동기
        if self._ord_thread is not None and self._ord_thread.isRunning():
            # 이전 요청이 진행 중이면 중단 후 재시작
            self._ord_thread.quit()

        worker = _OrdItemsWorker(self._api, ord_id)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.data_ready.connect(self._on_ord_items_done)
        worker.data_ready.connect(lambda *_: thread.quit())
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        self._ord_thread = thread
        thread.start()

    @pyqtSlot(int, list)
    def _on_ord_items_done(self, ord_id: int, enriched: list) -> None:
        """_OrdItemsWorker 완료 후 GUI 스레드에서 items 테이블 갱신."""
        # 도중에 다른 발주를 선택했으면 버림
        if self._current_ord_id() != ord_id:
            return

        self._items_table.setRowCount(len(enriched))
        for row, entry in enumerate(enriched):
            it = entry["item"]
            item_id = entry["item_id"]
            pp_data = entry["pp_data"]
            active_txn = entry["active_txn"]

            pp_label = self._format_pp_from_data(pp_data)
            cells = [
                str(item_id),
                str(it.get("cur_stat", "")),
                str(it.get("cur_res", "") or ""),
                self._format_defective(it.get("is_defective")),
                pp_label,
            ]
            for col, val in enumerate(cells):
                qi = QTableWidgetItem(val)
                qi.setTextAlignment(Qt.AlignCenter)
                self._items_table.setItem(row, col, qi)

            txn_id_raw = active_txn.get("txn_id") if active_txn else None
            if active_txn and txn_id_raw is not None:
                btn = QPushButton(f"▶ {active_txn.get('task_type', '?')} 진행")
                btn.setToolTip(
                    f"txn_id={txn_id_raw} task_type={active_txn.get('task_type')} "
                    f"stat={active_txn.get('txn_stat')}"
                )
                try:
                    txn_id = int(txn_id_raw)
                except (TypeError, ValueError):
                    btn = QPushButton("— 진행 가능 작업 없음 —")
                    btn.setEnabled(False)
                else:
                    btn.clicked.connect(lambda _checked, t=txn_id: self._advance_equip(t))
            else:
                btn = QPushButton("— 진행 가능 작업 없음 —")
                btn.setEnabled(False)
            self._items_table.setCellWidget(row, 5, btn)

        if self._status_label.text().endswith("(item 목록 로딩 중…)"):
            # 로딩 완료 메시지로 교체
            self._status_label.setText(
                self._status_label.text().replace(" (item 목록 로딩 중…)", "")
            )

    # ------------------------------------------------------------------
    # 헬퍼
    # ------------------------------------------------------------------
    def _format_defective(self, value: Any) -> str:
        if value is None:
            return "미검사"
        return "불량 (DP)" if value else "양품 (GP)"

    def _format_pp_from_data(self, pp_data: dict | None) -> str:
        """이미 조회된 pp_data dict 를 포맷. API 호출 없음."""
        if not pp_data:
            return "-"
        opts = pp_data.get("pp_options", [])
        statuses = {t.get("pp_nm"): t.get("txn_stat") for t in pp_data.get("pp_task_status", [])}
        if not opts:
            return "후처리 없음"
        return ", ".join(f"{o['pp_nm']}[{statuses.get(o['pp_nm'], 'QUE')}]" for o in opts)

    def _advance_equip(self, txn_id: int) -> None:
        try:
            rsp = self._api.advance_equip_task(txn_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Advance 실패", f"txn_id={txn_id}\n{exc}")
            return

        prev = rsp.get("prev_stat")
        nxt = rsp.get("new_stat")
        stat = rsp.get("txn_stat")
        item_stat = rsp.get("item_cur_stat")
        auto = rsp.get("auto") or {}

        msg = f"txn_id={txn_id}\n  {prev} → {nxt}  (txn_stat={stat})\n  item.cur_stat = {item_stat}"
        if auto.get("next_equip_txn_id"):
            msg += f"\n\n✅ 자동 생성: equip_task_txn={auto['next_equip_txn_id']}"
        if auto.get("next_trans_txn_id"):
            msg += (
                f"\n\n✅ 자동 생성: trans_task_txn={auto['next_trans_txn_id']} "
                f"AMR={auto.get('amr_id')}\n"
                "→ PP 워커 페이지에서 핸드오프 푸시버튼을 눌러 진행하세요."
            )

        QMessageBox.information(self, "Advance 완료", msg)
        self._on_ord_selected()

    @pyqtSlot()
    def _on_start_production(self) -> None:
        """단건 라인 투입 — Item + EquipTaskTxn 즉시 생성 (RA1/MM QUE).

        2026-04-27: '생산 시작' → '라인 투입' 으로 변경.
        큐 등록은 [생산 계획] 페이지에서 별도 진행.
        """
        ord_id = self._current_ord_id()
        if ord_id is None:
            return
        try:
            result = self._api.start_production_one(ord_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "라인 투입 실패", str(exc))
            return
        msg = (result or {}).get("message", "Started.")
        QMessageBox.information(self, "라인 투입 완료", f"발주 {ord_id}\n{msg}")
        self.refresh()

    @pyqtSlot()
    def _on_handoff_ack(self) -> None:
        try:
            data = self._api.post_handoff_ack() or {}
        except Exception as exc:  # noqa: BLE001
            from app.widgets.ui._helpers import set_property as _sp

            _sp(self._handoff_result, "tone", "danger")
            self._handoff_result.setText(f"❌ 호출 실패: {exc}")
            return
        from app.widgets.ui._helpers import set_property as _sp

        if data.get("released"):
            _sp(self._handoff_result, "tone", "ok")
            self._handoff_result.setText(
                f"✓ release: task={data.get('task_id')} amr={data.get('amr_id')} "
                f"item={data.get('item_id')} ord={data.get('ord_id')}"
            )
        else:
            _sp(self._handoff_result, "tone", "warn")
            self._handoff_result.setText(
                f"⚠ orphan: {data.get('reason', '대기 중인 핸드오프 없음')}"
            )

    # ------------------------------------------------------------------
    # WS message hook (production.py 통합)
    # ------------------------------------------------------------------
    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("type", "")
        if msg_type in (
            "production_update",
            "equipment_update",
            "process_stage_update",
            "order_update",
        ):
            self.refresh()
