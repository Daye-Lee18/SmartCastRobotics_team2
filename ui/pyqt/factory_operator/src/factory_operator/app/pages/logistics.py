"""물류/이송 모니터링 페이지 v0.4.

구성:
  1. AMR 상태 카드 (3대, 배터리 바 포함)
  2. 이송 작업 큐 (우선순위 배지)
  3. 출고 지시 테이블
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

from app.api_client import ApiClient
from app.pages.dashboard import KpiCard
from app.widgets.amr_card import AmrStatusCard

PRIORITY_STYLE = {
    "urgent": ("#fee2e2", "#991b1b", "#ef4444", "긴급"),
    "high": ("#fed7aa", "#9a3412", "#f97316", "높음"),
    "normal": ("#fef3c7", "#854d0e", "#f59e0b", "보통"),
    "low": ("#f3f4f6", "#374151", "#9ca3af", "낮음"),
}

STATUS_TEXT = {
    "running": "진행 중",
    "pending": "대기",
    "completed": "완료",
    "failed": "실패",
}


class LogisticsPage(QWidget):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._amr_cards: dict[str, AmrStatusCard] = {}
        self._kpi_cards: dict[str, KpiCard] = {}
        self._amr_live: list[dict[str, Any]] | None = None  # 실시간 데이터 수신 시 mock 대체
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("물류 / 이송")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # KPI 4개 카드 (물류 요약)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        kpi_items = [
            ("active_tasks", "진행 중 작업", "건"),
            ("pending_tasks", "대기 작업", "건"),
            ("completed_tasks", "완료 작업", "건"),
            ("idle_amr", "대기 중 AMR", "대"),
        ]
        for key, label, unit in kpi_items:
            card = KpiCard(label, unit=unit)
            self._kpi_cards[key] = card
            kpi_row.addWidget(card, stretch=1)
        layout.addLayout(kpi_row)

        # 1) AMR 카드 (최대 3대 가로 배치)
        amr_label = QLabel("AMR 현황")
        amr_label.setObjectName("sectionTitle")
        layout.addWidget(amr_label)

        self._amr_row = QHBoxLayout()
        self._amr_row.setSpacing(14)

        amr_container = QWidget()
        amr_container.setLayout(self._amr_row)
        amr_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(amr_container)

        # 2) 중단: 이송 작업 큐
        task_card = QFrame()
        task_card.setObjectName("tableCard")
        task_card.setFrameShape(QFrame.StyledPanel)
        task_layout = QVBoxLayout(task_card)
        task_layout.setContentsMargins(12, 10, 12, 12)
        task_layout.setSpacing(8)

        task_title = QLabel("이송 작업 큐")
        task_title.setObjectName("sectionTitle")
        task_layout.addWidget(task_title)

        self._task_table = QTableWidget(0, 6)
        self._task_table.setHorizontalHeaderLabels(
            ["우선순위", "작업 ID", "경로", "화물", "담당 AMR", "상태"]
        )
        self._task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._task_table.verticalHeader().setVisible(False)
        self._task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        task_layout.addWidget(self._task_table)
        layout.addWidget(task_card, stretch=1)

        # 3) 하단: 출고 지시 테이블
        outbound_label = QLabel("출고 지시")
        outbound_label.setObjectName("sectionTitle")
        layout.addWidget(outbound_label)

        self._outbound_table = QTableWidget(0, 6)
        self._outbound_table.setHorizontalHeaderLabels(
            ["주문 ID", "제품", "수량", "납품처", "정책", "상태"]
        )
        self._outbound_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._outbound_table.verticalHeader().setVisible(False)
        self._outbound_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._outbound_table.setMaximumHeight(200)
        layout.addWidget(self._outbound_table)

    def refresh(self) -> None:
        # AMR: 실시간 데이터가 있으면 그것을 사용, 없으면 API/mock 폴백
        # CASTING_DATA_MODE=normal 모드에서도 빈 응답이면 mock_data 사용 (UI 데모 보장)
        amrs = self._amr_live if self._amr_live is not None else (self._api.get_amr_status() or [])
        if not amrs:
            from app import mock_data

            amrs = mock_data.AMR_STATUS
        self._update_amr_cards(amrs)

        # 이송 작업 테이블
        tasks = self._sort_tasks_by_priority(self._api.get_transport_tasks() or [])
        self._update_task_table(tasks)

        # 출고 지시
        self._update_outbound_table(self._api.get_outbound_orders())

        # KPI 계산
        self._update_kpis(amrs, tasks)

    def _update_kpis(
        self,
        amrs: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
    ) -> None:
        active_tasks = sum(1 for t in tasks if str(t.get("status", "")).lower() == "running")
        pending_tasks = sum(1 for t in tasks if str(t.get("status", "")).lower() == "pending")
        completed_tasks = sum(1 for t in tasks if str(t.get("status", "")).lower() == "completed")
        idle_amrs = sum(1 for a in amrs if str(a.get("status", "")).lower() == "idle")

        self._kpi_cards["active_tasks"].update_value(active_tasks)
        self._kpi_cards["pending_tasks"].update_value(pending_tasks)
        self._kpi_cards["completed_tasks"].update_value(completed_tasks)
        self._kpi_cards["idle_amr"].update_value(idle_amrs)

    def _update_amr_cards(self, amrs: list[dict[str, Any]]) -> None:
        existing_ids = set(self._amr_cards.keys())
        seen: set[str] = set()

        for amr in amrs:
            amr_id = str(amr.get("id", ""))
            if not amr_id:
                continue
            seen.add(amr_id)

            card = self._amr_cards.get(amr_id)
            if card is None:
                card = AmrStatusCard(amr_id)
                card.transition_requested.connect(self._on_amr_transition)
                card.repair_requested.connect(self._on_amr_repair)
                self._amr_cards[amr_id] = card
                self._amr_row.addWidget(card, stretch=1)
            card.update_from_dict(amr)

        # 사라진 AMR 제거
        for gone_id in existing_ids - seen:
            card = self._amr_cards.pop(gone_id, None)
            if card is not None:
                self._amr_row.removeWidget(card)
                card.deleteLater()

    @staticmethod
    def _sort_tasks_by_priority(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        status_order = {"running": 0, "pending": 1, "completed": 2, "failed": 3}
        return sorted(
            tasks,
            key=lambda t: (
                status_order.get(str(t.get("status", "")).lower(), 9),
                order.get(str(t.get("priority", "normal")).lower(), 9),
            ),
        )

    def _update_task_table(self, tasks: list[dict[str, Any]]) -> None:
        self._task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            # 우선순위 배지
            priority = str(task.get("priority", "normal")).lower()
            bg, fg, _, label = PRIORITY_STYLE.get(priority, PRIORITY_STYLE["normal"])
            prio_item = QTableWidgetItem(label)
            prio_item.setTextAlignment(Qt.AlignCenter)
            prio_item.setBackground(_brush(bg))
            prio_item.setForeground(_brush(fg))
            self._task_table.setItem(row, 0, prio_item)

            # ID
            self._task_table.setItem(row, 1, QTableWidgetItem(str(task.get("id", ""))))

            # 경로
            route = f"{task.get('from', '')} → {task.get('to', '')}"
            self._task_table.setItem(row, 2, QTableWidgetItem(route))

            # 화물
            self._task_table.setItem(row, 3, QTableWidgetItem(str(task.get("cargo", ""))))

            # AMR
            amr_item = QTableWidgetItem(str(task.get("amr", "")))
            amr_item.setTextAlignment(Qt.AlignCenter)
            self._task_table.setItem(row, 4, amr_item)

            # 상태
            status = str(task.get("status", "")).lower()
            status_item = QTableWidgetItem(STATUS_TEXT.get(status, status))
            status_item.setTextAlignment(Qt.AlignCenter)
            self._task_table.setItem(row, 5, status_item)

    def _update_outbound_table(self, orders: list[dict[str, Any]]) -> None:
        self._outbound_table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            self._outbound_table.setItem(row, 0, QTableWidgetItem(str(order.get("id", ""))))
            self._outbound_table.setItem(row, 1, QTableWidgetItem(str(order.get("product", ""))))
            qty_item = QTableWidgetItem(str(order.get("qty", 0)))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._outbound_table.setItem(row, 2, qty_item)
            self._outbound_table.setItem(row, 3, QTableWidgetItem(str(order.get("customer", ""))))
            policy_item = QTableWidgetItem(str(order.get("policy", "")))
            policy_item.setTextAlignment(Qt.AlignCenter)
            self._outbound_table.setItem(row, 4, policy_item)

            status = str(order.get("status", "")).lower()
            status_item = QTableWidgetItem(STATUS_TEXT.get(status, status))
            status_item.setTextAlignment(Qt.AlignCenter)
            self._outbound_table.setItem(row, 5, status_item)

    def _on_amr_transition(self, robot_id: str, new_state: int) -> None:
        """AMR 카드 상태 전이 버튼 클릭 → gRPC TransitionAmrState 호출."""
        try:
            from app.management_client import ManagementClient

            client = ManagementClient()
            accepted, reason = client.transition_amr_state(robot_id, new_state)
            client.close()
            if accepted:
                logger.info("AMR 전이 성공: %s → state=%d (%s)", robot_id, new_state, reason)
            else:
                logger.warning("AMR 전이 거부: %s → state=%d (%s)", robot_id, new_state, reason)
                QMessageBox.warning(self, "전이 거부", f"{robot_id}: {reason}")
        except Exception as exc:
            logger.exception("AMR 전이 실패: %s", exc)
            QMessageBox.critical(self, "오류", f"전이 요청 실패: {exc}")

    def _on_amr_repair(self, robot_id: str) -> None:
        """AMR 수리 완료 버튼 → FAILED→IDLE 전이 (DB 동기화)."""
        reply = QMessageBox.question(
            self,
            "수리 완료 확인",
            f"<b>{robot_id}</b>의 수리가 완료되었습니까?<br>"
            "상태가 <b>대기(IDLE)</b>로 전환되고 DB에 반영됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            from app.management_client import ManagementClient

            client = ManagementClient()
            # TaskState.IDLE = 1
            accepted, reason = client.transition_amr_state(robot_id, 1)
            client.close()
            if accepted:
                logger.info("AMR 수리 완료: %s → IDLE (%s)", robot_id, reason)
                QMessageBox.information(
                    self, "수리 완료", f"{robot_id}이(가) 대기 상태로 전환되었습니다."
                )
            else:
                logger.warning("AMR 수리 전이 거부: %s (%s)", robot_id, reason)
                QMessageBox.warning(self, "전이 거부", f"{robot_id}: {reason}")
        except Exception as exc:
            logger.exception("AMR 수리 전이 실패: %s", exc)
            QMessageBox.critical(self, "오류", f"수리 완료 요청 실패: {exc}")

    def update_amr_live(self, amr_list: list[dict[str, Any]]) -> None:
        """AMR 실시간 데이터(배터리 등) 수신 — 이후 refresh()에서도 이 데이터를 사용."""
        self._amr_live = amr_list
        self._update_amr_cards(amr_list)

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("type", "")
        if msg_type in (
            "amr_update",
            "transport_task_update",
            "outbound_update",
        ):
            self.refresh()


def _brush(color: str):
    """Color hex → QBrush (lazy import to avoid circular)."""
    from PyQt5.QtGui import QBrush, QColor

    return QBrush(QColor(color))
