"""품질 검사 모니터링 페이지 v0.5.

구성:
  1. KPI 4개 (조건부 색상 적용)
  2. 카메라 라이브 뷰 + 분류 다이얼 (가로 분할)
  3. TOP3 불량 배지 + 검사 기준 참조 패널
  4. 차트 3개 (불량률 추이 / 불량 분포 / 생산량 vs 불량)
  5. 검사 이력 테이블
"""

from __future__ import annotations

import logging
import os
from typing import Any

from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.pages.dashboard import KpiCard
from app.widgets.camera_view import CameraLiveView
from app.widgets.charts import (
    DefectRateChart,
    DefectTypeDistChart,
    ProductionVsDefectsChart,
)
from app.widgets.defect_panels import InspectionStandardsPanel, TopDefectsPanel
from app.widgets.sorter_dial import SorterCard

logger = logging.getLogger(__name__)

# Jetson 실시간 프레임 (Stage B: server streaming via CameraFrameWorker)
_LIVE_CAMERA_ID = os.environ.get("MGMT_IP_CAMERA_ID", "CAM-INSP-01")


class QualityPage(QWidget):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self._api = api
        self._kpis: dict[str, KpiCard] = {}
        self._frame_thread: QThread | None = None
        self._frame_worker = None  # type: ignore[var-annotated]
        self._build_ui()
        self.refresh()
        # Stage B — Server streaming worker
        self._start_frame_stream()

    def _start_frame_stream(self) -> None:
        try:
            from app.workers.camera_frame_worker import CameraFrameWorker
        except ImportError:
            logger.exception("CameraFrameWorker import 실패")
            return
        self._frame_thread = QThread(self)
        self._frame_worker = CameraFrameWorker(camera_id=_LIVE_CAMERA_ID)
        self._frame_worker.moveToThread(self._frame_thread)
        self._frame_worker.frame_received.connect(self._on_frame)
        self._frame_thread.started.connect(self._frame_worker.run)
        self._frame_thread.start()
        logger.info("CameraFrameWorker 기동: camera=%s", _LIVE_CAMERA_ID)

    def _on_frame(self, data: bytes, encoding: str, sequence: int, received_at: str) -> None:
        """worker 에서 signal 로 받은 프레임을 카메라 뷰에 반영 (메인 스레드)."""
        self._camera.set_frame_bytes(
            data=data,
            encoding=encoding,
            sequence=sequence,
            received_at=received_at,
        )

    def shutdown(self) -> None:
        """앱 종료 시 main_window 에서 호출 (없어도 daemon thread 라 프로세스 종료 시 정리됨)."""
        if self._frame_worker is not None:
            try:
                self._frame_worker.request_stop()
            except Exception:  # noqa: BLE001
                pass
        if self._frame_thread is not None:
            self._frame_thread.quit()
            self._frame_thread.wait(2000)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("품질 검사")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ===== KPI 4 카드 =====
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)
        metrics = [
            ("total", "검사 수", "건"),
            ("ok", "합격", "건"),
            ("ng", "불합격", "건"),
            ("rate", "불량률", "%"),
        ]
        for col, (key, label, unit) in enumerate(metrics):
            card = KpiCard(label, unit=unit)
            self._kpis[key] = card
            kpi_grid.addWidget(card, 0, col)
        layout.addLayout(kpi_grid)

        # ===== 카메라 뷰 + 분류 다이얼 + TOP3 + 기준 =====
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self._camera = CameraLiveView()
        top_row.addWidget(self._camera, stretch=3)

        self._sorter_card = SorterCard()
        top_row.addWidget(self._sorter_card, stretch=2)

        self._top_defects = TopDefectsPanel()
        top_row.addWidget(self._top_defects, stretch=2)

        self._standards = InspectionStandardsPanel()
        top_row.addWidget(self._standards, stretch=3)

        layout.addLayout(top_row, stretch=1)

        # ===== 차트 3개 =====
        chart_row = QHBoxLayout()
        chart_row.setSpacing(14)

        self._rate_chart = DefectRateChart()
        self._rate_chart.setMinimumHeight(220)
        chart_row.addWidget(self._rate_chart, stretch=2)

        self._pie_chart = DefectTypeDistChart()
        self._pie_chart.setMinimumHeight(220)
        chart_row.addWidget(self._pie_chart, stretch=1)

        self._vs_chart = ProductionVsDefectsChart()
        self._vs_chart.setMinimumHeight(220)
        chart_row.addWidget(self._vs_chart, stretch=2)

        layout.addLayout(chart_row, stretch=1)

        # ===== 검사 이력 테이블 =====
        section = QLabel("최근 검사 이력")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["이미지", "검사 시각", "제품", "결과", "불량 유형", "담당자", "비고"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setMaximumHeight(220)
        layout.addWidget(self._table)

        # ===== 검사 진행 중 (PROC) — 결과 입력 (Gap 5, 2026-04-27) =====
        proc_label = QLabel("검사 진행 중 (결과 입력 대기)")
        proc_label.setObjectName("sectionTitle")
        layout.addWidget(proc_label)

        self._proc_table = QTableWidget(0, 6)
        self._proc_table.setHorizontalHeaderLabels(
            ["txn_id", "item_id", "res", "시작 시각", "양품 (GP)", "불량 (DP)"]
        )
        self._proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._proc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._proc_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._proc_table.verticalHeader().setVisible(False)
        self._proc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._proc_table.setMaximumHeight(180)
        layout.addWidget(self._proc_table)

    def refresh(self) -> None:
        # KPI + 조건부 색상
        stats = self._api.get_defect_stats()
        if stats:
            total = stats.get("total", 0)
            ok = stats.get("ok", 0)
            ng = stats.get("ng", 0)
            rate = float(stats.get("defect_rate", 0))
            self._kpis["total"].update_value(total)
            self._kpis["ok"].update_value(ok)
            self._kpis["ng"].update_value(ng)
            self._kpis["rate"].update_value(f"{rate:.1f}")
            self._colorize_rate(rate)

        # 카메라 피드
        vision = self._api.get_vision_feed()
        if vision:
            self._camera.set_result(
                result=str(vision.get("result", "idle")),
                product_id=str(vision.get("product_id", "-")),
                confidence=float(vision.get("confidence", 0)),
                inspected_at=str(vision.get("inspected_at", "-")),
                defect_type=str(vision.get("defect_type", "")),
            )

        # 분류 다이얼
        sorter = self._api.get_sorter_state()
        if sorter:
            self._sorter_card.set_state(
                angle=sorter.get("angle"),
                direction=sorter.get("direction"),
                success=sorter.get("success"),
                count_good=sorter.get("count_good"),
                count_bad=sorter.get("count_bad"),
            )

        # TOP3 + 기준 + 차트
        defects = self._api.get_defect_type_dist()
        self._top_defects.update_data(defects)
        self._standards.update_data(self._api.get_inspection_standards())

        self._rate_chart.update_data(self._api.get_defect_rate_trend())
        self._pie_chart.update_data(defects)
        self._vs_chart.update_data(self._api.get_production_vs_defects())

        # 검사 이력 (이미지 플레이스홀더 컬럼 포함)
        inspections = self._api.get_quality_inspections() or []
        self._table.setRowCount(len(inspections))
        for row, item in enumerate(inspections[:200]):
            # 이미지 플레이스홀더 (결과에 따라 이모지 아이콘)
            result = str(item.get("result", ""))
            icon = "📷" if result == "OK" else ("⚠" if result == "NG" else "·")
            image_item = QTableWidgetItem(icon)
            image_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, image_item)

            self._table.setItem(row, 1, QTableWidgetItem(str(item.get("inspected_at", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(item.get("product", ""))))

            result_item = QTableWidgetItem(result)
            result_item.setTextAlignment(Qt.AlignCenter)
            if result == "NG":
                result_item.setForeground(QColor("#dc2626"))
            elif result == "OK":
                result_item.setForeground(QColor("#059669"))
            self._table.setItem(row, 3, result_item)
            self._table.setItem(row, 4, QTableWidgetItem(str(item.get("defect_type", ""))))
            self._table.setItem(row, 5, QTableWidgetItem(str(item.get("inspector", ""))))
            self._table.setItem(row, 6, QTableWidgetItem(str(item.get("note", ""))))

        # ===== 검사 진행 중 (insp_task_txn.txn_stat=PROC) — Gap 5 =====
        self._refresh_proc_table()

    def _refresh_proc_table(self) -> None:
        """진행 중 검사 row 만 골라 GP/DP 버튼 행으로 표시."""
        try:
            rows = self._api.get_inspection_tasks()
        except Exception:  # noqa: BLE001
            rows = []
        proc_rows = [r for r in rows if str(r.get("txn_stat", "")).upper() == "PROC"]
        # 최신 우선 정렬
        proc_rows.sort(key=lambda r: r.get("start_at") or r.get("req_at") or "", reverse=True)

        self._proc_table.setRowCount(len(proc_rows))
        for row, r in enumerate(proc_rows):
            txn_id = int(r.get("txn_id", 0))
            cells = [
                str(txn_id),
                str(r.get("item_id", "")),
                str(r.get("res_id", "") or ""),
                str(r.get("start_at", r.get("req_at", "")))[:19],
            ]
            for col, val in enumerate(cells):
                qi = QTableWidgetItem(val)
                qi.setTextAlignment(Qt.AlignCenter)
                self._proc_table.setItem(row, col, qi)

            gp_btn = QPushButton("✅ GP")
            gp_btn.setToolTip("양품 처리 → insp_task_txn.result=True, item.is_defective=False")
            gp_btn.clicked.connect(lambda _c, t=txn_id: self._complete_inspection(t, True))
            self._proc_table.setCellWidget(row, 4, gp_btn)

            dp_btn = QPushButton("⚠ DP")
            dp_btn.setToolTip("불량 처리 → insp_task_txn.result=False, item.is_defective=True")
            dp_btn.clicked.connect(lambda _c, t=txn_id: self._complete_inspection(t, False))
            self._proc_table.setCellWidget(row, 5, dp_btn)

    def _complete_inspection(self, txn_id: int, result: bool) -> None:
        """GP/DP 버튼 핸들러 — POST /api/quality/inspections/{txn}/result?result=…"""
        verdict = "양품 (GP)" if result else "불량 (DP)"
        confirm = QMessageBox.question(
            self,
            "검사 결과 확정",
            f"insp_task_txn={txn_id} 를 {verdict} 으로 처리하시겠습니까?\n\n"
            "✓ 확정 시 insp_task_txn SUCC + end_at + item.is_defective 갱신.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            rsp = self._api.complete_inspection(txn_id, result)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "검사 완료 실패", f"txn_id={txn_id}\n{exc}")
            return

        QMessageBox.information(
            self,
            "검사 완료",
            f"txn_id={txn_id}\n"
            f"  txn_stat = {rsp.get('txn_stat')}\n"
            f"  result = {verdict}\n"
            f"  end_at = {rsp.get('end_at')}\n\n"
            "→ 발주 관리 페이지에서 DONE/SHIP/COMP 진행하세요.",
        )
        self.refresh()

    def _colorize_rate(self, rate: float) -> None:
        """불량률에 따른 KPI 카드 색상 (기준: 2% 미만 녹색, 5% 미만 주황, 초과 빨강)."""
        card = self._kpis["rate"]
        if rate < 2.0:
            color = "#10b981"
        elif rate < 5.0:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        card.setStyleSheet(
            f"#kpiCard {{ border: 2px solid {color}; }}#kpiValue {{ color: {color}; }}"
        )

    def handle_ws_message(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("type", "")
        if msg_type in (
            "quality_update",
            "inspection_completed",
            "vision_result",
            "sorter_update",
        ):
            self.refresh()
