"""ThemeManager — 시스템 다크모드 감지 + QSettings 영속화 + 런타임 토글.

사용 예:
    from app.styles import ThemeManager
    tm = ThemeManager()
    tm.apply()                  # QApplication.instance() 에 현재 모드로 QSS 적용
    tm.set_mode("dark")         # 사용자 명시 다크
    tm.set_mode("system")       # 시스템 모드 따라가기
    tm.theme_changed.connect(on_change)  # 테마 변화 시 시그널
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QApplication

try:
    import darkdetect  # type: ignore

    _DARKDETECT_OK = True
except ImportError:  # pragma: no cover
    darkdetect = None  # type: ignore
    _DARKDETECT_OK = False

from app.styles.builder import build_qss
from app.styles.tokens import DARK, LIGHT, Tokens

log = logging.getLogger(__name__)

VALID_MODES = ("system", "light", "dark")


class ThemeManager(QObject):
    """앱 전역 테마 매니저. 싱글톤 권장 (main 에서 1회 생성).

    Signals:
        theme_changed(str)  — 적용된 모드 ("light" | "dark") 가 바뀔 때 emit.
    """

    theme_changed = pyqtSignal(str)

    _ORG = "SmartCastRobotics"
    _APP = "MonitoringApp"

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(self._ORG, self._APP)
        raw_mode = self._settings.value("theme/mode", "system")
        mode = raw_mode if isinstance(raw_mode, str) else "system"
        self._mode: str = mode if mode in VALID_MODES else "system"
        self._last_resolved: str | None = None
        log.info("ThemeManager init: mode=%s darkdetect=%s", self._mode, _DARKDETECT_OK)

    @property
    def mode(self) -> str:
        return self._mode

    def resolved_mode(self) -> str:
        if self._mode == "system":
            return self._detect_system_mode()
        return self._mode

    def current_tokens(self) -> Tokens:
        return DARK if self.resolved_mode() == "dark" else LIGHT

    def apply(self, app: QApplication | None = None) -> None:
        app_ = app or QApplication.instance()
        if app_ is None:
            log.warning("ThemeManager.apply: QApplication 없음 — 무시")
            return

        try:
            app_.setStyle("Fusion")
        except Exception:  # noqa: BLE001
            pass

        tokens = self.current_tokens()
        qss = build_qss(tokens)
        app_.setStyleSheet(qss)

        resolved = self.resolved_mode()
        if resolved != self._last_resolved:
            self._last_resolved = resolved
            log.info("Theme applied: mode=%s resolved=%s", self._mode, resolved)
            self.theme_changed.emit(resolved)

    def set_mode(self, mode: str, *, persist: bool = True) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"invalid mode: {mode!r} (expected one of {VALID_MODES})")
        if mode == self._mode and self._last_resolved == self.resolved_mode():
            return
        self._mode = mode
        if persist:
            self._settings.setValue("theme/mode", mode)
        self.apply()

    def toggle_light_dark(self) -> None:
        cur = self.resolved_mode()
        self.set_mode("dark" if cur == "light" else "light")

    def _detect_system_mode(self) -> str:
        if not _DARKDETECT_OK or darkdetect is None:
            return "light"
        try:
            theme = darkdetect.theme()
        except Exception:  # noqa: BLE001
            return "light"
        if isinstance(theme, str) and theme.lower() == "dark":
            return "dark"
        return "light"
