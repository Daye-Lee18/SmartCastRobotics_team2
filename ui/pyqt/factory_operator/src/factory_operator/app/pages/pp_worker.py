"""후처리 작업자 화면 (Post-Processing Worker) — 2026-04-26.

시나리오 (사용자 요청):
  1. AMR 이 ToPP 로 도착하면 작업자가 "후처리 ACK" 버튼을 누른다 → handoff
  2. 작업자가 RFID 리더기로 주물을 스캔 → item_id + 필요 후처리 옵션 표시
  3. 후처리 작업 완료 + RFID 부착 후 컨베이어 TOF1 진입 → 후처리 SUCC + 검사 라인 진입
  4. 컨베이어 TOF2 도달 → ToINSP 종료 + 검사 시작

본 페이지는 위 4단계를 GUI 버튼 4개로 시뮬레이션한다. 실 HW 가 붙으면
아래 버튼들은 해당 이벤트의 도착에 의해 자동 트리거되도록 교체된다.

레이아웃:
  ┌──── 상단 컨트롤 (가로 한 줄) ────────────────────────────────────────┐
  │  RFID payload [ ____________ ]  [핸드오프 ACK] [RFID 스캔]            │
  │  [TOF1 진입]   [TOF2 도달]   상태: ...                               │
  └──────────────────────────────────────────────────────────────────────┘
  ┌──── 본문 ───────────────────────────────────────────────────────────┐
  │  item 정보 (item_id / cur_stat / equip_task_type / cur_res / ord_id) │
  ├─────────────────────────────────────────────────────────────────────┤
  │  후처리 옵션 표 (pp_nm / extra_cost / 진행 상태)                    │
  └─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient


class PpWorkerPage(QWidget):
    """후처리 작업자 시뮬 화면 — 핸드오프 / RFID / TOF1 / TOF2."""

    refresh_requested = pyqtSignal()

    def __init__(self, api: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._api = api
        self._current_item_id: int | None = None
        self._current_payload: str = ""
        self._build_ui()

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- 작업자 로그인 (작업 3) ----
        login_box = QGroupBox("작업자 로그인")
        login_grid = QGridLayout(login_box)
        login_grid.addWidget(QLabel("이메일:"), 0, 0)
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("operator@example.com")
        self._email_edit.setMinimumWidth(280)
        login_grid.addWidget(self._email_edit, 0, 1)

        self._btn_login = QPushButton("로그인")
        self._btn_login.clicked.connect(self._on_login)
        login_grid.addWidget(self._btn_login, 0, 2)

        self._btn_logout = QPushButton("로그아웃")
        self._btn_logout.clicked.connect(self._on_logout)
        login_grid.addWidget(self._btn_logout, 0, 3)

        self._operator_label = QLabel("현재: 비로그인")
        self._operator_label.setProperty("tone", "muted")
        login_grid.addWidget(self._operator_label, 0, 4)
        login_grid.setColumnStretch(4, 1)

        root.addWidget(login_box)

        # ---- 상단 컨트롤 ----
        ctrl_box = QGroupBox("후처리 작업자 컨트롤 (시뮬)")
        grid = QGridLayout(ctrl_box)
        grid.setSpacing(8)

        grid.addWidget(QLabel("RFID payload:"), 0, 0)
        self._payload_edit = QLineEdit()
        self._payload_edit.setPlaceholderText("order_17_item_20260417_7")
        self._payload_edit.setMinimumWidth(320)
        grid.addWidget(self._payload_edit, 0, 1)

        self._btn_handoff = QPushButton("① 핸드오프 ACK (버튼)")
        self._btn_handoff.clicked.connect(self._on_handoff_ack)
        grid.addWidget(self._btn_handoff, 0, 2)

        self._btn_scan = QPushButton("② RFID 스캔")
        self._btn_scan.clicked.connect(self._on_rfid_scan)
        grid.addWidget(self._btn_scan, 0, 3)

        self._btn_tof1 = QPushButton("③ 컨베이어 TOF1 진입")
        self._btn_tof1.clicked.connect(self._on_tof1)
        grid.addWidget(self._btn_tof1, 1, 2)

        self._btn_tof2 = QPushButton("④ 컨베이어 TOF2 도달 (검사 시작)")
        self._btn_tof2.clicked.connect(self._on_tof2)
        grid.addWidget(self._btn_tof2, 1, 3)

        self._status_label = QLabel("")
        self._status_label.setProperty("tone", "muted")
        self._status_label.setWordWrap(True)
        grid.addWidget(self._status_label, 2, 0, 1, 4)

        root.addWidget(ctrl_box)

        # ---- item 정보 ----
        item_box = QGroupBox("선택 item 정보")
        item_grid = QGridLayout(item_box)
        item_grid.setSpacing(6)
        self._item_labels: dict[str, QLabel] = {}
        for row, key, label in [
            (0, "item_id", "item_id"),
            (0, "ord_id", "ord_id"),
            (1, "cur_stat", "현재 공정 (cur_stat)"),
            (1, "equip_task_type", "equip_task_type"),
            (2, "cur_res", "점유 자원 (cur_res)"),
            (2, "is_defective", "불량 여부"),
        ]:
            cell_label = QLabel(f"{label}:")
            cell_label.setObjectName("itemFieldLabel")
            cell_value = QLabel("-")
            cell_value.setProperty("tone", "primary")
            self._item_labels[key] = cell_value
            col = 0 if label.startswith(("item_id", "현재", "점유")) else 2
            item_grid.addWidget(cell_label, row, col)
            item_grid.addWidget(cell_value, row, col + 1)

        root.addWidget(item_box)

        # ---- 후처리 옵션 표 ----
        opts_box = QGroupBox("필요 후처리 옵션 (정의 + 진행 현황)")
        opts_v = QVBoxLayout(opts_box)
        self._opts_table = QTableWidget(0, 5)
        self._opts_table.setHorizontalHeaderLabels(
            ["pp_id", "pp_nm", "extra_cost", "txn_stat", "txn_id"]
        )
        self._opts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._opts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._opts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._opts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        opts_v.addWidget(self._opts_table)

        root.addWidget(opts_box, 1)

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _set_status(self, msg: str, ok: bool = True) -> None:
        # tone 변경 시 QSS 재계산을 위해 unpolish/polish 트리거
        self._status_label.setProperty("tone", "ok" if ok else "danger")
        style = self._status_label.style()
        if style is not None:
            style.unpolish(self._status_label)
            style.polish(self._status_label)
        self._status_label.setText(msg)

    def _payload(self) -> str:
        return (self._payload_edit.text() or "").strip()

    # ---- 로그인 ----
    def _on_login(self) -> None:
        email = (self._email_edit.text() or "").strip()
        if not email:
            self._set_status("이메일 입력 필요", ok=False)
            return
        try:
            r = self._api.auth_lookup(email)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "로그인 실패", str(exc))
            self._set_status(f"로그인 실패: {exc}", ok=False)
            self._operator_label.setText("현재: 비로그인")
            return
        if not r:
            self._set_status("응답 없음", ok=False)
            return
        self._operator_label.setText(f"현재: {self._api.current_operator_label()}")
        self._set_status(
            f"로그인 OK — user_id={r.get('user_id')} 이후 후처리 작업은 자동으로 operator_id 기록"
        )

    def _on_logout(self) -> None:
        self._api.__init_operator__()
        self._api._operator = None  # noqa: SLF001
        self._operator_label.setText("현재: 비로그인")
        self._set_status("로그아웃 완료")

    def _on_handoff_ack(self) -> None:
        try:
            r = self._api.post_handoff_ack()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "핸드오프 실패", str(exc))
            self._set_status(f"핸드오프 실패: {exc}", ok=False)
            return
        if not r:
            self._set_status("핸드오프 응답 없음 (서버 또는 mock_only 모드)", ok=False)
            return
        if r.get("released"):
            ord_id = r.get("ord_id")
            item_id = r.get("item_id")
            self._set_status(
                f"① 핸드오프 OK — AMR={r.get('amr_id')} item_id={item_id} "
                f"ord_id={ord_id} pp_task QUE={r.get('pp_task_txn_ids')} → "
                f"item.cur_stat={r.get('item_cur_stat')}"
            )
            # payload 자동 채움
            if item_id and ord_id:
                self._payload_edit.setText(f"order_{ord_id}_item_20260417_{item_id}")
            self._current_item_id = item_id
        else:
            self._set_status(
                f"① 핸드오프 orphan — 대기 AMR 없음 (reason={r.get('reason')})",
                ok=False,
            )

    def _on_rfid_scan(self) -> None:
        payload = self._payload()
        if not payload:
            self._set_status("RFID payload 입력 필요 (예: order_17_item_20260417_7)", ok=False)
            return
        try:
            r = self._api.post_sim_rfid_scan(payload)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "RFID 스캔 실패", str(exc))
            self._set_status(f"② RFID 스캔 실패: {exc}", ok=False)
            return
        if not r:
            self._set_status("② RFID 응답 없음", ok=False)
            return
        self._current_payload = payload
        if r.get("matched"):
            item = r.get("item") or {}
            self._render_item(item)
            self._render_options(r.get("pp_options") or [])
            self._current_item_id = item.get("item_id")
            self._set_status(
                f"② RFID 매칭 OK — item_id={item.get('item_id')} "
                f"cur_stat={item.get('cur_stat')} 옵션={len(r.get('pp_options') or [])}건"
            )
        else:
            self._set_status(
                f"② RFID 매칭 실패 — parse_status={r.get('parse_status')} reason={r.get('reason')}",
                ok=False,
            )

    def _on_tof1(self) -> None:
        payload = self._payload()
        try:
            r = self._api.post_sim_conveyor_tof1(
                res_id="CONV-01",
                rfid_payload=payload or None,
                item_id=self._current_item_id,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "TOF1 실패", str(exc))
            self._set_status(f"③ TOF1 실패: {exc}", ok=False)
            return
        if not r:
            self._set_status("③ TOF1 응답 없음", ok=False)
            return
        self._set_status(
            f"③ TOF1 진입 OK — item_id={r.get('item_id')} "
            f"cur_stat={r.get('item_cur_stat')} pp_succ={r.get('pp_task_txn_succ')} "
            f"equip_task_id={r.get('equip_task_txn_id')}"
        )
        # 화면 갱신: lookup 으로 최신 상태 가져오기
        if payload:
            self._refresh_lookup(payload)

    def _on_tof2(self) -> None:
        payload = self._payload()
        try:
            r = self._api.post_sim_conveyor_tof2(
                res_id="CONV-01",
                item_id=self._current_item_id,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "TOF2 실패", str(exc))
            self._set_status(f"④ TOF2 실패: {exc}", ok=False)
            return
        if not r:
            self._set_status("④ TOF2 응답 없음", ok=False)
            return
        self._set_status(
            f"④ TOF2 도달 OK — item_id={r.get('item_id')} "
            f"cur_stat={r.get('item_cur_stat')} insp_task_id={r.get('insp_task_txn_id')}"
        )
        if payload:
            self._refresh_lookup(payload)

    def _refresh_lookup(self, payload: str) -> None:
        try:
            r = self._api.lookup_item_by_rfid(payload)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"lookup 실패: {exc}", ok=False)
            return
        if not r:
            return
        self._render_item(r.get("item") or {})
        self._render_options(r.get("pp_options") or [])

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def _render_item(self, item: dict[str, Any]) -> None:
        for key, lbl in self._item_labels.items():
            v = item.get(key)
            lbl.setText("-" if v is None else str(v))

    def _render_options(self, options: list[dict[str, Any]]) -> None:
        self._opts_table.setRowCount(len(options))
        for r, opt in enumerate(options):
            cells = [
                str(opt.get("pp_id", "")),
                str(opt.get("pp_nm", "")),
                "-" if opt.get("extra_cost") is None else f"{int(opt['extra_cost']):,}",
                str(opt.get("txn_stat") or "-"),
                str(opt.get("txn_id") or "-"),
            ]
            for c, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                cell.setTextAlignment(Qt.AlignCenter)
                if c == 3:  # txn_stat
                    if opt.get("txn_stat") == "SUCC":
                        cell.setForeground(Qt.darkGreen)
                    elif opt.get("txn_stat") == "FAIL":
                        cell.setForeground(Qt.red)
                self._opts_table.setItem(r, c, cell)
