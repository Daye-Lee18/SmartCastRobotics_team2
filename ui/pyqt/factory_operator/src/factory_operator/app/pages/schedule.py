"""생산 계획 페이지 — 우선순위 계산 + 순서 확정.

웹의 "생산 승인" 버튼으로 주문이 in_production 상태로 전환되면
ProductionJob 레코드가 생성되어 이 페이지의 풀에 들어온다.

워크플로:
    1. 승인 주문 풀(approved + in_production) 조회
    2. 다중 선택 → "우선순위 계산" 버튼
    3. 7요소 가중 점수 결과 표시 (상단 테이블)
    4. (향후) 수동 순서 조정 + 사유 입력 + PriorityLog 기록
    5. (향후) 생산 개시 확정 → 자원 배정

@MX:NOTE: 2026-04-08 웹에서 이관된 기능. 기존 src/app/production/schedule 페이지 삭제.
@MX:NOTE: 2026-04-26 디자인 시스템 v2 마이그레이션 — 인라인 setStyleSheet 제거,
          objectName/setProperty(variant|tone) 기반 글로벌 QSS 룰로 전환.
"""

from __future__ import annotations

from typing import Any

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.pages.dashboard import KpiCard

# ---------- 표시용 상수 ----------

STATUS_LABEL = {
    "approved": "승인 대기",
    "in_production": "생산 승인",
}

STATUS_COLOR = {
    "approved": "#fef3c7",  # amber 100 (셀 배경 — 토큰화 대상은 아님: 셀별 의미 색)
    "in_production": "#dbeafe",  # blue 100
}

DELAY_RISK_LABEL = {
    "high": "높음",
    "medium": "보통",
    "low": "낮음",
}

DELAY_RISK_COLOR = {
    "high": "#ef4444",
    "medium": "#f59e0b",
    "low": "#10b981",
}


def _format_currency(value: Any) -> str:
    try:
        num = float(value or 0)
    except (TypeError, ValueError):
        return "-"
    return f"₩{int(num):,}"


def _format_date(value: str | None) -> str:
    if not value:
        return "-"
    return value[:10]


# ---------- 페이지 본체 ----------


class SchedulePage(QWidget):
    """생산 계획 — 우선순위 계산 UI."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._kpi_cards: dict[str, KpiCard] = {}
        self._orders: list[dict[str, Any]] = []
        self._priority_results: list[dict[str, Any]] = []
        self._calculation_count: int = 0

        self._build_ui()
        self.refresh()

    # ================================================================
    # UI 구성
    # ================================================================

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # 페이지 제목
        title = QLabel("생산 계획 — 우선순위 계산")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "웹에서 '생산 승인'된 주문의 우선순위를 7요소 가중 점수제(100점 만점)로 계산합니다. "
            "좌측에서 주문을 선택하고 '우선순위 계산' 버튼을 누르세요."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)

        # KPI 카드 (3개)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        kpi_items = [
            ("approved_count", "승인 대기", "건"),
            ("in_production_count", "생산 승인", "건"),
            ("calc_count", "금일 계산", "회"),
        ]
        for key, label, unit in kpi_items:
            card = KpiCard(label, unit=unit)
            self._kpi_cards[key] = card
            kpi_row.addWidget(card, stretch=1)
        root.addLayout(kpi_row)

        # 주문 풀 + 결과 2열 레이아웃
        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        left_panel = self._build_orders_panel()
        split_layout.addWidget(left_panel, stretch=1)

        right_panel = self._build_results_panel()
        split_layout.addWidget(right_panel, stretch=1)

        root.addLayout(split_layout, stretch=1)

        # 하단 액션 버튼
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addStretch()

        self._refresh_btn = QPushButton("↻ 새로고침")
        self._refresh_btn.setMinimumHeight(42)
        self._refresh_btn.clicked.connect(self.refresh)
        self._refresh_btn.setProperty("variant", "secondary")
        action_row.addWidget(self._refresh_btn)

        root.addLayout(action_row)

    def _build_orders_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("cardSection")  # 글로벌 QSS 가 카드 룰 적용

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QLabel("📋 승인 주문 풀")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        hint = QLabel("Ctrl/Shift 다중 선택 · 계산할 주문을 체크하세요")
        hint.setProperty("tone", "muted")
        layout.addWidget(hint)

        self._orders_table = QTableWidget(0, 5)
        self._orders_table.setHorizontalHeaderLabels(["주문 ID", "회사명", "납기", "금액", "상태"])
        self._orders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._orders_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self._orders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._orders_table.verticalHeader().setVisible(False)
        self._orders_table.setAlternatingRowColors(True)
        # 스타일은 글로벌 QSS 가 처리

        header_view = self._orders_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self._orders_table.setMinimumHeight(280)
        layout.addWidget(self._orders_table, stretch=1)

        self._orders_count_lbl = QLabel("총 0건")
        self._orders_count_lbl.setProperty("tone", "muted")
        layout.addWidget(self._orders_count_lbl)

        # 승인 주문 풀 바로 아래 액션 버튼 (계산 + 선택 해제)
        pool_actions = QHBoxLayout()
        pool_actions.setSpacing(8)

        self._calc_btn = QPushButton("⚙ 우선순위 계산")
        self._calc_btn.setObjectName("primaryButton")
        self._calc_btn.setMinimumHeight(38)
        self._calc_btn.clicked.connect(self._on_calculate)
        # 기본 primary 룰 사용 — variant 미설정
        pool_actions.addWidget(self._calc_btn, stretch=2)

        self._clear_btn = QPushButton("선택 해제")
        self._clear_btn.setMinimumHeight(38)
        self._clear_btn.clicked.connect(self._on_clear_selection)
        self._clear_btn.setProperty("variant", "secondary")
        pool_actions.addWidget(self._clear_btn, stretch=1)

        layout.addLayout(pool_actions)

        return panel

    def _build_results_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("cardSection")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QLabel("🏆 우선순위 계산 결과")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        hint = QLabel(
            "7요소 가중 점수 (납기 25 · 착수 20 · 체류 15 · 지연 15 · 고객 10 · 수량 10 · 세팅 5)"
        )
        hint.setWordWrap(True)
        hint.setProperty("tone", "muted")
        layout.addWidget(hint)

        self._results_table = QTableWidget(0, 6)
        self._results_table.setHorizontalHeaderLabels(
            ["순위", "주문 ID", "회사명", "총점", "지연위험", "착수"]
        )
        self._results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._results_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self._results_table.verticalHeader().setVisible(False)
        self._results_table.setAlternatingRowColors(True)
        # 스타일은 글로벌 QSS 가 처리

        header_view = self._results_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self._results_table.itemSelectionChanged.connect(self._on_result_selected)
        self._results_table.setMinimumHeight(280)
        layout.addWidget(self._results_table, stretch=1)

        # 선택된 결과의 상세 (추천 사유 등)
        self._reason_label = QLabel("결과 행을 선택하면 추천 사유가 표시됩니다.")
        self._reason_label.setObjectName("reasonBox")
        self._reason_label.setWordWrap(True)
        self._reason_label.setMinimumHeight(60)
        layout.addWidget(self._reason_label)

        # 결과 테이블 바로 아래: 선택 주문 일괄 큐 등록 버튼 (큰 success)
        # 2026-04-27 라벨 명확화 — '생산 시작' → '생산 큐 등록' (ord_stat MFG transition).
        # 실제 라인 투입(Item + EquipTaskTxn 생성)은 [실시간 운영 모니터링] 페이지의
        # '라인 투입' 버튼이 별도로 호출.
        self._start_selected_btn = QPushButton("▶  선택 주문 생산 큐 등록  ▶")
        self._start_selected_btn.setMinimumHeight(50)
        self._start_selected_btn.setCursor(Qt.PointingHandCursor)
        self._start_selected_btn.setToolTip(
            "선택 주문(들)을 MFG 큐에 등록합니다 (ord_stat APPR→MFG transition).\n"
            "이 단계는 큐 등록만 하며, 실제 공정 라인 투입은 [실시간 운영 모니터링] 페이지의 '라인 투입' 버튼에서 진행."
        )
        self._start_selected_btn.clicked.connect(self._on_start_selected)
        self._start_selected_btn.setProperty("variant", "success")
        self._start_selected_btn.setProperty("size", "lg")
        layout.addWidget(self._start_selected_btn)

        # 두 endpoint 차이 안내 (운영자 혼동 방지)
        flow_hint = QLabel(
            "📋 운영 흐름: ① 여기서 우선순위 계산·다건 큐 등록 → "
            "② [실시간 운영 모니터링] 페이지에서 단건씩 라인 투입 (Item + MM task 생성)"
        )
        flow_hint.setProperty("tone", "muted")
        flow_hint.setWordWrap(True)
        layout.addWidget(flow_hint)

        return panel

    # ================================================================
    # 데이터 로드 / 렌더
    # ================================================================

    def refresh(self) -> None:
        self._orders = self._api.get_approved_and_running_orders()
        if not self._orders:
            self._orders = self._orders_from_schedule_jobs(self._api.get_production_jobs())
        self._render_orders_table()
        self._update_kpis()

    @staticmethod
    def _orders_from_schedule_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback projection for the production schedule queue endpoint."""
        orders: list[dict[str, Any]] = []
        for job in jobs:
            order_id = job.get("order_id") or str(job.get("id", "")).replace("PJ-ORD-", "")
            if not order_id:
                continue
            orders.append(
                {
                    "id": str(order_id),
                    "company_name": "-",
                    "customer_name": "-",
                    "total_amount": 0,
                    "requested_delivery": job.get("estimated_completion") or "",
                    "confirmed_delivery": job.get("estimated_completion") or "",
                    "created_at": job.get("created_at") or "",
                    "status": "in_production" if job.get("started_at") else "approved",
                }
            )
        return orders

    def _render_orders_table(self) -> None:
        selected_ids: set[str] = set()
        for item in self._orders_table.selectedItems():
            id_cell = self._orders_table.item(item.row(), 0)
            if id_cell:
                selected_ids.add(id_cell.text())

        self._orders_table.setRowCount(0)
        for idx, order in enumerate(self._orders):
            self._orders_table.insertRow(idx)

            id_item = QTableWidgetItem(str(order.get("id", "")))
            id_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._orders_table.setItem(idx, 0, id_item)

            self._orders_table.setItem(
                idx, 1, QTableWidgetItem(str(order.get("company_name", "-")))
            )

            due_item = QTableWidgetItem(_format_date(order.get("requested_delivery")))
            due_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._orders_table.setItem(idx, 2, due_item)

            amount_item = QTableWidgetItem(_format_currency(order.get("total_amount")))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._orders_table.setItem(idx, 3, amount_item)

            status = str(order.get("status", ""))
            label = STATUS_LABEL.get(status, status)
            status_item = QTableWidgetItem(label)
            status_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            color = STATUS_COLOR.get(status, "#f3f4f6")
            status_item.setBackground(QColor(color))
            self._orders_table.setItem(idx, 4, status_item)

        self._orders_count_lbl.setText(f"총 {len(self._orders)}건")

        if selected_ids:
            for row in range(self._orders_table.rowCount()):
                id_cell = self._orders_table.item(row, 0)
                if id_cell and id_cell.text() in selected_ids:
                    self._orders_table.selectRow(row)

    def _update_kpis(self) -> None:
        approved = sum(1 for o in self._orders if o.get("status") == "approved")
        in_prod = sum(1 for o in self._orders if o.get("status") == "in_production")
        self._kpi_cards["approved_count"].update_value(approved)
        self._kpi_cards["in_production_count"].update_value(in_prod)
        self._kpi_cards["calc_count"].update_value(self._calculation_count)

    # ================================================================
    # 액션: 우선순위 계산
    # ================================================================

    def _get_selected_order_ids(self) -> list[str]:
        selected_rows: set[int] = set()
        for item in self._orders_table.selectedItems():
            selected_rows.add(item.row())

        ids: list[str] = []
        for row in sorted(selected_rows):
            id_item = self._orders_table.item(row, 0)
            if id_item and id_item.text():
                ids.append(id_item.text())
        return ids

    def _on_calculate(self) -> None:
        order_ids = self._get_selected_order_ids()
        if not order_ids:
            QMessageBox.information(
                self,
                "주문 선택 필요",
                "우선순위를 계산할 주문을 좌측 풀에서 1건 이상 선택하세요.\n(Ctrl/Shift 다중 선택)",
            )
            return

        try:
            self._calc_btn.setEnabled(False)
            self._calc_btn.setText("⏳ 계산 중...")
            response = self._api.calculate_priority(order_ids)
        except requests.RequestException as exc:
            QMessageBox.critical(
                self,
                "우선순위 계산 실패",
                f"백엔드 API 호출 실패:\n{exc}\n\n백엔드 서버가 실행 중인지 확인하세요.",
            )
            return
        finally:
            self._calc_btn.setEnabled(True)
            self._calc_btn.setText("⚙ 우선순위 계산")

        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            QMessageBox.warning(
                self,
                "계산 결과 없음",
                "백엔드가 빈 결과를 반환했습니다. 선택한 주문이 'approved' 상태인지 확인하세요.",
            )
            return

        self._priority_results = results
        self._calculation_count += 1
        self._render_results_table()
        self._update_kpis()

    def _render_results_table(self) -> None:
        self._results_table.setRowCount(0)
        self._reason_label.setText("결과 행을 선택하면 추천 사유가 표시됩니다.")

        sorted_results = sorted(
            self._priority_results,
            key=lambda r: (r.get("rank", 999), -float(r.get("total_score", 0))),
        )

        for idx, result in enumerate(sorted_results):
            self._results_table.insertRow(idx)

            rank_item = QTableWidgetItem(f"#{result.get('rank', idx + 1)}")
            rank_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if idx == 0:
                rank_item.setBackground(QColor("#fef3c7"))
                rank_item.setForeground(QColor("#92400e"))
            self._results_table.setItem(idx, 0, rank_item)

            id_item = QTableWidgetItem(str(result.get("order_id", "-")))
            id_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._results_table.setItem(idx, 1, id_item)

            self._results_table.setItem(
                idx, 2, QTableWidgetItem(str(result.get("company_name", "-")))
            )

            score = result.get("total_score", 0)
            score_item = QTableWidgetItem(f"{score:.1f} / 100")
            score_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self._results_table.setItem(idx, 3, score_item)

            delay = str(result.get("delay_risk", "low"))
            delay_item = QTableWidgetItem(DELAY_RISK_LABEL.get(delay, delay))
            delay_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            delay_item.setForeground(QColor(DELAY_RISK_COLOR.get(delay, "#9ca3af")))
            self._results_table.setItem(idx, 4, delay_item)

            # 착수 컬럼: 큐 등록 버튼 (행별 단건)
            ready = str(result.get("ready_status", ""))
            order_id = str(result.get("order_id", ""))
            start_btn = QPushButton("▶ 큐 등록")
            start_btn.setEnabled(ready == "ready")
            start_btn.setCursor(Qt.PointingHandCursor)
            start_btn.setProperty("size", "sm")
            if ready == "ready":
                start_btn.setToolTip(f"주문 {order_id} 생산을 즉시 개시")
                start_btn.setProperty("variant", "success")
            else:
                blocking = ", ".join(result.get("blocking_reasons", [])) or "착수 제약"
                start_btn.setToolTip(f"착수 불가: {blocking}")
                # disabled 룰이 자동으로 회색 처리
            start_btn.clicked.connect(
                lambda _checked=False, oid=order_id: self._on_start_single(oid)
            )
            self._results_table.setCellWidget(idx, 5, start_btn)

    def _on_result_selected(self) -> None:
        rows = self._results_table.selectionModel().selectedRows()
        if not rows:
            return
        row_idx = rows[0].row()
        if row_idx >= len(self._priority_results):
            return

        sorted_results = sorted(
            self._priority_results,
            key=lambda r: (r.get("rank", 999), -float(r.get("total_score", 0))),
        )
        result = sorted_results[row_idx]

        reason = result.get("recommendation_reason", "추천 사유 없음")
        blocking = result.get("blocking_reasons", [])
        factors = result.get("factors", [])

        parts: list[str] = [f"📌 추천 사유: {reason}"]
        if factors:
            factor_texts = [
                f"{f.get('name', '-')} {f.get('score', 0):.1f}/{f.get('max_score', 0)}"
                for f in factors
            ]
            parts.append("• 세부 점수: " + " · ".join(factor_texts))
        if blocking:
            parts.append("⚠ 착수 제약: " + ", ".join(blocking))

        self._reason_label.setText("\n".join(parts))

    def _on_clear_selection(self) -> None:
        self._orders_table.clearSelection()

    # ================================================================
    # 액션: 생산 개시
    # ================================================================

    def _on_start_single(self, order_id: str) -> None:
        if not order_id:
            return
        confirm = QMessageBox.question(
            self,
            "생산 개시 확인",
            f"주문 {order_id} 의 생산을 개시합니다.\n"
            "ProductionJob 이 생성되고 주문 상태가 'in_production' 으로 전환됩니다.\n\n"
            "계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm == QMessageBox.Yes:
            self._do_start([order_id])

    def _on_start_selected(self) -> None:
        rows = self._results_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self,
                "선택 필요",
                "우선순위 결과 테이블에서 시작할 주문을 1건 이상 선택하세요.\n"
                "(Ctrl/Shift 로 다중 선택)",
            )
            return

        sorted_results = sorted(
            self._priority_results,
            key=lambda r: (r.get("rank", 999), -float(r.get("total_score", 0))),
        )

        order_ids: list[str] = []
        blocked: list[str] = []
        for idx_model in rows:
            row = idx_model.row()
            if row >= len(sorted_results):
                continue
            r = sorted_results[row]
            oid = str(r.get("order_id", ""))
            if r.get("ready_status") == "ready":
                order_ids.append(oid)
            else:
                blocked.append(oid)

        if not order_ids:
            QMessageBox.warning(
                self,
                "착수 불가",
                "선택된 주문 모두 착수 제약에 걸려 있습니다.\n"
                "'✗ 불가' 상태 주문은 제외하고 다시 선택하세요.",
            )
            return

        msg = f"선택된 {len(order_ids)}건의 주문 생산을 개시합니다.\n\n"
        msg += "\n".join(f"  • {oid}" for oid in order_ids)
        if blocked:
            msg += f"\n\n⚠ 착수 불가로 제외된 주문: {', '.join(blocked)}"
        msg += "\n\n계속하시겠습니까?"

        confirm = QMessageBox.question(
            self,
            "다중 생산 개시 확인",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm == QMessageBox.Yes:
            self._do_start(order_ids)

    def _do_start(self, order_ids: list[str]) -> None:
        try:
            from app.workers.start_production_worker import (
                StartProductionThread,
                StartProductionWorker,
            )
        except ImportError as exc:
            QMessageBox.critical(
                self,
                "워커 모듈 로드 실패",
                f"start_production_worker 임포트 실패:\n{exc}",
            )
            return

        if getattr(self, "_start_thread_active", False):
            return
        self._start_thread_active = True
        self._start_selected_btn.setEnabled(False)
        self._start_selected_btn.setText("⏳ 큐 등록 중...")

        worker = StartProductionWorker(order_ids)
        worker.succeeded.connect(self._on_start_succeeded)
        worker.failed.connect(self._on_start_failed)
        worker.finished.connect(self._on_start_finished)

        self._start_thread = StartProductionThread(worker)
        self._start_thread.start()

    def _on_start_succeeded(self, order_acks: list) -> None:
        if not order_acks:
            QMessageBox.warning(
                self,
                "작업 생성 결과 없음",
                "Management Service 가 빈 결과를 반환했습니다.\n"
                "선택한 주문이 승인 대상이 아니거나 모두 반려되었을 수 있습니다.",
            )
            return

        accepted = [ack for ack in order_acks if getattr(ack, "accepted", False)]
        rejected = [ack for ack in order_acks if not getattr(ack, "accepted", False)]

        lines = []
        for ack in accepted:
            lines.append(
                f"  • 주문 {ack.ord_id} 승인"
                f" (item={ack.item_id or '-'}, txn={ack.equip_task_txn_id or '-'})"
            )
        for ack in rejected:
            ord_label = ack.ord_id if ack.ord_id else "?"
            lines.append(
                f"  • 주문 {ord_label} 반려"
                f" ({ack.reason or 'rejected'})"
            )

        QMessageBox.information(
            self,
            "작업 생성 완료",
            f"요청 {len(order_acks)}건 중 승인 {len(accepted)}건, 반려 {len(rejected)}건.\n\n"
            + "\n".join(lines)
            + "\n\n다음 단계: 백그라운드 오케스트레이터가 후속 흐름을 이어갑니다.",
        )
        self.refresh()

    def _on_start_failed(self, kind: str, message: str) -> None:
        title_map = {
            "value": "입력 오류",
            "grpc": "생산 개시 실패 (gRPC)",
            "import": "모듈 로드 실패",
            "other": "생산 개시 실패",
        }
        body_extra = ""
        if kind == "grpc":
            body_extra = "\n\nManagement Service(:50051) 가 실행 중인지 확인하세요."
        QMessageBox.critical(self, title_map.get(kind, "오류"), message + body_extra)

    def _on_start_finished(self) -> None:
        self._start_thread_active = False
        self._start_selected_btn.setEnabled(True)
        self._start_selected_btn.setText("▶  선택 주문 생산 큐 등록  ▶")
        self._priority_results = []
        self._render_results_table()

    # ================================================================
    # WebSocket / MQTT 브로드캐스트 (선택적)
    # ================================================================

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("type", "")).lower() if payload else ""
        if event_type in ("order_update", "order_status_changed", "production_approved"):
            self.refresh()
