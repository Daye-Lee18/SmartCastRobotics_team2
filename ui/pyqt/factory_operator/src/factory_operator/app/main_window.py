"""QMainWindow - 좌측 사이드바 + 우측 스택 레이아웃."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from config import AMR_POLL_INTERVAL, APP_NAME, APP_VERSION, REFRESH_INTERVAL_MS

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.api_client import ApiClient
from app.pages.dashboard import DashboardPage
from app.pages.logistics import LogisticsPage
from app.pages.map import FactoryMapPage
from app.pages.pattern_control import PatternControlPage
from app.pages.operations import OperationsPage
from app.pages.pp_worker import PpWorkerPage
from app.pages.production import ProductionPage
from app.pages.quality import QualityPage
from app.pages.schedule import SchedulePage
from app.pages.storage import StoragePage
from app.widgets.alert_widgets import ToastNotification, _normalize_level

# 2026-04-27: '실시간 운영 모니터링' (operations) 은 발주/패턴/공정단계/Item 위치/핸드오프 통합 관리,
# '생산 모니터링' (production) 은 제어 패널 + 실시간 게이지 + 차트 (HW 직결 시각화) 전담.
NAV_ITEMS: list[tuple[str, str]] = [
    ("pattern_control", "패턴 위치 조작 및 생산 시작"),
    ("operations", "실시간 운영 모니터링"),
    ("pp_worker", "후처리 작업자"),
    ("dashboard", "대시보드"),
    ("map", "공장 맵"),
    ("production", "생산 모니터링"),
    ("schedule", "생산 계획"),
    ("quality", "품질 검사"),
    ("logistics", "물류 / 이송"),
    ("storage", "적재"),
]


class MainWindow(QMainWindow):
    """모니터링 앱 메인 윈도우."""

    def __init__(self, theme_manager=None) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(800, 600)
        self.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
        self.resize(1400, 900)

        self._api = ApiClient()
        self._amr_thread = None
        self._theme_manager = theme_manager  # ThemeManager (옵션 — main.py 가 주입)
        # 알림 중복 방지 (같은 critical 5초 내 재발행 차단). __init__ 에서 초기화 —
        # 2026-04-27: 이전엔 _build_ui 내부 dead-code 영역에 있어 실행되지 않아
        # _maybe_show_toast_for_alert 가 AttributeError 로 죽었던 버그 픽스.
        self._seen_alerts: set[str] = set()

        self._build_ui()
        self._install_extra_shortcuts()
        self._start_refresh_timer()
        self._start_alert_stream()
        self._start_amr_status()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 좌측 사이드바
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        self._sidebar = sidebar
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        logo = QLabel("주물공장 모니터링")
        logo.setObjectName("sidebarLogo")
        logo.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(logo)

        self._nav = QListWidget()
        self._nav.setObjectName("sidebarNav")
        for _, label in NAV_ITEMS:
            self._nav.addItem(QListWidgetItem(label))
        self._nav.currentRowChanged.connect(self._on_nav_changed)
        side_layout.addWidget(self._nav, stretch=1)

        # 사이드바 하단: 라이트/다크 테마 토글 + 버전
        if self._theme_manager is not None:
            theme_btn = QToolButton()
            theme_btn.setObjectName("sidebarThemeToggle")
            self._theme_btn = theme_btn
            theme_btn.setToolTip("라이트/다크 테마 전환")
            theme_btn.setCursor(Qt.PointingHandCursor)
            theme_btn.setAutoRaise(True)
            self._refresh_theme_btn_label()
            theme_btn.clicked.connect(self._on_theme_toggle)
            # 스타일은 글로벌 QSS (#sidebarThemeToggle) 가 처리
            side_layout.addWidget(theme_btn)
            self._theme_manager.theme_changed.connect(lambda _m: self._refresh_theme_btn_label())

        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setObjectName("sidebarVersion")
        version_lbl.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(version_lbl)

        root.addWidget(sidebar)

        # 사이드바 토글 바 (얇은 수직 버튼)
        self._sidebar_toggle = QToolButton()
        self._sidebar_toggle.setObjectName("sidebarToggle")
        self._sidebar_toggle.setCheckable(False)
        self._sidebar_toggle.setText("◀")
        self._sidebar_toggle.setToolTip("사이드바 숨기기/보이기 (Ctrl+B)")
        self._sidebar_toggle.setFixedWidth(16)
        self._sidebar_toggle.setCursor(Qt.PointingHandCursor)
        self._sidebar_toggle.setAutoRaise(True)
        # 스타일은 글로벌 QSS (#sidebarToggle) 가 처리
        self._sidebar_toggle.clicked.connect(self._toggle_sidebar)
        root.addWidget(self._sidebar_toggle)

        # 우측 스택 (NAV_ITEMS 순서와 반드시 일치)
        self._stack = QStackedWidget()
        self._pattern_control = PatternControlPage(self._api)  # NAV_ITEMS[0] — 수동 패턴/생산 시작
        self._operations = OperationsPage(self._api)  # NAV_ITEMS[1] — 실시간 운영 모니터링
        self._pp_worker = PpWorkerPage(self._api)  # NAV_ITEMS[2]
        self._dashboard = DashboardPage(self._api)
        self._map = FactoryMapPage(self._api)
        self._production = ProductionPage(self._api)  # NAV_ITEMS[5] — 생산 모니터링 (게이지/차트)
        self._schedule = SchedulePage(self._api)
        self._quality = QualityPage(self._api)
        self._logistics = LogisticsPage(self._api)
        self._storage = StoragePage(self._api)

        for page in (
            self._pattern_control,
            self._operations,
            self._pp_worker,
            self._dashboard,
            self._map,
            self._production,
            self._schedule,
            self._quality,
            self._logistics,
            self._storage,
        ):
            self._stack.addWidget(page)

        root.addWidget(self._stack, stretch=1)

        # 상태바
        status = QStatusBar()
        self.setStatusBar(status)

        # 좌측: 버전 안내
        hint = QLabel(f"v{APP_VERSION}  ·  F11 전체화면")
        hint.setProperty("tone", "muted")
        status.addWidget(hint)

        # 우측: 시계 + 연결 상태
        self._clock_label = QLabel("--:--:--")
        self._clock_label.setObjectName("statusBarClock")
        status.addPermanentWidget(self._clock_label)

        self._stream_status_label = QLabel("gRPC: ready")
        self._stream_status_label.setProperty("tone", "muted")
        status.addPermanentWidget(self._stream_status_label)

        # 시계 타이머 (1초)
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

        # 전체화면 단축키 F11
        self._fullscreen_action = QAction("전체화면 토글", self)
        self._fullscreen_action.setShortcut(QKeySequence("F11"))
        self._fullscreen_action.triggered.connect(self._toggle_fullscreen)
        self.addAction(self._fullscreen_action)

        # 테마 토글 단축키 Ctrl+Shift+T
        if self._theme_manager is not None:
            self._theme_action = QAction("테마 전환", self)
            self._theme_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
            self._theme_action.triggered.connect(self._on_theme_toggle)
            self.addAction(self._theme_action)

    # ---------- Theme toggle ----------
    def _refresh_theme_btn_label(self) -> None:
        if self._theme_manager is None or not hasattr(self, "_theme_btn"):
            return
        cur = self._theme_manager.resolved_mode()
        # 클릭 시 전환될 모드를 표시
        if cur == "light":
            self._theme_btn.setText("🌙  다크 모드")
        else:
            self._theme_btn.setText("☀️  라이트 모드")

    def _on_theme_toggle(self) -> None:
        if self._theme_manager is None:
            return
        self._theme_manager.toggle_light_dark()

    # ---------- 단축키 / 첫 페이지 설정 (기존 _on_theme_toggle 내부 dead code 였음 — 2026-04-27 픽스) ----------
    def _install_extra_shortcuts(self) -> None:
        """ESC, Ctrl+B, Ctrl+1..N 단축키 등록 + 첫 페이지 선택.

        2026-04-27: 이전엔 _on_theme_toggle 함수 내부에 들여쓰기되어
        테마 토글 시마다 단축키가 중복 등록 + 페이지가 0번으로 강제 이동.
        __init__ 에서 1회만 호출하도록 분리.
        """
        # ESC 로 전체화면 해제
        self._exit_fs_action = QAction("전체화면 나가기", self)
        self._exit_fs_action.setShortcut(QKeySequence("Escape"))
        self._exit_fs_action.triggered.connect(self._exit_fullscreen)
        self.addAction(self._exit_fs_action)

        # 사이드바 토글 단축키 Ctrl+B
        self._toggle_sidebar_action = QAction("사이드바 토글", self)
        self._toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self._toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        self.addAction(self._toggle_sidebar_action)

        # 페이지 단축키 Ctrl+1..N
        for i in range(len(NAV_ITEMS)):
            action = QAction(f"Page {i + 1}", self)
            action.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            action.triggered.connect(lambda _=False, idx=i: self._nav.setCurrentRow(idx))
            self.addAction(action)

        # 첫 페이지 선택
        self._nav.setCurrentRow(0)

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)
            page = self._stack.currentWidget()
            if hasattr(page, "refresh"):
                page.refresh()

    def _toggle_sidebar(self) -> None:
        """좌측 사이드바 표시/숨김 토글."""
        visible = self._sidebar.isVisible()
        self._sidebar.setVisible(not visible)
        self._sidebar_toggle.setText("▶" if visible else "◀")
        self._sidebar_toggle.setToolTip(
            "사이드바 보이기 (Ctrl+B)" if visible else "사이드바 숨기기 (Ctrl+B)"
        )

    # ---------- 주기 갱신 ----------
    def _start_refresh_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._refresh_current_page)
        self._timer.start()

    def _refresh_current_page(self) -> None:
        # 이전 refresh 가 아직 진행 중이면 중복 실행 방지 (메인 스레드 큐 폭주 방지)
        if getattr(self, "_refreshing", False):
            return
        page = self._stack.currentWidget()
        if not hasattr(page, "refresh"):
            return
        self._refreshing = True
        try:
            page.refresh()
        finally:
            self._refreshing = False

    # ---------- gRPC AlertStreamWorker (V6 canonical: Management 직결) ----------
    def _start_alert_stream(self) -> None:
        try:
            from app.workers.alert_stream_worker import AlertStreamThread, AlertStreamWorker
        except ImportError:
            return
        # severity_filter=None → 모든 severity 수신 (critical/warning/info).
        # critical 은 main_window 에서 모달, 그 외는 토스트.
        self._alert_worker = AlertStreamWorker(severity_filter=None)
        self._alert_worker.alert_event.connect(self._on_alert_event)
        self._alert_worker.connection_state.connect(self._on_alert_conn_state)
        self._alert_thread = AlertStreamThread(self._alert_worker)
        self._alert_thread.start()

    def _on_alert_event(
        self,
        alert_id: str,
        severity: str,
        error_code: str,
        message: str,
        equipment_id: str,
        zone: str,
        at_iso: str,
    ) -> None:
        """gRPC alert → severity 별 차별 표시.

        - critical: QMessageBox.critical (모달, 사용자 ack 필요)
        - warning/info/etc: 우상단 토스트 (5초 자동 사라짐)

        critical 모달 폭주 방지: 같은 alert_id 는 1회만 표시 (set 캐시).

        @MX:NOTE: AlertStreamWorker.pyqtSignal 의 슬롯. WebSocket 단종 대체 채널 (V6 Phase 8).
        @MX:REASON: critical 은 사용자 ack 보장 필요 (자동 사라짐 토스트로는 누락 가능).
        """
        import logging as _lg

        _lg.getLogger(__name__).info(
            "gRPC alert 수신: id=%s sev=%s code=%s msg=%s",
            alert_id[:24],
            severity,
            error_code,
            message[:50],
        )

        title_prefix = {"critical": "🚨 CRITICAL", "warning": "⚠ WARNING", "info": "ℹ INFO"}
        title = f"{title_prefix.get(severity, severity.upper())} {error_code or zone or ''}".strip()
        body = message or alert_id
        if equipment_id:
            body = f"{body}\n설비: {equipment_id}"

        if (severity or "").lower() == "critical":
            # 폭주 방지 — 같은 alert_id 는 모달 1회만
            if not hasattr(self, "_shown_critical_alerts"):
                self._shown_critical_alerts = set()
            if alert_id in self._shown_critical_alerts:
                return
            self._shown_critical_alerts.add(alert_id)
            # 캐시 크기 cap (오래된 것 정리)
            if len(self._shown_critical_alerts) > 200:
                self._shown_critical_alerts = set(list(self._shown_critical_alerts)[-100:])

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle(title)
            box.setText(body)
            if at_iso:
                box.setInformativeText(
                    f"발생 시각: {at_iso[:19].replace('T', ' ')}\nID: {alert_id}"
                )
            box.setStandardButtons(QMessageBox.Ok)
            # 중요: 메인 GUI 스레드에서 호출되므로 exec_() 로 모달 처리
            box.exec_()
            return

        # critical 외: 기존 토스트
        self.show_toast(severity, title, body)

    def _on_alert_conn_state(self, connected: bool) -> None:
        # AlertStream 연결 상태는 ws_status_label 우측에 작은 표시 (옵션)
        pass

    def _update_clock(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._clock_label.setText(now)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()

    def show_toast(self, level: str, title: str, message: str) -> None:
        """우상단 토스트 알림 (5초 자동 사라짐)."""
        toast = ToastNotification(self, level, title, message)
        toast.show()

    def _maybe_show_toast_for_alert(self, alert: dict[str, Any]) -> None:
        """critical/error 레벨 알림이면 토스트 표시 (중복 방지)."""
        level = _normalize_level(str(alert.get("level", "")))
        if level not in ("critical", "error"):
            return
        key = f"{alert.get('id', '')}-{alert.get('message', '')[:50]}"
        if key in self._seen_alerts:
            return
        self._seen_alerts.add(key)
        # 간단한 LRU: 최대 50개 유지
        if len(self._seen_alerts) > 50:
            self._seen_alerts.clear()
        self.show_toast(
            level=level,
            title=str(alert.get("source", "시스템")),
            message=str(alert.get("message", "")),
        )

    def _on_handoff_ack(self, payload: dict[str, Any]) -> None:
        """후처리존 인수인계 ACK 이벤트 — 상태바 메시지 + 로그.

        SPEC-AMR-001 FR-AMR-01-06: WebSocket `handoff.ack` 수신 시 Factory
        Operator 에게 AMR 해제 사실을 즉시 알린다.
        """
        task_id = payload.get("task_id") or "-"
        amr_id = payload.get("amr_id") or "-"
        zone = payload.get("zone") or "postprocessing"
        orphan = bool(payload.get("orphan"))
        source = payload.get("source") or "unknown"

        if orphan:
            msg = f"⚠ handoff.ack (orphan) — zone={zone} source={source}"
        else:
            msg = f"✓ handoff.ack — {zone}: task={task_id} amr={amr_id} (source={source})"

        logger.info("WS handoff.ack: %s", msg)
        if hasattr(self, "statusBar"):
            self.statusBar().showMessage(msg, 8000)  # 8초 노출

    # ---------- AMR 실시간 배터리 (gRPC → Management Service) ----------
    def _start_amr_status(self) -> None:
        try:
            from app.workers.amr_status_worker import (
                AmrStatusThread,
                AmrStatusWorker,
            )
        except ImportError:
            return
        self._amr_worker = AmrStatusWorker(poll_interval=AMR_POLL_INTERVAL)
        self._amr_worker.status_updated.connect(self._on_amr_status)
        self._amr_thread = AmrStatusThread(self._amr_worker)
        self._amr_thread.start()

    def _on_amr_status(self, amr_list: list) -> None:
        """AMR 실시간 데이터를 logistics 페이지에 직접 반영."""
        self._logistics.update_amr_live(amr_list)

    # ---------- 종료 ----------
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._amr_thread is not None:
            try:
                self._amr_thread.shutdown()
            except Exception:  # noqa: BLE001
                pass
        super().closeEvent(event)
